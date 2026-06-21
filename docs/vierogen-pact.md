# Het Vierogen-pact

Strategiedocument voor het peer-review-netwerk van auditbureaus op EAA Monitor.
Status: concept, klaar voor de eerste wervingsronde (juni 2026).

## Het idee in één zin

Een openbare groep auditbureaus die zich verbinden aan collegiale toetsing achteraf:
een afgerond rapport kan worden nagekeken door een vakgenoot van een ander aangesloten
bureau, en ze zijn bereid een second opinion te geven als er discussie ontstaat over een
bevinding. De plaatsing op EAA Monitor is het zichtbare bewijs dat een bureau dat aandurft.

## Waarom

Sinds de European Accessibility Act zijn er veel auditbureaus bijgekomen. Een deel doet
audits erbij, naast marketing- of ontwikkelwerk, zonder jarenlange ervaring met digitale
toegankelijkheid. Voor een opdrachtgever is het kaf niet van het koren te onderscheiden.
Het Vierogen-pact maakt dat onderscheid zichtbaar: serieuze bureaus durven hun werk
publiekelijk te laten toetsen door een vakgenoot, gelegenheidsauditeurs niet.

## Wat een bureau belooft (het pact)

Geen keuring, geen controle vooraf. Wel een openbare belofte op naam. Dat is de hele
kracht ervan. Vier punten:

1. Ik sta achter de kwaliteit van mijn rapporten en durf ze te laten meelezen.
2. Ik laat een afgerond rapport achteraf toetsen door een vakgenoot van een ander
   aangesloten bureau, en ik doe die toetsing ook voor anderen.
3. Loopt een discussie met een klant vast op een bevinding, dan werk ik mee aan een
   onafhankelijke second opinion door een collega-bureau uit het netwerk.
4. Ik werk aantoonbaar volgens WCAG-EM en toets WCAG 2.1, WCAG 2.2 en indien van
   toepassing EN 301 549, en ik kan mijn methode uitleggen.

De belofte is openbaar en op naam. Een bureau dat weigert mee te werken als het erop
aankomt, valt vanzelf door de mand bij collega's en klanten. Daarom is controle vooraf
niet nodig: het netwerk is zelfreinigend.

## Twee momenten, allebei achteraf

Houd deze twee gescheiden. Ze worden snel door elkaar gehaald.

- **Collegiale toetsing.** Een afgerond rapport wordt nagekeken door een vakgenoot van
  een ander bureau. Altijd achteraf, nooit meekijken tijdens de audit.
- **Second opinion.** Betwist een klant een bevinding, dan geeft een ander aangesloten
  bureau een onafhankelijk oordeel.

## Hoe de second opinion werkt

EAA Monitor is matchmaker, geen partij. Zo blijf je buiten aansprakelijkheid.

- Op de pagina staat een knop "Vraag een second opinion aan", een formulier naar de
  Worker (zoals de bezwaar- en vraagformulieren die er al zijn).
- De aanvrager (een klant of een bureau) beschrijft de bevinding waar discussie over is.
- Een ander aangesloten bureau pakt het op. De afspraak over kosten en levering is tussen
  die twee partijen, niet via EAA Monitor.

## Toelating

Lichte drempel, geen beoordeling. Bij aanmelding vraag je om één referentie van een
collega-bureau of opdrachtgever, of een voorbeeldrapport. Dat is genoeg teken dat het echt
vakwerk is. Je controleert de inhoud niet, je houdt alleen de gelegenheidsauditeur buiten
de deur. Zo blijft het pact geloofwaardig zonder dat jij iets keurt.

## Proper Access

Proper Access doet mee als betalend lid, met een open vermelding op de pagina dat EAA
Monitor uit die hoek komt. EAA Monitor is bewust losgekoppeld van het Proper Access-merk,
dus de transparantie is nodig: een bezoeker moet kunnen zien dat de maker van de monitor
zelf ook in de directory staat, op gelijke voet en tegen hetzelfde tarief als de rest.

## Wat de klant op de pagina ziet

De huidige kale tabel (naam, specialisatie, talen) wordt een set bureauprofielen met een
herkenbaar label **"Doet mee aan collegiale toetsing"**. De directory is het netwerk:
alleen aangesloten bureaus staan erop. Dat geeft de plaatsing waarde en voorkomt een
verwarrende gratis-versus-betaald-tabel.

Belangrijke formulering: het label zegt "dit bureau heeft zich verbonden aan toetsing",
niet "dit bureau is gekeurd". Die precisie beschermt EAA Monitor tegen de indruk dat je
kwaliteit verkoopt die je niet verifieert.

### Datamodel (`data/auditbureaus.json`)

Uitbreiden van het huidige schema (`naam`, `website`, `specialisatie`, `talen`) met:

| Veld           | Verplicht | Toelichting                                             |
| -------------- | --------- | ------------------------------------------------------- |
| `peerreview`   | ja        | `true` toont het label                                  |
| `beschrijving` | ja        | Korte profieltekst                                      |
| `regio`        | nee       | Werkgebied                                              |
| `methodiek`    | nee       | Bijvoorbeeld "WCAG-EM, WCAG 2.1/2.2, EN 301 549"        |
| `logo`         | nee       | Pad naar logo in `public/static/`                       |
| `contact`      | nee       | Contactlink of e-mail (let op: repo is openbaar)        |

## Prijs

- **2 maanden gratis** bij de start, zonder verplichting. Lost het kip-ei-probleem op:
  bureaus stappen makkelijker in als de pagina nog leeg is.
- Daarna een **jaartarief van € 395 (excl. btw)**, in lijn met de € 385 die Julia eerder
  zelf voor een vergelijkbare plaatsing betaalde.
- **Founding-tarief € 295/jaar** voor iedereen die in deze eerste ronde (2026) instapt, en
  dat tarief houden ze. Beloont de eerste lichting die het netwerk geloofwaardig maakt.
- Eén jaarfactuur, stilzwijgend verlengd met opzegtermijn. Maandfacturatie is bij dit
  bedrag niet de moeite waard.

## Aanpak van de werving

1. **Wervingspagina** op de site ("Word lid van Het Vierogen-pact") met het pact, de
   werkwijze en het tarief. Te linken vanuit de uitnodigingsmail.
2. **Aanmelding.** Voor versie 1 volstaat terugkoppeling per mail; een formulier kan later.
3. **Uitnodigingsmail** naar de bureaus, kort en in je-vorm.

## Openstaande punten

- Tekst van de uitnodigingsmail schrijven.
- Wervingspagina bouwen.
- `data/auditbureaus.json` en `build_auditbureaus.py` uitbreiden met het profielmodel en
  het label.
- Beslissen of het second-opinion-formulier in versie 1 al live gaat of later.
