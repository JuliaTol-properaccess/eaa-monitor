# EAA Monitor

Hub over de European Accessibility Act (EAA) in Nederland. Het dashboard controleert wekelijks of Nederlandse webshops (ACM-toezicht) en financiële instellingen (AFM-toezicht) een toegankelijkheidsverklaring hebben in hun footer; de kennisbank legt uit hoe de wet werkt (scope, toezicht, boetes, mythes).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools). Statische site (HTML + Tailwind via CDN + vanilla JS). Design: **Coinbase-look** (navy/Coinbase-blauw, Inter), bewust losgemaakt van het Proper Access-merk; Proper Access blijft in footer-attributie en schema.

### Tools
- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks, en bij elke scrape de cijfers + Dataset JSON-LD in de doel-HTML en de meet-regio in `llms.txt` bakt. **Twee datasets** via `--dataset {webshops,financieel}` (default `webshops`): `webshops` bakt in `index.html`, `financieel` in `monitor-financieel.html` + een hub-kaart op `index.html` (markers `STAT:finTotal`/`STAT:finPctWithout`)
- `tools/build_articles.py` — Artikelgenerator: rendert `content/artikelen/*.md` → `public/artikelen/*.html`, bouwt `public/artikelen.html`, regenereert `sitemap.xml` en patcht de artikellijst-regio in `llms.txt`
- `tools/build_auditbureaus.py` — Rendert `data/auditbureaus.json` → `public/wcag-audit.html` (server-rendered tabel). Deelt head/header/footer met `build_articles.py`
- `tools/build_vragen.py` — Rendert `data/vragen.json` → `public/vragen.html` (server-rendered vraag-en-antwoord met FAQPage JSON-LD). Deelt head/header/footer met `build_articles.py`
- `tools/build_bronnen.py` — Rendert `data/bronnen.json` → `public/bronnen.html` (server-rendered, filterbaar bronnenoverzicht). Deelt head/header/footer met `build_articles.py`; de filters/zoek werken client-side via `public/static/bronnen.js`
- `tools/build_halloffame.py` — Rendert `data/halloffame.json` → `public/eregalerij.html` (server-rendered, met ItemList JSON-LD). Slaat entries zonder `observaties` over met een waarschuwing (vangrail tegen te vroeg gemergde nominatie-PR's). Stemtellers komen client-side van de Worker via `public/static/halloffame.js`. Deelt head/header/footer met `build_articles.py`
- `tools/fetch_bron_dates.py` — Best-effort: haalt elke bron-URL op en vult `date` aan in `data/bronnen.json` (uit `datePublished`/`article:published_time`/`<time>`). Verzint nooit een datum; vindt het niets, dan blijft het veld leeg
- `tools/scrape_thuiswinkel.py` / `tools/scrape_webwinkelkeur.py` — Bouwen `webshops.json` aan met keurmerk-leden

### Data
- `data/webshops.json` — Lijst van te controleren webshops (deels handmatig, deels gescraped)
- `data/results.json` — Automatisch gegenereerde scrape-resultaten (niet handmatig bewerken)
- `data/financieel.json` — Handmatig samengestelde lijst van financiële instellingen uit de AFM/DNB-registers (velden: `name`, `url`, `category` ∈ `bank`/`verzekeraar`/`betaaldienst`/`beleggen`/`lease`, optioneel `bron`). Zelfde schema als `webshops.json`
- `data/results-financieel.json` / `data/history-financieel.json` — Automatisch gegenereerd door de financiële scrape (niet handmatig bewerken)
- `data/objections.json` — Webshops met bezwaar (overlay; client-side uitgesloten, geen e-mailadressen). Bijgewerkt via PR's van de bezwaar-Worker of handmatig
- `data/auditbureaus.json` — Handmatig samengestelde lijst van auditbureaus voor de WCAG-audit-pagina (velden: `naam`, `website`, `specialisatie`, `talen`)
- `data/vragen.json` — Handmatig samengestelde lijst van beantwoorde praktijkvragen (velden: `vraag`, `antwoord`, optioneel `toezichthouder`, `datum`, `thema`, `bron`). Gevuld vanuit binnengekomen anonieme vragen; nooit antwoorden verzinnen
- `data/bronnen.json` — Externe bronnen over de EAA voor de bronnenpagina (velden: `title`, `url`, `author`, `category`, optioneel `date`). `category` uit de vaste lijst in `build_bronnen.py`. `date` wordt aangevuld door `fetch_bron_dates.py`
- `data/halloffame.json` — Eregalerij-vermeldingen (velden: `naam`, `url`, `slug`, `datum`, `motivatie`, `observaties` met `titel`/`beschrijving`/`code`/`wcag`, optioneel `categorie`, `hulptechnologie`). De Worker voegt entries toe via PR's (nominatieflow); Julia vult `observaties` bij review (zie `workflows/handle_nominatie.md`). **Nooit e-mailadressen** in dit bestand; `slug` na publicatie niet wijzigen (stemtellers hangen eraan)

### Pagina's (`public/`)
- `index.html` — Hub-homepage: cijfer-gedreven hero, kerncijfers, uitgelichte artikelen. **Bevat de scraper-markers** (zie hieronder); niet verwijderen
- `monitor.html` + `app.js` — Het interactieve dashboard (grafiek/tabel, filters, sorteerbare tabel). Leest `?q=` uit de URL voor de zoekterm vanaf de home. `app.js` is config-gestuurd via `window.EAA_MONITOR_CONFIG` (`dataUrl`, `noun`, `categoryLabels`, `sortLabels`); zonder config gelden de webshop-defaults
- `monitor-financieel.html` — Hetzelfde dashboard voor de financiële sector (AFM-toezicht), met eigen config (leest `data/results-financieel.json`, "Type"-kolom). **Bevat de scraper-markers**; gevuld door `scrape_footer.py --dataset financieel`. Deelt `app.js`
- `artikelen.html` + `artikelen/*.html` — Kennisbank, **gegenereerd** door `build_articles.py` (niet handmatig bewerken)
- `wcag-audit.html` — Overzicht van auditbureaus, **gegenereerd** door `build_auditbureaus.py` uit `data/auditbureaus.json` (niet handmatig bewerken)
- `vragen.html` — Vragen uit de praktijk, **gegenereerd** door `build_vragen.py` uit `data/vragen.json` (niet handmatig bewerken)
- `vraag-stellen.html` — Anoniem vraagformulier → bezwaar-Worker (`VRAAG_ENDPOINT`, route `/vraag`). Handgeschreven
- `bronnen.html` — Doorzoekbaar bronnenoverzicht met categoriefilters, **gegenereerd** door `build_bronnen.py` uit `data/bronnen.json` (niet handmatig bewerken)
- `eregalerij.html` — Hall of fame van aantoonbaar toegankelijke websites, **gegenereerd** door `build_halloffame.py` uit `data/halloffame.json` (niet handmatig bewerken). Stemtellers en stemformulieren via `static/halloffame.js` (progressive enhancement: zonder JS verborgen)
- `nomineren.html` — Nominatieformulier voor de eregalerij → bezwaar-Worker (`NOMINATIE_ENDPOINT`, route `/hof/nominate`). Handgeschreven
- `bezwaar.html` — Bezwaarformulier → bezwaar-Worker (`BEZWAAR_ENDPOINT`), valt terug op Formspree
- `bezwaren.html` + `bezwaren.js` — Openbare lijst van bezwaren
- `over.html` — Over het dashboard
- `static/theme.js` — Gedeelde Tailwind-tokens (één bron van waarheid). `static/site.css` — componenten, prose, animaties. `static/reveal.js` — scroll-reveal

### Designtokens (`public/static/theme.js`)
- `brand` `#0052FF` (primair), `navy` `#0A0E27` (donkere secties/hero), `softblue` `#F5F8FF`, status `found`/`notfound`/`error`. Font: **Inter**. De oude PA-tokens (magenta/petrol) zijn vervangen.

### Overig
- `worker/` — Cloudflare Worker voor bezwaren met domein-verificatie, artikel-feedback, anonieme vragen, nieuwsbrief-opt-in én de eregalerij (zie `worker/DEPLOY.md`). Routes: `POST /submit`, `GET /confirm`, `POST /feedback`, `POST /vraag`, `POST /newsletter`, `GET /newsletter/confirm`, `GET /newsletter/unsubscribe`, `POST /hof/nominate`, `GET /hof/nominate/confirm`, `POST /hof/vote`, `GET /hof/vote/confirm`, `GET /hof/votes`. De eregalerij-flows: nomineren = dubbele opt-in → PR op `data/halloffame.json` (zelfnominatie wordt gevlagd, nooit auto-live); stemmen = dubbele opt-in, 1 stem per gehasht e-mailadres per `slug` in KV (`hof:vote:`/`hof:count:`), eigen-domein-stemmen geweigerd; `GET /hof/votes` levert de tellers (gecachet) aan `static/halloffame.js`. `/feedback` mailt een opmerking over een artikel rechtstreeks naar `NOTIFY_EMAIL`; `/vraag` mailt een anonieme EAA-vraag naar `VRAGEN_EMAIL` (`vragen@eaa-monitor.nl`, terugval op `NOTIFY_EMAIL`) — beide zonder PR, opslag of extra secrets. `/newsletter` is een dubbele opt-in: na bevestiging via een getekende link wordt het adres opgeslagen in de KV-namespace `NEWSLETTER` (sleutel `sub:<email>`); afzender `NEWSLETTER_FROM` (terugval op `FROM_EMAIL`). Het inschrijfformulier staat in de footer (`site_footer()` in `build_articles.py`, endpoint in `NEWSLETTER_ENDPOINT`, submit-logica in `public/static/newsletter.js`). Onder elk artikel staat een bron-disclaimer + feedbackformulier dat `build_articles.py` rendert (endpoint in `FEEDBACK_ENDPOINT`). Na Worker-wijziging opnieuw deployen.
- `workflows/handle_objection.md` — SOP voor het verwerken van een bezwaar
- `workflows/handle_vraag.md` — SOP voor het verwerken van een binnengekomen anonieme vraag (voorleggen aan toezichthouder, antwoord in `data/vragen.json`)
- `workflows/handle_nominatie.md` — SOP voor het verwerken van een eregalerij-nominatie (toegankelijkheidscheck, geverifieerde observaties schrijven, PR mergen)
- `.github/workflows/scrape.yml` — Wekelijkse cron die scrapt en resultaten commit
- `.github/workflows/deploy.yml` — Deploy naar GitHub Pages (kopieert de hele `public/`-tree recursief)

## Auto-gegenereerde regio's (niet breken)

`scrape_footer.py` vervangt bij elke scrape de inhoud tussen letterlijke markers in de doel-HTML (`index.html` voor webshops, `monitor-financieel.html` voor financieel): `GEO-SUMMARY:START/END`, `STAT:total`, `STAT:pctWith`, `STAT:pctWithout`, `LASTUPDATED`, `JSONLD-DATASET:START/END`. Elke `STAT`-marker mag maar **één keer** voorkomen (de vervanging pakt alleen de eerste match). De financiële run patcht daarnaast de hub-kaart op `index.html` (`STAT:finTotal`/`STAT:finPctWithout`). `llms.txt` heeft drie marker-regio's: `MEASUREMENT` (webshop-scraper), `FIN-MEASUREMENT` (financiële scraper) en `ARTICLES` (`build_articles.py`).

## Commando's

```bash
# Scraper draaien (volledige lijst, sequentieel)
python tools/scrape_footer.py

# Financiële sector scrapen (kleine lijst, geen sharding)
python tools/scrape_footer.py --dataset financieel

# Sharded draaien (zoals de cron): 1 van de 8 delen, daarna mergen
python tools/scrape_footer.py --shard 0 --num-shards 8 --out results.part-0.json
python tools/scrape_footer.py --merge <map-met-part-bestanden>

# Artikelen (her)bouwen na een wijziging in content/artikelen/
python tools/build_articles.py

# WCAG-audit-pagina (her)bouwen na een wijziging in data/auditbureaus.json
python tools/build_auditbureaus.py

# Praktijkvragen-pagina (her)bouwen na een wijziging in data/vragen.json
python tools/build_vragen.py
# Bronnenpagina (her)bouwen na een wijziging in data/bronnen.json
python tools/build_bronnen.py

# Eregalerij (her)bouwen na een wijziging in data/halloffame.json
python tools/build_halloffame.py

# Publicatiedatums aanvullen in data/bronnen.json (best-effort, haalt de URL's op)
python tools/fetch_bron_dates.py            # alleen ontbrekende
python tools/fetch_bron_dates.py --overwrite  # ook bestaande opnieuw

# Frontend lokaal testen
python -m http.server 8000 -d public

# Playwright installeren (eerste keer)
pip install -r requirements.txt
playwright install chromium
```

## Data flow

```
webshops.json (handmatig) → scrape_footer.py (cron) → results.json (auto) → index.html (statisch)
content/artikelen/*.md → build_articles.py → public/artikelen/*.html + artikelen.html + sitemap.xml
data/bronnen.json → fetch_bron_dates.py (datums) → build_bronnen.py → public/bronnen.html
bezwaar.html → Worker → PR op objections.json → app.js sluit bezwaarmakers uit → bezwaren.html toont ze
```

## Artikel schrijven

Maak `content/artikelen/<slug>.md` met YAML-frontmatter (`title`, `slug`, `description`, `date`, `theme` uit scope/toezicht/praktijk/mythes, optioneel `keywords` en `sources`). Schrijf de body in markdown; raw HTML mag (de scope-checker is zo ingebed). Draai daarna `python tools/build_articles.py`. Toon volgens de nlds-schrijfwijzer (je-vorm, geen jargon, geen em-dashes). **Nooit cijfers verzinnen**; onbevestigde claims als zodanig markeren.

## Bezwaar tegen vermelding

Webshops die buiten de EAA vallen kunnen via `public/bezwaar.html` bezwaar maken. Het formulier gaat naar de bezwaar-Worker (`worker/`), die twee routes kiest:

- **Automatisch (domein-geverifieerd):** staat het e-mailadres op het webshop-domein, dan stuurt de Worker een bevestigingslink naar dat adres. Na het klikken opent de Worker een PR op `data/objections.json`. Julia controleert kort en merget. De domeincheck voorkomt dat een concurrent een ander laat verwijderen.
- **Handmatig (geen domeinmatch):** bij een adres buiten het domein mailt de Worker naar Julia, die het bezwaar verwerkt volgens `workflows/handle_objection.md`.

De frontend sluit bezwaarmakers client-side uit van tabel en cijfers en toont ze op `public/bezwaren.html`. Entries bevatten nooit een e-mailadres, want de repo is openbaar. Uitrol en beheer van de Worker staan in `worker/DEPLOY.md`.

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
