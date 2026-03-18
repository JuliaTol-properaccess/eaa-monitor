# EAA Monitor

Dashboard dat controleert of Nederlandse webshops een toegankelijkheidsverklaring hebben in hun footer, zoals vereist door de European Accessibility Act (EAA).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools).

- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks
- `data/webshops.json` — Handmatig samengestelde lijst van te controleren webshops
- `data/results.json` — Automatisch gegenereerde scrape-resultaten (niet handmatig bewerken)
- `public/index.html` + `public/app.js` — Statisch dashboard (HTML + Tailwind + vanilla JS)
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
```

## Webshops toevoegen

Voeg entries toe aan `data/webshops.json`:
```json
{ "name": "Naam", "url": "https://www.voorbeeld.nl", "category": "categorie" }
```

Categorieen: `marketplace`, `elektronica`, `mode`, `supermarkt`, `drogisterij`, `wonen`, `sport`, `boeken`, `speelgoed`, `overig`
