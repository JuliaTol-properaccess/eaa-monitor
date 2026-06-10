# Migratie naar een Europese stack

*Stand: 10 juni 2026. Prijzen zijn indicatief en exclusief btw; controleer ze op het moment van keuze.*

## Waarom dit document

We willen in de footer kunnen zeggen dat eaa-monitor.nl op Europese diensten draait. Dat kan nu niet: alleen het domein is Europees, de rest van de stack is Amerikaans. Dit document beschrijft per onderdeel wat er moet gebeuren, wat het kost en hoeveel werk het is.

## Huidige stack

| Onderdeel | Dienst | Herkomst |
|---|---|---|
| Domeinregistratie | One.com (registrar), SIDN (.nl-register) | Denemarken / Nederland |
| Statistieken | Plausible Analytics | Estland (hosting in Duitsland) |
| DNS | Cloudflare | VS |
| Hosting | GitHub Pages (Microsoft) | VS |
| Formulieren en nieuwsbrief | Cloudflare Worker + KV | VS |
| E-mailverzending | Resend | VS |
| Fonts | Google Fonts (CDN) | VS |
| CSS | Tailwind via cdn.tailwindcss.com | VS |
| Code en wekelijkse scrape | GitHub + GitHub Actions | VS |

Alleen de domeinlaag is dus al Europees. Alles wat een bezoeker raakt (hosting, DNS, fonts, formulieren, mail) loopt via Amerikaanse bedrijven.

## Wat er per onderdeel moet gebeuren

### 1. Fonts zelf hosten — €0, 0,5 tot 1 uur — ✅ gedaan (10 juni 2026)

Download Montserrat en serveer hem vanaf de eigen site (`public/static/fonts/`). Daarmee verdwijnt het verzoek naar Google volledig. Dit is ook los van de EU-claim verstandig: Duitse rechters oordeelden al dat het doorsturen van bezoekers-IP's naar Google Fonts een AVG-probleem is. Alternatief zonder zelf hosten: Bunny Fonts (Sloveens, gratis, drop-in vervanger), maar zelf hosten is netter en sneller.

### 2. Tailwind lokaal bouwen — €0, 1 tot 2 uur — ✅ gedaan (10 juni 2026)

`cdn.tailwindcss.com` is bedoeld voor ontwikkeling, niet voor productie. Vervang het door een lokale Tailwind-build die één CSS-bestand genereert (build-stap in de deploy). Sneller voor bezoekers en weer een Amerikaans verzoek minder.

### 3. DNS verhuizen — €0, ongeveer 0,5 uur

Verhuis de DNS van Cloudflare naar Hetzner DNS (gratis) of naar One.com (zit bij de registrar inbegrepen). Let op: dit kan pas nadat de Worker is vervangen (stap 5), want de Worker draait op Cloudflare.

### 4. Hosting naar Hetzner — circa €4,50 per maand, 2 tot 4 uur

Eén Hetzner Cloud VPS (CX22, instapmodel, conform onze standaard) in Falkenstein of Neurenberg, met Caddy of nginx voor de statische site. De deploy wordt: build draaien en `public/` naar de server synchroniseren. HTTPS regelt Caddy automatisch.

Gratis EU-alternatief: Codeberg Pages (Duitse non-profit). Maar omdat we toch een server nodig hebben voor de formulieren en de scraper (stap 5 en 7), is één VPS die alles doet logischer.

### 5. Formulieren-Worker vervangen — €0 extra, 4 tot 8 uur

De Cloudflare Worker (bezwaar, anonieme vragen, artikel-feedback, nieuwsbrief met dubbele opt-in) wordt een klein Node-dienstje op dezelfde VPS. De KV-opslag voor nieuwsbriefadressen wordt SQLite of een JSON-bestand op de server. De routes en de domein-verificatielogica verhuizen één-op-één mee; de frontend hoeft alleen andere endpoint-URL's.

### 6. E-mail van Resend naar een Europese dienst — €0 tot €1 per maand, 1 tot 2 uur

Ons volume is klein (bevestigingsmails en notificaties). Twee geverifieerde opties:

- **Scaleway TEM** (Frans): 300 mails per maand gratis, daarna €0,25 per 1.000. Pay-as-you-go, geen vast bedrag.
- **Brevo** (Frans): 300 mails per dag gratis (campagne- en transactiemail delen die limiet).

Beide hebben een gewone REST-API; de centrale verzendfunctie in de Worker-code hoeft alleen een ander endpoint en andere headers.

### 7. Wekelijkse scrape van GitHub Actions naar de VPS — €0 extra, 2 tot 4 uur

De maandag-cron draait nu op GitHub Actions met 8 shards. Op de VPS wordt dat een cronjob die `scrape_footer.py` draait (Playwright en Chromium werken prima op een Linux-VPS) en de resultaten naar de repo pusht. De 10.000 webshops kunnen 's nachts sequentieel of met een paar parallelle processen; het hoeft niet binnen een Actions-tijdslimiet te passen.

### 8. Optioneel, strengste variant: code weg van GitHub — €0, 4 tot 8 uur

De repo verhuizen naar Codeberg (Duits). Dit is alleen nodig als je de claim wilt oprekken naar "alles, ook onze eigen ontwikkeltools". Voor de footer-claim is het niet nodig: de code is openbaar en bevat geen bezoekersdata.

## Kosten en uren samengevat

| Fase | Wat | Kosten | Werk |
|---|---|---|---|
| 1. Quick wins | Fonts zelf hosten, Tailwind lokaal | €0 | 2 tot 3 uur |
| 2. Kern | VPS, site-hosting, Worker-vervanger, EU-mail, DNS, scraper-cron | circa €4,50/mnd (~€54/jr) + €0 tot €1/mnd mail | 10 tot 18 uur |
| 3. Optioneel | Code naar Codeberg | €0 | 4 tot 8 uur |

## Welke claim mag wanneer

- **Nu:** alleen "ons .nl-domein is geregistreerd bij een Europese registrar". Te mager voor een footer-sectie.
- **Na fase 1 (✅ 10 juni 2026):** de browser van een bezoeker maakt geen enkel verzoek meer naar een Amerikaanse dienst (fonts zelf-gehost, Tailwind lokaal gebouwd, statistieken via het Europese Plausible). Maar de site wordt nog steeds gesérveerd vanaf Amerikaanse hosting, dus nog geen volledige EU-claim.
- **Na fase 2:** "Deze website draait volledig op Europese infrastructuur: hosting in Duitsland (Hetzner), Nederlands domein (SIDN), Europese e-mail." Dit is de eerlijke ondergrens voor de footer-sectie; bezoekersdata raakt dan geen enkele Amerikaanse dienst meer.
- **Na fase 3:** ook de ontwikkelketen is Europees.

## Aandachtspunten

- De Worker-vervanger eerst live zetten en testen vóór de DNS-verhuizing, anders breken de formulieren.
- **Inkomende mail**: info@, vragen@ en bezwaar@eaa-monitor.nl bestaan alleen als doorstuuradressen in Cloudflare Email Routing. Dat stopt zodra de DNS-zone weg is bij Cloudflare. Vóór de verhuizing een vervanger regelen, bijvoorbeeld e-mail/doorsturen bij One.com (zit vaak bij het domeinpakket) en de nieuwe MX-records meenemen in de DNS-migratie.
- **Brevo**: het versturen werkt pas als (1) de server-IP's geautoriseerd zijn onder Security → Authorised IPs, en (2) het domein eaa-monitor.nl geverifieerd is onder Senders & Domains (DKIM-records; kan nu al, de DNS staat nog bij Cloudflare).
- Bij de mailmigratie opnieuw SPF/DKIM instellen voor eaa-monitor.nl bij de nieuwe dienst.
- De Dataset JSON-LD, llms.txt-regio's en sitemap blijven onveranderd werken; alleen de deploy-route verandert.
- Per server documenteren: IP, SSH-toegang, stack en deploy-procedure (conform onze hostingstandaard).

## Cutover-draaiboek (DNS-verhuizing)

*Stand van de voorbereiding: server, site, formulieren-service en Brevo-mail draaien en zijn getest (10 juni 2026). De stappen hieronder zijn wat er nog rest.*

### Vooraf (kan ruim voor de cutover)

1. **GitHub-token op de server.** Fine-grained PAT (Contents + Pull requests: read & write op de eaa-monitor-repo) als `GITHUB_TOKEN` in `/etc/eaa-forms.env`, daarna `systemctl restart eaa-forms`. Zonder dit kan de service geen bezwaar-PR's openen.
2. **Inkomende mail regelen.** info@, vragen@ en bezwaar@eaa-monitor.nl zijn nu doorstuuradressen in Cloudflare Email Routing; dat stopt bij de verhuizing. Vervanging: e-mail/doorsturen bij One.com aanzetten en de bijbehorende MX-records noteren voor stap 4.
3. **DNS-zone exporteren uit Cloudflare** (DNS → Records → Export) als referentie.
4. **Zone aanmaken bij Hetzner DNS** (dns.hetzner.com, zelfde login): `A eaa-monitor.nl → 128.140.50.96`, `AAAA → 2a01:4f8:c014:6c5d::1`, `CNAME www → eaa-monitor.nl`, de Brevo-records (DKIM, uit Brevo → Senders & Domains), de MX-records uit stap 2, plus wat er verder nog relevant is uit de export. De GitHub Pages-records niet meenemen.
5. **Nieuwsbrief-abonnees meenemen.** Bevestigde adressen staan in de Cloudflare KV-namespace `NEWSLETTER` (sleutels `sub:<email>`). Exporteren met `wrangler kv key list/get --remote` en importeren in `/var/lib/eaa-forms/kv.json` op de server.

### De cutover zelf (rustig moment, ±30-60 minuten)

6. **Frontend-endpoints omzetten** van `https://eaa-bezwaar.juliatol.workers.dev/...` naar `https://eaa-monitor.nl/api/...` op vier plekken: `FEEDBACK_ENDPOINT` en `NEWSLETTER_ENDPOINT` in `tools/build_articles.py`, `BEZWAAR_ENDPOINT` in `public/bezwaar.html`, `VRAAG_ENDPOINT` in `public/vraag-stellen.html`, en de gebakken `data-endpoint`-attributen in de footers van de handgeschreven pagina's. Builders draaien, committen, pushen (deploy zet het op Pages én VPS).
7. **Caddy op het domein zetten:** in `/etc/caddy/Caddyfile` het blok `:80` vervangen door `eaa-monitor.nl` en het www-redirect-blok aanzetten, daarna `systemctl reload caddy`. Caddy haalt automatisch een TLS-certificaat zodra de DNS wijst.
8. **Nameservers omzetten bij One.com:** van `renan/maya.ns.cloudflare.com` naar de drie Hetzner-nameservers die de zone uit stap 4 opgeeft.
9. **Controleren:** `dig eaa-monitor.nl` wijst naar de VPS, https werkt met geldig certificaat, nieuwsbrief- en vraagformulier doen het, mail naar info@ komt aan, Plausible telt nog.
10. **Cloudflare Worker een week laten draaien** voor bevestigingslinks die nog onderweg zijn (tokens zijn 7 dagen geldig). Daarna kan de Worker uit en kan stap 5 desgewenst nog één keer voor nakomers.
11. **De footer-sectie "Europese infrastructuur" toevoegen**: het oorspronkelijke doel. Pas nu klopt de claim helemaal.

## Bronnen

- [Brevo: limieten gratis plan](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan)
- [Scaleway TEM-prijzen](https://www.scaleway.com/en/pricing/managed-services/)
- [Scaleway TEM-mogelijkheden en limieten](https://www.scaleway.com/en/docs/transactional-email/reference-content/tem-capabilities-and-limits/)
