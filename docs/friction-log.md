# Friction-log EAA Monitor

Bekende valkuilen bij externe API-calls, deploys en config. Check dit bestand
voordat je met Cloudflare, wrangler of e-mail aan de slag gaat. Voeg na afloop
nieuwe frictie toe met datum, context en oplossing.

## 2026-06-12 — lokale DNS-verificatie onbruikbaar: het netwerk onderschept alle DNS-queries

**Context.** Tijdens de DNS-cutover naar Hetzner wilden we de zone en de delegatie
controleren met `dig @hydrogen.ns.hetzner.com` vanaf de lokale machine. De antwoorden
klopten niet: queries kwamen recursief terug (`+norecurse` gaf REFUSED) en zelfs een
query naar het gegarandeerd dode adres 192.0.2.1 kreeg antwoord. Het lokale netwerk
onderschept dus álle DNS-verkeer, ongeacht de opgegeven server. Na de cutover gaf
`curl https://eaa-monitor.nl` lokaal nog `server: GitHub.com` door diezelfde cache.

**Vermijd voortaan.** DNS- en cutover-verificatie nooit vanaf het lokale netwerk doen.
Draai `dig` via SSH op de VPS (`ssh root@128.140.50.96`), en test https op het nieuwe
adres met `curl --resolve eaa-monitor.nl:443:128.140.50.96 https://eaa-monitor.nl/`
zodat de lokale resolver er niet tussen zit.

## 2026-06-12 — Caddy stript `/api`: interne tests op 127.0.0.1:8787 zonder prefix

**Context.** Bij de nominatie-e2e-test op de VPS gaf
`http://127.0.0.1:8787/api/hof/nominate/confirm` een 404. Caddy proxyt `/api/*` met
prefix-stripping naar de Node-service; de Worker-routes kennen dus geen `/api`.

**Vermijd voortaan.** Publiek testen: `https://eaa-monitor.nl/api/<route>`. Intern op
de VPS testen: `http://127.0.0.1:8787/<route>` (zonder `/api`).

## 2026-06-09 — wrangler `email sending list/dns get` geeft 2036 Unauthorized

**Context.** Na het verhuizen van `eaa-monitor.nl` naar Cloudflare wilden we de
verzendkant controleren met `npx wrangler email sending dns get eaa-monitor.nl`
en `... list`. Beide gaven `Unauthorized [code: 2036]`, terwijl `wrangler whoami`
wel `email_sending (write)` toonde en `wrangler deploy` gewoon werkte.

**Wat er aan de hand was.** Dit zijn **open-beta** commando's die op het
OAuth-login-token een autorisatiefout geven op het account-endpoint
`/accounts/.../email/sending/zones`. Het is een kink in de beta-CLI, geen
weerspiegeling van de echte staat van het domein.

**Hoe we het oplosten.** Niet de CLI vertrouwen maar de DNS zelf checken met
`dig`. De setup bleek volledig correct:
- MX: `route1/2/3.mx.cloudflare.net` (Email Routing, ontvangen)
- SPF: precies één record `v=spf1 include:_spf.mx.cloudflare.net ~all`
- DKIM: `cf2024-1._domainkey` met geldige `v=DKIM1; ...` sleutel (dit is de
  selector die Cloudflare Email Sending gebruikt, dus domein is onboarded)

`wrangler deploy` toonde daarna `env.EMAIL (unrestricted)`, wat bevestigt dat de
Worker naar willekeurige ontvangers mag versturen.

**Vermijd voortaan.** Draai `email sending enable` niet nog eens "voor de zekerheid"
als de DKIM/SPF-records al staan, dat kan records dubbel zetten. Verifieer de staat
met `dig` (MX, TXT voor SPF, TXT op `cf2024-1._domainkey`), niet met de beta-CLI.
Wil je de beta-commando's tóch laten werken, dan heb je een API-token met
expliciete Email-permissies nodig in plaats van de OAuth-login.

---

## Scraper boekt false negatives op grote sites (22 juni 2026)

**Context.** bol.com heeft een toegankelijkheidsverklaring maar stond op "zonder
verklaring". Bleek geen toeval: twee structurele lekken in `scrape_footer.py`,
allebei richting vals "zonder", en juist bij de grootste EAA-plichtige merken.

**Wat er aan de hand was.**
1. **Resource-blocking als bot-signatuur.** De scraper blokkeert
   image/media/font/stylesheet via request-interceptie. Sites achter
   bot-management (bol.com) zien dat patroon als bot en serveren een kale
   challenge-pagina (2 links). Testmatrix: mét blocking 2 links/niet gevonden,
   zónder blocking ~1.400 links/verklaring gevonden. De wachttijd (footer-wait
   vs networkidle) maakte niets uit; de blocking wél.
2. **Verklaring-link niet als platte `<a>`.** JS-frameworks (MediaMarkt PWA)
   renderen de link als knop of bewaren hem in embedded JSON (`/`-escaped).
   De `<a href>`-scan miste hem, ook bij volledige render.

**Hoe we het oplosten.**
- `find_statement_in_raw_html()`: fallback die in de gerenderde HTML een URL met
  verklaring-trefwoord zoekt, JSON-escapes normaliseert, en **alleen op het eigen
  domein** matcht (sluit overlay-CDN's als accessibe.com/userway.org uit, voorkomt
  valse treffers uit marketingtekst).
- `recheck_unblocked()`: bij een challenge/lege render (<5 links) één keer
  opnieuw ophalen zonder resource-blocking. Alleen voor verdachte gevallen, dus
  goedkoop. Geverifieerd: bol.com, MediaMarkt, Coolblue, HEMA flippen naar
  GEVONDEN; Decathlon/Kruidvat blijven harde challenge → eerlijk "niet te
  controleren" i.p.v. vals "zonder".

**Vermijd voortaan.** Een "success + niet gevonden" op een grote site is
verdacht: check met een no-block + raw-HTML-render voordat je "zonder verklaring"
als waarheid aanneemt. Verifieer een verklaring altijd op volledige render (geen
resource-blocking), niet op de snelle scrape-context.
