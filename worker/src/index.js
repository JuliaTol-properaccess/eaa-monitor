/**
 * EAA Monitor — bezwaar-Worker
 *
 * Verwerkt bezwaren tegen vermelding automatisch, met domein-verificatie als
 * misbruikbescherming. Een webshop kan alleen automatisch verwijderd worden als
 * iemand op het webshop-domein zelf de bevestigingslink aanklikt. Lukt dat niet
 * (e-mailadres staat niet op het domein), dan gaat het bezwaar naar Julia voor
 * een handmatige check, precies zoals het nu al gaat.
 *
 * Routes:
 *   POST /submit                 — ontvangt het bezwaarformulier, valideert, stuurt bevestigingsmail
 *   GET  /confirm                — verifieert de getekende token en opent een PR op objections.json
 *   POST /feedback               — feedback op een kennisbank-artikel, mailt Julia rechtstreeks
 *   POST /vraag                  — anonieme EAA-vraag voor de toezichthouder, mailt Julia rechtstreeks
 *   POST /newsletter             — nieuwsbrief-opt-in, stuurt een bevestigingsmail (dubbele opt-in)
 *   GET  /newsletter/confirm     — bevestigt de inschrijving en slaat het adres op in KV
 *   GET  /newsletter/unsubscribe — meldt het adres af en verwijdert het uit KV
 *
 * Bezwaar, feedback en vraag hebben geen database nodig: de bevestigingslink
 * draagt een HMAC-getekende token met alle gegevens. Na bevestiging opent de
 * Worker een pull request; Julia keurt die met één klik goed. De actie is
 * idempotent (al vermelde webshops en al ingediende bezwaren worden overgeslagen).
 *
 * De nieuwsbrief gebruikt wél opslag: bevestigde adressen komen in de KV-namespace
 * NEWSLETTER. Ook hier is de bevestigingslink een getekende token, dus pas na de
 * dubbele opt-in wordt een adres opgeslagen.
 *
 * Vereiste secrets (via `wrangler secret put`):
 *   SIGNING_SECRET  — willekeurige string voor de HMAC-handtekening
 *   GITHUB_TOKEN    — fine-grained PAT met Contents + Pull requests: read & write
 *
 * Vereiste vars en bindings (wrangler.jsonc): zie dat bestand (incl. KV NEWSLETTER).
 */

const TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000; // bevestigingslink 7 dagen geldig

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return withCors(env, new Response(null, { status: 204 }));
    }
    if (url.pathname === "/submit" && request.method === "POST") {
      return withCors(env, await handleSubmit(request, env));
    }
    if (url.pathname === "/feedback" && request.method === "POST") {
      return withCors(env, await handleFeedback(request, env));
    }
    if (url.pathname === "/vraag" && request.method === "POST") {
      return withCors(env, await handleVraag(request, env));
    }
    if (url.pathname === "/confirm" && request.method === "GET") {
      return handleConfirm(request, env, url);
    }
    if (url.pathname === "/newsletter" && request.method === "POST") {
      return withCors(env, await handleNewsletter(request, env));
    }
    if (url.pathname === "/newsletter/confirm" && request.method === "GET") {
      return handleNewsletterConfirm(request, env, url);
    }
    if (url.pathname === "/newsletter/unsubscribe" && request.method === "GET") {
      return handleNewsletterUnsubscribe(request, env, url);
    }
    return new Response("Not found", { status: 404 });
  },
};

// ── /submit ──────────────────────────────────────────────────────────────

async function handleSubmit(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Ongeldige aanvraag." }, 400);
  }

  // Honeypot: bots vullen dit verborgen veld; doe alsof het lukte, doe niets.
  if ((form.get("_gotcha") || "").trim() !== "") {
    return json({ ok: true, mode: "verify" });
  }

  const name = (form.get("bedrijfsnaam") || "").trim();
  const webadres = (form.get("webadres") || "").trim();
  const email = (form.get("email") || "").trim();
  const toelichting = (form.get("toelichting") || "").trim();
  const declared = {
    under_10_fte: form.get("verklaring_minder_dan_10_medewerkers") === "ja",
    under_2m_turnover: form.get("verklaring_omzet_onder_2_miljoen") === "ja",
    b2b_only: form.get("verklaring_uitsluitend_b2b") === "ja",
  };

  if (!name || !webadres || !email) {
    return json({ ok: false, error: "Vul je bedrijfsnaam, webadres en e-mailadres in." }, 422);
  }
  if (!isValidEmail(email)) {
    return json({ ok: false, error: "Dit lijkt geen geldig e-mailadres." }, 422);
  }
  const webHost = hostFromUrl(webadres);
  if (!webHost) {
    return json({ ok: false, error: "Dit lijkt geen geldig webadres. Begin met https://" }, 422);
  }
  if (!declared.under_10_fte || !declared.under_2m_turnover || !declared.b2b_only) {
    return json(
      { ok: false, error: "Je kunt alleen bezwaar maken als je alle drie de verklaringen aanvinkt." },
      422
    );
  }

  const webDomain = registrableDomain(webHost);
  const emailDomain = registrableDomain(email.split("@")[1] || "");

  // Domein-verificatie: alleen wie mail ontvangt op het webshop-domein kan
  // automatisch bevestigen. Anders: handmatige route via Julia.
  if (webDomain && emailDomain && webDomain === emailDomain) {
    const payload = {
      name,
      url: webadres,
      email,
      declared,
      exp: Date.now() + TOKEN_TTL_MS,
    };
    const token = await signToken(env, payload);
    const origin = new URL(request.url).origin;
    const confirmUrl = `${origin}/confirm?token=${encodeURIComponent(token)}`;

    try {
      await sendConfirmationEmail(env, { name, email, webadres, confirmUrl });
    } catch (err) {
      console.error("Bevestigingsmail mislukt:", err && err.message);
      return json(
        { ok: false, error: "We konden de bevestigingsmail niet versturen. Probeer het later opnieuw of mail naar info@eaa-monitor.nl." },
        502
      );
    }
    return json({ ok: true, mode: "verify", email });
  }

  // Geen domeinmatch: stuur door naar Julia voor handmatige verwerking.
  try {
    await sendManualReviewEmail(env, { name, webadres, email, declared, toelichting, webDomain, emailDomain });
  } catch (err) {
    console.error("Notificatiemail mislukt:", err && err.message);
    return json(
      { ok: false, error: "Er ging iets mis bij het versturen. Probeer het later opnieuw of mail naar info@eaa-monitor.nl." },
      502
    );
  }
  return json({ ok: true, mode: "manual" });
}

// ── /feedback ──────────────────────────────────────────────────────────────

async function handleFeedback(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Ongeldige aanvraag." }, 400);
  }

  // Honeypot: bots vullen dit verborgen veld; doe alsof het lukte, doe niets.
  if ((form.get("_gotcha") || "").trim() !== "") {
    return json({ ok: true });
  }

  const bericht = (form.get("bericht") || "").trim();
  const email = (form.get("email") || "").trim();
  const artikel = (form.get("artikel_titel") || "").trim();
  const artikelUrl = (form.get("artikel_url") || "").trim();

  if (!bericht) {
    return json({ ok: false, error: "Schrijf even waar het om gaat voordat je verstuurt." }, 422);
  }
  if (bericht.length > 4000) {
    return json({ ok: false, error: "Je bericht is te lang. Houd het onder de 4000 tekens." }, 422);
  }
  if (email && !isValidEmail(email)) {
    return json({ ok: false, error: "Dit lijkt geen geldig e-mailadres." }, 422);
  }

  try {
    await sendFeedbackEmail(env, { bericht, email, artikel, artikelUrl });
  } catch (err) {
    console.error("Feedbackmail mislukt:", err && err.message);
    return json(
      { ok: false, error: "Er ging iets mis bij het versturen. Probeer het later opnieuw of mail naar info@eaa-monitor.nl." },
      502
    );
  }
  return json({ ok: true });
}

// ── /vraag ───────────────────────────────────────────────────────────────────

async function handleVraag(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Ongeldige aanvraag." }, 400);
  }

  // Honeypot: bots vullen dit verborgen veld; doe alsof het lukte, doe niets.
  if ((form.get("_gotcha") || "").trim() !== "") {
    return json({ ok: true });
  }

  const vraag = (form.get("vraag") || "").trim();
  const email = (form.get("email") || "").trim();
  const sector = (form.get("sector") || "").trim();

  if (!vraag) {
    return json({ ok: false, error: "Schrijf je vraag voordat je verstuurt." }, 422);
  }
  if (vraag.length > 4000) {
    return json({ ok: false, error: "Je vraag is te lang. Houd het onder de 4000 tekens." }, 422);
  }
  if (email && !isValidEmail(email)) {
    return json({ ok: false, error: "Dit lijkt geen geldig e-mailadres." }, 422);
  }

  try {
    await sendVraagEmail(env, { vraag, email, sector });
  } catch (err) {
    console.error("Vraagmail mislukt:", err && err.message);
    return json(
      { ok: false, error: "Er ging iets mis bij het versturen. Probeer het later opnieuw of mail naar vragen@eaa-monitor.nl." },
      502
    );
  }
  return json({ ok: true });
}

// ── /confirm ─────────────────────────────────────────────────────────────

async function handleConfirm(request, env, url) {
  const token = url.searchParams.get("token") || "";
  const payload = await verifyToken(env, token);

  if (!payload) {
    return htmlPage(
      "Link ongeldig of verlopen",
      `<p>Deze bevestigingslink is niet geldig of is verlopen. Vraag de verwijdering opnieuw aan via het
       <a href="https://eaa-monitor.nl/bezwaar.html">bezwaarformulier</a>.</p>`,
      400
    );
  }

  const entry = {
    name: payload.name,
    url: payload.url,
    date: todayISO(),
    declared: payload.declared,
  };

  let result;
  try {
    result = await createObjectionPR(env, entry);
  } catch (err) {
    console.error("Bezwaar-PR aanmaken mislukt:", err && err.message);
    return htmlPage(
      "Er ging iets mis",
      `<p>We konden je bezwaar nu niet verwerken. Probeer de link later opnieuw, of mail naar
       <a href="mailto:info@eaa-monitor.nl">info@eaa-monitor.nl</a>.</p>`,
      502
    );
  }

  let body;
  if (result.status === "already_listed") {
    body = `<p><strong>Je webshop is al verwijderd.</strong></p>
            <p>Er hoeft niets meer te gebeuren. Je vindt je bezwaar terug op de
            <a href="https://eaa-monitor.nl/bezwaren.html">pagina met ingediende bezwaren</a>.</p>`;
  } else if (result.status === "already_submitted") {
    body = `<p><strong>Je verzoek is al ingediend.</strong></p>
            <p>We hebben je eerdere bevestiging al ontvangen. Het wacht op een laatste controle en wordt
            daarna verwerkt.</p>`;
  } else {
    body = `<p><strong>Bedankt, je verwijdering is bevestigd.</strong></p>
            <p>Je verzoek is ingediend. Na een laatste controle, meestal binnen een paar dagen, halen we je
            webshop uit het dashboard. Je vindt je bezwaar daarna terug op de
            <a href="https://eaa-monitor.nl/bezwaren.html">pagina met ingediende bezwaren</a>.</p>`;
  }

  return htmlPage("Bezwaar bevestigd", body, 200);
}

// ── Nieuwsbrief: opt-in met dubbele bevestiging ────────────────────────────

const NEWSLETTER_UNSUB_TTL_MS = 365 * 24 * 60 * 60 * 1000; // afmeldlink een jaar geldig

async function handleNewsletter(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Ongeldige aanvraag." }, 400);
  }

  // Honeypot: bots vullen dit verborgen veld; doe alsof het lukte, doe niets.
  if ((form.get("_gotcha") || "").trim() !== "") {
    return json({ ok: true, mode: "verify" });
  }

  const email = (form.get("email") || "").trim().toLowerCase();
  if (!email || !isValidEmail(email)) {
    return json({ ok: false, error: "Dit lijkt geen geldig e-mailadres." }, 422);
  }

  // Pas na bevestiging opslaan (dubbele opt-in). De link draagt een getekende
  // token met het e-mailadres, dus tot dan slaan we niets op.
  const token = await signToken(env, { email, type: "newsletter", exp: Date.now() + TOKEN_TTL_MS });
  const origin = new URL(request.url).origin;
  const confirmUrl = `${origin}/newsletter/confirm?token=${encodeURIComponent(token)}`;

  try {
    await sendNewsletterConfirmEmail(env, { email, confirmUrl });
  } catch (err) {
    console.error("Nieuwsbrief-bevestigingsmail mislukt:", err && err.message);
    return json(
      { ok: false, error: "We konden de bevestigingsmail niet versturen. Probeer het later opnieuw." },
      502
    );
  }
  return json({ ok: true, mode: "verify" });
}

async function handleNewsletterConfirm(request, env, url) {
  const payload = await verifyNewsletterToken(env, url.searchParams.get("token") || "", "newsletter");
  if (!payload) {
    return htmlPage(
      "Link ongeldig of verlopen",
      `<p>Deze bevestigingslink is niet geldig of is verlopen. Schrijf je opnieuw in via de
       nieuwsbrief onderaan <a href="https://eaa-monitor.nl/">eaa-monitor.nl</a>.</p>`,
      400
    );
  }

  try {
    await env.NEWSLETTER.put(
      `sub:${payload.email}`,
      JSON.stringify({ email: payload.email, confirmed_at: todayISO() })
    );
  } catch (err) {
    console.error("Nieuwsbrief opslaan mislukt:", err && err.message);
    return htmlPage(
      "Er ging iets mis",
      `<p>We konden je inschrijving nu niet opslaan. Probeer de link later opnieuw, of mail naar
       <a href="mailto:info@eaa-monitor.nl">info@eaa-monitor.nl</a>.</p>`,
      502
    );
  }

  const unsubToken = await signToken(env, {
    email: payload.email,
    type: "newsletter-unsub",
    exp: Date.now() + NEWSLETTER_UNSUB_TTL_MS,
  });
  const unsubUrl = `${new URL(request.url).origin}/newsletter/unsubscribe?token=${encodeURIComponent(unsubToken)}`;

  return htmlPage(
    "Inschrijving bevestigd",
    `<p><strong>Bedankt, je bent ingeschreven voor de nieuwsbrief.</strong></p>
     <p>Je krijgt af en toe een update over de EAA. Afmelden kan altijd via de link onderaan elke
        nieuwsbrief, of <a href="${escapeHtml(unsubUrl)}">nu meteen</a>.</p>`,
    200
  );
}

async function handleNewsletterUnsubscribe(request, env, url) {
  const payload = await verifyNewsletterToken(env, url.searchParams.get("token") || "", "newsletter-unsub");
  if (!payload) {
    return htmlPage(
      "Link ongeldig of verlopen",
      `<p>Deze afmeldlink is niet geldig of is verlopen. Mail anders naar
       <a href="mailto:info@eaa-monitor.nl">info@eaa-monitor.nl</a>, dan halen we je er handmatig uit.</p>`,
      400
    );
  }

  try {
    await env.NEWSLETTER.delete(`sub:${payload.email}`);
  } catch (err) {
    console.error("Afmelden mislukt:", err && err.message);
    return htmlPage(
      "Er ging iets mis",
      `<p>We konden je afmelding nu niet verwerken. Probeer het later opnieuw.</p>`,
      502
    );
  }

  return htmlPage(
    "Afgemeld",
    `<p><strong>Je bent afgemeld voor de nieuwsbrief.</strong></p>
     <p>Je ontvangt geen e-mails meer. Van gedachten veranderd? Je kunt je altijd opnieuw inschrijven
        op <a href="https://eaa-monitor.nl/">eaa-monitor.nl</a>.</p>`,
    200
  );
}

// ── GitHub: bezwaar als pull request indienen ──────────────────────────────

async function createObjectionPR(env, entry) {
  const repo = env.GITHUB_REPO;
  const base = env.GITHUB_BRANCH || "main";
  const norm = normalizeUrl(entry.url);
  const contentsApi = `https://api.github.com/repos/${repo}/contents/data/objections.json`;

  // 1. Huidige objections.json op de basisbranch ophalen en dedupliceren.
  const getRes = await fetch(`${contentsApi}?ref=${encodeURIComponent(base)}`, {
    headers: githubHeaders(env),
  });
  if (!getRes.ok) throw new Error(`GitHub GET contents ${getRes.status}`);
  const file = await getRes.json();

  let current;
  try {
    current = JSON.parse(b64decode(file.content || ""));
  } catch {
    current = [];
  }
  if (!Array.isArray(current)) current = [];
  if (current.some((o) => normalizeUrl(o.url) === norm)) {
    return { status: "already_listed" };
  }

  // 2. Branch maken vanaf de kop van de basisbranch. Deterministische naam, dus
  //    een tweede bevestiging voor dezelfde webshop botst (422) en opent geen
  //    tweede PR.
  const branch = `bezwaar/${slugForBranch(norm)}`;
  const headSha = await getBranchHeadSha(env, repo, base);
  const createRef = await fetch(`https://api.github.com/repos/${repo}/git/refs`, {
    method: "POST",
    headers: githubHeaders(env),
    body: JSON.stringify({ ref: `refs/heads/${branch}`, sha: headSha }),
  });
  if (createRef.status === 422) {
    return { status: "already_submitted" };
  }
  if (!createRef.ok) throw new Error(`GitHub create ref ${createRef.status}`);

  // 3. Bijgewerkte objections.json naar de nieuwe branch committen.
  current.push(entry);
  const putRes = await fetch(contentsApi, {
    method: "PUT",
    headers: githubHeaders(env),
    body: JSON.stringify({
      message: `Bezwaar verwerkt (automatisch, domein-geverifieerd): ${entry.name}`,
      content: b64encode(JSON.stringify(current, null, 2) + "\n"),
      sha: file.sha,
      branch,
    }),
  });
  if (!putRes.ok) throw new Error(`GitHub PUT ${putRes.status}`);

  // 4. Pull request openen voor Julia.
  const prRes = await fetch(`https://api.github.com/repos/${repo}/pulls`, {
    method: "POST",
    headers: githubHeaders(env),
    body: JSON.stringify({
      title: `Bezwaar: ${entry.name}`,
      head: branch,
      base,
      body: [
        `Domein-geverifieerd bezwaar tegen vermelding in de EAA Monitor.`,
        ``,
        `- Webshop: ${entry.name}`,
        `- URL: ${entry.url}`,
        `- Datum: ${entry.date}`,
        ``,
        `De aanvrager heeft de verwijdering bevestigd via een link die naar een e-mailadres op het`,
        `webshop-domein is gestuurd. Controleer kort en merge om de webshop uit het dashboard te halen.`,
      ].join("\n"),
    }),
  });
  if (!prRes.ok) throw new Error(`GitHub create PR ${prRes.status}`);
  const pr = await prRes.json();
  return { status: "pr_opened", url: pr.html_url };
}

async function getBranchHeadSha(env, repo, branch) {
  const res = await fetch(
    `https://api.github.com/repos/${repo}/git/ref/heads/${encodeURIComponent(branch)}`,
    { headers: githubHeaders(env) }
  );
  if (!res.ok) throw new Error(`GitHub get ref ${res.status}`);
  const data = await res.json();
  return data.object.sha;
}

function slugForBranch(norm) {
  return (
    norm
      .replace(/[^a-z0-9.-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "webshop"
  );
}

function githubHeaders(env) {
  return {
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "eaa-monitor-bezwaar-worker",
    "Content-Type": "application/json",
  };
}

// ── E-mails ────────────────────────────────────────────────────────────────

async function sendConfirmationEmail(env, { name, email, webadres, confirmUrl }) {
  const subject = "Bevestig de verwijdering van je webshop uit de EAA Monitor";
  const text = [
    `Hoi,`,
    ``,
    `Er is een verzoek binnengekomen om "${name}" (${webadres}) uit de EAA Monitor te halen.`,
    ``,
    `Klik op de onderstaande link om de verwijdering te bevestigen. De link is 7 dagen geldig.`,
    ``,
    confirmUrl,
    ``,
    `Heb jij dit niet aangevraagd? Dan hoef je niets te doen. Zonder bevestiging gebeurt er niets.`,
    ``,
    `EAA Monitor, eaa-monitor.nl`,
  ].join("\n");
  const html = `
    <div style="font-family: Arial, sans-serif; color: #1F2937; line-height: 1.6;">
      <p>Hoi,</p>
      <p>Er is een verzoek binnengekomen om <strong>${escapeHtml(name)}</strong>
         (${escapeHtml(webadres)}) uit de EAA Monitor te halen.</p>
      <p>Klik op de knop om de verwijdering te bevestigen. De link is 7 dagen geldig.</p>
      <p>
        <a href="${escapeHtml(confirmUrl)}"
           style="display:inline-block;background:#A30D4B;color:#fff;text-decoration:none;
                  padding:12px 20px;border-radius:8px;font-weight:bold;">
          Verwijdering bevestigen
        </a>
      </p>
      <p style="font-size:13px;color:#6B7280;">Werkt de knop niet? Kopieer dan deze link naar je browser:<br>
        <span style="word-break:break-all;">${escapeHtml(confirmUrl)}</span></p>
      <p>Heb jij dit niet aangevraagd? Dan hoef je niets te doen. Zonder bevestiging gebeurt er niets.</p>
      <p style="color:#6B7280;font-size:13px;">EAA Monitor, eaa-monitor.nl</p>
    </div>`;

  await env.EMAIL.send({
    to: email,
    from: { email: env.FROM_EMAIL, name: env.FROM_NAME || "EAA Monitor" },
    replyTo: env.NOTIFY_EMAIL,
    subject,
    text,
    html,
  });
}

async function sendManualReviewEmail(env, { name, webadres, email, declared, toelichting, webDomain, emailDomain }) {
  const subject = `Bezwaar (handmatige check): ${name}`;
  const lines = [
    `Er is een bezwaar binnengekomen dat niet automatisch geverifieerd kon worden,`,
    `omdat het e-mailadres niet op het webshop-domein staat.`,
    ``,
    `Bedrijfsnaam: ${name}`,
    `Webadres: ${webadres}`,
    `E-mailadres: ${email}`,
    `Webshop-domein: ${webDomain || "?"}`,
    `E-maildomein: ${emailDomain || "?"}`,
    ``,
    `Verklaringen:`,
    `- minder dan 10 medewerkers: ${declared.under_10_fte ? "ja" : "nee"}`,
    `- omzet onder 2 miljoen: ${declared.under_2m_turnover ? "ja" : "nee"}`,
    `- uitsluitend B2B: ${declared.b2b_only ? "ja" : "nee"}`,
    ``,
    `Toelichting: ${toelichting || "(geen)"}`,
    ``,
    `Verwerk dit volgens workflows/handle_objection.md.`,
  ];
  await env.EMAIL.send({
    to: env.NOTIFY_EMAIL,
    from: { email: env.FROM_EMAIL, name: env.FROM_NAME || "EAA Monitor" },
    replyTo: email,
    subject,
    text: lines.join("\n"),
  });
}

async function sendFeedbackEmail(env, { bericht, email, artikel, artikelUrl }) {
  const subject = `Feedback op artikel: ${artikel || "(onbekend)"}`;
  const lines = [
    `Er is feedback binnengekomen via een kennisbank-artikel.`,
    ``,
    `Artikel: ${artikel || "(onbekend)"}`,
    `URL: ${artikelUrl || "(onbekend)"}`,
    `Reageren kan naar: ${email || "(geen e-mailadres opgegeven)"}`,
    ``,
    `Bericht:`,
    bericht,
  ];
  await env.EMAIL.send({
    to: env.NOTIFY_EMAIL,
    from: { email: env.FROM_EMAIL, name: env.FROM_NAME || "EAA Monitor" },
    replyTo: email && isValidEmail(email) ? email : env.NOTIFY_EMAIL,
    subject,
    text: lines.join("\n"),
  });
}

async function sendVraagEmail(env, { vraag, email, sector }) {
  // Eigen postbus voor anonieme vragen, met terugval op het algemene adres.
  const to = env.VRAGEN_EMAIL || env.NOTIFY_EMAIL;
  const subject = `Anonieme EAA-vraag${sector ? ` (${sector})` : ""}`;
  const lines = [
    `Er is een anonieme vraag over de EAA binnengekomen om aan de toezichthouder voor te leggen.`,
    ``,
    `Sector/context: ${sector || "(niet opgegeven)"}`,
    `Antwoord gewenst op: ${email || "(volledig anoniem, geen adres opgegeven)"}`,
    ``,
    `Vraag:`,
    vraag,
    ``,
    `Verwerk dit volgens workflows/handle_vraag.md: leg de vraag namens de vrager voor`,
    `aan de juiste toezichthouder en publiceer het antwoord in data/vragen.json`,
    `(pagina /vragen.html). Publiceer nooit het e-mailadres of herleidbare gegevens.`,
  ];
  await env.EMAIL.send({
    to,
    from: { email: env.FROM_EMAIL, name: env.FROM_NAME || "EAA Monitor" },
    replyTo: email && isValidEmail(email) ? email : to,
    subject,
    text: lines.join("\n"),
  });
}

async function sendNewsletterConfirmEmail(env, { email, confirmUrl }) {
  const from = env.NEWSLETTER_FROM || env.FROM_EMAIL;
  const subject = "Bevestig je inschrijving voor de EAA Monitor nieuwsbrief";
  const text = [
    `Hoi,`,
    ``,
    `Je hebt je ingeschreven voor de nieuwsbrief van de EAA Monitor.`,
    ``,
    `Klik op de onderstaande link om je inschrijving te bevestigen. De link is 7 dagen geldig.`,
    ``,
    confirmUrl,
    ``,
    `Heb jij dit niet aangevraagd? Dan hoef je niets te doen. Zonder bevestiging gebeurt er niets.`,
    ``,
    `EAA Monitor, eaa-monitor.nl`,
  ].join("\n");
  const html = `
    <div style="font-family: Arial, sans-serif; color: #1F2937; line-height: 1.6;">
      <p>Hoi,</p>
      <p>Je hebt je ingeschreven voor de nieuwsbrief van de <strong>EAA Monitor</strong>.</p>
      <p>Klik op de knop om je inschrijving te bevestigen. De link is 7 dagen geldig.</p>
      <p>
        <a href="${escapeHtml(confirmUrl)}"
           style="display:inline-block;background:#0052FF;color:#fff;text-decoration:none;
                  padding:12px 20px;border-radius:8px;font-weight:bold;">
          Inschrijving bevestigen
        </a>
      </p>
      <p style="font-size:13px;color:#6B7280;">Werkt de knop niet? Kopieer dan deze link naar je browser:<br>
        <span style="word-break:break-all;">${escapeHtml(confirmUrl)}</span></p>
      <p>Heb jij dit niet aangevraagd? Dan hoef je niets te doen. Zonder bevestiging gebeurt er niets.</p>
      <p style="color:#6B7280;font-size:13px;">EAA Monitor, eaa-monitor.nl</p>
    </div>`;

  await env.EMAIL.send({
    to: email,
    from: { email: from, name: env.FROM_NAME || "EAA Monitor" },
    replyTo: env.NOTIFY_EMAIL,
    subject,
    text,
    html,
  });
}

// ── Token: HMAC-getekend, stateless ────────────────────────────────────────

async function signToken(env, payload) {
  const body = b64urlEncode(JSON.stringify(payload));
  const sig = await hmac(env, body);
  return `${body}.${sig}`;
}

async function verifyToken(env, token) {
  if (!token || token.indexOf(".") === -1) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const expected = await hmac(env, body);
  if (!timingSafeEqual(sig, expected)) return null;
  let payload;
  try {
    payload = JSON.parse(b64urlDecode(body));
  } catch {
    return null;
  }
  if (!payload || typeof payload.exp !== "number" || Date.now() > payload.exp) return null;
  if (!payload.url || !payload.name) return null;
  return payload;
}

// Verifieert een nieuwsbrief-token (inschrijven of afmelden). Zelfde HMAC, maar
// andere veldcontrole dan het bezwaar-token: een geldig e-mailadres en het
// verwachte type, zodat een inschrijflink niet als afmeldlink kan dienen.
async function verifyNewsletterToken(env, token, expectedType) {
  if (!token || token.indexOf(".") === -1) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const expected = await hmac(env, body);
  if (!timingSafeEqual(sig, expected)) return null;
  let payload;
  try {
    payload = JSON.parse(b64urlDecode(body));
  } catch {
    return null;
  }
  if (!payload || typeof payload.exp !== "number" || Date.now() > payload.exp) return null;
  if (payload.type !== expectedType) return null;
  if (!payload.email || !isValidEmail(payload.email)) return null;
  return payload;
}

async function hmac(env, data) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(env.SIGNING_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  return b64urlBytes(new Uint8Array(sig));
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function hostFromUrl(value) {
  try {
    const u = new URL(value);
    if (u.protocol !== "http:" && u.protocol !== "https:") return "";
    return u.hostname.toLowerCase();
  } catch {
    return "";
  }
}

// Vereenvoudigde eTLD+1. Dekt de gangbare Nederlandse gevallen (.nl, .com, .be)
// plus een korte lijst tweelaagse TLD's. Geen volledige public-suffix-lijst.
const TWO_LEVEL_TLDS = new Set([
  "co.uk", "org.uk", "me.uk", "com.de", "co.nz", "com.au", "co.za",
]);
function registrableDomain(host) {
  if (!host) return "";
  host = host.toLowerCase().replace(/\.$/, "").replace(/^www\./, "");
  const parts = host.split(".");
  if (parts.length <= 2) return host;
  const lastTwo = parts.slice(-2).join(".");
  if (TWO_LEVEL_TLDS.has(lastTwo)) return parts.slice(-3).join(".");
  return lastTwo;
}

// Moet exact overeenkomen met normalizeUrl in public/app.js zodat de overlay matcht.
function normalizeUrl(url) {
  if (!url) return "";
  return url
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/\/+$/, "");
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// UTF-8-veilige base64 (namen met accenten).
function b64encode(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
function b64decode(b64) {
  const bin = atob(String(b64).replace(/\s/g, ""));
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
function b64urlEncode(str) {
  return b64encode(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(b64) {
  let s = String(b64).replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return b64decode(s);
}
function b64urlBytes(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function withCors(env, response) {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", env.ALLOWED_ORIGIN || "*");
  headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  headers.set("Vary", "Origin");
  return new Response(response.body, { status: response.status, headers });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function htmlPage(title, bodyHtml, status = 200) {
  const html = `<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>${escapeHtml(title)} — EAA Monitor</title>
  <style>
    body { font-family: Arial, sans-serif; color: #1F2937; background: #F5F5F5; margin: 0; padding: 0; }
    .wrap { max-width: 640px; margin: 0 auto; padding: 48px 24px; }
    .card { background: #fff; border-top: 4px solid #A30D4B; border-radius: 12px; padding: 32px; }
    h1 { font-size: 24px; color: #1F2937; margin-top: 0; }
    a { color: #004050; }
    p { line-height: 1.6; }
    .brand { color: #6B7280; font-size: 13px; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>${escapeHtml(title)}</h1>
      ${bodyHtml}
      <p class="brand">EAA Monitor, eaa-monitor.nl</p>
    </div>
  </div>
</body>
</html>`;
  return new Response(html, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
