# GEO-audit EAA Monitor

**Datum:** 5 juli 2026
**URL:** https://eaa-monitor.nl
**Type site:** Publisher / open-data-hub (informatie + wekelijkse meting)
**Pagina's bekeken:** 37 HTML-pagina's (NL + EN), plus robots.txt, llms.txt en sitemap.xml
**Methode:** broncode lokaal geïnspecteerd, live site en headers gecheckt, extern merkonderzoek via websearch

---

## Samenvatting

**GEO-score: 65/100 (Redelijk)**

De EAA Monitor is technisch bijna voorbeeldig geoptimaliseerd voor AI-zoeksystemen. De inhoud is server-side gerenderd, de cijfers staan gewoon in de HTML, er is een rijke llms.txt, een complete schema-graph en een robots.txt die AI-crawlers expliciet welkom heet. Op de pagina zelf doe je vrijwel alles goed.

Het hele gat zit buiten de site. "EAA Monitor" heeft nog geen enkele externe vermelding: geen backlinks, geen Wikipedia of Wikidata, geen social profielen, geen pers. Voor een AI-systeem is autoriteit vooral wat anderen over je zeggen, en dat is op dit moment niets. Daar komt een naamprobleem bij: "EAA" botst met astronomie (Electronically Assisted Astronomy) en luchtvaart (Experimental Aircraft Association), die veel bekender zijn. Zonder context lost "EAA" bij een taalmodel eerder op naar die betekenissen dan naar jouw wet.

Kort gezegd: je on-page GEO is top, je off-site autoriteit is nul. Dat is precies waar de winst zit.

### Scoreoverzicht

| Categorie | Score | Weging | Gewogen |
|---|---|---|---|
| AI-citeerbaarheid | 85/100 | 25% | 21,3 |
| Merkautoriteit | 12/100 | 20% | 2,4 |
| Inhoud (E-E-A-T) | 72/100 | 20% | 14,4 |
| Technische GEO | 92/100 | 15% | 13,8 |
| Schema en gestructureerde data | 90/100 | 10% | 9,0 |
| Platformaanwezigheid | 40/100 | 10% | 4,0 |
| **Totaal** | | | **65/100** |

---

## Wat sterk is

- **Server-side rendering.** Alle kerncijfers, navigatie en tekst staan in de ruwe HTML. Een AI-crawler heeft geen JavaScript nodig om je meting te lezen. Dit is de belangrijkste GEO-basis en die is op orde.
- **robots.txt.** GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-Web, PerplexityBot en Google-Extended staan allemaal expliciet toegestaan. Sitemap netjes gelinkt.
- **llms.txt.** Aanwezig en inhoudelijk, met zeven meet-regio's die per sector de laatste cijfers geven. Dit is precies waar het formaat voor bedoeld is.
- **Schema-graph.** WebSite, Organization (met `knowsAbout` en `contactPoint`), FAQPage, zeven Dataset-blokken met DataDownload, ItemList, BreadcrumbList, AboutPage, plus Article met SpeakableSpecification op elk kennisbankartikel. Voor een datasite is de Dataset-markup een sterke, onderscheidende zet.
- **Citeerbare vorm.** FAQ-blokken, vraag-en-antwoord op vragen.html, cijfers met datum en bron, korte alinea's. Dit is het soort tekst dat een AI makkelijk letterlijk overneemt.
- **Meertalig correct.** hreflang NL/EN/x-default in de sitemap en in de head, aparte /en/-tree.
- **Eigen data.** De wekelijkse meting is origineel onderzoek dat nergens anders bestaat. Dat is een sterk Experience-signaal en een reden voor een AI om juist jou te citeren.

---

## Kritieke punten

Geen. Er zijn geen blokkerende problemen: de site is crawlbaar, indexeerbaar, gerenderd en voorzien van structuur.

## Hoge prioriteit (deze maand oppakken)

### 1. Merkautoriteit is nul (Merkautoriteit 12/100)
Elke zoekopdracht naar "eaa-monitor.nl" of "EAA Monitor" levert alleen je eigen pagina's op. Geen enkele externe bron linkt of noemt je. Dit weegt 20% en trekt de totaalscore in z'n eentje omlaag.

**Doen:**
- Maak een **Wikidata-item** aan voor "EAA Monitor" (type: website / organisatie, met beschrijving "monitor van de European Accessibility Act in Nederland", link naar de site en de betrokken toezichthouders). Wikidata is de snelste manier om als entiteit herkend te worden door taalmodellen.
- Zorg voor **een handvol backlinks** uit de toegankelijkheidshoek: laat je opnemen in een linkoverzicht van digitoegankelijk.nl, accessibility.nl of een community-roundup. Eén link van een gezaghebbende bron doet meer dan tien van onbekende.
- Regel **een of twee vermeldingen** in vakmedia of blogs (Frankwatching, een nieuwsbrief in de sector). Elke onafhankelijke vermelding is een autoriteitssignaal.

### 2. Naamdubbelzinnigheid (raakt Merkautoriteit en Platform)
"EAA" resolveert bij een taalmodel eerder naar astronomie of luchtvaart. Je moet de naam altijd disambigueren.

**Doen:**
- Koppel in metadata en `knowsAbout` de naam consequent aan context: "EAA Monitor, de monitor van de European Accessibility Act in Nederland". Dat staat er deels al; trek het door in `alternateName` op het Organization-schema en in de eerste zin van llms.txt.
- Overweeg een `alternateName` als "European Accessibility Act Monitor" in het Organization-blok.

### 3. Geen `sameAs` op het Organization-schema
Het Organization-blok heeft geen `sameAs`-array. Dat is logisch (er zijn nog geen profielen), maar het is ook het gevolg van punt 1. Zodra je een Wikidata-item, LinkedIn-pagina of ander profiel hebt, zet die in `sameAs`. Dat verbindt de losse signalen tot één entiteit.

## Middelhoge prioriteit

### 4. Geen platformaanwezigheid buiten de eigen site (Platform 40/100)
Technisch ben je klaar voor AI Overviews, ChatGPT, Perplexity en Gemini (crawlbaar, gestructureerd, llms.txt). Maar je bestaat alleen op je eigen domein. Geen LinkedIn, geen YouTube, geen aanwezigheid op plekken waar modellen op trainen.

**Doen:**
- Zet een **LinkedIn-pagina** op voor de EAA Monitor. Deel wekelijks het nieuwe cijfer. Dit is meteen een `sameAs`-bron en een backlink.
- Overweeg je cijfers periodiek te delen op plekken die AI's citeren (een korte post, een bericht in een relevante community). Niet als marketing, maar omdat het je entiteit zichtbaar maakt.

### 5. Naamloze redactie beperkt E-E-A-T (Inhoud 72/100)
Attributie is nu alleen "redactie". Dat is een bewuste keuze (team anoniem), maar het kost wel Expertise- en Authoritativeness-punten, want AI weegt aantoonbare menselijke expertise mee.

**Afweging, geen harde fix:** je hoeft geen namen te noemen. Je kunt de expertise wel institutioneel aantoonbaar maken: een zin op over.html over de achtergrond van de redactie (bijvoorbeeld "samengesteld door auditors met x jaar ervaring in digitale toegankelijkheid"), een methodologie-uitleg bij de meting, en bronvermelding bij elke sectorlijst. Dat verhoogt Trust zonder de anonimiteit op te geven.

## Lage prioriteit

- **Geen Content-Security-Policy-header** op de live site (wel HSTS en X-Content-Type-Options). Voor GEO niet kritiek, wel goede hygiëne.
- **Dataset-schema verrijken.** De Dataset-blokken zijn er; je kunt ze sterker maken met `temporalCoverage`, `measurementTechnique` en een expliciete `license` (bijvoorbeeld CC BY). Dat maakt de data nog aantrekkelijker om te citeren en te hergebruiken.
- **"Belangrijkste conclusie"-blok.** Overweeg boven aan elke monitorpagina één samenvattende zin in een duidelijk kader ("X% van de webshops heeft geen verklaring, meting 1 juli 2026"). AI's pakken zo'n kant-en-klare samenvatting graag letterlijk over.

---

## Categorie-analyse

### AI-citeerbaarheid (85/100)
Sterk. De inhoud staat in de HTML, is opgedeeld in korte, feitelijke blokken met datum en bron, en de FAQ- en vraag-en-antwoordvorm is ideaal voor overname. De llms.txt met per-sector-meetregio's is een cadeau voor een AI die je cijfers wil samenvatten. Ruimte voor verbetering: expliciete samenvattingsblokken bovenaan de datapagina's en meer "kernconclusie"-zinnen die los citeerbaar zijn.

### Merkautoriteit (12/100)
De grote zwakte, en het enige wat de score echt drukt. Nul externe vermeldingen, geen Wikipedia of Wikidata, geen social profielen, geen backlinks van toezichthouders of vaksites. Plus een naam die botst met bekendere betekenissen. Dit is normaal voor een site die in 2026 is gestart, maar het is wel de plek waar elke verbetering het meeste oplevert. Concurrenten om AI-citaten: digitoegankelijk.nl (Logius, gezaghebbend), accessibility.nl, ictrecht.nl, plus de toezichthouders zelf.

### Inhoud E-E-A-T (72/100)
Goede diepgang (index 2.450 woorden, bronnenpagina 2.784, artikelen met datum en bronnen). Experience is sterk dankzij de eigen wekelijkse meting die nergens anders bestaat. Trust is goed: onafhankelijk, open data, contactadres, bronvermelding, over-pagina met AboutPage-schema. Freshness is goed: wekelijkse updates, `datePublished` en `dateModified` op alle artikelen. Wat de score remt is het ontbreken van aantoonbare, benoemde expertise (alleen "redactie").

### Technische GEO (92/100)
Bijna perfect. Server-side rendering, AI-crawlers welkom, llms.txt aanwezig en gevuld, sitemap met hreflang, canonicals, HTTP/2, HSTS en nosniff-header, SpeakableSpecification op zeven artikelen. Enige minpunt: geen CSP-header (niet kritiek voor GEO). Geen JavaScript-afhankelijkheid voor de kerninhoud, wat de meeste sites juist verkeerd doen.

### Schema en gestructureerde data (90/100)
Zeer compleet: WebSite, Organization, FAQPage, zeven Dataset + DataDownload, ItemList, BreadcrumbList, AboutPage, CollectionPage, Article + Speakable per artikel. De Dataset-markup is voor een datasite onderscheidend en precies goed. Kleine winst: `sameAs` op Organization (zodra er profielen zijn), `alternateName`, en rijkere Dataset-velden (`license`, `temporalCoverage`).

### Platformaanwezigheid (40/100)
Technisch klaar voor alle grote AI-platforms, maar feitelijk alleen aanwezig op het eigen domein. Geen enkele externe plek (LinkedIn, YouTube, Wikipedia, community's) waar een model je tegenkomt of op traint. De helft van deze categorie is techniek (goed), de andere helft is aanwezigheid (leeg).

---

## Snelle winst (deze week)

1. **Wikidata-item aanmaken** voor EAA Monitor, met beschrijving en link. Grootste hefboom, kost een uur.
2. **LinkedIn-pagina** opzetten en de laatste meting delen. Levert meteen een `sameAs`-bron en een backlink.
3. **`alternateName` en `sameAs`** toevoegen aan het Organization-schema (nu vast leeg voorbereiden, vullen zodra profielen live zijn).
4. **Eén disambiguerende zin** bovenaan llms.txt en in de Organization-`description`: "EAA Monitor is de Nederlandse monitor van de European Accessibility Act" (niet de astronomie- of luchtvaart-EAA).
5. **Eén backlink regelen** uit de toegankelijkheidshoek (digitoegankelijk.nl-linklijst, community-roundup of een vakblog).

## Plan voor 30 dagen

### Week 1: Entiteit vestigen
- [ ] Wikidata-item aanmaken en koppelen aan de site
- [ ] LinkedIn-pagina live zetten
- [ ] `alternateName` + `sameAs` in Organization-schema verwerken

### Week 2: Autoriteit opbouwen
- [ ] Twee tot drie backlinks regelen uit de sector (toezichthouders, vaksites, community)
- [ ] Eerste vermelding in vakmedia of nieuwsbrief nastreven
- [ ] Methodologie-uitleg toevoegen bij de meting (versterkt Trust)

### Week 3: Inhoud verdiepen
- [ ] Institutionele expertise-zin op over.html (zonder namen)
- [ ] Samenvattingsblok bovenaan elke monitorpagina ("kernconclusie")
- [ ] Dataset-schema verrijken met `license`, `temporalCoverage`, `measurementTechnique`

### Week 4: Platform verbreden
- [ ] Wekelijkse cijferpost op LinkedIn tot routine maken
- [ ] Cijfers delen op één of twee plekken die AI's citeren
- [ ] Herhaal de brand-mention-scan om verandering te meten

---

## Bijlage: bekeken pagina's (selectie)

| Pagina | Woorden | Belangrijkste observatie |
|---|---|---|
| index.html | 2.450 | Volledige schema-graph, server-rendered cijfers, sterke hub |
| over.html | 1.273 | AboutPage-schema; alleen "redactie" als attributie |
| bronnen.html | 2.784 | Diepe, citeerbare bronnenlijst |
| vragen.html | 1.103 | FAQ-vorm, ideaal voor AI-overname |
| artikelen/*.html (7) | wisselend | Article + Speakable + datePublished/dateModified |
| monitor*.html (7 sectoren) | wisselend | Dataset-schema, gebakken kerncijfer in HTML |
| wcag-audit.html | 415 | Kort; kan diepgang gebruiken |
| eregalerij.html | 482 | ItemList-schema |

---

*Kernpunt: on-page GEO is zo goed als af. De volgende sprong komt niet van nog meer schema, maar van externe autoriteit en het oplossen van de naamdubbelzinnigheid. Wikidata, een paar backlinks en een LinkedIn-pagina brengen de merkautoriteit van 12 naar boven de 40, en tillen de totaalscore van 65 richting de 80.*
