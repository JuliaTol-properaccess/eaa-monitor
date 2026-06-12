# Migratie naar een Europese stack

*Stand: 12 juni 2026. Prijzen zijn indicatief en exclusief btw; controleer ze op het moment van keuze.*

## Waarom dit document

We willen in de footer kunnen zeggen dat eaa-monitor.nl op Europese diensten draait. Dit document beschrijft per onderdeel wat er moet gebeuren, wat het kost en hoeveel werk het is, en bevat het draaiboek voor de resterende stappen.

## Huidige stack

| Onderdeel | Dienst | Herkomst | Status |
|---|---|---|---|
| Domeinregistratie | One.com (registrar), SIDN (.nl-register) | Denemarken / Nederland | ✅ EU |
| Statistieken | Plausible Analytics | Estland (hosting in Duitsland) | ✅ EU |
| Fonts en CSS | Zelf-gehost (Fontsource) + lokale Tailwind-build | eigen server | ✅ gedaan (10 juni) |
| Hosting (doel) | Hetzner VPS `eaa-monitor-1`, Falkenstein (zie `server.md`) | Duitsland | ✅ draait, wacht op DNS |
| Formulieren-service (doel) | Node-service `eaa-forms` op de VPS | Duitsland | ✅ draait, wacht op DNS |
| Inkomende mail | Google Workspace (groepen info@, vragen@, bezwaar@) | VS | ✅ werkt; bewust geaccepteerd, zie onderaan |
| **DNS** | Cloudflare | VS | ⏳ verhuizen naar Hetzner DNS |
| **Hosting (live)** | GitHub Pages (Microsoft) | VS | ⏳ vervalt bij DNS-cutover |
| **Formulieren (live)** | Cloudflare Worker + KV | VS | ⏳ vervalt bij DNS-cutover |
| **E-mailverzending** | Resend (live Worker), Brevo (op de VPS) | VS / Frankrijk | ⏳ wordt AhaSend, zie hieronder |
| **Code en wekelijkse scrape** | GitHub + GitHub Actions | VS | ⏳ fase 3: naar Codeberg + VPS-cron |

## Besluiten (bijgewerkt 12 juni 2026)

1. **E-mailverzending: AhaSend** (Nederland) in plaats van Brevo. Op 10 juni was Brevo op de VPS ingericht; op 12 juni is na vergelijking definitief voor AhaSend gekozen: puur transactioneel, Nederlands, gratis tot 1.000 mails per maand, API-vorm vrijwel gelijk aan Resend. Het sending domain `eaa-monitor.nl` is geverifieerd en getest: DKIM-CNAME's (`ahasend._domainkey`, `ahasend2._domainkey`) en return-path `psrp.eaa-monitor.nl → rp.ahasend.com` staan in de DNS, en een testmail kwam binnen met SPF, DKIM én DMARC op pass. Let op: het psrp-CNAME moet **DNS only** zijn, niet Proxied (dat was de enige instelfout). `AHASEND_API_KEY` (alleen send-scope) en `AHASEND_ACCOUNT_ID` staan in `.env`; API: `POST https://api.ahasend.com/v2/accounts/{account_id}/messages` met Bearer-auth en payload `{from:{email,name}, recipients:[{email,name}], subject, text_content, html_content}`.
2. **Code-hosting: Codeberg** (Duitse non-profit, Forgejo). Een GitLab-account was al aangemaakt, maar gitlab.com is een Amerikaans bedrijf met hosting op Google Cloud in de VS; voor de claim "volledig Europees" is Codeberg de zuivere keuze. CI-werk (deploys, scrape) draait niet bij Codeberg maar op de eigen VPS.
3. **DNS: Hetzner DNS** (gratis, zelfde console als de server).
4. **Inkomende mail blijft voorlopig bij Google Workspace.** Bewust geaccepteerd om de migratie behapbaar te houden; EU-alternatieven (mailbox.org, Infomaniak) staan onderaan als vervolgstap.

## Wat er al af is

- **Fase 1 (10 juni):** fonts zelf-gehost via Fontsource, Tailwind lokaal gebouwd. De browser van een bezoeker maakt geen enkel verzoek meer naar een Amerikaanse dienst.
- **Server (10 juni):** Hetzner CX23 `eaa-monitor-1` in Falkenstein met Caddy en de formulieren-service `eaa-forms` (zelfde code als de Worker, via de Node-adapter `worker/server.mjs`, opslag in `/var/lib/eaa-forms/kv.json`). Zie `docs/server.md` voor IP, toegang en deploy.
- **Inkomende mail (10 juni):** eaa-monitor.nl is secundair domein in de Proper Access-Workspace met drie gratis groepen (info@, vragen@, bezwaar@); MX staat op `smtp.google.com` en is end-to-end getest.
- **Deploy (10 juni):** elke push naar `main` deployt via GitHub Actions naar GitHub Pages én naar de VPS.
- **AhaSend (12 juni):** domein geverifieerd, testmail met alle checks op pass (zie besluit 1).

## Restplan A: laatste voorbereidingen vóór de DNS-cutover

1. **Eregalerij-PR mergen (PR #44).** Die bevat de eregalerij (nomineren en stemmen) plus een refactor van de PR-helper in de Worker-code. Mergen vóór de cutover, dan verhuist alles in één keer mee en testen we de nieuwe routes meteen op de VPS. Na de merge heeft de frontend twee éxtra endpoint-constanten die in cutover-stap 6 mee moeten: `NOMINATIE_ENDPOINT` in `public/nomineren.html` en `HOF_ENDPOINT_BASE` in `tools/build_halloffame.py`. De service heeft de var `HOF_DATA_URL` nodig in `/etc/eaa-forms.env`.
2. **`sendEmail()` omzetten naar AhaSend.** Een AhaSend-tak toevoegen in `worker/src/index.js` (vóór de Brevo-tak), op de VPS `AHASEND_API_KEY` en `AHASEND_ACCOUNT_ID` in `/etc/eaa-forms.env` zetten en `BREVO_API_KEY` verwijderen, service herstarten, één bevestigingsflow end-to-end testen. De Cloudflare Worker blijft tot de cutover gewoon op Resend draaien (die heeft geen Brevo/AhaSend-keys), dus de live site merkt hier niets van.
3. **PR-token op de server.** De formulieren-service opent PR's (bezwaren, nominaties) en heeft daarvoor een token nodig in `/etc/eaa-forms.env`. Tot de Codeberg-verhuizing (restplan B) is dat een fine-grained GitHub-PAT (`GITHUB_TOKEN`, Contents + Pull requests: read & write op de eaa-monitor-repo); na de verhuizing vervangt een Codeberg-token hem. Vijf minuten werk, twee keer; dat is de prijs van de DNS eerder verhuizen dan de code.
4. **DNS-zone exporteren uit Cloudflare** (DNS → Records → Export) als referentie.
5. **Zone aanmaken bij Hetzner DNS** (dns.hetzner.com, zelfde login):
   - `A eaa-monitor.nl → 128.140.50.96` en `AAAA → 2a01:4f8:c014:6c5d::1`
   - `CNAME www → eaa-monitor.nl`
   - `MX @ 1 smtp.google.com` + de Google-verificatie-TXT
   - **AhaSend:** `CNAME ahasend._domainkey → dfcf2098318c3bc1.setup.ahasend.com`, `CNAME ahasend2._domainkey → 8fab7697088619c4.setup.ahasend.com`, `CNAME psrp → rp.ahasend.com`
   - SPF: `v=spf1 include:_spf.google.com ~all` (AhaSend hoeft hier niet in: de SPF-check loopt via het psrp-return-path; de oude verwijzingen naar Cloudflare en Brevo vervallen)
   - `_dmarc` TXT overnemen (blijft voorlopig `p=none`)
   - **Niet meenemen:** de GitHub Pages-A-records, de Brevo-records (brevo1/brevo2._domainkey en de brevo-code-TXT) en de Resend-records. De Resend-records in de **Cloudflare**-zone wél laten staan zolang de Worker nog draait (de naweek van stap 10).
6. **Nieuwsbrief-abonnees meenemen.** Bevestigde adressen staan in de Cloudflare KV-namespace `NEWSLETTER` (sleutels `sub:<email>`). Exporteren met `wrangler kv key list/get --remote` (let op de quoted-key gotchas, zie `friction-log.md`) en importeren in `/var/lib/eaa-forms/kv.json`. Aantallen voor en na vergelijken.

## Restplan A: de cutover zelf (rustig moment, 30 tot 60 minuten)

7. **Frontend-endpoints omzetten** van `https://eaa-bezwaar.juliatol.workers.dev/...` naar `https://eaa-monitor.nl/api/...` op zes plekken: `FEEDBACK_ENDPOINT` en `NEWSLETTER_ENDPOINT` in `tools/build_articles.py`, `BEZWAAR_ENDPOINT` in `public/bezwaar.html`, `VRAAG_ENDPOINT` in `public/vraag-stellen.html`, `NOMINATIE_ENDPOINT` in `public/nomineren.html` en `HOF_ENDPOINT_BASE` in `tools/build_halloffame.py`. Alle builders draaien, committen, pushen (deploy zet het op Pages én VPS).
8. **Caddy op het domein zetten:** in `/etc/caddy/Caddyfile` het blok `:80` vervangen door `eaa-monitor.nl` en het www-redirect-blok aanzetten, daarna `systemctl reload caddy`. Caddy haalt automatisch een TLS-certificaat zodra de DNS wijst.
9. **Nameservers omzetten bij One.com:** van `renan/maya.ns.cloudflare.com` naar de drie Hetzner-nameservers die de zone uit stap 5 opgeeft.
10. **Controleren:** `dig eaa-monitor.nl` wijst naar de VPS, https werkt met geldig certificaat, nieuwsbrief-, vraag-, bezwaar- en nominatieformulier doen het (bevestigingsmails komen nu van AhaSend), mail naar info@ komt aan, Plausible telt nog, en een proefbezwaar opent een PR.
11. **Cloudflare Worker een week laten draaien** voor bevestigingslinks die nog onderweg zijn (tokens zijn 7 dagen geldig). Daarna de Worker en de KV-namespace verwijderen en stap 6 desgewenst nog één keer draaien voor nakomers.
12. **De footer-sectie "Europese infrastructuur" toevoegen.** Formuleer eerlijk: hosting, formulieren, statistieken en e-mailverzending zijn Europees en bezoekersverkeer raakt geen Amerikaanse dienst; wie ons mailt of een formulier instuurt, bereikt een postbus die (voorlopig) bij Google draait. Zie ook "Welke claim mag wanneer".

## Restplan B: ontwikkelketen naar Codeberg (fase 3)

Kan los van de cutover, ervoor of erna; erna is aan te raden zodat niet alles tegelijk verandert.

1. **Repo aanmaken op Codeberg** (zelfde naam, openbaar) en de GitHub-repo pushen (`git push --mirror`). Vanaf dan is Codeberg de bron van waarheid; GitHub wordt alleen-lezen.
2. **PR-helper omzetten naar de Forgejo-API.** `createDataPR` in `worker/src/index.js` gebruikt nu de GitHub-API. De Forgejo-API van Codeberg kan hetzelfde, zelfs simpeler (geverifieerd op 12 juni tegen `codeberg.org/swagger.v1.json`): `PUT /api/v1/repos/{owner}/{repo}/contents/{filepath}` accepteert een `new_branch`-veld, dus bestand-ophalen, branch-maken en committen worden samen twee calls (GET contents voor de sha, PUT met `new_branch`), en `POST /api/v1/repos/{owner}/{repo}/pulls` opent de PR. Idempotentie blijft: een tweede commit naar dezelfde `new_branch` faalt en wordt "already_submitted". Auth: header `Authorization: token <CODEBERG_TOKEN>`. Token aanmaken met alleen repo-schrijfrechten, in `/etc/eaa-forms.env`, en `GITHUB_TOKEN` daar verwijderen. Eerst de endpoints met een kleine handmatige call testen (werkregel: API's eerst verifiëren), dan één proefbezwaar end-to-end.
3. **Deploy van Codeberg naar de VPS.** De GitHub Action vervalt. In de plaats: een Codeberg-webhook (push op `main`, met HMAC-secret) naar een klein deploy-endpoint op de VPS dat `git pull`, de builders, `npm run build:css` en de rsync naar `/var/www/eaa-monitor` draait, plus een herstart van `eaa-forms` als de worker-bestanden wijzigden. Terugvaloptie als webhooks gedoe geven: een cron die elke tien minuten `git fetch` doet en alleen bij nieuwe commits deployt. Handmatige deploy blijft altijd mogelijk (zie `server.md`).
4. **Wekelijkse scrape naar de VPS.** De maandag-cron (08:00 UTC, nu GitHub Actions met 8 shards) wordt een cronjob op de VPS die `scrape_footer.py` per dataset draait (Playwright en Chromium staan dan lokaal; sequentieel of met een paar parallelle processen, er is geen Actions-tijdslimiet meer) en de resultaten naar Codeberg pusht met een deploy key. De push triggert via stap 3 vanzelf de site-deploy. De shard-logica blijft in de tool zitten maar is op de VPS niet nodig.
5. **GitHub afronden.** Workflows verwijderen, repo archiveren met een README-verwijzing naar Codeberg. GitHub Pages vervalt vanzelf (de DNS wijst er na de cutover al niet meer heen).
6. **Documentatie bijwerken:** `CLAUDE.md` (deploy, cron, PR-flows), `server.md`, `worker/DEPLOY.md`, de SOP's (`handle_objection.md`, `handle_nominatie.md`: PR's staan voortaan op Codeberg) en het friction-log.

## Opruimlijst (na afloop)

- Cloudflare: Worker, KV-namespace en daarna de hele DNS-zone verwijderen; account kan weg.
- Resend: account opzeggen (na de naweek van cutover-stap 11).
- Brevo: account opzeggen; de Brevo-DNS-records komen al niet mee naar Hetzner.
- GitLab-account: ongebruikt, kan weg (besluit 2).
- DMARC aanscherpen van `p=none` naar `p=quarantine` en later `p=reject`, zodra een paar weken alle mail netjes via AhaSend en Google loopt.

## Kosten na de migratie

| Wat | Kosten |
|---|---|
| Hetzner CX23 (server, incl. btw) | €3,99/mnd |
| Hetzner DNS | gratis |
| AhaSend (tot 1.000 mails/mnd) | gratis |
| Codeberg (non-profit; doneren is sympathiek) | gratis |
| Plausible | bestaand abonnement |
| Vervallen: Cloudflare, Resend, Brevo, GitHub | €0 |

## Welke claim mag wanneer

- **Nu (na fase 1):** de browser van een bezoeker maakt geen enkel verzoek meer naar een Amerikaanse dienst, maar de site wordt nog gesérveerd vanaf Amerikaanse hosting. Nog geen volledige EU-claim.
- **Na restplan A:** "Deze website draait volledig op Europese infrastructuur: hosting in Duitsland (Hetzner), Nederlands domein (SIDN), Europese statistieken (Plausible) en e-mailverzending (AhaSend, Nederland)." Bezoekersverkeer en formulierverwerking raken geen Amerikaanse dienst meer. Eerlijke kanttekening die we niet in de footer hoeven te zetten maar wel moeten weten: de póstbus achter info@/vragen@/bezwaar@ draait bij Google, dus de inhoud van binnengekomen mail (waaronder formulier-notificaties) staat daar.
- **Na restplan B:** ook de ontwikkelketen (code, CI, cron) is Europees.
- **Helemaal compleet** wordt het pas als ook de inkomende mail naar een EU-provider gaat, zie hieronder.

## Vervolgstap (los van deze migratie): inkomende mail naar de EU

De Google Workspace-groepen werken en blijven voorlopig. Wil je later ook dit stuk Europees: mailbox.org (Duits, ~€3/mnd) of Infomaniak (Zwitsers, gratis instap) kunnen postbus plus aliassen voor de drie adressen leveren; de wissel is dan alleen MX-records omzetten in de Hetzner-zone en de groepen opheffen. Daarna kan ook de DMARC-policy strakker.

## Aandachtspunten

- De formulieren-service eerst volledig getest hebben (incl. AhaSend en het PR-token) vóór de DNS-verhuizing, anders breken de formulieren.
- Bij elke mailwijziging één echte end-to-end-test doen en de headers controleren (SPF/DKIM/DMARC op pass), niet alleen op de API-respons vertrouwen.
- De Dataset JSON-LD, llms.txt-regio's en sitemap blijven onveranderd werken; alleen de deploy-route verandert.
- Per server documenteren: IP, SSH-toegang, stack en deploy-procedure (staat in `server.md`; actueel houden).
- Backups: de site en data staan in git, maar `/var/lib/eaa-forms/kv.json` (abonnees, straks stemmen) niet. Bij restplan B een nachtelijke dump van dat bestand meenemen (bijvoorbeeld versleuteld naar Hetzner Storage Box of een tweede locatie), plus Hetzner-server-backups aanzetten (±20% van de serverprijs).

## Bronnen

- [AhaSend API: send message](https://ahasend.com/docs/send-api/send-email)
- [Forgejo API (Codeberg): swagger](https://codeberg.org/swagger.v1.json) — contents-PUT met `new_branch`, pulls-POST, branches-POST geverifieerd 12 juni 2026
- [Hetzner DNS](https://dns.hetzner.com)
- [Brevo: limieten gratis plan](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) (historisch; besluit is AhaSend)
