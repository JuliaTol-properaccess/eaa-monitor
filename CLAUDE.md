# EAA Monitor

Dashboard dat controleert of Nederlandse webshops een toegankelijkheidsverklaring hebben in hun footer, zoals vereist door de European Accessibility Act (EAA).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools).

- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks
- `data/webshops.json` — Handmatig samengestelde lijst van te controleren webshops
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
