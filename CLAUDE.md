# EAA Monitor

Dashboard dat controleert of Nederlandse webshops een toegankelijkheidsverklaring hebben in hun footer, zoals vereist door de European Accessibility Act (EAA).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools).

- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks
- `tools/scrape_thuiswinkel.py` — Bouwt webshops.json aan met leden van Thuiswinkel.org
- `tools/scrape_webwinkelkeur.py` — Bouwt webshops.json aan met leden van WebwinkelKeur (server-rendered ledenlijst + JSON-LD per profiel; resume-cache in `.tmp/`)
- `data/webshops.json` — Lijst van te controleren webshops (deels handmatig, deels via de scrapers hierboven)
- `data/results.json` — Automatisch gegenereerde scrape-resultaten (niet handmatig bewerken)
- `data/objections.json` — Handmatig bijgehouden lijst van webshops die bezwaar hebben gemaakt tegen vermelding (overlay; sluit ze uit van het dashboard, geen e-mailadressen)
- `public/index.html` + `public/app.js` — Statisch dashboard (HTML + Tailwind + vanilla JS)
- `public/bezwaar.html` — Bezwaarformulier (verstuurt via Formspree naar Julia)
- `public/bezwaren.html` + `public/bezwaren.js` — Openbare lijst van ingediende bezwaren
- `workflows/handle_objection.md` — SOP voor het verwerken van een bezwaar
- `.github/workflows/scrape.yml` — Wekelijkse cron die scrapt en resultaten commit
- `.github/workflows/deploy.yml` — Deploy naar GitHub Pages

## Commando's

```bash
# Scraper draaien
python tools/scrape_footer.py

# Frontend lokaal testen
python -m http.server 8000 -d public

# Playwright installeren (eerste keer)
pip install -r requirements.txt
playwright install chromium
```

## Data flow

```
webshops.json (handmatig) → scrape_footer.py (cron) → results.json (auto) → index.html (statisch)
objections.json (handmatig) → app.js sluit bezwaarmakers uit → bezwaren.html toont ze
```

## Bezwaar tegen vermelding

Webshops die buiten de EAA vallen kunnen via `public/bezwaar.html` bezwaar maken. Julia verwerkt dit handmatig volgens `workflows/handle_objection.md`: na controle een entry toevoegen aan `data/objections.json` (zonder e-mailadres, want de repo is openbaar). De frontend sluit die webshops client-side uit van tabel en cijfers en toont ze op `public/bezwaren.html`.

## Webshops toevoegen

Voeg entries toe aan `data/webshops.json`:
```json
{ "name": "Naam", "url": "https://www.voorbeeld.nl", "category": "categorie" }
```

Categorieen: `marketplace`, `elektronica`, `mode`, `supermarkt`, `drogisterij`, `wonen`, `sport`, `boeken`, `speelgoed`, `overig`

### Bronnen voor bulk-uitbreiding

- **Thuiswinkel.org** en **WebwinkelKeur** publiceren een doorzoekbare ledenlijst, gescraped via de tools hierboven.
- **Stichting Webshop Keurmerk** (keurmerk.info) publiceert geen ledenregister, alleen een per-webshop verificatietool. Niet bulk-scrapebaar.
- **Twinkle100 / Emerce100** zijn kleine ranglijsten (~100 grote namen) met veel overlap; sneller om gericht te diffen tegen bekende grote shops dan apart te scrapen.
- We richten ons bewust op shops die bij een keurmerk/vakorganisatie zijn aangesloten. Webshops die nergens bij aangesloten zijn, zijn vaak micro-ondernemingen (<10 medewerkers, <€2 mln omzet) en daarmee vrijgesteld van de EAA.
