# Meetplan editie 2: de opleidingenzoeker van hbo en mbo

Status: plan, niets gebouwd. Opdracht van Chief op 12 oktober 2026, als aanscherping op
`docs/sectoronderzoek-plan.md` uit pull request 91. Julia heeft de meetopzet van editie 2 gekozen:
onderwijs, en per instelling twee dingen. De pagina waar een bezoeker een opleiding kiest, met
axe-core. En een downloadbare opleidings-PDF van dezelfde instelling, met onze eigen PDF-tool.
Over de uitkomst komt een artikel zonder namen van instellingen.

Het brede plan over zes sectoren blijft staan als kader: het datamodel, de regels voor
zorgvuldigheid en de tekst over wat een scan niet zegt gelden hier onverkort. Dit document doet
één ding: het beschrijft hoe een ronde over ongeveer 95 instellingen uitvoerbaar wordt.

Alles wat hieronder "gemeten" heet, is gemeten op 12 oktober 2026. De proef ging over 14
instellingen, 8 hbo en 6 mbo, en staat zonder namen in dit document. Deze repository is openbaar,
en een scanuitkomst naast een instellingsnaam hoort daar niet in. De lijst met hosts en de sleutel
bij de letters houd ik buiten de repository.

## Advies in het kort

1. **Hergebruik de engine, niet de workflow.** `tools/scan_axe.py` met axe-core 4.11.4 uit
   `tools/vendor/axe.min.js` draait ongewijzigd op een eigen lijst. Gemeten: 6 standen in 29
   seconden op mijn eigen server, 4,8 seconden per stand. `scan-axe.yml` gebruiken we niet, want
   `deploy.yml` kopieert de hele map `data/` naar de live site en naar de VPS.
2. **Draai de ronde op mijn server, niet in Actions.** Dan komt er geen enkel bestand met
   instellingsgegevens in een openbare repository of op eaa-monitor.nl terecht, kost de ronde 0
   Actions-minuten, en hoeft er geen workflow te wijzigen.
3. **Van de drie standen is alleen stand 1 volledig automatisch.** Van de 12 bereikbare
   instellingen zette een algemene filterklik bij 7 een filter aan, en bij 5 van die 7 kwam het
   filter in de URL. Van de 3 die ik daarna met de echte scanner natrok, gaf 1 de gefilterde
   pagina terug. De filterstap is dus handwerk per instelling.
4. **De PDF-URL's zijn niet te oogsten.** In 20.480 sitemap-URL's van 11 hosts staan 2
   PDF-bestanden, geen van beide een opleidingsdocument. Op 1 van de 12 zoekerpagina's stond een
   PDF-link, en dat was een cookieverklaring. Mandy moet die URL's met de hand leveren.
5. **Reken op een uur scannen en een dag handwerk voor ronde 1.** Een tweede ronde is ongeveer een
   kwart daarvan.

Vier besluiten liggen bij Julia, onderaan dit document.

## 1. De opleidingenzoeker vinden en vastleggen

### Een URL-patroon is een hint, geen methode

Ik heb bij 14 instellingen het patroon `https://<host>/opleidingen` geprobeerd, met een eigen
user-agent en met een Chrome-string:

- 12 hosts antwoordden met 200;
- 1 host gaf 404, het patroon bestaat daar niet;
- 1 host gaf 403 tegen beide user-agents, dus bot-bescherming;
- 6 van de 12 werkende adressen leidden door naar een andere URL. De eindadressen liepen uiteen
  van `/studeren/opleidingen` en `/mbo/opleidingen` tot `/Opleidingen.htm`, en één host leidde van
  `www` naar het domein zonder `www`.

De les: leg de URL vast zoals hij na alle doorverwijzingen luidt, en bouw hem nooit op uit een
patroon. Een meting op het adres vóór de doorverwijzing meet in het ongunstige geval een andere
pagina dan de volgende ronde.

### Hoe je weet dat je de filterpagina hebt

Een losse opleidingspagina en een zoeker zijn met twee tellingen te onderscheiden. Beide tel je op
de gerenderde pagina, niet op de bron, en beide tel je buiten de cookielaag:

- **Filterbesturing aanwezig.** Een zichtbaar keuzevakje, een keuzerondje, een keuzelijst, of een
  element met `aria-expanded` dat een filterpaneel opent. Gemeten: bij 7 van de 12 instellingen
  vond een algemeen script direct een keuzevakje buiten de cookielaag. Bij de andere 5 stonden 7
  tot 26 elementen met `aria-expanded` op de pagina, wat op filters achter een paneel wijst. Dat
  laatste heb ik niet verder nagelopen; dat is de handmatige stap uit sectie 2.
- **Meer dan één resultaat.** Tel de unieke links naar een diepere pagina op dezelfde host waarvan
  het pad `opleiding`, `studie` of `cursus` bevat. Gemeten over de 12 instellingen: minimaal 5,
  hoogstens 374, mediaan 27,5. Een losse opleidingspagina blijft daar ruim onder.

De regel voor de lijst: een pagina geldt als zoeker wanneer er minstens 5 resultaatlinks op staan
én minstens 1 filterbesturing buiten de cookielaag. Haalt een pagina dat niet, dan is de uitkomst
"geen zoeker gevonden" en gaat die instelling niet in de scan. Dat is een geldige uitkomst voor het
artikel, geen gat in de meting.

Let op bij het tellen van keuzevakjes: de cookiemelding levert ze ook. Bij één instelling stonden
70 keuzevakjes op de pagina waarvan het grootste deel in de cookielaag zat, bij een andere zaten
alle 67 daarin. Tel dus alleen wat buiten een container met `cookie`, `consent`, `cmp` of
`onetrust` in de identificatie of de klassenaam staat.

### Wat je per instelling vastlegt

Eén record per instelling, in een JSON-bestand buiten deze repository:

```json
{
  "letter": "A",
  "soort": "hbo",
  "instellingscode": "00AA",
  "host": "www.example.com",
  "zoeker_url": "https://www.example.com/studeren/opleidingen",
  "zoeker_bewijs": {
    "status": 200,
    "doorverwezen_van": "https://www.example.com/opleidingen",
    "resultaatlinks": 23,
    "filterbesturing": 24,
    "gemeten": "2026-10-20"
  },
  "filter_url": "https://www.example.com/studeren/opleidingen?opleiding=bachelor",
  "filter_stap": {"label": "Bachelor", "selector": "#filter-niveau input[value=bachelor]"},
  "resultaatcontainer": "[data-results]",
  "bron": "https://www.example.com/studeren",
  "vastgelegd": "2026-10-20"
}
```

Bewaar per ronde ook de gerenderde HTML en een schermafdruk van stand 1. Verandert een uitkomst
tussen twee rondes, dan is dat het enige materiaal waarmee je kunt nagaan of de site veranderde of
onze meting.

## 2. axe-core op een pagina die pas na interactie vult

### Wat stand 1 is, en wat erin meetelt

Stand 1 is de pagina zoals een bezoeker hem krijgt. `tools/scan_axe.py` klikt geen cookiemelding
weg, anders dan `scrape_footer.py`, dus die melding hoort bij de meting. Gemeten: bij 10 van de 12
instellingen stond er een zichtbaar cookieblok van meer dan 40.000 beeldpunten op de pagina.

Dat heeft gevolgen voor het cijfer. Ik heb bij 6 instellingen elk gevonden element ingedeeld naar
binnen of buiten de cookielaag:

| Instelling | Elementen in de cookielaag | Elementen in de pagina |
|---|---|---|
| A | 0 | 19 |
| B | 2 | 0 |
| C | 0 | 385 |
| D | 3 | 3 |
| E | 0 | 0 |
| F | 5 | 35 |

Over de 6 instellingen samen: 10 van de 452 elementen zaten in de cookielaag. Bij B kwamen alle
bevindingen daaruit en bij D de helft. Een cijfer per instelling zonder die splitsing meet dus bij
de instellingen met weinig fouten vooral de leverancier van de cookiemelding.

Mijn voorstel: laat de melding staan, want zo krijgt een bezoeker de pagina, en rapporteer de
bevindingen uit de cookielaag apart. Dat vraagt een kleine uitbreiding van de scanner: de
doelselectors van de gevonden elementen bewaren en per element kijken of het binnen een
cookiecontainer valt. Ik heb dat als losse meting al werkend, het is ongeveer 30 regels in een
kopie van de scanner.

### De resultaatlijst staat er al voordat je filtert

Bij alle 12 instellingen stonden er al resultaten op de kale pagina, van 5 tot 374 links. Een
filter verandert dus niet of er een lijst is, maar welke opleidingen erin staan. Dat is belangrijk
voor de uitleg bij het artikel: "de resultaatlijst" is geen pagina die pas na interactie bestaat.

### Stand 2 langs de URL, de route die automatisch kan

Bij 5 van de 7 instellingen waar een algemene klik een filter aanzette, kwam dat filter in de
URL terecht. De vormen liepen uiteen: `?opleiding=bachelor`, `?type[52]=52`, `?fid=15` en
`?f[0]=college:1533`.

Werkt dat ook in een verse sessie? Dat heb ik met de echte scanner natrokken, 3 instellingen, 2
standen elk:

| Instelling | Stand 1 | Stand 2 met filter-URL | Verschil |
|---|---|---|---|
| C | 16.624 elementen in de DOM, 4 regels, 385 elementen gemeld | 5.419 in de DOM, 4 regels, 125 gemeld | lijst echt gefilterd |
| G | 6.448 in de DOM, 0 regels | 6.448 in de DOM, 0 regels | geen verschil |
| H | 1.099 in de DOM, 0 regels | 1.113 in de DOM, 0 regels | geen zichtbaar verschil |

Die cijfers zijn stabiel: ik heb de proef twee keer gedraaid met een halfuur ertussen en alleen bij
H week het aantal elementen 1 af. De 14 elementen verschil bij H zijn dus echt, maar het zijn geen
resultaten: het aantal resultaatlinks bleef 23.

Bij G en H doet de parameter in een verse sessie dus niets: het filter wordt in de browser
toegepast en de URL is alleen een notitie. Daarom is de regel: een filter-URL geldt pas als
vastgelegd wanneer de resultaatlijst meetbaar verandert tegenover stand 1. Verandert hij niet, dan
heeft die instelling een klikstap nodig of valt stand 2 weg.

### Stand 2 langs een klik, de route die handwerk is

Bij 5 van de 12 instellingen vond een algemeen script geen enkele filterbesturing buiten de
cookielaag. Daar zitten de filters achter een knop met `aria-expanded`, dus de stap is: paneel
openen, dan filter aanzetten, dan wachten tot de lijst opnieuw is opgebouwd. Dat is per instelling
een eigen recept van twee of drie selectors.

Dat recept is niet af te leiden uit de pagina. Reken op ongeveer 3 minuten per instelling om het
te vinden en te controleren, dus ongeveer 5 uur voor 95 instellingen. Het recept is daarna
herbruikbaar, maar moet elke ronde opnieuw bevestigd worden, want een site kan veranderd zijn.

### Wat stand 3 moet betekenen

Twee lezingen, en Julia kiest:

- **De hele pagina na het filteren.** Dan valt stand 3 samen met stand 2 zodra de filter-URL werkt,
  en meet je twee keer hetzelfde.
- **Alleen de resultaatlijst.** axe-core kan op een deel van de pagina draaien;
  `tools/scan_axe.py` geeft nu altijd `document` mee. Een optie voor een selector erbij is klein
  werk, maar het vraagt per instelling de selector van de lijstcontainer, dus hetzelfde handwerk
  als het filterrecept.

Mijn advies is de tweede lezing. De vraag van het onderzoek gaat over het kiezen van een
opleiding, en dat gebeurt in die lijst. Dan zijn de drie standen: de pagina zoals hij komt, de
pagina met één filter aan, en de lijst zelf.

### Tel regels, niet elementen

Bij instelling C daalde het aantal gemelde elementen van 385 naar 125 door één filter, terwijl het
aantal regels op 4 bleef staan en de regels dezelfde waren. Het aantal gemelde elementen hangt dus
vooral aan het aantal kaarten in de lijst, en daarmee aan de grootte van het opleidingenaanbod.
Publiceer daarom per instelling welke regels overtreden zijn, niet hoeveel elementen. Voor het
artikel is de vergelijkbare maat: hoeveel instellingen falen op welke regel.

### Wat de scanner al goed doet, en houdt

- Een pagina met minder dan 50 elementen in de DOM is "niet gerenderd" en nooit "geen fouten".
- Een cap van 120 seconden per site, met zelfherstart bij een onbreekbare hang.
- Injectie van axe-core via `page.evaluate`, zodat een strenge Content Security Policy de scan niet
  stil laat slagen.
- Alleen WCAG A en AA tot en met 2.2, best practice uitgesloten.

Dat alles geldt per regel in de lijst. Drie standen zijn dus drie regels, en een stand die
vastloopt maakt de andere twee niet ongeldig.

## 3. De opleidings-PDF vinden en de URL vastleggen

Wij oogsten hier alleen URL's. We testen geen PDF en we raken de PDF-tool niet aan: dat is werk
van Julia.

### Oogsten langs de sitemap werkt niet

Ik heb per host `robots.txt` gelezen, de `Sitemap`-regels gevolgd en de URL's geteld. Bij een index
heb ik de eerste twee onderliggende bestanden genomen, dus bij 3 hosts is de telling een
ondergrens.

- 20.480 URL's geteld over 11 hosts.
- Daarvan 2 PDF-bestanden, bij één en dezelfde instelling. Het waren een onderzoeksverslag en een
  handleiding, geen opleidingsdocument.
- 1 host heeft geen sitemap: geen `Sitemap`-regel in `robots.txt` en `/sitemap.xml` gaf 404.
- 3 hosts noemen geen sitemap in `robots.txt` terwijl `/sitemap.xml` wel bestaat. Probeer dus
  altijd beide.

### Oogsten op de zoekerpagina werkt ook niet

Bij 1 van de 12 zoekerpagina's stond een PDF-link, en dat was de cookieverklaring van de
instelling. Een script dat de eerste PDF op de pagina pakt, levert dus het verkeerde document.

### Op 3 van de 8 opleidingspagina's stond wel een opleidings-PDF

Ik heb bij 8 instellingen één opleidingspagina uit de sitemap gehaald en bekeken. Twee
waarschuwingen vooraf: bij 3 van de 8 was de gekozen pagina geen opleidingspagina maar een
bedankpagina, een nieuwsbericht of een onderliggende tab. Ook daarom heeft deze meting de lijst van
Mandy nodig.

Wat er stond:

- 2 pagina's hadden een directe link naar een `.pdf`, beide bevestigd als `application/pdf`: een
  studieroutebestand van 857 kB en een informatieblad van 112 kB.
- 2 downloadlinks zonder `.pdf` in de URL geven wel een PDF terug: een pagina-PDF van 665 kB achter
  `?pdf=1`, en een brochure van 8,0 MB achter een pad in de vorm `/brochure/download/<nummer>`, met
  de bestandsnaam in de `Content-Disposition`. Die laatste stond op dezelfde pagina als een van de
  twee directe links, dus 3 van de 8 pagina's leverden samen een bruikbaar opleidingsdocument.
- 1 pagina had alleen een PDF-link naar de cookieverklaring.

Een filter op de extensie `.pdf` mist dus juist de echte brochures, en een filter op de eerste PDF
op de pagina pakt het verkeerde bestand.

### De regels voor een PDF-URL

- **Controleer op inhoud, niet op de naam.** Vraag 1 kB op met een `Range`-verzoek en eis
  `Content-Type: application/pdf` en de eerste bytes `%PDF`. Zo weet je het zonder een bestand van
  8 MB te downloaden.
- **Leg de URL vast na alle doorverwijzingen**, plus het type, het aantal bytes, de pagina waar de
  link stond en de datum.
- **Geen formulier.** Zit de brochure achter een formulier dat een e-mailadres vraagt, dan is het
  voor deze meting geen downloadbare PDF. Dat is een geldige uitkomst: "geen openbaar
  opleidingsdocument gevonden".
- **Eén soort document voor de hele ronde.** Een informatieblad van 112 kB en een brochure van 8,0
  MB zijn niet vergelijkbaar. Vraag Mandy om één soort met een terugvaloptie, in deze voorkeur:
  studiegids of opleidingsblad, dan brochure of digifolder, dan de onderwijs- en examenregeling.
- **Dezelfde instelling als de zoeker**, zodat de twee metingen over één organisatie gaan.

## 4. De keten

### De engine hergebruiken: ja, gemeten

`tools/scan_axe.py` draait ongewijzigd op een eigen lijst. Ik heb hem op deze server gedraaid met
een lijst van 6 URL's, 3 instellingen in 2 standen:

```text
axe-core scan | 6 sites | alleen WCAG A/AA
[1/6] C stand 1          4 regels,  385 elem, dom=16624 (9.5s)
[2/6] C stand 2          4 regels,  125 elem, dom=5419 (3.9s)
[3/6] G stand 1          0 regels,    0 elem, dom=6448 (4.6s)
[4/6] G stand 2          0 regels,    0 elem, dom=6448 (3.7s)
[5/6] H stand 1          0 regels,    0 elem, dom=1099 (3.6s)
[6/6] H stand 2          0 regels,    0 elem, dom=1113 (3.2s)

Gescand: 6/6 geslaagd.
real 0m29.305s
```

Twee keer gedraaid: 28,8 en 29,3 seconden voor 6 standen, dus 4,8 tot 4,9 seconden per stand.

Dezelfde engine als de Monitor en als wcag-scan: axe-core 4.11.4. Een eigen lijst is genoeg;
`tools/build_axe_targets.py` hebben we niet nodig, want dat gereedschap bouwt de doellijst uit
`data/results*.json` en dat is precies de Monitor-populatie.

### De workflow hergebruiken: nee, en dit is waarom

1. **`deploy.yml` publiceert de hele map `data/`.** De stap "Prepare site" doet
   `cp -R data _site/data`, en daarna gaat dezelfde boom met `rsync` naar de VPS. Gemeten:
   `https://eaa-monitor.nl/data/axe-results.json` antwoordt met 200 en 31.715 bytes, en
   `data/webshops.json` met 1,1 MB. Een resultaatbestand in `data/` staat dus live op het domein,
   ook als geen enkele pagina ernaar linkt. Onderwijs valt onder het Tijdelijk besluit digitale
   toegankelijkheid overheid en hoort daar niet.
2. **`build_axe_overlay.py` schrijft precies de bestanden die de Monitor serveert**:
   `data/axe-results.json` en het gebakken cijfer tussen de `AXE-STAT`-markers in
   `public/monitor.html`. Draai dat gereedschap nooit op onderwijsuitvoer. Omgekeerd leest de
   Monitor onze uitvoer nergens, want `app.js` koppelt alleen op `data/axe-results.json`.
3. **Een workflow toevoegen of wijzigen kan ik niet.** Het token heeft met opzet geen rechten op
   `.github/workflows/`. Elke route via Actions kost dus een commit van Julia.
4. **De repository is openbaar** en een artifact biedt daar geen beschutting. Gemeten: de
   artifactlijst van een openbare repository is zonder token op te vragen, antwoord 200. De zip
   zelf geeft zonder token 401, maar leesrecht op een openbare repository heeft iedereen met een
   GitHub-account, dus een artifact is geen plek voor gegevens per instelling.
5. **De deploy zou niet vanzelf meeliften.** `deploy.yml` reageert op `workflow_run` van alleen
   "Scrape webshop footers" en "WCAG-scan sites met verklaring", dus een nieuwe workflow met een
   andere naam zet de site niet opnieuw live. Maar hij reageert ook op elke push naar `main`, dus
   een commit met resultaten triggert alsnog een deploy.

### Wat ik voorstel

- **De code mag openbaar.** Zet hem als `tools/onderwijs/` in deze repository: een kopie van de
  scanner met drie toevoegingen, namelijk de indeling naar de cookielaag, een optie voor de
  selector van de resultaatlijst, en een eigen user-agent. Een kopie en geen generalisatie van
  `scan_axe.py`, om dezelfde reden als in sectie 5 van het brede plan: de Monitor is een lopende
  meetreeks en die zetten we niet op het spel voor een tweede product.
- **De lijst en de uitvoer blijven buiten de repository.** De ronde draait op mijn server, de
  uitvoer staat in mijn werkmap, en wat Julia moet lezen gaat via `werk/uit/` naar `pa_gedeeld`.
  Die repository is besloten.
- **Een slot in het script.** Weigert te schrijven zodra het doelpad onder `data/` of `public/`
  valt, en stopt zodra er een instellings-URL in `data/axe-results.json` opduikt. Na elke ronde
  controleer ik dat `git status` schoon is.
- De wekelijkse Monitor-run raakt dit niet, want er verandert geen workflow, geen `data/`-bestand
  en geen pagina. De samenloopgroep `scan-axe` blijft van de Monitor alleen.

Wil Julia het toch in Actions, dan is de enige veilige variant een besloten repository met uitvoer
in een artifact. Dan tellen de minuten wel mee. Hoeveel er nog over zijn kan ik niet meten: de
facturatie-API geeft mij 403.

## 5. Tempo, robots.txt en belasting per site

### Wat robots.txt zegt

Gemeten bij 14 hosts: alle 14 leveren een `robots.txt` met status 200, en bij alle 14 is het pad
van de zoeker toegestaan. Dat geldt zowel voor de regels bij onze eigen naam als bij `*`, gerekend
met de regel dat het langste patroon wint. Eén host geeft `Crawl-delay: 10`.

De regels voor de ronde:

- Lees `robots.txt` per host, elke ronde opnieuw. Verbiedt hij de pagina, dan is de uitkomst
  "uitgesloten door robots.txt", met de regel erbij. Dat is iets anders dan "niet te controleren".
- Volg `Crawl-delay` waar die staat. Staat er niets, dan 5 seconden tussen twee verzoeken aan
  dezelfde host.
- Eén verzoek per host tegelijk, de instellingen achter elkaar, nooit twee standen van dezelfde
  instelling parallel.
- Geen inloggedeelte, geen formulier verzenden, geen zoekopdracht afvuren, geen persoonsgegevens.
  Een filter aanzetten is een gewone bezoekershandeling en blijft binnen deze regel.
- Bot-bescherming omzeilen we niet. De host die 403 gaf blijft "niet te controleren", en dat
  aandeel publiceren we gewoon.

### Zeggen wie we zijn kost niets

Gemeten op 13 bereikbare hosts: een user-agent die ons noemt en naar een methodepagina wijst,
krijgt exact hetzelfde antwoord als een Chrome-string. Zelfde status, zelfde aantal bytes, bij alle
13. De ene host die 403 gaf, gaf dat tegen beide. De aanbeveling uit het brede plan is dus
haalbaar. In `tools/scan_axe.py` staat nu een Chrome-string in `UA`; die vervangen we in de kopie
door onze eigen naam met een URL erbij. Zet die methodepagina online voordat ronde 1 draait, zodat
een beheerder kan nazoeken wie er langskwam.

### Hoe zwaar een meting is

Gemeten bij 4 instellingen, per paginabezoek, alleen de verzoeken naar de host van de instelling
zelf:

| Instelling | Verzoeken | Bytes |
|---|---|---|
| C | 17 | 2,7 MB |
| G | 25 | 1,4 MB |
| B | 31 | 0,6 MB |
| F | 31 | 2,1 MB |

Drie standen komen daarmee op ongeveer 50 tot 95 verzoeken en 2 tot 8 MB per instelling per ronde.
Dat is de orde van één bezoeker die drie pagina's bekijkt. Over de hele ronde: 285 paginabezoeken,
verdeeld over ongeveer een uur, nooit twee tegelijk op dezelfde host.

## 6. Kosten en doorlooptijd

### De basis, uit onze eigen runs

- Monitor-run 37465464111 van 6 oktober 2026: 290 sites, de scanstap liep van 12:45:04 tot
  13:08:08, dus 1.384 seconden. Dat is 4,77 seconden per site. De hele job duurde 23 minuten en 39
  seconden, waarvan 28 seconden opzet.
- Mijn eigen proef op deze server, twee keer gedraaid: 6 standen in 28,8 en 29,3 seconden, dus 4,8
  tot 4,9 seconden per stand. Dezelfde orde, dus de getallen van de Monitor zijn bruikbaar.

### Een ronde van 95 instellingen

| Post | Tijd |
|---|---|
| 285 standen scannen, 4,8 seconden per stand | 23 minuten |
| Pauzes tussen de standen, 2 keer 5 seconden per instelling | 16 minuten |
| robots.txt per host | 2 minuten |
| Marge voor vastlopers: 10% van de standen op de cap van 120 seconden | 10 minuten |
| **Totaal rekentijd** | **ongeveer 1 uur** |

Dat is wandkloktijd, want de ronde draait sequentieel. Sharden kan wel, maar niet per host, en de
winst weegt niet op tegen het risico dat twee shards dezelfde instelling tegelijk raken.

Actions-minuten: 0, want de ronde draait op mijn server. Zou hij in deze openbare repository
draaien, dan rekent GitHub ook 0 minuten, maar dan staan de resultaten op het verkeerde domein
(zie sectie 4). In een besloten repository kost een ronde ongeveer 60 minuten plus 1 minuut opzet.

### Het handwerk is de echte post

| Post | Ronde 1 | Ronde 2 |
|---|---|---|
| Zoeker-URL controleren, 1 minuut per instelling | 1,5 uur | 1,5 uur |
| Filterrecept of filter-URL vinden en natrekken, 3 minuten | 5 uur | 0,5 uur |
| Selector van de resultaatlijst, 1 minuut | 1,5 uur | 0,5 uur |
| PDF-URL natrekken, 1 minuut | 1,5 uur | 1,5 uur |
| **Totaal** | **ongeveer 10 uur** | **ongeveer 4 uur** |

Ronde 1 is dus een dag handwerk naast dat uur scannen. Ronde 2 is ongeveer een kwart van ronde 1,
mits de recepten bewaard zijn en de instellingen hun site niet hebben verbouwd. Een verbouwing
merk je aan de controle: de resultaatlijst verandert niet meer, of het aantal resultaatlinks wijkt
sterk af van de vorige ronde.

Over tijdstippen: beloof geen uur en geen dagdeel. Een cron van GitHub start in de praktijk uren
later dan opgegeven, bij onze eigen workflows mediaan 5 tot 7 uur. Draait de ronde met de hand op
mijn server, dan speelt dat niet, maar zet in alle gevallen de echte meetdatum uit de gegevens op
de pagina.

## 7. Wat ik van Mandy's lijst nodig heb

### De populatie

Chief noemt ongeveer 95 instellingen. Welke 95 dat zijn, moet uit een registerbron komen, met per
regel de vindplaats en het criterium dat is gebruikt. Een naam zonder instellingscode is bij mbo
lastig: een bevoegd gezag met meerdere colleges kan per college een eigen site en een eigen zoeker
hebben, en dan is de vraag of je het bevoegd gezag of het college meet. Die keuze hoort in de
lijst, niet in mijn script.

### Per instelling

Minimaal nodig om te kunnen starten:

- naam en soort, hbo of mbo;
- instellingscode;
- de host;
- de URL van de opleidingenzoeker, zoals die luidt na alle doorverwijzingen;
- één PDF-URL van dezelfde instelling, met het soort document erbij.

Daar bovenop, als zij het toch al ziet tijdens het zoeken:

- het aantal filters en het aantal resultaten dat zij op de zoeker zag, met de datum. Dat is het
  bewijs uit sectie 1 en het scheelt mij een controle;
- de pagina waarop de PDF-link stond;
- de opmerking dat iets er niet is. Vier uitkomsten komen zeker voor: geen zoeker, zoeker achter
  een inlog, zoeker op een ander domein zoals een gezamenlijk portaal, en geen openbaar
  opleidingsdocument. Die horen als uitkomst in de lijst, met een reden.

Wat ik daarna zelf meet en niet aan haar vraag: of de pagina de filterpagina is volgens de twee
tellingen, of de PDF-URL echt een PDF teruggeeft, en wat `robots.txt` per host zegt.

### Waarom een lijst met alleen namen niet werkt

Uit de proef: het patroon `/opleidingen` gaf bij 1 van de 14 hosts een 404, bij 1 een 403, en bij 6
van de 12 werkende hosts een doorverwijzing naar een ander adres. Uit de sitemap een
opleidingspagina kiezen gaf bij 3 van de 8 instellingen een pagina die geen opleidingspagina was.
Zonder de URL's per instelling begint de ronde met raden.

### De planning

Mandy levert donderdag 16 oktober. Komt de lijst met de vijf minimale velden, dan kan ik de
controle van de zoekers en de PDF-URL's in één dag draaien. Het filterrecept per instelling is
daarna de langste post, die 5 uur uit de tabel hierboven. Een eerste volledige ronde is dus
haalbaar in de week van 20 oktober, mits Julia de vier besluiten hieronder heeft genomen.

## Besluiten voor Julia

1. **Waar de ronde draait.** Mijn advies: op mijn server, uitvoer via `werk/uit/` naar
   `pa_gedeeld`. Het alternatief is Actions in een besloten repository.
2. **Of de cookielaag meetelt in het cijfer.** Mijn advies: laten staan in de meting, apart
   rapporteren. Gemeten reden: bij 2 van de 6 instellingen kwam de helft of alles uit die laag.
3. **Wat stand 3 is.** Mijn advies: alleen de resultaatlijst, met een selector per instelling.
   Anders meet stand 3 hetzelfde als stand 2.
4. **Welk soort PDF.** Mijn advies: één soort voor de hele ronde met een terugvaloptie, anders zijn
   de uitkomsten niet vergelijkbaar.

Daarnaast één punt voor Gerard, voordat er iets gepubliceerd wordt: of hbo- en mbo-instellingen
onder het Tijdelijk besluit digitale toegankelijkheid overheid vallen, en zo niet, onder welke norm
we de uitkomst dan uitleggen. De meting hangt daar niet van af, de tekst van het artikel wel.

## Wat deze meting niet zegt

Sectie 9 van `docs/sectoronderzoek-plan.md` geldt onverkort: een scan is geen audit, wij meten één
pagina per instelling, een uitkomst geldt op de meetdatum, en tussen twee rondes wisselde in onze
webshopmeting 3,9% tot 6,2% van de sites van status zonder dat er iets aan de site veranderde. Bij
95 instellingen zijn dat 4 tot 6 instellingen per ronde.

Twee dingen komen daar voor onderwijs bij:

- **Het aantal gemelde elementen zegt vooral iets over de grootte van het aanbod.** Gemeten: één
  filter bracht het aantal gemelde elementen van 385 naar 125 terwijl de overtreden regels
  dezelfde bleven. Publiceer daarom regels, geen aantallen elementen.
- **Een deel van de bevindingen is niet van de instelling.** De cookiemelding komt van een externe
  leverancier. Wat uit die laag komt, rapporteren we apart.

## Bronnen en meetmomenten

Alles gemeten op 12 oktober 2026, op een proef van 14 instellingen: 8 hbo en 6 mbo. 12 waren
bereikbaar, 1 gaf 404 op het geprobeerde pad en 1 gaf 403 tegen beide user-agents. De letters A tot
H in dit document staan niet in dezelfde orde als de hosts, en de sleutel staat niet in deze
repository.

- Scanstap van Monitor-run 37465464111, 6 oktober 2026, via de tijdstempels van de job.
- `data/axe-results.json` zoals live geserveerd op 12 oktober 2026: 290 sites, axe-core 4.11.4,
  meting van 6 oktober.
- Eigen proefrun van `tools/scan_axe.py` op deze server, 6 standen, 28,8 seconden.
- `robots.txt`, sitemaps, paginabezoeken en axe-runs van de proef: eigen metingen, opgeslagen
  buiten deze repository.
