# Plan: eigen sectoronderzoek buiten de EAA Monitor

Opgesteld 10 oktober 2026 door James, op verzoek van Chief naar een vraag van Julia van
10 oktober. Dit is een plan, er is niets gebouwd. Julia kiest eerst de plek en de sector.

Sectoren uit de opdracht: onderwijs met hbo, wo en mbo, overheid met gemeenten, provincies,
waterschappen en uitvoeringsorganisaties, musea en cultuur, en zorg met ziekenhuizen.

Alle cijfers in dit document zijn zelf gemeten. Bij elk cijfer staat de meetdatum. Waar ik iets
niet heb kunnen meten, staat dat er met zoveel woorden bij.

## 1. Advies in het kort

1. **Publiceer op properaccess.nl**, onder een eigen sectie `/onderzoek/`. Dat is het merk waar
   het onderzoek volgens het besluit van 10 oktober onder uitgaat, het is de sterkste van onze
   domeinen, en de repo kan de data zelf bijwerken: er staat al een dagelijkse cron in
   `.github/workflows/main.yml` die een script draait, het resultaat terugcommit naar `main` en
   in dezelfde run publiceert. Er staat ook al een door Hugo gerenderde datapagina met
   meetcijfers op de site.
2. **Maandelijks meten, niet wekelijks.** De claimkant beweegt langzaam: in de laatste 12
   maandpunten van het Dashboard DigiToegankelijk veranderen gemiddeld 196 van 9.096 sites per
   maand van status, 2,2%. De bron publiceert zelf één punt per maand. En onze eigen scan is
   tussen twee rondes 3,9% tot 6,2% onstabiel, in beide richtingen. Wekelijks publiceren maakt
   ruis tot nieuws.
3. **Begin bij de overheid, niet bij onderwijs**, als je het onderzoek onderscheidend wilt
   hebben. Een automatische scan van één pagina per site is voor alle vier de gevraagde sectoren
   al gratis beschikbaar bij een andere partij, met meer sites dan wij zouden meten. Wat niemand
   publiceert is de vergelijking tussen wat een organisatie zelf in het register claimt en wat
   een meting vindt. Die claim bestaat alleen bij de overheid.
4. **Meet in ronde 1 één hoofdsite per organisatie**, met het aantal sites van die organisatie
   in het register als context. Dat is vergelijkbaar, uitlegbaar en goedkoop.
5. **Vraag de registerdata op bij Logius** voordat je gaat crawlen. De dataset staat op
   data.overheid.nl onder licentie CC-BY 4.0 en de beschrijving zegt dat een CSV met de scores
   van organisaties op aanvraag beschikbaar is.

Wat Julia moet beslissen staat in sectie 10.

## 2. Wat er al is

Dit is de belangrijkste uitkomst van de verkenning, en hij verandert de vraag. Gemeten op
10 oktober 2026.

### toegankelijkheidsindex.nl, van Emble

- 2.943 Nederlandse websites in 27 sectoren.
- Methode: één opgegeven pagina per site, geladen in een browser en gecontroleerd met axe-core.
  Dus dezelfde engine en dezelfde diepte als `tools/scan_axe.py`.
- Laatste meting 28 september 2026, de metingen worden periodiek herhaald.
- Dekking van onze vier sectoren: gemeenten 340, universiteiten 17, hogescholen met mbo en hbo
  samen 40, ziekenhuizen 67, musea 37.
- Eigen voorbehoud op de site: "De scan geeft signalen over mogelijke toegankelijkheidsproblemen;
  hij is geen volledige WCAG-audit."

### Silktide Index

- Er bestaat een categorie "Netherlands Government". Hoeveel organisaties daarin zitten, staat
  niet op de pagina die ik las, dus het getal "ruim 400" uit de opdracht heb ik niet kunnen
  bevestigen.
- Methode volgens de rapportpagina van gemeente Groningen: "an automated assessment of 25
  webpages on 6th September 2026", score 93%, plaats 154 in die categorie.
- Dus 25 pagina's per site, dieper dan één pagina, en ook volledig automatisch.

### Dashboard DigiToegankelijk, van het ministerie van Binnenlandse Zaken

- De officiële claimkant: per overheidsorganisatie de status van elke site en app uit de
  toegankelijkheidsverklaringen, bijgewerkt per dag, met een historische reeks per maand.
- Stand op 30 september 2026: status A 858, B 4.409, C 558, D 2.376 en E 895, samen 9.096 sites
  en apps.
- Dit is geen concurrent, dit is onze bron.

### Wat dat betekent

De scan zelf is geen product meer. Een ranglijst per sector op basis van axe-core op één pagina
bestaat al, is gratis, en dekt meer sites dan wij in ronde 1 zouden halen. Bouwen wij hetzelfde,
dan leveren we een kleinere kopie van iets dat er is, en moeten we bovendien uitleggen waarom
onze cijfers afwijken van die van Emble terwijl we dezelfde engine gebruiken.

Wat wij wel als enige kunnen: de claim naast de meting leggen. Een overheidsorganisatie zegt in
het register zelf welke status haar site heeft, welke succescriteria niet gehaald worden, wie het
onderzoek deed, met welke methode en hoe oud dat onderzoek is. Dat staat machineleesbaar in het
register. Niemand publiceert wat er gebeurt als je die zelfverklaring naast een meting legt. Wij
zijn auditor, dus dat is ook het onderwerp waar wij iets over mogen zeggen.

## 3. Waar het komt te staan

### De drie opties naast elkaar

**properaccess.nl.** Hugo 0.151.0, publieke repo, GitHub Pages achter Cloudflare. Een merge gaat
meteen live en Julia merget daar zelf. Voordelen: het juiste merk, de sterkste domeinautoriteit
van onze sites, en de bouwstenen staan er al. In `.github/workflows/main.yml` staat een cron die
elke dag om 06:00 UTC draait, met `permissions: contents: write`, een Python-script uitvoert, het
resultaat terugcommit naar `main` en in dezelfde run deployt. Datapagina's uit een Hugo-databestand
bestaan ook al: `layouts/shortcodes/eaa-monitor-chart.html` rendert `data/eaa_monitor.yaml` op
`content/english/european-accessibility-act.md`, server-side, met de meetdatum in de kop. Dat
bestand staat op `measured: 2026-09-07` en is dus op 10 oktober 33 dagen oud; dat laat precies
zien waarom het bijwerken geautomatiseerd moet.

**Een nieuwe repo met eigen domein.** Alles uit de EAA Monitor werkt daar direct, want de Monitor
is zo gebouwd. Nadelen: een tweede site om bij te houden, een nieuw domein zonder autoriteit,
eigen ontwerp, eigen `llms.txt`, eigen cookie- en privacyteksten, en een merk los van Proper
Access terwijl het besluit van 10 oktober juist zegt dat het onderzoek onder de naam Proper
Access uitgaat. De EAA Monitor laat zien wat die keuze kost aan onderhoud.

**testtoegankelijkheid.nl.** Next.js met Postgres op onze eigen server. Technisch het meest
geschikt voor cijfers die vaak veranderen, want er is een database en een scan-engine. Drie
bezwaren: het merk is Testtoegankelijkheid en WCAG Toolkit en niet Proper Access, elke wijziging
vraagt een deploy van Julia op de server, en de repo is privé, dus Actions-minuten tellen daar
wel mee.

### Advies

properaccess.nl, in een eigen sectie `/onderzoek/<sector>/`. Met per sector:

- een overzichtspagina met de cijfers, gerenderd door Hugo uit een databestand, dus zichtbaar
  voor een crawler zonder JavaScript;
- een lijstpagina met alle gemeten organisaties, ook server-rendered;
- een methodepagina met de meetregels, de statussen en wat de scan niet zegt;
- een vaste verwijzing naar de bron en de meetdatum op elke pagina.

### Hoe de data er komt

Drie stappen, in de orde van voorkeur:

1. **Meting buiten de website.** De scan draait in een workflow en schrijft één databestand per
   sector, bijvoorbeeld `data/onderzoek/onderwijs.yaml`. Hugo rendert daaruit de pagina's. Dit is
   hetzelfde patroon als `data/eaa_monitor.yaml` en `data/amersfoort.yaml` nu.
2. **De workflow commit het databestand zelf naar `main`** en de bestaande deploy publiceert het
   in dezelfde run. Dat patroon staat er al voor de dagelijkse LinkedIn-serie. Bij één ronde per
   maand is dat één automatische commit per maand.
3. Wil Julia er eerst naar kijken, dan opent de workflow in plaats daarvan een pull request met
   alleen het databestand, en merget zij die. Eén merge per maand is te overzien, en dan gaat er
   nooit een cijfer live dat niemand heeft gezien.

Twee dingen die ik niet zelf kan doen:

- **Ik kan geen workflowbestand pushen.** Mijn token heeft dat recht met opzet niet. De workflow
  stel ik voor in de pull request, Julia zet hem erin.
- **Ik merge niet op properaccess.nl.** Dat doet Julia, en een hook blokkeert het ook.

Waar de meetcode staat, is een aparte keuze. Mijn voorkeur is in `properaccess.nl` zelf, naast de
bestaande `scripts/`, omdat er dan geen token tussen twee repo's nodig is en de data en de pagina
in dezelfde commit zitten. De Monitor blijft dan de plek voor de EAA-sectoren en leent zijn
gereedschap uit.

## 4. Het datamodel: claim naast meting

### Waar de claim staat, per sector

Gemeten op 10 oktober 2026 in het Dashboard DigiToegankelijk, aantal organisaties en aantal
websites in het register per organisatietype:

| Organisatietype | Organisaties | Websites in het register |
|---|---|---|
| Gemeente | 353 | 5.517 |
| Provincie | 12 | 486 |
| Waterschap | 21 | 194 |
| ZBO | 93 | 520 |
| Agentschap | 34 | 524 |
| Samenwerking | 459 | 634 |
| Rijksoverheid | 87 | 696 |
| GGD | 24 | 98 |

Samen 1.083 organisaties en 8.669 websites. Het register kent 353 gemeenten terwijl Nederland er
342 heeft, dus er zitten opgeheven of samengevoegde organisaties in. Die moet je er bij het
koppelen uit halen.

Voor de andere drie sectoren is er geen claimkant. In het register staan op 10 oktober 26
verklaringen die op "universiteit" matchen, 14 op "museum", 3 op "hogeschool" en 0 op
"ziekenhuis". Het Dashboard kent geen organisatietype onderwijs, zorg of cultuur; de types zijn
Gemeente, Provincie, Waterschap, ZBO, Agentschap, Samenwerking, Rijksoverheid, GGD,
Adviescollege, Hoge College van Staat, Koepelorganisatie, Organisatie met overheidsbemoeienis,
RUD-Omgevingsdienst, Rechtspraak, Veiligheidsregio en Overige.

Daar volgt uit dat het onderzoek per sector een ander karakter heeft:

- **Overheid:** claim uit het register naast onze meting. Dit is het onderscheidende onderzoek.
- **Onderwijs, musea en cultuur, zorg:** geen register, dus de claim is wat de organisatie zelf
  op haar site publiceert. Dat is het webshopmodel van de Monitor: staat er een
  toegankelijkheidsverklaring, en zo ja, met een onderzoeksrapport erbij. Plus onze scan.

Of deze organisaties onder het Besluit digitale toegankelijkheid overheid vallen, is een
juridische vraag en niet aan mij. Het register suggereert van niet, en dat is een meting van de
praktijk, niet van de wet. Laat de wettelijke inkadering per sector toetsen door Gerard voordat
er een woord over verplichtingen op de site staat.

### Is de registerdata in bulk op te halen

Ja, en er zijn vier routes. Alle vier gemeten op 10 oktober 2026.

1. **Vragen bij Logius.** De dataset "Toegankelijkheidsverklaring websites van de overheid" staat
   op data.overheid.nl, bronhouder Logius, licentie CC-BY 4.0, contact Digitoegankelijk@logius.nl.
   In de beschrijving staat: "Op aanvraag is een CSV bestand beschikbaar met een lijst van scores
   van organisaties". Dit is de nette route, levert waarschijnlijk de volledige set in één keer,
   en geeft ons een gesprek met de bronhouder in plaats van verkeer op hun server. Begin hier.
2. **Een CSV per organisatie uit het Dashboard.** `GET /organisaties/download/<id>` geeft een
   `text/csv` met de kolommen Naam/URL, Adres, Status in dashboard, Aantal succescriteria waaraan
   wordt voldaan, Totaal aantal succescriteria, Opmerking, en Site of app. Voor Logius, id 27,
   zijn dat 66 regels. Eén verzoek per organisatie, dus 1.083 verzoeken voor de hele overheid.
3. **De zoekpagina van het Dashboard.** `/zoeken` is volledig server-rendered, met `?page=N` en
   filters `type[]`, `organisation-type[]` en `level[]`. Daarmee haal je de organisatie-id's per
   type op zonder JavaScript. Het Dashboard heeft geen `robots.txt`.
4. **Het register zelf.** `toegankelijkheidsverklaring.nl/register` is een Drupal-overzicht met
   50 rijen per pagina en als laatste pagina `?page=168`, dus ongeveer 8.450 verklaringen. Er is
   één filter, `w`, die op naam zoekt. `robots.txt` staat `/register` toe en zet geen
   `Crawl-delay`.

De verklaringpagina's zelf zijn machineleesbaar, en dat is de rijkste bron. Op
`/register/19532` staat microdata met onder andere `website-url`, `nalevingsstatus`,
`bewerkdatum`, `onderbouwingcontrole`, `onderzoeksresultaat-url`, `onderzoeksresultaat-datum`,
`onderzoeksresultaat-uitvoerder`, `onderzoeksresultaat-scope`, `onderzoeksresultaat-methode`,
`onderzoeksresultaat-actualiteit`, `alternatief`, `maatregel`, `template-versie`, en een
`sc-onvoldoende` per succescriterium dat de organisatie zelf niet haalt. Op die ene pagina staan
19 keer `sc-onvoldoende`.

Dat laatste is het goud van dit onderzoek: de organisatie zegt zelf welke succescriteria niet
gehaald worden. Dat kun je naast de uitkomst van onze scan leggen, succescriterium voor
succescriterium, want `tools/scan_axe.py` levert de WCAG-criteria al mee via `sc_from_tags`.

Mandy zoekt de bulkvraag ook uit. Ik kan haar kanaal niet bereiken, de brug kent alleen james,
gerard, nata en chris. Deze sectie is wat ik gemeten heb; laat Chief het aan haar doorgeven zodat
we niet twee keer hetzelfde doen. Wat ik haar zou vragen: route 1 bij Logius oppakken, en voor de
drie sectoren zonder register de populatielijst met een bron per regel, zoals
`workflows/research_sector_list.md` dat voor de EAA-sectoren voorschrijft.

### Hoe je claim en meting koppelt

De sleutel is de genormaliseerde host. Gebruik dezelfde normalisatie als `normalizeUrl` in
`public/app.js` regel 218: kleine letters, schema eraf, `www.` eraf, afsluitende slash eraf.
Anders lopen de cijfers op de pagina en in de data uiteen, en dat is precies de fout die de
Monitor met `build_lijsten.py` moest repareren.

Koppelen in deze volgorde, en de uitkomst vastleggen als eigen veld:

1. **Exacte host.** De `Adres`-kolom of `website-url` is gelijk aan de gemeten URL. Zekerheid
   `exact`.
2. **Zelfde hoofddomein, andere host.** Bijvoorbeeld een verklaring voor `afspraken.amersfoort.nl`
   terwijl wij `amersfoort.nl` meten. Zekerheid `hoofddomein`. Dit mag nooit stil doorgaan voor
   een verklaring over de gemeten site.
3. **Niets gevonden.** Zekerheid `niet-gevonden`. Het label is dan "geen verklaring voor deze URL
   in het register gevonden", en nooit "geen verklaring".

Twee dingen die je apart moet behandelen:

- **Apps.** De `Adres`-kolom bevat ook URL's van de App Store en Google Play. Dat zijn apps, niet
  websites. Haal ze eruit en zeg in de methode dat je ze niet meet.
- **Organisatie met verklaringen, hoofdsite zonder.** Een gemeente met 23 verklaringen en geen
  verklaring voor de hoofdsite is een eigen uitkomst, en een interessante. Label hem als zodanig
  en niet als "geen verklaring".

### De records

Eén bestand per sector, met per organisatie de sites en per site één meetrecord. In velden:

- `organisatie`: naam, type, sector, `bron` met de vindplaats van de populatielijst, en
  `register_id` als die er is.
- `site`: `url`, `host`, `rol` met hoofdsite of subsite.
- `claim`: `bron` met register, eigen site of geen, `status` met A tot E of geen, `verklaring_url`,
  `bewerkdatum`, `onderbouwingcontrole`, `onderzoek` met url, datum, uitvoerder, methode, scope en
  actualiteit, en `sc_onvoldoende` als lijst.
- `meting`: `scan_status`, `gemeten_op`, aantal overtredingen per succescriterium, en de
  axe-versie.
- `koppeling`: `sleutel`, `zekerheid`, en `opmerking`.
- `uitkomst`: het afgeleide label, zie hieronder.

De vier labels op de pagina:

- **Claim en meting liggen in lijn.** De status is D of de verklaring noemt de criteria die onze
  scan ook vindt.
- **De claim is gunstiger dan onze meting.** Status A, en onze scan vindt overtredingen van WCAG
  A of AA. Dit is de kern van het onderzoek, en tegelijk het label waar je het meest voorzichtig
  mee moet zijn, want een scan dekt maar een deel van de criteria. Zie sectie 9.
- **Geen claim gevonden.**
- **Niet te controleren.** Bot-bescherming, wachtrij, niet gerenderd, of uitgesloten door
  `robots.txt`.

Er is een werkend voorbeeld van dit model in huis: `data/amersfoort.yaml` in de repo
`properaccess.nl`. Daarin staat per site `status`, `status_label`, `verklaring_url`,
`rapportdatum`, `laatst_gewijzigd`, `verloopt_op`, `ons_rapport` en `auditor`, met `host` als
sleutel, gehaald uit het register met de `w`-filter. Dat is één gemeente en handmatig gevuld,
maar het model hoeft dus niet bedacht te worden: het hoeft alleen gegeneraliseerd en
geautomatiseerd.

## 5. Wat we hergebruiken

Per gereedschap: kopiëren, generaliseren of laten staan.

### `tools/scrape_footer.py`: splitsen, en het harde deel kopiëren

Dit bestand doet twee dingen. Het eerste is de detectie van een verklaring op een site, met de
trefwoordlijsten, de link- en tekstcontrole, de controle van de doelpagina met
`STATEMENT_CONTENT_MARKERS`, het weglopen door maximaal 5 subpagina's, de cookie-selectors en de
`OVERLAY_VENDOR_DOMAINS`. Het tweede is het bakken van cijfers in de HTML van de Monitor, met de
markers, de hub-kaarten, `llms.txt` en de Dataset-JSON-LD.

- **Nemen:** de detector en de run-machinerie. Die machinerie is het deel dat je niet opnieuw
  wilt uitvinden, want er zit de meetervaring van de Monitor sinds maart 2026 in:
  `PER_SITE_CAP_S` van 90 seconden met een watchdog en zelfherstart,
  `NAVIGATION_TIMEOUT` van 15 seconden, `CONTEXT_RECYCLE_EVERY` op 200, `FLUSH_EVERY` op 100 zodat
  een afgebroken run zijn werk houdt, het blokkeren van afbeeldingen en fonts, en de render-grens
  van `MIN_RENDERED_TEXT` 200 tekens en `MIN_RENDERED_LINKS` 5 links die een challenge-pagina
  onderscheidt van een echte site. Dat herschrijf je niet; dat is eerder duur geleerd.
- **Niet nemen:** alles rond de markers, de hub-kaarten en `llms.txt`. Dat hoort bij de
  pagina-opzet van de Monitor. Hugo rendert de pagina's van het onderzoek uit het databestand, dus
  bakken is er niet bij.
- **Kopiëren, niet generaliseren.** De Monitor draait elke maandag over 10.271 sites en is onze
  publieke meetreeks. Een refactor van 1.800 regels om een tweede product te bedienen zet die
  reeks op het spel voor een voordeel dat we nu nog niet nodig hebben. Kopieer de detector en de
  run-machinerie naar een eigen module, en neem `tests/test_detector.py` mee, inclusief de
  fixtures en de confusion matrix. Een detector zonder zijn tests is een gok.
- **Wel generaliseren als de derde sector komt.** Op het moment dat twee producten dezelfde
  detector gebruiken en er een fout in zit, moet die op één plek te repareren zijn. Zet dat als
  voorwaarde in de pull request van ronde 2, niet in ronde 1.

### `tools/scan_axe.py` met `build_axe_targets.py` en `build_axe_overlay.py`: kopiëren zoals het is

Dit is al een losstaande keten: een lijst in, een overlay uit. Hij levert precies wat we willen
en op dezelfde manier als onze andere producten, en dat is een eigenschap die geld waard is: één
engine, axe-core 4.11 uit `tools/vendor/axe.min.js`, dezelfde versie als op wcag-scan.eu, alleen
WCAG A en AA, best-practice-regels uit. Neem mee: de render-waarborg van minder dan 50
DOM-elementen die `niet-gerenderd` geeft in plaats van "geen fouten", de injectie via
`page.evaluate` zodat een strenge Content Security Policy de scan niet stilletjes laat slagen,
`SCAN_CAP_S` van 120 seconden met zelfherstart, en `FLUSH_EVERY` op 25.

Eén wijziging is nodig: `build_axe_targets.py` bouwt de doellijst nu uit sites met
`has_statement=True`. Voor het onderzoek wil je elke site in de populatie scannen, ook die zonder
claim, want "geen verklaring en toch geen fouten" is een uitkomst. Dat is een
commandoregel-optie, geen herbouw.

### `tools/build_lijsten.py`: niet kopiëren, de regels wel

Dit bestand bestaat omdat `monitor.html` zijn tabel in de browser opbouwt en een crawler zonder
JavaScript dus geen enkele naam ziet. Op properaccess.nl is dat probleem er niet: Hugo rendert de
lijst uit het databestand tijdens de build. De code is daar dus niet nodig.

De regels eruit zijn wel nodig, en ze moeten letterlijk hetzelfde blijven als wat de pagina
toont:

- een organisatie met bezwaar valt uit de lijst én uit de telling;
- `scrape_status != success` is "niet te controleren" en nooit "geen verklaring";
- de scanuitslag koppelt op de genormaliseerde URL, los van de claim, zodat een nieuwe ronde de
  andere helft niet overschrijft.

Zet die drie als testcase in de nieuwe keten. In de Monitor moesten de filterregels van
`app.js` en `build_lijsten.py` met de hand gelijk worden gehouden; dat is een valkuil die je in
een nieuw product niet hoeft te herhalen, omdat er maar één renderpad is.

### `tools/sync_confirmed.py`: kopiëren voor de sectoren zonder register

De logica is: een eenmaal geverifieerde verklaring blijft 30 dagen staan, een fout of time-out
laat de bevestiging staan, en een weggehaalde verklaring verdwijnt. Dat beschermt tegen een site
die één ronde achter een challenge zit. Voor onderwijs, musea en zorg heb je dat net zo hard
nodig als bij de webshops.

Voor de overheid is het niet nodig: daar komt de claim uit het register en niet van de site.
Blijft de registerbron een ronde onbereikbaar, dan is het antwoord niet "geen verklaring" maar
"deze ronde niet opgehaald", en bewaar je de vorige waarde met zijn datum.

### Nieuw te bouwen

- `fetch_register.py`: haalt de claimkant op via route 1 of 2 van sectie 4 en normaliseert naar de
  records van sectie 4.
- `koppel.py`: koppelt claim en meting op de genormaliseerde host en zet `zekerheid` en `uitkomst`.
- `robots.py`: leest en respecteert `robots.txt` per host. De Monitor doet dit nu niet, zie
  sectie 8.
- Hugo-templates voor de drie pagina's per sector.

## 6. Schaal, duur en kosten

### Wat een site kost, gemeten aan onze eigen runs

- **Footer-scrape.** Run 37343741564 van 5 oktober 2026: 10.271 webshops, 12 shards plus een
  merge-job, samen 968,7 Actions-minuten, 141 minuten wandklok. Dat is 5,7 seconden per site.
- **Axe-scan.** Run 37465464111 van 6 oktober 2026: 290 sites in 23,6 minuten, in één job. Dat is
  4,9 seconden per site.
- Samen dus ongeveer 10,6 seconden per site voor claim en scan, inclusief de sites die
  vastlopen, opnieuw moeten of achter een muur zitten.

### Wat een ronde kost

| Omvang | Rekentijd | Wandklok met 12 shards |
|---|---|---|
| 100 sites | 18 minuten | 2 minuten |
| 353 gemeenten, één hoofdsite elk | 62 minuten | 5 minuten |
| 1.083 overheidsorganisaties, één hoofdsite elk | 3,2 uur | 16 minuten |
| Alle 8.669 overheidssites uit het register | 25,5 uur | 2,2 uur |

De claimkant erbij: 1.083 verzoeken voor een CSV per organisatie is bij één verzoek per 2 seconden
36 minuten. Het hele register langslopen is 169 overzichtspagina's plus ongeveer 8.450
verklaringpagina's, bij dezelfde snelheid 4,8 uur. Vraag je de CSV op bij Logius, dan is dit één
download.

De sectoren zonder register zijn klein. Voor de ordegrootte: Emble meet 17 universiteiten, 40
hogescholen en mbo-instellingen, 67 ziekenhuizen en 37 musea. Dat zijn bij elkaar 161 sites, dus
ongeveer een half uur rekentijd per ronde. De echte populatielijst komt van Mandy; deze getallen
zijn van een andere partij en alleen bedoeld om de orde van grootte te laten zien.

### GitHub Actions-minuten

`eaa-monitor` en `properaccess.nl` zijn publieke repo's. Voor publieke repo's rekent GitHub geen
Actions-minuten, dus de hele ronde is gratis, ook de variant van 25,5 uur. Zou het onderzoek op
testtoegankelijkheid.nl landen, dan verandert dat: `wcag-scan` is een privérepo en daar tellen de
minuten wel mee.

Eén praktische waarschuwing over de planning. De cron van GitHub start in de praktijk uren later
dan de opgegeven tijd; ik heb eerder een mediaan van 5 tot 7 uur vertraging gemeten op onze eigen
workflows. Beloof dus geen tijdstip op de site, alleen een maand of een week, en zet de werkelijke
meetdatum uit de data op de pagina.

### Wekelijks of maandelijks

Maandelijks. Met drie metingen als onderbouwing:

1. **De claimkant beweegt langzaam.** Over de laatste 12 maandpunten van het Dashboard verandert
   gemiddeld 196 van 9.096 sites per maand van status, 2,2% per maand. De grootste
   maandverschuiving in dat jaar was 145 sites van B.
2. **De bron publiceert zelf maandelijks.** De historische reeks van het Dashboard heeft één punt
   per maand, van 30 april 2022 tot 30 september 2026, 54 punten. Wekelijks publiceren zou bij een
   maandelijkse bron een preciezer beeld suggereren dan er is.
3. **Onze scan is tussen twee rondes niet stabiel genoeg om wekelijks nieuws te maken.** Ik heb
   drie opeenvolgende rondes van `data/axe-results.json` uit de git-historie vergeleken: tussen
   8 en 22 september wisselde 11 van 264 sites van scanstatus, 4,2%; tussen 22 september en
   3 oktober 17 van 273, 6,2%; tussen 3 en 6 oktober 11 van 280, 3,9%. De wisselingen gaan in
   beide richtingen, dus een deel is echte verandering en een deel is ruis van cookiemuren,
   dynamische inhoud en timing. Bij 353 gemeenten zouden dat per week 14 tot 22 sites zijn die van
   label wisselen zonder dat er iets aan de site is gedaan.

Voor de webshopmonitor blijft wekelijks wel logisch: daar is de verandering zelf het verhaal en
is de reeks al wekelijks. Voor dit onderzoek is de jaarvergelijking het verhaal.

## 7. Scope van ronde 1

- Eén hoofdsite per organisatie, aangewezen in de populatielijst en niet door ons geraden.
- Het aantal sites van die organisatie in het register staat als context op de pagina, zodat
  niemand denkt dat wij de hele organisatie hebben gemeten.
- Eén pagina per site in de scan, net als nu. Meer pagina's per site is de logische volgende stap
  en meteen het punt waarop we dieper gaan dan Emble met zijn ene pagina, maar het vermenigvuldigt
  de kosten en de ruis. Doe dat pas als ronde 1 staat.
- Geen apps.

## 8. Zorgvuldigheid

Wij zijn de auditor. Een verkeerd label kost ons meer dan een ontbrekend cijfer. De regels
hieronder zijn daarom hard.

### Wat er nu nog niet goed staat

**`robots.txt` wordt in de Monitor niet gelezen.** Ik heb het nagekeken: in geen enkel bestand in
`tools/` komt robots voor. En de user-agent is een gewone Chrome-string die niet zegt wie wij zijn.
Voor een monitor van webshops was dat te verdedigen. Voor een onderzoek onder onze eigen naam
tegen publieke instellingen is het dat niet. Dus voor dit product:

- **Lees `robots.txt` per host** en respecteer hem. Verbiedt hij de pagina, dan is de uitkomst
  `uitgesloten-robots` met de reden erbij, en dat is iets anders dan "geen verklaring" en iets
  anders dan "niet te controleren".
- **Zeg wie je bent in de user-agent**, met een URL naar de methodepagina, bijvoorbeeld
  `ProperAccessOnderzoek/1.0 (+https://www.properaccess.nl/onderzoek/methode/)`. Dan kan een
  beheerder zien wie er langskwam en ons bellen.
- **Eén verzoek per host tegelijk**, met de pauze die de scraper nu al heeft, en nooit parallel
  op hetzelfde domein. De shards verdelen op host, niet op URL.
- **Alleen openbare pagina's.** Geen inloggedeelte, geen formulier verzenden, geen zoekopdracht
  afvuren, geen pagina achter een betaalmuur. Geen persoonsgegevens vastleggen; wat we opslaan is
  een URL, een status en een meetuitkomst.

### Bot-bescherming

De harde regel uit de Monitor blijft staan, en gaat hier zwaarder wegen: bot-bescherming, een
wachtrij of een niet-gerenderde pagina is **"niet te controleren"** en nooit "geen verklaring".
Technisch zit dat al in de render-waarborg van beide gereedschappen.

Daar hoort één nieuwe regel bij. In `docs/bot-protected-monitoring.md` staat het plan om harde
bot-bescherming te omzeilen met een dienst die de challenge oplost. Voor dit onderzoek is die
route dicht. Wij omzeilen geen bescherming van een publieke instelling om haar daarna te kunnen
beoordelen. Zo'n site blijft "niet te controleren", en dat percentage publiceren we gewoon.

### Recht op weerwoord

Neem de bezwaarroute van de Monitor over, ook hier. Op elke organisatiepagina een regel met wat
te doen als het cijfer niet klopt, en een bezwaar dat zichtbaar wordt verwerkt. Bij overheden is
dat extra belangrijk, omdat onze meting naast hun eigen formele verklaring komt te staan.

### Herkomst en licentie

De registerdata is van Logius, onder CC-BY 4.0. Dat betekent dat we hem mogen hergebruiken, met
naamsvermelding. Zet op elke pagina de bron, de licentie en de datum waarop wij hem ophaalden. En
onze eigen uitkomsten publiceren we net zo open als de Monitor dat doet, met het databestand
erbij.

## 9. Wat de scan niet kan zeggen

Deze tekst hoort op de methodepagina en in verkorte vorm bij elke tabel. Hij is er om te
voorkomen dat iemand een scanuitkomst leest als een uitspraak over conformiteit.

- **Een scan is geen audit.** axe-core controleert een deel van de WCAG-succescriteria
  automatisch. Veel criteria vragen een mens: of een alternatieve tekst klopt, of de koppen de
  inhoud beschrijven, of een video een goede ondertiteling heeft, of de taal begrijpelijk is. Geen
  fouten in de scan betekent dus niet dat een site toegankelijk is.
- **Wij meten één pagina per site.** De rest van de site kan er anders voor staan.
- **Een uitkomst geldt op de meetdatum.** Die staat erbij.
- **De meting is niet volkomen stabiel.** Tussen twee rondes wisselde in onze eigen
  webshopmeting 3,9% tot 6,2% van de sites van scanstatus. Een enkele wisseling is daarom geen
  verhaal; een reeks is dat wel.
- **De status uit het register is een zelfverklaring.** Bij status A tot D zegt de organisatie zelf
  hoe zij er voor staat; Logius controleert of de onderbouwing voldoende is om te kunnen
  beoordelen, niet of de site toegankelijk is. Status A betekent dus "de organisatie zegt met een
  rapport zonder fouten dat de site voldoet".
- **Een verschil tussen claim en scan is geen betrapping.** Het kan een wijziging na het onderzoek
  zijn, een andere pagina, of een criterium dat de scan anders weegt. Wat wij publiceren is het
  verschil, met de datums van beide kanten erbij, en de uitnodiging om ernaar te kijken.
- **Wij doen geen uitspraak over naleving van de wet.** Welke organisatie waaraan moet voldoen, is
  een vraag voor de toezichthouder.

Laat deze teksten toetsen door Gerard voordat ze live gaan, zoals we dat bij de Monitor ook doen.

## 10. Wat Julia moet kiezen

1. **De plek.** Mijn advies: properaccess.nl onder `/onderzoek/`. Zeg je ja, dan is de
   vervolgvraag of de workflow het databestand zelf naar `main` mag committen, of dat je er elke
   maand een pull request voor wilt zien.
2. **De sector om mee te beginnen.** Mijn advies is overheid, omdat daar de registerclaim ligt en
   het onderzoek daarmee iets zegt wat niemand anders publiceert. Mandy begint aan onderwijs; daar
   is geen claimkant, dus dat onderzoek komt dicht bij wat Emble al gratis publiceert. Kies je
   toch onderwijs, dan is mijn voorstel het onderzoek daar te richten op de vraag of een
   instelling een verklaring en een onderzoeksrapport publiceert, en niet op een ranglijst van
   scanfouten.
3. **De omvang.** Eén hoofdsite per organisatie in ronde 1, of meteen alle sites uit het register.
4. **Het ritme.** Maandelijks volgens mijn advies, met de meetdatum op de pagina.

Wat ik nodig heb voordat er gebouwd wordt:

- Van Mandy: de populatielijst per sector met een bron per regel en de aangewezen hoofdsite, en de
  uitkomst van de aanvraag bij Logius.
- Van Gerard: de wettelijke inkadering per sector, de teksten uit sectie 9, en of "de claim is
  gunstiger dan onze meting" zo mag heten.
- Van Nata: welke vorm het publicatieplan vraagt, want dat bepaalt of een sector één pagina krijgt
  of een pagina per organisatie.
- Van Julia: de vier besluiten hierboven.

## Bronnen en meetmomenten

Alles gemeten op 10 oktober 2026, behalve waar een andere datum staat.

- Dashboard DigiToegankelijk: `/zoeken` met filters en `?page=`, `/organisaties/<id>`,
  `/organisaties/download/<id>`, `/download-grafiek-data` met 54 maandpunten tot 30 september 2026.
- Register van toegankelijkheidsverklaringen: `/register` met `?page=` tot 168 en de `w`-filter,
  `/register/19532` voor de microdata, `/robots.txt`.
- data.overheid.nl: dataset `toegankelijkheidsverklaring-websites-van-de-overheid`, licentie
  CC-BY 4.0, bronhouder Logius.
- toegankelijkheidsindex.nl van Emble, en index.silktide.com voor de categorie Netherlands
  Government.
- Eigen runs: `gh api` op run 37343741564 van 5 oktober en run 37465464111 van 6 oktober, en
  `data/axe-results.json` op de commits `cbe2383`, `32cd153`, `6aa668a` en `56a7bd4`.
- Eigen code: `tools/scrape_footer.py`, `tools/scan_axe.py`, `tools/build_lijsten.py`,
  `tools/sync_confirmed.py`, `public/app.js` regel 218, en in de repo `properaccess.nl`
  `.github/workflows/main.yml`, `data/eaa_monitor.yaml`, `data/amersfoort.yaml` en
  `layouts/shortcodes/eaa-monitor-chart.html`.
