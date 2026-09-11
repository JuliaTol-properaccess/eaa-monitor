# GEO Audit Report: EAA Monitor

**Auditdatum:** 12 juni 2026
**URL:** https://eaa-monitor.nl
**Type site:** Publisher / data-hub (onafhankelijke monitor + kennisbank, Nederlandstalig)
**Pagina's geanalyseerd:** 21 (volledige sitemap) + robots.txt, llms.txt, sitemap.xml, JSON-data

---

## Samenvatting

**Totale GEO-score: 56/100 (Matig)**

De site is on-page een van de best voorbereide GEO-sites in zijn niche: server-gebakken meetcijfers, Dataset/FAQPage/Article JSON-LD, een voorbeeldige llms.txt, alle AI-crawlers expliciet welkom, en uniek eigen onderzoek (wekelijkse meting van ~10.500 organisaties) dat geen concurrent heeft. De score wordt vrijwel volledig omlaag getrokken door één factor: de entiteit "EAA Monitor" bestaat buiten het eigen domein nergens. Geen externe vermeldingen, geen backlinks, geen LinkedIn, geen Wikidata, geen aantoonbare Bing-indexering. Daarnaast ontbreekt de trust-basis die AI-systemen als baseline verwachten: een contactroute, een colofon en een privacyverklaring.

### Score-opbouw

| Categorie | Score | Gewicht | Gewogen |
|---|---|---|---|
| AI Citability | 73/100 | 25% | 18,3 |
| Brand Authority | 5/100 | 20% | 1,0 |
| Content E-E-A-T | 64/100 | 20% | 12,8 |
| Technical GEO | 84/100 | 15% | 12,6 |
| Schema & Structured Data | 58/100 | 10% | 5,8 |
| Platform Optimization | 57/100 | 10% | 5,7 |
| **Totaal** | | | **56/100** |

---

## Critical (direct oppakken)

### 1. Geen contactroute en geen privacyverklaring
[over.html](https://eaa-monitor.nl/over.html) zegt "Zie je een fout? Mail ons", maar nergens op de site staat een e-mailadres of contactlink (nul mailto's in alle HTML). De nieuwsbrief verzamelt e-mailadressen zonder vindbare privacyverklaring: een AVG-risico én een E-E-A-T-baseline die ontbreekt.
**Fix:** functioneel adres (bijv. `redactie@eaa-monitor.nl`, de mail-infrastructuur bestaat al via de Worker/Resend) plus een colofon- en privacypagina. Vereist geen persoonsnamen.

### 2. Onafhankelijkheidsclaim zonder relatievermelding Proper Access
De site claimt "we verkopen geen audits", terwijl de maker een auditbureau is en twee artikelen naar Proper Access linken zonder relatievermelding. Onontdekt kost dit E-E-A-T-transfer (900+ audits aan autoriteit blijft onbenut); ontdekt slaat het sterkste trust-signaal om in het zwakste.
**Let op:** de projectdocumentatie (CLAUDE.md) zegt "Proper Access blijft in footer-attributie en schema", maar live is álle attributie verdwenen. Check of dat de bedoeling was.
**Fix:** één transparantiezin op over.html ("EAA Monitor is een initiatief van Proper Access; de monitor verkoopt niets en Proper Access staat niet in de bureaulijst") plus `parentOrganization` in het Organization-schema.

### 3. Brand Authority is vrijwel nul
Nul vermeldingen gevonden op Wikipedia, Reddit, LinkedIn, YouTube en vakmedia (Tweakers, Emerce, Frankwatching, accessibility.nl). Een `site:eaa-monitor.nl`-zoekopdracht leverde niets op. AI-modellen beslissen wat ze citeren grotendeels op externe corroboratie, en die ontbreekt volledig. De ironie: de partijen die nu de EAA-zoekresultaten domineren hebben géén wekelijkse data.
**Fix:** distributiestrategie (zie 30-dagenplan, week 4). Eén vakmedia-artikel met link is meer waard dan elke verdere on-page optimalisatie.

---

## High priority (binnen 1 week)

1. **monitor.html is zonder JavaScript leeg.** De pagina over de grootste dataset (10.397 webshops) toont een no-JS-crawler alleen "—" en "Data laden...", terwijl de vijf sectorpagina's wél gebakken samenvattingen hebben. Fix: GEO-SUMMARY-markers + Dataset JSON-LD toevoegen aan `public/monitor.html` en de `webshops`-entry in de `DATASETS`-dict van `tools/scrape_footer.py` daarop aanpassen.
2. **Geen Bing Webmaster Tools-verificatie en geen IndexNow.** Bing voedt zowel Copilot als ChatGPT search; de indexstatus is nu onbekend en er is geen enkel positief signaal. Fix: site verifiëren (statisch bestand werkt op GitHub Pages), sitemap indienen, IndexNow-keyfile in `public/` + ping in `.github/workflows/scrape.yml` en `deploy.yml`.
3. **Organization-schema mist entity-verankering.** Geen `sameAs`, `logo`, `contactPoint`, `foundingDate` of `parentOrganization` in het `@graph`-blok op index.html. Fix: verrijken (zie schema-deepdive), plus een LinkedIn-bedrijfspagina (mag merknaam-only) en een Wikidata-item voor de dataset.
4. **Dataset-`url` wijst op alle vijf sectorpagina's naar de homepage** in plaats van naar de eigen monitorpagina (hardcoded in `tools/scrape_footer.py:563`). AI-systemen die de dataset citeren linken naar de verkeerde pagina. Fix: `url` afleiden per dataset of een `page_url`-veld toevoegen aan de `DATASETS`-dict.
5. **wcag-audit.html is een lege placeholder** ("De lijst wordt binnenkort gevuld"), wel in nav en sitemap; over.html noemt "Hulp" als een van de vier pijlers. `data/auditbureaus.json` is `[]`. Fix: vullen, of pagina en pijler tijdelijk uit navigatie en sitemap halen.
6. **Geen redactie-/auteurssignaal.** Alle expertise is onzichtbaar voor AI-entityherkenning. Fix die de anonimiteit respecteert: een "Over de redactie"-blok zonder namen (vakachtergrond, werkwijze, verificatieproces), gelinkt vanuit `author.url` in het Article-schema.
7. **Article-schema mist `image` en `@id`-koppelingen** naar de Organization. Fix in `tools/build_articles.py`: `image` (og.png bestaat al) plus `author`/`publisher` via `{"@id": "https://eaa-monitor.nl/#organization"}`.

---

## Medium priority (binnen 1 maand)

1. **Datum-inconsistentie webshopmeting:** homepage en llms.txt zeggen "6 juni 2026" (zaterdag) terwijl de site "elke maandag" claimt en de sectoren op 10-12 juni staan. Uitzoeken waarom de maandag-run van 8 juni de webshopcijfers niet ververste.
2. **0 van de 82 bronnen op bronnen.html heeft een datum**, terwijl `tools/fetch_bron_dates.py` er al voor bestaat. Eén commando.
3. **Slechts 2 van de 7 artikelen gebruiken de eigen meetdata**, het sterkste experience-signaal. Per artikel één gemeten cijfer met datum en monitorlink invlechten.
4. **Titelvraag-artikelen beantwoorden de vraag pas onderaan.** "Valt mijn website onder de EAA?" geeft het antwoord pas na de checker. Vast patroon in `build_articles.py`: 40-60 woorden samenvattend antwoord direct onder de H1.
5. **Sectorcijfers op de homepage staan in cards, niet in een `<table>`.** Een echte HTML-tabel (sector, aantal, % zonder verklaring, meetdatum) is direct extracteerbaar voor AI Overviews en featured snippets. Zet ook de per-sector-meetdatum op de hub-kaarten.
6. **Security headers ontbreken volledig** (HSTS, CSP, X-Frame-Options, etc.). Niet oplosbaar op GitHub Pages; meenemen in de geplande Hetzner-migratie (`docs/eu-stack-migratie.md`).
7. **Schema-aanvullingen:** `spatialCoverage` + `creator @id` in de Dataset-template (scrape_footer.py), SearchAction op index.html (zoek bestaat al via `monitor.html?q=`), BreadcrumbList + speakable op artikelen (build_articles.py), ItemList op bronnen.html en wcag-audit.html (build_bronnen.py / build_auditbureaus.py).
8. **Geen community-aanwezigheid.** Voor Perplexity de grootste ontbrekende factor naast een verder uitstekende bronpositie. De maandagmeting periodiek delen op Reddit (r/webdev, r/accessibility) en relevante fora.
9. **Boete-claims leunen op vakmedia** (netjes gemarkeerd). Versterken met het Staatsblad (staat al in bronnen.json) als primaire bron in toezicht-en-boetes.md.
10. **`dateModified` is altijd gelijk aan `datePublished`.** Frontmatter-veld `updated` ondersteunen in build_articles.py en zichtbaar tonen ("Bijgewerkt op ...").

---

## Low priority

1. `sitemap.xml`: `<lastmod>` staat alleen op artikelen, niet op de monitor- en hoofdpagina's. Juist bij wekelijks verversende cijfers waardevol; vul met de laatste scrape-datum.
2. `bezwaar.html` is indexeerbaar maar staat niet in de sitemap. Toevoegen of de uitsluiting documenteren.
3. Fonts (Fraunces, Atkinson) niet gepreload; kleine FOUT/LCP-marge te winnen met `<link rel="preload">`.
4. Geen `llms-full.txt` met volledige artikelteksten; genereren vanuit `build_articles.py` en linken vanuit llms.txt.
5. `artikelen.html` toont geen publicatiedatums en mist CollectionPage/ItemList-schema.
6. `over.html` heeft geen schema (AboutPage) en geen zichtbare "laatst bijgewerkt"-datum, terwijl dit dé pagina is waarmee journalisten en AI-modellen de bron beoordelen.
7. Artikelen zijn relatief kort (~600 woorden). Voldoende voor citatie; voor Gemini's diepgang-voorkeur 2-3 kernartikelen uitbouwen tot 1.500+ woorden pijlerpagina's.
8. Het subsidie-artikel schreeuwt om een vergelijkingstabel (gemeente, max bedrag, dekt implementatie ja/nee).
9. Hero-zin op de homepage ("Op dit moment publiceert 2% ...") is niet zelfstandig citeerbaar; herschrijf met datum en aantal.
10. FAQ-rich-results toont Google sinds 2023 alleen voor overheid/gezondheid; de FAQPage-markup behouden (semantische waarde voor AI), maar er geen snippets van verwachten. Overweeg `dateCreated` per vraag in build_vragen.py.

---

## Deepdives per categorie

### AI Citability (73/100)
Sterke spreiding. Beste pagina: [toezicht-en-boetes](https://eaa-monitor.nl/artikelen/toezicht-en-boetes.html) (88/100) met passages die claim + cijfer + bron + datum in drie zinnen combineren, precies wat een AI verbatim overneemt. De homepage (85) heeft server-gebakken cijfers en FAQ in HTML én JSON-LD. Zwakste: monitor.html (25), zonder JS geen enkel cijfer zichtbaar; de H1 stelt een vraag die de pagina voor een no-JS-lezer nooit beantwoordt. llms.txt scoort 80/100: spec-conform, actueel, met de zeldzame plus van directe JSON-data-links; alleen llms-full.txt ontbreekt.

### Brand Authority (5/100)
Volledig afwezig op alle gecheckte platformen (Wikipedia NL+EN via API, Reddit, LinkedIn, YouTube, vakmedia, nieuws). Consistent met een site die in 2026 live ging, maar dit is nu de bottleneck voor alles. Kanttekening: de websearch is VS-georiënteerd en kan kleine Nederlandse LinkedIn-vermeldingen missen.

### Content E-E-A-T (64/100)
Experience 21/25 (uniek eigen onderzoek, "Gemeten, niet beweerd" wordt waargemaakt), Expertise 14/25 (aantoonbaar deskundig maar onzichtbaar), Authoritativeness 13/25 (sterke curatie en regulator-antwoorden, geen entity-verankering), Trustworthiness 16/25 (voorbeeldige methodologische eerlijkheid, ondergraven door ontbrekend contact/colofon/privacy). De epistemische discipline is opvallend: boetebedragen expliciet als "indicatie uit vakmedia" gemarkeerd, geen verzonnen claims gevonden. vragen.html is het sterkste trust-asset: antwoorden van de ACM zelf, gedateerd en gebronned.

### Technical GEO (84/100)
Uitstekende basis: één canonieke host met correcte 301's, echte 404's, zelfverwijzende canonicals op alle 22 pagina's, complete OG/Twitter-tags, `lang="nl"` overal, geen enkele afbeelding zonder alt-tekst, first load onder 300 KB, alle JS non-blocking. Aftrek: security headers (GitHub Pages-beperking), het monitor.html-renderinggat, en sitemap-lastmod op de hoofdpagina's.

### Schema & Structured Data (58/100)
Alle 15 JSON-LD-blokken zijn geldig. De zes Dataset-schema's zijn top 5%-markup (distribution, temporalCoverage, measurementTechnique, CC-BY-licentie, variableMeasured, verse dateModified). Gaten: de hardcoded Dataset-url, ontbrekende entity-verankering in Organization, en geen markup op de overzichtspagina's (artikelen.html, bronnen.html, wcag-audit.html). Concrete JSON-LD-voorbeelden per fix staan in de High/Medium-secties hierboven; de juiste build-scripts zijn erbij genoemd.

### Platform Optimization (57/100)
| Platform | Score | Oordeel |
|---|---|---|
| Perplexity | 68 | Sterkste platform: primaire data, methodologie, open JSON, vers. Alleen community-validatie ontbreekt |
| Google AI Overviews | 67 | Goede vraagstructuur en FAQ; autoriteit/backlinks ontbreken; geen `<table>` met sectorcijfers |
| ChatGPT search | 63 | Crawlertoegang perfect (25/25); entity recognition 8/35; afhankelijk van onbekende Bing-index |
| Bing Copilot | 52 | Geen verificatie, geen IndexNow; content past wel goed bij compliance-queries |
| Gemini | 37 | Zwakste: geen Google-ecosysteem, geen Knowledge Graph-entiteit, geen sameAs |

---

## Quick wins (deze week)

1. **`python tools/fetch_bron_dates.py` draaien** en bronnen.html herbouwen: 82 bronnen krijgen datums. Vijf minuten.
2. **Dataset-url-fix** in `tools/scrape_footer.py:563`: sectorpagina's citeren dan naar de juiste pagina. Eén regel plus `page_url` in de DATASETS-dict.
3. **Bing Webmaster Tools verifiëren + sitemap indienen + IndexNow-ping** in de deploy-workflow. Ontsluit twee platformen (Copilot, ChatGPT search) tegelijk.
4. **Organization-schema verrijken** (logo, foundingDate, contactPoint, parentOrganization Proper Access) plus de transparantiezin op over.html. Lost Critical #2 en High #3 in één keer op.
5. **Contactadres + colofon-/privacypagina** publiceren. Lost Critical #1 op zonder de anonimiteit te raken.

## 30-dagenplan

### Week 1: Trust-basis
- [ ] Functioneel e-mailadres live + "Mail ons" op over.html koppelen
- [ ] Colofon- en privacypagina (nieuwsbrief-AVG) toevoegen aan footer
- [ ] Transparantiezin Proper Access op over.html + `parentOrganization` in schema (na merkcheck: CLAUDE.md en live site spreken elkaar tegen)
- [ ] wcag-audit.html vullen (`data/auditbureaus.json`) of tijdelijk uit nav en sitemap

### Week 2: Schema en techniek
- [ ] Dataset-url-fix + `spatialCoverage`/`creator @id` in `scrape_footer.py`
- [ ] Organization verrijken op index.html; Article-schema: `image` + `@id`-koppelingen + BreadcrumbList + speakable in `build_articles.py`
- [ ] monitor.html: GEO-SUMMARY-markers + Dataset JSON-LD via de DATASETS-dict
- [ ] Bing Webmaster Tools + IndexNow in scrape.yml/deploy.yml; sitemap-lastmod voor monitorpagina's
- [ ] Datum-inconsistentie webshopmeting (run van 8 juni) uitzoeken

### Week 3: Content en citability
- [ ] Antwoordblok-patroon (40-60 woorden onder de H1) in `build_articles.py` + toepassen op alle 7 artikelen
- [ ] Eigen meetcijfer met datum invlechten in de 5 artikelen die het nog niet hebben
- [ ] Sectortabel als echte `<table>` met meetdatums op de homepage
- [ ] Vergelijkingstabel in het subsidie-artikel; Staatsblad als bron in toezicht-en-boetes
- [ ] Redactie-blok zonder namen op over.html + `author.url`
- [ ] `fetch_bron_dates.py` + ItemList op bronnen.html

### Week 4: Distributie en entity
- [ ] LinkedIn-bedrijfspagina EAA Monitor + eerste wekelijkse cijferpost
- [ ] Wikidata-item voor de dataset/site aanmaken; `sameAs` bijwerken
- [ ] Maandagmeting pitchen als datajournalistiek naar Emerce, Frankwatching, Tweakers
- [ ] Dataset aanbieden aan accessibility.nl en bestaande EAA-kennisbanken die nu ranken
- [ ] Reddit-post met de cijfers (r/accessibility, r/webdev)
- [ ] llms-full.txt genereren

---

## Bijlage: geanalyseerde pagina's

| URL | Titel/inhoud | Issues |
|---|---|---|
| / | Hub-homepage | hero-zin niet zelfstandig, cards i.p.v. tabel, Organization-schema kaal |
| /monitor.html | Webshopmonitor | geen gebakken cijfers (grootste gat), geen Dataset-schema |
| /monitor-financieel.html e.a. (5×) | Sectormonitors | Dataset-url wijst naar homepage; verder sterk |
| /artikelen.html | Kennisbank-overzicht | geen datums, geen ItemList |
| /artikelen/*.html (7×) | Artikelen | schema mist image/@id; antwoord soms pas onderaan; weinig eigen data |
| /vragen.html | Vragen uit de praktijk | sterkste trust-asset; dateCreated per vraag toevoegen |
| /bronnen.html | Bronnenoverzicht | 0/82 datums; geen ItemList |
| /wcag-audit.html | Auditbureaus | lege placeholder |
| /over.html | Over + methodologie | geen contactroute, geen schema, geen datum |
| /bezwaren.html, /bezwaar.html, /vraag-stellen.html | Formulieren/lijsten | bezwaar.html niet in sitemap |

*Audit uitgevoerd met vijf parallelle analyses (AI-zichtbaarheid, platforms, techniek, E-E-A-T, schema). Brand-searches zijn VS-georiënteerd; kleine Nederlandse vermeldingen kunnen gemist zijn.*
