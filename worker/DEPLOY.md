# Bezwaar-Worker uitrollen

Deze Cloudflare Worker verwerkt bezwaren tegen vermelding grotendeels
automatisch. De misbruikbescherming zit in domein-verificatie: een bezwaar wordt
alleen automatisch ingediend als iemand op het webshop-domein zelf de
bevestigingslink aanklikt. Na bevestiging opent de Worker een pull request, die
Julia met één klik goedkeurt. Past het e-mailadres niet bij het webshop-domein,
dan krijgt Julia een mail en verwerkt ze het bezwaar handmatig volgens
`workflows/handle_objection.md`.

## Flow

```
bezwaar.html  ──POST /submit──▶  Worker
                                   │
                  e-maildomein == webshopdomein?
                   ja │                       │ nee
                      ▼                       ▼
        bevestigingsmail naar         mail naar Julia
        het webshop-adres             (handmatige check)
                      │
        gebruiker klikt de link
                      ▼
              GET /confirm  ──▶  branch + commit + pull request op objections.json
                      ▼
              Julia merget de PR  ──▶  deploy.yml draait  ──▶  webshop verdwijnt
```

## Eenmalige setup

### 1. Dependencies

```bash
cd worker
npm install
npx wrangler login
```

### 1b. eaa-monitor.nl naar Cloudflare verhuizen (DNS)

De e-mail van de Worker leunt op Cloudflare: zowel het versturen (Email Sending,
stap 2) als het ontvangen op `info@eaa-monitor.nl` (Email Routing, stap 2b) werkt
alleen als het domein als zone bij Cloudflare staat. De DNS draait nu bij one.com,
dus die verhuis je eerst. **De site blijft op GitHub Pages**, alleen de
naamservers wijzigen.

Uitgangssituatie (gecontroleerd):
- Naamservers nu: `ns01.one.com`, `ns02.one.com`.
- De site wijst naar GitHub Pages (apex A-records + `www` als CNAME).
- De MX staat op "null MX" (`0 .`): het domein ontvangt nu geen mail.

Stappen:

1. Maak (gratis) een Cloudflare-account aan en kies **Add a site**. Vul
   `eaa-monitor.nl` in en kies het gratis plan. Cloudflare scant de bestaande DNS.
2. Controleer dat Cloudflare deze **GitHub Pages-records** heeft overgenomen. Zo
   niet, voeg ze handmatig toe en zet ze op **DNS only** (grijze wolk, niet
   geproxyd, anders werkt GitHub Pages niet goed):

   | Type  | Naam  | Waarde                                                        |
   | ----- | ----- | ------------------------------------------------------------- |
   | A     | `@`   | `185.199.108.153`                                             |
   | A     | `@`   | `185.199.109.153`                                             |
   | A     | `@`   | `185.199.110.153`                                             |
   | A     | `@`   | `185.199.111.153`                                             |
   | CNAME | `www` | `juliatol-properaccess.github.io`                             |

3. **Neem de null MX (`0 .`) niet over.** Laat de MX leeg; Email Routing (stap 2b)
   zet straks de juiste MX-records klaar.
4. Cloudflare toont nu twee toegewezen naamservers (bijvoorbeeld
   `xxx.ns.cloudflare.com`). Log in bij **one.com**, ga naar de DNS-/naamserver-
   instellingen van `eaa-monitor.nl` en vervang `ns01.one.com` en `ns02.one.com`
   door de twee Cloudflare-naamservers.
5. Wacht tot Cloudflare de zone als **Active** meldt (meestal minuten, soms tot 24
   uur). Check daarna dat de site nog laadt en dat in **GitHub → Settings → Pages**
   het custom domain `eaa-monitor.nl` nog groen staat met "Enforce HTTPS" aan.

Daarna kun je door met stap 2 (versturen) en stap 2b (ontvangen).

### 2. E-mailverzending aanzetten voor het domein

Het `FROM_EMAIL`-domein (`eaa-monitor.nl`) moet onboarden bij Cloudflare Email
Sending. Dit kan alleen als `eaa-monitor.nl` als zone in je Cloudflare-account
staat (DNS via Cloudflare beheerd).

```bash
npx wrangler email sending enable eaa-monitor.nl
npx wrangler email sending dns get eaa-monitor.nl   # controleer SPF + DKIM
```

Staat `eaa-monitor.nl` niet bij Cloudflare? Twee opties:
- Verhuis de DNS van `eaa-monitor.nl` naar Cloudflare (de site blijft op GitHub
  Pages staan, alleen de naamservers wijzigen), of
- gebruik tijdelijk een ander Cloudflare-domein als afzender en pas `FROM_EMAIL`
  in `wrangler.jsonc` aan.

### 2b. E-mail ontvangen op `info@eaa-monitor.nl` (Email Routing)

Email Sending (stap 2) kan alleen versturen. Om binnenkomende mail op
`info@eaa-monitor.nl` te ontvangen, zet je **Email Routing** aan. Dat stuurt mail
voor dat adres door naar je echte inbox. Dit is nodig zodat:

- bezwaarmakers die op de bevestigingsmail antwoorden bij jou terechtkomen
  (de reply-to is `NOTIFY_EMAIL`),
- handmatige-check-meldingen binnenkomen (de Worker mailt die naar `NOTIFY_EMAIL`),
- het contactadres dat op de site staat ook echt werkt.

**Voorwaarde:** `eaa-monitor.nl` staat als zone in je Cloudflare-account, net als
bij stap 2.

Stappen in het Cloudflare-dashboard:

1. Kies de zone **eaa-monitor.nl** en ga naar **Email → Email Routing**.
2. Klik **Get started / Enable**. Cloudflare zet automatisch de benodigde
   MX- en SPF-records klaar. Bevestig dat het die records mag toevoegen.
3. Ga naar **Destination addresses** en voeg je echte inbox toe (bijvoorbeeld een
   eigen Gmail of een bestaand mailadres dat je leest). Cloudflare stuurt daar een
   verificatiemail. Klik de link in die mail om het adres te bevestigen.
4. Ga naar **Routing rules → Custom addresses** en maak een regel:
   `info@eaa-monitor.nl` **Send to** je geverifieerde inbox. Bewaar.
5. Aanrader: voeg ook een regel toe voor `bezwaar@eaa-monitor.nl` naar diezelfde
   inbox, voor het geval iemand op het afzenderadres antwoordt. Of zet een
   **catch-all** aan die al het overige naar je inbox stuurt.

**Let op de SPF-samenloop.** Email Sending (stap 2) en Email Routing zetten allebei
DNS-records. Cloudflare voegt ze meestal correct samen, maar controleer in
**DNS → Records** dat er precies één geldige SPF-regel staat (begint met
`v=spf1` en bevat `include:_spf.mx.cloudflare.net`), niet twee losse. De send-kant
check je met:

```bash
npx wrangler email sending dns get eaa-monitor.nl
```

**Worker-config neutraal zetten.** Wijzig in `wrangler.jsonc` de regel:

```jsonc
"NOTIFY_EMAIL": "info@eaa-monitor.nl",
```

Dit adres is zowel de bestemming van de handmatige meldingen als de reply-to op de
bevestigingsmails. Omdat Email Routing het doorstuurt naar je echte inbox, blijft
alles werken en staat er nergens meer een ander mailadres zichtbaar. Deploy daarna
opnieuw met `npx wrangler deploy`.

**Testen.** Dien via het formulier een bezwaar in met een Gmail-adres (geen
domeinmatch). De Worker stuurt dan een melding naar `info@eaa-monitor.nl`. Komt die
binnen in je echte inbox, dan werkt de routing.

### 3. GitHub-token aanmaken

Maak een **fine-grained personal access token**:
- Repository access: alleen `JuliaTol-properaccess/eaa-monitor`
- Permissions: **Contents → Read and write** en **Pull requests → Read and write**
- Looptijd: zo kort als praktisch is, met een herinnering om te verversen

### 4. Secrets zetten

```bash
# Willekeurige sterke string, bv. uit: openssl rand -hex 32
npx wrangler secret put SIGNING_SECRET

# De fine-grained PAT uit stap 3
npx wrangler secret put GITHUB_TOKEN
```

### 5. Deployen

```bash
npx wrangler deploy
```

Wrangler toont de Worker-URL, bijvoorbeeld
`https://eaa-bezwaar.<jouw-subdomein>.workers.dev`. De bevestigingslink in de
mail wijst automatisch naar `/confirm` op ditzelfde adres, dus je hoeft niets
extra's te configureren. Wil je een net adres (bv. `bezwaar.eaa-monitor.nl`),
voeg dan een Worker-route of custom domain toe in het Cloudflare-dashboard.

### 6. Frontend koppelen

Zet in `public/bezwaar.html` de constante `BEZWAAR_ENDPOINT` op de
`/submit`-URL van de Worker:

```js
const BEZWAAR_ENDPOINT = "https://eaa-bezwaar.<jouw-subdomein>.workers.dev/submit";
```

Zolang die leeg is, blijft het formulier via Formspree naar Julia mailen, dus de
site blijft werken tot je klaar bent om de Worker live te zetten. Commit en push
deze wijziging pas als de Worker draait.

## Feedback op artikelen (`POST /feedback`)

Dezelfde Worker bedient ook het feedbackformulier onder elk kennisbank-artikel
(gegenereerd door `tools/build_articles.py`). De route `/feedback` hergebruikt de
e-mail-infra: een opmerking wordt rechtstreeks naar `NOTIFY_EMAIL` gemaild, met de
artikeltitel en -URL erbij. Geen GitHub-PR, geen opslag, **geen extra secrets of
vars nodig**.

- De frontend-constante staat in `tools/build_articles.py` (`FEEDBACK_ENDPOINT`).
  Wijzig je het Worker-adres, pas die aan en draai `python tools/build_articles.py`.
- Een opgegeven e-mailadres is optioneel en wordt de reply-to, zodat je direct kunt
  antwoorden. Zonder adres valt reply-to terug op `NOTIFY_EMAIL`.
- **Na een wijziging aan de Worker opnieuw deployen** (`npx wrangler deploy`),
  anders is `/feedback` nog niet bereikbaar.

## Anonieme vragen (`POST /vraag`)

Dezelfde Worker bedient ook het formulier op `public/vraag-stellen.html`, waarmee
ondernemers anoniem een vraag over de EAA stellen. De route `/vraag` mailt de vraag
rechtstreeks naar een **eigen postbus** (`VRAGEN_EMAIL`, standaard
`vragen@eaa-monitor.nl`), zodat vragen niet tussen de bezwaren en artikelfeedback
verdwijnen. Geen GitHub-PR, geen opslag. De vrager hoeft geen naam of e-mailadres op
te geven; geeft die wel een adres, dan wordt dat de reply-to (en blijft het privé).

Julia verwerkt elke vraag volgens `workflows/handle_vraag.md`: ze legt de vraag voor
aan de toezichthouder en publiceert het antwoord in `data/vragen.json`, waarna
`python tools/build_vragen.py` de pagina `public/vragen.html` opnieuw bouwt.

- De frontend-constante staat in `public/vraag-stellen.html` (`VRAAG_ENDPOINT`). Wijs
  die naar de `/vraag`-URL van de Worker.
- **Na een wijziging aan de Worker opnieuw deployen** (`npx wrangler deploy`).

### Nieuw e-mailadres `vragen@eaa-monitor.nl` aanmaken

De vragen komen binnen op een nieuw adres. Dankzij Cloudflare Email Routing (zie
stap 2b) hoef je geen mailbox aan te maken; je maakt alleen een **doorstuurregel**
die mail voor `vragen@eaa-monitor.nl` naar je echte inbox stuurt. Voorwaarde:
`eaa-monitor.nl` staat al als zone in Cloudflare en Email Routing is aan (stap 2b).

1. Log in op het **Cloudflare-dashboard** en kies de zone **eaa-monitor.nl**.
2. Ga naar **Email → Email Routing → Routing rules**.
3. Heb je al een **catch-all** aanstaan die alles naar je inbox stuurt? Dan werkt
   `vragen@eaa-monitor.nl` al en hoef je hier niets te doen. Ga door naar stap 6.
4. Zo niet: klik onder **Custom addresses** op **Create address**.
   - **Custom address:** `vragen@eaa-monitor.nl`
   - **Action:** *Send to an email*
   - **Destination:** je geverifieerde inbox (dezelfde als bij `info@`)
   - Bewaar de regel.
5. Is die inbox nog niet geverifieerd, voeg hem dan eerst toe onder **Destination
   addresses** en klik de verificatielink in de mail die Cloudflare stuurt.
6. **Controleer dat de Worker het adres gebruikt.** In `worker/wrangler.jsonc` staat
   `"VRAGEN_EMAIL": "vragen@eaa-monitor.nl"`. Klopt dat, deploy dan opnieuw:
   `npx wrangler deploy`. Wil je tijdelijk geen apart adres, haal de regel weg; dan
   vallen vragen terug op `NOTIFY_EMAIL` (`info@eaa-monitor.nl`).
7. **Testen.** Stuur via `public/vraag-stellen.html` een testvraag. Er hoort een mail
   met onderwerp "Anonieme EAA-vraag" in je inbox te komen.

> Let op: `vragen@eaa-monitor.nl` is **alleen ontvangen** (Email Routing). De Worker
> verstuurt nog steeds vanaf `FROM_EMAIL` (`bezwaar@eaa-monitor.nl`); dat hoeft niet
> te veranderen. Wil je ook vanaf `vragen@` versturen, dan moet dat adres apart
> onboarden bij Email Sending, maar dat is voor deze functie niet nodig.

## Nieuwsbrief-opt-in (`POST /newsletter`)

Dezelfde Worker bedient het inschrijfformulier in de footer (op elke pagina). De
inschrijving gaat met **dubbele opt-in**:

1. `POST /newsletter` ontvangt het e-mailadres en stuurt een bevestigingsmail met
   een HMAC-getekende link. Er wordt nog **niets** opgeslagen.
2. `GET /newsletter/confirm?token=…` verifieert de link en slaat het adres pas dan
   op in de KV-namespace **NEWSLETTER** (sleutel `sub:<e-mailadres>`).
3. `GET /newsletter/unsubscribe?token=…` haalt het adres weer uit KV. De
   bevestigingspagina toont meteen een afmeldlink; in elke nieuwsbrief hoort
   dezelfde link onderaan te staan.

### KV-namespace aanmaken (eenmalig)

```bash
cd worker
npx wrangler kv namespace create NEWSLETTER
```

Wrangler print een `id`. Zet dat in `worker/wrangler.jsonc` op de plek van
`VUL_KV_NAMESPACE_ID_IN`:

```jsonc
"kv_namespaces": [{ "binding": "NEWSLETTER", "id": "<het-id-uit-het-commando>" }],
```

Deploy daarna opnieuw: `npx wrangler deploy`. Zonder geldig id faalt de deploy.

### Afzender

De bevestigingsmail gaat standaard vanaf `NEWSLETTER_FROM`
(`nieuwsbrief@eaa-monitor.nl`); is die niet gezet, dan valt hij terug op
`FROM_EMAIL`. Het adres hoeft niet te bestaan als mailbox: versturen werkt zolang
het domein onboarded is bij Email Sending (stap 2). De reply-to is `NOTIFY_EMAIL`.

### Inschrijvingen bekijken / exporteren

```bash
# Alle bevestigde inschrijvingen oplijsten
npx wrangler kv key list --binding NEWSLETTER
# Eén adres bekijken
npx wrangler kv key get --binding NEWSLETTER "sub:iemand@voorbeeld.nl"
```

Het versturen van de nieuwsbrief zelf is nog niet gebouwd; deze route verzamelt
voorlopig alleen de (bevestigde) adressen.

### Aandachtspunten

- De frontend-constante staat in `tools/build_articles.py` (`NEWSLETTER_ENDPOINT`)
  en wordt in de footer gebakken via `site_footer()`; submit-logica in
  `public/static/newsletter.js`.
- Zet in Cloudflare een **rate-limit** op `/newsletter` (zoals op `/submit`,
  `/feedback` en `/vraag`) om misbruik te voorkomen.
- **Na een wijziging aan de Worker opnieuw deployen** (`npx wrangler deploy`).

## Testen

1. **Lokaal** (stuurt echte mail, gebruik een eigen testadres):
   ```bash
   cd worker
   # tijdelijk "remote": true bij send_email in wrangler.jsonc voor echte mail
   npx wrangler dev
   ```
   Test met een webadres en e-mailadres op hetzelfde domein dat je beheert.

2. **Domeinmatch** (auto-route): vul een webadres in en een e-mailadres op
   datzelfde domein. Je hoort een bevestigingsmail te krijgen; na klikken opent
   er een pull request op de repo met de nieuwe entry in `data/objections.json`.

3. **Geen match** (handmatige route): vul een gmail-adres in. Julia krijgt een
   notificatiemail, er wordt geen PR aangemaakt.

4. **Dubbel klikken**: klik de bevestigingslink twee keer. De tweede keer meldt
   de pagina dat het verzoek al is ingediend. Geen tweede PR.

## Logs

```bash
cd worker
npx wrangler tail
```

## Aandachtspunten / beperkingen

- **E-mailbommen voorkomen.** Iemand kan `/submit` herhaaldelijk aanroepen met
  een webshop-adres en zo bevestigingsmails naar dat domein laten sturen. Zet in
  Cloudflare een **Rate Limiting Rule** op het pad `/submit` (bv. max 5 per
  minuut per IP). Zet dezelfde rule ook op `/feedback` en `/vraag`, die net zo
  goed mail versturen.
- **eTLD-lijst is beperkt.** De domeinvergelijking dekt `.nl`, `.com`, `.be` en
  een korte lijst tweelaagse TLD's (`co.uk` enz.), geen volledige public-suffix-
  lijst. Twijfelgevallen vallen veilig terug op de handmatige route.
- **Token is stateless.** De bevestigingslink draagt zelf alle gegevens, getekend
  met `SIGNING_SECRET`. Roteer dat secret als je vermoedt dat het gelekt is; alle
  openstaande links vervallen dan.
- **Merge triggert deploy.** De Worker pusht niet naar `main`, maar opent een PR.
  Zodra jij die merget (een push door jou, niet door Actions' `GITHUB_TOKEN`),
  draait `deploy.yml` en is het dashboard meestal binnen enkele minuten bij.
- **Branch-opruiming.** Zet in de repo-instellingen "Automatically delete head
  branches" aan, dan ruimt GitHub de `bezwaar/...`-branches na de merge op.
