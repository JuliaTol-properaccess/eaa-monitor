# EAA Monitor

Hub over de European Accessibility Act (EAA) in Nederland. Het dashboard controleert wekelijks in zes sectoren of Nederlandse organisaties een toegankelijkheidsverklaring in hun footer hebben: webshops en e-bookplatforms (ACM), financiële instellingen (AFM), telecomaanbieders (ACM), personenvervoerders (ILT) en mediadiensten (Commissariaat voor de Media). De kennisbank legt uit hoe de wet werkt (scope, toezicht, boetes, mythes).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools). Statische site (HTML + lokaal gebouwde Tailwind + vanilla JS); geen Amerikaanse CDN's of font-diensten meer, zie `docs/eu-stack-migratie.md`. Design: **"De Telling"** (warm papier, loofgroen, okergeel; zie `docs/rebranding/rebranding-voorstel.md`), bewust losgemaakt van het Proper Access-merk; Proper Access blijft in footer-attributie en schema.

### Tools
- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks, en bij elke scrape de cijfers + Dataset JSON-LD in de doel-HTML en de eigen meet-regio in `llms.txt` bakt. **Zes datasets** via `--dataset {webshops,financieel,telecom,vervoer,media,ebooks}` (default `webshops`), volledig config-gestuurd via de `DATASETS`-dict: `webshops` bakt in `index.html` (legacy ongeprefixte markers); elke andere sector bakt in zijn eigen `monitor-<sector>.html` én vult een hub-kaart op `index.html` (markers `STAT:{hub_prefix}Total`/`STAT:{hub_prefix}PctWithout`). Nieuwe sector toevoegen = DATASETS-entry + `data/<sector>.json` + monitorpagina + hub-kaart op index.html + llms-regio. Pagina's met bot-protectie of wachtrij (minder dan 5 links) tellen als "niet te controleren", nooit als "zonder verklaring"
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
- `data/telecom.json` / `data/vervoer.json` / `data/media.json` / `data/ebooks.json` — Handmatig samengestelde sectorlijsten, zelfde schema maar **`bron` verplicht** per entry (zie `workflows/research_sector_list.md`). Categorieën staan in de `categoryLabels` van de bijbehorende monitorpagina
- `data/results-<sector>.json` / `data/history-<sector>.json` — Automatisch gegenereerd door de sector-scrapes (niet handmatig bewerken)
- `data/objections.json` — Webshops met bezwaar (overlay; client-side uitgesloten, geen e-mailadressen). Bijgewerkt via PR's van de bezwaar-Worker of handmatig
- `data/auditbureaus.json` — Handmatig samengestelde lijst van auditbureaus voor de WCAG-audit-pagina (velden: `naam`, `website`, `specialisatie`, `talen`)
- `data/vragen.json` — Handmatig samengestelde lijst van beantwoorde praktijkvragen (velden: `vraag`, `antwoord`, optioneel `toezichthouder`, `datum`, `thema`, `bron`). Gevuld vanuit binnengekomen anonieme vragen; nooit antwoorden verzinnen
- `data/bronnen.json` — Externe bronnen over de EAA voor de bronnenpagina (velden: `title`, `url`, `author`, `category`, optioneel `date`). `category` uit de vaste lijst in `build_bronnen.py`. `date` wordt aangevuld door `fetch_bron_dates.py`
- `data/halloffame.json` — Eregalerij-vermeldingen (velden: `naam`, `url`, `slug`, `datum`, `motivatie`, `observaties` met `titel`/`beschrijving`/`code`/`wcag`, optioneel `categorie`, `hulptechnologie`). De Worker voegt entries toe via PR's (nominatieflow); Julia vult `observaties` bij review (zie `workflows/handle_nominatie.md`). **Nooit e-mailadressen** in dit bestand; `slug` na publicatie niet wijzigen (stemtellers hangen eraan)

### Pagina's (`public/`)
- `index.html` — Hub-homepage: cijfer-gedreven hero, kerncijfers, uitgelichte artikelen. **Bevat de scraper-markers** (zie hieronder); niet verwijderen
- `monitor.html` + `app.js` — Het interactieve dashboard (grafiek/tabel, filters, sorteerbare tabel). Leest `?q=` uit de URL voor de zoekterm vanaf de home. `app.js` is config-gestuurd via `window.EAA_MONITOR_CONFIG` (`dataUrl`, `noun`, `categoryLabels`, `sortLabels`); zonder config gelden de webshop-defaults
- `monitor-financieel.html` / `monitor-telecom.html` / `monitor-vervoer.html` / `monitor-media.html` / `monitor-ebooks.html` — Hetzelfde dashboard per sector, elk met eigen config (`dataUrl`, `noun`, `categoryLabels`) en eigen copy. **Bevatten de scraper-markers**; gevuld door `scrape_footer.py --dataset <sector>`. Delen allemaal `app.js`
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
- `static/tailwind.css` — **Gegenereerd** door `npm run build:css` uit `tailwind.config.js` (niet handmatig bewerken; na elke class-wijziging opnieuw bouwen, de deploy bouwt hem ook zelf als vangnet). `static/fonts.css` + `static/fonts/` — zelf-gehoste fonts via Fontsource: Fraunces (koppen/telcijfers), Atkinson Hyperlegible (lopende tekst), IBM Plex Mono (alles wat gemeten is); geen Google Fonts. `static/site.css` — componenten, prose, animaties. `static/reveal.js` — scroll-reveal

### Designtokens (`tailwind.config.js`)
- Palet "De Telling": `papier` `#FAF7F1` (hoofdachtergrond), `inkt` `#20281F` (tekst), `loofgroen` `#1A5632` (primair), `dennengroen` `#0D2B1F` (donkere secties/footer), `oker` `#F4C84B` (telmarker; nooit als tekstkleur op licht), `zachtgroen` `#E9F2EA`, status `found`/`notfound`/`error`. De oude tokennamen (`brand`/`navy`/`softblue`) bestaan als alias zodat bestaande classes blijven werken. Fonts: **Fraunces** (koppen, via `font-display`), **Atkinson Hyperlegible** (lopende tekst), **IBM Plex Mono** (gemeten cijfers, via `font-mono`). Status communiceert nooit met kleur alleen (icoon/bol + tekstlabel; telbalk-segmenten met witte scheiders). Eén bron van waarheid: `tailwind.config.js`.

### Overig
- `worker/` — Cloudflare Worker voor bezwaren met domein-verificatie, artikel-feedback, anonieme vragen, nieuwsbrief-opt-in én de eregalerij (zie `worker/DEPLOY.md`). Routes: `POST /submit`, `GET /confirm`, `POST /feedback`, `POST /vraag`, `POST /pact/aanmelden`, `POST /newsletter`, `GET /newsletter/confirm`, `GET /newsletter/unsubscribe`, `POST /hof/nominate`, `GET /hof/nominate/confirm`, `POST /hof/vote`, `GET /hof/vote/confirm`, `GET /hof/votes`. De eregalerij-flows: nomineren = dubbele opt-in → PR op `data/halloffame.json` (zelfnominatie wordt gevlagd, nooit auto-live); stemmen = dubbele opt-in, 1 stem per gehasht e-mailadres per `slug` in KV (`hof:vote:`/`hof:count:`), eigen-domein-stemmen geweigerd; `GET /hof/votes` levert de tellers (gecachet) aan `static/halloffame.js`. `/feedback` mailt een opmerking over een artikel rechtstreeks naar `NOTIFY_EMAIL`; `/vraag` mailt een anonieme EAA-vraag naar `VRAGEN_EMAIL` (`vragen@eaa-monitor.nl`, terugval op `NOTIFY_EMAIL`) — beide zonder PR, opslag of extra secrets. `/pact/aanmelden` mailt een aanmelding voor Het Vierogen-pact (auditbureau of freelance auditor) naar `NOTIFY_EMAIL` (`public/vierogen-pact.html`, zie `docs/vierogen-pact.md`), eveneens mail-only. `/newsletter` is een dubbele opt-in: na bevestiging via een getekende link wordt het adres opgeslagen in de KV-namespace `NEWSLETTER` (sleutel `sub:<email>`); afzender `NEWSLETTER_FROM` (terugval op `FROM_EMAIL`). Het inschrijfformulier staat in de footer (`site_footer()` in `build_articles.py`, endpoint in `NEWSLETTER_ENDPOINT`, submit-logica in `public/static/newsletter.js`). Onder elk artikel staat een bron-disclaimer + feedbackformulier dat `build_articles.py` rendert (endpoint in `FEEDBACK_ENDPOINT`). Na Worker-wijziging opnieuw deployen.
- `workflows/handle_objection.md` — SOP voor het verwerken van een bezwaar
- `workflows/handle_vraag.md` — SOP voor het verwerken van een binnengekomen anonieme vraag (voorleggen aan toezichthouder, antwoord in `data/vragen.json`)
- `workflows/handle_nominatie.md` — SOP voor het verwerken van een eregalerij-nominatie (toegankelijkheidscheck, geverifieerde observaties schrijven, PR mergen)
- `workflows/research_sector_list.md` — SOP voor het samenstellen of uitbreiden van een sectorlijst (registerbron eerst, `bron` verplicht, live-check, eerste scrape als e2e-test)
- `.github/workflows/scrape.yml` — Wekelijkse cron die scrapt en resultaten commit
- `.github/workflows/deploy.yml` — Deploy naar GitHub Pages (kopieert de hele `public/`-tree recursief)

## Auto-gegenereerde regio's (niet breken)

`scrape_footer.py` vervangt bij elke scrape de inhoud tussen letterlijke markers in de doel-HTML (`index.html` voor webshops, `monitor-<sector>.html` voor de andere sectoren): `GEO-SUMMARY:START/END`, `STAT:total`, `STAT:pctWith`, `STAT:pctWithout`, `LASTUPDATED`, `JSONLD-DATASET:START/END`. Elke marker moet **precies één keer** voorkomen; bij een ontbrekende of dubbele marker faalt de run hard (bewust: stille mismatch = verouderde cijfers live). Uitzondering: de `GEO-SUMMARY`-patch staat per dataset uit te zetten met `"geo_summary": False` in `DATASETS`; voor `webshops` staat hij uit en bevat `index.html` dus géén GEO-SUMMARY-markers (de samenvattingskaart is daar in juni 2026 bewust verwijderd, de zes sectorkaarten dragen de cijfers). Elke niet-webshop-run patcht daarnaast zijn hub-kaart op `index.html` (`STAT:{hub_prefix}Total`/`STAT:{hub_prefix}PctWithout`; prefixen `fin`/`tel`/`vervoer`/`media`/`ebooks`). `llms.txt` is een **hand-onderhouden skelet** met zeven marker-regio's: per sector een meet-regio (`MEASUREMENT`, `FIN-MEASUREMENT`, `TEL-MEASUREMENT`, `VERVOER-MEASUREMENT`, `MEDIA-MEASUREMENT`, `EBOOKS-MEASUREMENT`) plus `ARTICLES` (`build_articles.py`). De scraper patcht alleen de eigen regio en faalt hard als die ontbreekt; verwijder een regio dus nooit zonder de bijbehorende dataset uit `scrape.yml` te halen.

## Commando's

```bash
# Scraper draaien (volledige lijst, sequentieel)
python tools/scrape_footer.py

# Een kleine sector scrapen (kleine lijst, geen sharding)
python tools/scrape_footer.py --dataset financieel   # of telecom/vervoer/media/ebooks

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

# Tailwind-CSS (her)bouwen na een wijziging in classes of tailwind.config.js
npm install        # eerste keer
npm run build:css

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
