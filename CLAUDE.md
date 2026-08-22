# EAA Monitor

Hub over de European Accessibility Act (EAA) in Nederland. Het dashboard controleert wekelijks in zes sectoren of Nederlandse organisaties een toegankelijkheidsverklaring in hun footer hebben: webshops en e-bookplatforms (ACM), financiële instellingen (AFM), telecomaanbieders (ACM), personenvervoerders (ILT) en mediadiensten (Commissariaat voor de Media). De kennisbank legt uit hoe de wet werkt (scope, toezicht, boetes, mythes).

## Architectuur

Volgt het WAT framework (Workflows, Agents, Tools). Statische site (HTML + lokaal gebouwde Tailwind + vanilla JS); geen Amerikaanse CDN's of font-diensten meer, zie `docs/eu-stack-migratie.md`. Design: **"De Telling"** (warm papier, loofgroen, okergeel; zie `docs/rebranding/rebranding-voorstel.md`), bewust losgemaakt van het Proper Access-merk; Proper Access blijft in footer-attributie en schema.

### Tools
- `tools/scrape_footer.py` — Playwright-based scraper die footers checkt op toegankelijkheidslinks, en bij elke scrape de cijfers + Dataset JSON-LD in de doel-HTML en de eigen meet-regio in `llms.txt` bakt. **Zes datasets** via `--dataset {webshops,financieel,telecom,vervoer,media,ebooks}` (default `webshops`), volledig config-gestuurd via de `DATASETS`-dict: `webshops` bakt in `index.html` (legacy ongeprefixte markers); elke andere sector bakt in zijn eigen `monitor-<sector>.html` én vult een hub-kaart op `index.html` (markers `STAT:{hub_prefix}Total`/`STAT:{hub_prefix}PctWithout`). Nieuwe sector toevoegen = DATASETS-entry + `data/<sector>.json` + monitorpagina + hub-kaart op index.html + llms-regio. Pagina's met bot-protectie of wachtrij (minder dan 5 links) tellen als "niet te controleren", nooit als "zonder verklaring"
- `tools/build_articles.py` — Artikelgenerator: rendert `content/artikelen/*.md` → `public/artikelen/*.html`, bouwt `public/artikelen.html`, regenereert `sitemap.xml` en patcht de artikellijst-regio in `llms.txt`
- `public/llms-full.txt` — **Gegenereerd** door `write_llms_full()` in `build_articles.py`: de volledige tekst van alle artikelen plus de beantwoorde praktijkvragen in één bestand. Bewust **zonder meetcijfers**, want die veranderen wekelijks en zouden hier zonder verse datum blijven staan
- `tools/build_auditbureaus.py` — Rendert `data/auditbureaus.json` → `public/wcag-audit.html` (server-rendered tabel). Deelt head/header/footer met `build_articles.py`
- `tools/build_articles_en.py` — Engelse kennisbank: rendert `content/articles-en/*.md` → `public/en/articles/*.html` + `public/en/articles.html`, met eigen Engelse header/footer en Engelse Article/FAQPage JSON-LD. Engelse artikelen worden **apart geschreven en nooit vertaald**, dus er is geen hreflang-koppeling met een Nederlands artikel. `en_urls()` levert de URL's aan de sitemap. Links naar Nederlandse pagina's krijgen "(NL)" plus `hreflang`/`lang`
- `tools/build_lijsten.py` — Rendert de volledige meting per sector als platte HTML naar `public/lijst/` plus de hub `public/lijst.html`. De monitorpagina's bouwen hun tabel client-side, dus zonder deze pagina's ziet een crawler geen enkele naam. Webshops wordt gesplitst per beginletter, de andere zes sectoren krijgen één pagina. **Filterregels moeten gelijk blijven aan `public/app.js`**: bezwaren uit `objections.json` vallen uit lijst én telling, `scrape_status != success` is "niet te controleren" en nooit "geen verklaring", en de WCAG-scan komt uit `axe-results.json` op genormaliseerde URL. **Staat niet in git** (2,6 MB die elke week verandert); `deploy.yml` bouwt de pagina's. `lijst_urls()` levert de URL's aan de sitemap in `build_articles.py`
- `tools/build_hulp.py` — Rendert `data/hulptools.json` → `public/tools.html` (server-rendered toolsoverzicht per categorie, met SoftwareApplication ItemList JSON-LD). Categorieën staan in `CATEGORIES` in de tool; een onbekende categorie laat de build hard falen. Deelt head/header/footer met `build_articles.py`
- `tools/build_vragen.py` — Rendert `data/vragen.json` → `public/vragen.html` (server-rendered vraag-en-antwoord met FAQPage JSON-LD). Deelt head/header/footer met `build_articles.py`
- `tools/build_bronnen.py` — Rendert `data/bronnen.json` → `public/bronnen.html` (server-rendered, filterbaar bronnenoverzicht). Deelt head/header/footer met `build_articles.py`; de filters/zoek werken client-side via `public/static/bronnen.js`
- `tools/build_halloffame.py` — Rendert `data/halloffame.json` → `public/eregalerij.html` (server-rendered, met ItemList JSON-LD). Observaties zijn optioneel; staan ze er, dan toont de kaart het blok "Wat doet deze website goed?" met codevoorbeelden. **Draait ook in `deploy.yml`**, zodat een nominatie die de Worker naar main commit meteen live komt. Stemtellers komen client-side van de Worker via `public/static/halloffame.js`. Deelt head/header/footer met `build_articles.py`
- `tools/fetch_bron_dates.py` — Best-effort: haalt elke bron-URL op en vult `date` aan in `data/bronnen.json` (uit `datePublished`/`article:published_time`/`<time>`). Verzint nooit een datum; vindt het niets, dan blijft het veld leeg
- `tools/scrape_thuiswinkel.py` / `tools/scrape_webwinkelkeur.py` — Bouwen `webshops.json` aan met keurmerk-leden
- `tools/sync_confirmed.py` — Onderhoudt de bevestigd-groen-lijst (`data/confirmed.json`) na een scrape: nieuwe greens toevoegen, herbevestigde verversen (datum vandaag), weggehaalde verklaringen verwijderen; error/timeout laat de bestaande bevestiging staan. Draait in `scrape.yml` na de merge (shard-veilig). De scraper zelf **slaat** bevestigd-groene sites op de wekelijkse run **over** zolang `confirmed` < `REVERIFY_DAYS` (30) oud is, en herverifieert ze daarna vanzelf. Beschermt ook handmatig geverifieerde greens (bv. bol.com) tegen wegvallen door een transiente bot-challenge
- `tools/scan_axe.py` — WCAG-scanner: draait **axe-core 4.11** (lokaal gevendord in `tools/vendor/axe.min.js`, dezelfde engine als wcag-scan.eu) in headless Chromium over een lijst sites en aggregeert de violations. Standaard **alleen WCAG A/AA** (best-practice zoals landmarks uitgesloten, want in NL geen WCAG-falen). **Render-waarborg**: een pagina met < 50 DOM-elementen na laden geldt als niet gerenderd (redirect/consent/bot-muur) → status `niet-gerenderd`, nooit "geen fouten"; axe wordt via `page.evaluate` geïnjecteerd (CSP-proof), niet via `add_script_tag`. `tools/build_axe_targets.py` bouwt de doellijst (elke site met `has_statement=True`, gededupliceerd op URL). `tools/gen_axe_rules.js` genereert de regelcatalogus `data/axe-rules.json` (welke regels meetellen vs. uitgesloten). **Wall-clock-cap per site** (`SCAN_CAP_S`) plus zelfherstart bij een onbreekbare hang: hergebruikt de watchdog van `scrape_footer.py`, want de losse Playwright-timeouts dekken de axe-run in `page.evaluate` niet. Schrijft elke `FLUSH_EVERY` sites tussentijds weg, zodat een afgebroken run zijn werk houdt
- `tools/build_axe_overlay.py` — Rendert een scan-output → de overlay `data/axe-results.json` (url → `fouten`/`schoon`/`niet-scanbaar`). Met `--patch-html public/monitor.html` bakt het ook het kerncijfer tussen de `<!--AXE-STAT:START/END-->`-markers (GEO/no-JS). Draait wekelijks via `scan-axe.yml`
- `tests/test_detector.py` (deterministische detector-fixtures, confusion matrix), `tests/test_confirmed.py` (overslaan + sync), `tests/test_site_timeout.py` (per-site-cap + shard-zelfherstart), `tests/test_axe_scan.py` (scan-aggregatie + statusvertaling), `tests/check_live.py` + `tests/groundtruth_sites.json` (periodieke live-validatie tegen echte sites)

### Data
- `data/webshops.json` — Lijst van te controleren webshops (deels handmatig, deels gescraped)
- `data/results.json` — Automatisch gegenereerde scrape-resultaten (niet handmatig bewerken)
- `data/confirmed.json` — Bevestigd-groen-lijst (`sites` met `url`, `statement_url`, `statement_link_text`, `confirmed`-datum). Onderhouden door `tools/sync_confirmed.py`; de scraper slaat verse entries over en herverifieert na 30 dagen. Handmatig toevoegen mag (geverifieerde verklaring-URL, `confirmed`-datum), nooit verzinnen
- `data/financieel.json` — Handmatig samengestelde lijst van financiële instellingen uit de AFM/DNB-registers (velden: `name`, `url`, `category` ∈ `bank`/`verzekeraar`/`betaaldienst`/`beleggen`/`lease`, optioneel `bron`). Zelfde schema als `webshops.json`
- `data/telecom.json` / `data/vervoer.json` / `data/media.json` / `data/ebooks.json` — Handmatig samengestelde sectorlijsten, zelfde schema maar **`bron` verplicht** per entry (zie `workflows/research_sector_list.md`). Categorieën staan in de `categoryLabels` van de bijbehorende monitorpagina
- `data/results-<sector>.json` / `data/history-<sector>.json` — Automatisch gegenereerd door de sector-scrapes (niet handmatig bewerken)
- `data/objections.json` — Webshops met bezwaar (overlay; client-side uitgesloten, geen e-mailadressen). Bijgewerkt via PR's van de bezwaar-Worker of handmatig
- `data/auditbureaus.json` — Handmatig samengestelde lijst van auditbureaus voor de WCAG-audit-pagina (velden: `naam`, `website`, `specialisatie`, `talen`)
- `data/vragen.json` — Handmatig samengestelde lijst van beantwoorde praktijkvragen (velden: `vraag`, `antwoord`, optioneel `toezichthouder`, `datum`, `thema`, `bron`). Gevuld vanuit binnengekomen anonieme vragen; nooit antwoorden verzinnen
- `data/hulptools.json` — Handmatig samengestelde lijst van tools voor de hulppagina (velden: `naam`, `url`, `aanbieder`, `categorie`, `wat`, `grens`, `prijs`, `platform`, optioneel `varianten`). `grens` is verplicht: elke tool krijgt erbij wat hij *niet* vindt. optioneel `uitleg` met `titel` en `url` voor een handleiding elders, die als link op de kaart verschijnt. `categorie` mag een lijst zijn, dan verschijnt de tool in elke genoemde categorie; met `varianten` geef je per categorie een eigen `wat` en `grens`, zodat de kaart vertelt wat de tool in dát rijtje doet (de WCAG Radar staat zo in drie categorieën). Niemand betaalt voor een plek
- `data/bronnen.json` — Externe bronnen over de EAA voor de bronnenpagina (velden: `title`, `url`, `author`, `category`, optioneel `date`). `category` uit de vaste lijst in `build_bronnen.py`. `date` wordt aangevuld door `fetch_bron_dates.py`
- `data/axe-results.json` — Automatisch gegenereerde **WCAG-scan-overlay** (door `build_axe_overlay.py`): per site met verklaring een `status` (`fouten`/`schoon`/`niet-scanbaar`) plus een `summary`. `app.js` koppelt dit client-side op `normalizeUrl`, **los van de footer-scrape** (zoals `objections.json`), zodat een nieuwe scrape de scanuitslag niet overschrijft. Niet handmatig bewerken. `data/axe-rules.json` is de regelcatalogus (welke axe-regels meetellen)
- `data/halloffame.json` — Eregalerij-vermeldingen (velden: `naam`, `url`, `slug`, `datum`, `motivatie`, optioneel `observaties` met `titel`/`beschrijving`/`code`/`wcag`, `categorie`, `hulptechnologie`). De Worker commit bevestigde nominaties **direct naar main** (geen PR, geen controle, besluit 21 juni 2026); de deploy bouwt de eregalerij opnieuw. Julia kan een entry later verrijken met `observaties`. **Nooit e-mailadressen** in dit bestand; `slug` na publicatie niet wijzigen (stemtellers hangen eraan)

### Pagina's (`public/`)
- `index.html` — Hub-homepage: cijfer-gedreven hero, kerncijfers, uitgelichte artikelen. **Bevat de scraper-markers** (zie hieronder); niet verwijderen
- `monitor.html` + `app.js` — Het interactieve dashboard (grafiek/tabel, filters, sorteerbare tabel). Leest `?q=` uit de URL voor de zoekterm vanaf de home. `app.js` is config-gestuurd via `window.EAA_MONITOR_CONFIG` (`dataUrl`, `noun`, `categoryLabels`, `sortLabels`); zonder config gelden de webshop-defaults. Bevat de kolom **WCAG-scan** (fouten gevonden / geen fouten gevonden / niet te scannen, met doorverwijzing naar wcag-scan.eu voor detail), gevoed door de overlay `data/axe-results.json` en alleen gevuld bij sites met een verklaring. `monitor.html` heeft de `AXE-STAT`-markers voor het gebakken kerncijfer
- `monitor-financieel.html` / `monitor-telecom.html` / `monitor-vervoer.html` / `monitor-media.html` / `monitor-ebooks.html` — Hetzelfde dashboard per sector, elk met eigen config (`dataUrl`, `noun`, `categoryLabels`) en eigen copy. **Bevatten de scraper-markers**; gevuld door `scrape_footer.py --dataset <sector>`. Delen allemaal `app.js`
- `artikelen.html` + `artikelen/*.html` — Kennisbank, **gegenereerd** door `build_articles.py` (niet handmatig bewerken)
- `tools.html` — Hulp bij digitale toegankelijkheid: toolsoverzicht per categorie (in-pagina checkers, contrast, structuur, schermlezers, documenten), **gegenereerd** door `build_hulp.py` uit `data/hulptools.json` (niet handmatig bewerken). Staat in de hoofdnavigatie als "Tools"
- `wcag-audit.html` — Overzicht van auditbureaus, **gegenereerd** door `build_auditbureaus.py` uit `data/auditbureaus.json` (niet handmatig bewerken)
- `vragen.html` — Vragen uit de praktijk, **gegenereerd** door `build_vragen.py` uit `data/vragen.json` (niet handmatig bewerken)
- `vraag-stellen.html` — Anoniem vraagformulier → bezwaar-Worker (`VRAAG_ENDPOINT`, route `/vraag`). Handgeschreven
- `bronnen.html` — Doorzoekbaar bronnenoverzicht met categoriefilters, **gegenereerd** door `build_bronnen.py` uit `data/bronnen.json` (niet handmatig bewerken)
- `eregalerij.html` — Hall of fame van aantoonbaar toegankelijke websites, **gegenereerd** door `build_halloffame.py` uit `data/halloffame.json` (niet handmatig bewerken). Stemtellers en stemformulieren via `static/halloffame.js` (progressive enhancement: zonder JS verborgen)
- `nomineren.html` — Nominatieformulier voor de eregalerij → bezwaar-Worker (`NOMINATIE_ENDPOINT`, route `/hof/nominate`). Handgeschreven
- `bezwaar.html` — Bezwaarformulier → bezwaar-Worker (`BEZWAAR_ENDPOINT`); het `action`-attribuut wijst naar dezelfde Worker, zodat ook een no-JS-verzending in de EU blijft (geen Formspree meer)
- `bezwaren.html` + `bezwaren.js` — Openbare lijst van bezwaren
- `over.html` — Over het dashboard
- `static/tailwind.css` — **Gegenereerd** door `npm run build:css` uit `tailwind.config.js` (niet handmatig bewerken; na elke class-wijziging opnieuw bouwen, de deploy bouwt hem ook zelf als vangnet). `static/fonts.css` + `static/fonts/` — zelf-gehoste fonts via Fontsource: Fraunces (koppen/telcijfers), Atkinson Hyperlegible (lopende tekst), IBM Plex Mono (alles wat gemeten is); geen Google Fonts. `static/site.css` — componenten, prose, animaties. `static/reveal.js` — scroll-reveal

### Designtokens (`tailwind.config.js`)
- Palet "De Telling": `papier` `#FAF7F1` (hoofdachtergrond), `inkt` `#20281F` (tekst), `loofgroen` `#1A5632` (primair), `dennengroen` `#0D2B1F` (donkere secties/footer), `oker` `#F4C84B` (telmarker; nooit als tekstkleur op licht), `zachtgroen` `#E9F2EA`, status `found`/`notfound`/`error`. De oude tokennamen (`brand`/`navy`/`softblue`) bestaan als alias zodat bestaande classes blijven werken. Fonts: **Fraunces** (koppen, via `font-display`), **Atkinson Hyperlegible** (lopende tekst), **IBM Plex Mono** (gemeten cijfers, via `font-mono`). Status communiceert nooit met kleur alleen (icoon/bol + tekstlabel; telbalk-segmenten met witte scheiders). Eén bron van waarheid: `tailwind.config.js`.

### Overig
- `worker/` — Cloudflare Worker voor bezwaren met domein-verificatie, artikel-feedback, anonieme vragen, nieuwsbrief-opt-in én de eregalerij (zie `worker/DEPLOY.md`). Routes: `POST /submit`, `GET /confirm`, `POST /feedback`, `POST /vraag`, `POST /pact/aanmelden`, `POST /newsletter`, `GET /newsletter/confirm`, `GET /newsletter/unsubscribe`, `POST /hof/nominate`, `GET /hof/nominate/confirm`, `POST /hof/vote`, `GET /hof/vote/confirm`, `GET /hof/votes`. De eregalerij-flows: nomineren = dubbele opt-in → de Worker commit de nominatie direct naar `data/halloffame.json` op main (geen PR, geen controle; de deploy herbouwt de pagina); stemmen = dubbele opt-in, 1 stem per gehasht e-mailadres per `slug` in KV (`hof:vote:`/`hof:count:`), eigen-domein-stemmen geweigerd; `GET /hof/votes` levert de tellers (gecachet) aan `static/halloffame.js`. `/feedback` mailt een opmerking over een artikel rechtstreeks naar `NOTIFY_EMAIL`; `/vraag` mailt een anonieme EAA-vraag naar `VRAGEN_EMAIL` (`vragen@eaa-monitor.nl`, terugval op `NOTIFY_EMAIL`) — beide zonder PR, opslag of extra secrets. `/pact/aanmelden` mailt een aanmelding voor Het Vierogen-pact (auditbureau of freelance auditor) naar `NOTIFY_EMAIL` (`public/vierogen-pact.html`, zie `docs/vierogen-pact.md`), eveneens mail-only. `/newsletter` is een dubbele opt-in: na bevestiging via een getekende link wordt het adres opgeslagen in de KV-namespace `NEWSLETTER` (sleutel `sub:<email>`); afzender `NEWSLETTER_FROM` (terugval op `FROM_EMAIL`). Het inschrijfformulier staat in de footer (`site_footer()` in `build_articles.py`, endpoint in `NEWSLETTER_ENDPOINT`, submit-logica in `public/static/newsletter.js`). Onder elk artikel staat een bron-disclaimer + feedbackformulier dat `build_articles.py` rendert (endpoint in `FEEDBACK_ENDPOINT`). Na Worker-wijziging opnieuw deployen.
- `workflows/handle_objection.md` — SOP voor het verwerken van een bezwaar
- `workflows/handle_vraag.md` — SOP voor het verwerken van een binnengekomen anonieme vraag (voorleggen aan toezichthouder, antwoord in `data/vragen.json`)
- `workflows/handle_nominatie.md` — SOP voor het optioneel verrijken van een al geplaatste eregalerij-nominatie met geverifieerde observaties (nominaties komen automatisch live, zonder controle)
- `workflows/research_sector_list.md` — SOP voor het samenstellen of uitbreiden van een sectorlijst (registerbron eerst, `bron` verplicht, live-check, eerste scrape als e2e-test)
- `.github/workflows/scrape.yml` — Wekelijkse cron die scrapt en resultaten commit
- `.github/workflows/scan-axe.yml` — Wekelijkse cron (dinsdag, na de maandag-scrape) die `build_axe_targets` → `scan_axe` → `build_axe_overlay --patch-html` draait en `data/axe-results.json` + `public/monitor.html` commit
- `.github/workflows/deploy.yml` — Deploy naar GitHub Pages (kopieert de hele `public/`-tree recursief)

## Navigatie: twee plekken, geen één

`NAV_ITEMS` in `tools/build_articles.py` is de bron voor de gegenereerde pagina's (kennisbank,
artikelen, bronnen, vragen, eregalerij, wcag-audit, hulp, colofon, privacy). De handgeschreven
pagina's (`index.html`, alle `monitor*.html`, `over.html`, de formulierpagina's) hebben elk een
eigen kopie van diezelfde header en footer in de HTML. Voeg je een nav-item toe, dan moet je die
kopieën apart patchen, anders loopt de navigatie per pagina uiteen. De Engelse pagina's in
`public/en/` hebben een eigen nav en blijven buiten een NL-only toevoeging.

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

# Bevestigd-groen-lijst bijwerken na een scrape (cron doet dit na de merge)
python tools/sync_confirmed.py --dataset webshops

# Detector-tests draaien (deterministisch; geen netwerk)
python tests/test_detector.py
python tests/test_confirmed.py
python tests/test_site_timeout.py
python tests/test_axe_scan.py
# Live ground-truth-validatie tegen echte sites (kan wisselen door bot-challenges)
python tests/check_live.py

# Artikelen (her)bouwen na een wijziging in content/artikelen/
python tools/build_articles.py

# WCAG-audit-pagina (her)bouwen na een wijziging in data/auditbureaus.json
python tools/build_auditbureaus.py

# Praktijkvragen-pagina (her)bouwen na een wijziging in data/vragen.json
python tools/build_vragen.py
# Engelse kennisbank (her)bouwen na een wijziging in content/articles-en/
python tools/build_articles_en.py

# Volledige meetlijsten bouwen (staan niet in git; de deploy doet dit ook)
python tools/build_lijsten.py

# Hulppagina (her)bouwen na een wijziging in data/hulptools.json
python tools/build_hulp.py
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
