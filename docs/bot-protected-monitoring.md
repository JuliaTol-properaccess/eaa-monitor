# Bot-beschermde sites apart checken

**Status:** plan, nog niet geïmplementeerd. Opgesteld 22 juni 2026.

## Probleem

Een handvol grote, EAA-plichtige ketens zit achter zwaar bot-management
(Akamai / Cloudflare / DataDome). Headless Chromium op onze Hetzner-VPS krijgt
daar consequent een challenge-pagina terug (0-2 links) in plaats van de echte
site. `scrape_footer.py` kan ze daardoor niet betrouwbaar controleren; ze landen
op "niet te controleren". Voor bekende merken als Kruidvat is dat niet goed
genoeg: de bezoeker verwacht juist hier een uitspraak.

De twee structurele scraper-lekken zijn al gedicht (no-block retry + raw-HTML
fallback, zie `docs/friction-log.md` en `tools/scrape_footer.py`). Die lossen de
bol.com- en MediaMarkt-klasse op, maar niet de echt hard beschermde sites: die
geven óók zonder resource-blocking en na meerdere pogingen een challenge.

De lijst staat in `data/bot-protected.json` (`barrier: hard` = altijd challenge,
`stochastisch` = rendert soms wel). Meetervaring 22 juni 2026.

## Aanpak: twee lagen

- **Laag 1 (bestaand):** `scrape_footer.py` met no-block retry + raw-HTML
  fallback voor de ~10.000 gewone sites.
- **Laag 2 (nieuw):** een aparte checker die alleen `data/bot-protected.json`
  afgaat via een anti-bot-dienst die de challenge oplost, en de geverifieerde
  verklaring-URL terug in `data/results.json` merget (zelfde merge-logica als de
  handmatige correctie van 22 juni: alleen `has_statement=true` zetten bij een
  echte, same-domain verklaring-URL, nooit verzinnen, daarna rebaken).

Laag 2 hoeft niet wekelijks; maandelijks of op verzoek is genoeg voor ~13 sites.

## Tooladvies (research juni 2026)

Volume is laag: ~13-50 sites, 1 footer-check per site, geen login, geen
persoonsgegevens, geen diepe crawl.

### Aanbevolen: gefaseerd

1. **Eerst gratis proberen, zelf-gehost:** Playwright vervangen/aanvullen met
   **nodriver** of **camoufox** op de VPS, eventueel met een residentieel IP.
   In 2026-benchmarks haalt nodriver 28/31 Cloudflare-targets (beter dan
   patchright/camoufox) en camoufox 0% headless-detectie, maar ~40 s per
   Cloudflare-challenge. Geen externe afhankelijkheid, EU-only (onze VPS).
   Nadeel: onderhoud elke paar maanden, en zonder residentieel IP redt het de
   zwaarste (DataDome/Akamai) sites vaak niet.

2. **Als dat de hardste sites niet haalt, een anti-bot-dienst als fallback:**
   - **Scrapfly** (EU-bedrijf, Parijs) — sterkste anti-bot in onafhankelijke
     benchmark (99%). Gratis tier 1.000 credits zonder tijdslimiet; met ASP
     ~10 credits/request, dus ~13-50 requests/maand past ruim gratis. **Eerste
     keus vanwege EU-vestiging en AVG-voorkeur.**
   - **Bright Data Web Unlocker** — gratis tier 5.000 requests/maand, alleen
     succesvolle requests tellen; technisch het sterkst en voor ons volume €0.
     Nadeel: niet-EU (Israël, wel adequaatheidsbesluit). Tweede keus.

### Apify

Apify (Praag, EU) is een orkestratieplatform, geen eigen anti-bot-engine. Voor
puur challenge-bypass voegt het weinig toe boven Scrapfly/Bright Data; je betaalt
voor scheduling/dashboards. Voor ~50 sites/week niet nodig.

### Niet doen

- **ZenRows** (vanaf $69/mnd) en **ScrapingBee** (vanaf $49/mnd): te duur voor
  dit volume, geen permanente gratis tier.

### AVG / EU

Voorkeursvolgorde op EU-vriendelijkheid: zelf-gehost (nodriver/camoufox op
Hetzner) > Scrapfly (FR) / Apify (CZ) > Bright Data (niet-EU).

### Juridisch/ethisch (kort, geen juridisch advies)

We lezen alleen een publieke homepage-footer: geen login, geen persoonsgegevens
(een footerlink is geen PII), 1 request per site, non-profit met publiek belang
(toezicht op EAA-naleving). De vier grenzen uit de NL-rechtsliteratuur (geen
login forceren, geen persoonsgegevens, geen copyright, geen serveroverbelasting)
worden alle vier gerespecteerd. Risicocategorie laag.

## Volgende stap (morgen)

1. Beslissen: eerst zelf-gehost (nodriver/camoufox) proberen, of meteen Scrapfly
   gratis tier als snelste route naar werkende cijfers.
2. `tools/check_bot_protected.py` schrijven: leest `data/bot-protected.json`,
   haalt per site de footer op via de gekozen route, hergebruikt
   `find_statement_in_raw_html` / `check_links_for_statement` uit
   `scrape_footer.py`, en merget geverifieerde vondsten in `results.json` +
   rebaket (`patch_target_html` + `patch_llms_measurement`).
3. Handmatige nacontrole van elke nieuwe "gevonden" voordat het live gaat
   (zoals bij bol.com): alleen een echte same-domain verklaring-URL telt.

## Bronnen

- Scrapfly pricing: https://scrapfly.io/pricing
- Bright Data Web Unlocker: https://brightdata.com/pricing/web-unlocker
- Apify pricing: https://apify.com/pricing
- Playwright stealth benchmark 2026: https://scrapewise.ai/blogs/playwright-stealth-2026
- Anti-detect benchmark 2026 (nodriver/patchright/camoufox): https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/
- NL scraping juridisch kader: https://www.browserless.io/blog/is-web-scraping-legal
