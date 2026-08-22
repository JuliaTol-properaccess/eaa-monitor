# Entiteitsverankering: Wikidata, Zenodo en sameAs

Werkdocument voor het vindbaar maken van EAA Monitor als entiteit bij AI-zoekmachines.
Opgesteld 22 augustus 2026.

## Waarom dit nodig is

Het `Organization`-schema op de homepage heeft geen `sameAs`. Er is dus geen enkele
externe plek waar "EAA Monitor" aan gekoppeld kan worden. Een AI-zoekmachine die de naam
tegenkomt, kan niet vaststellen over welke organisatie het gaat, en koppelt de cijfers
daardoor niet aan een bron die hij herkent.

Julia koos op 22 augustus 2026 voor verankering **zonder namen van personen**. Het colofon
zegt bewust "we noemen geen namen", en dat blijft zo. Verankering op organisatieniveau
botst daar niet mee.

## Wat er nu niet is

Nagetrokken op 22 augustus 2026:

- **Geen Wikidata-item.** De zoekopdracht op "EAA Monitor" geeft "no results, you may
  create a new item".
- **Geen onafhankelijke dekking.** Een zoektocht naar vermeldingen buiten de eigen site
  levert alleen de site zelf op, plus pagina's van andere partijen over hetzelfde
  onderwerp. Geen vakmedia die de cijfers overneemt, geen toezichthouder die verwijst,
  geen register.

## Waarom Wikidata niet als eerste stap moet

Wikidata accepteert een item als het aan één van drie criteria voldoet. Het enige dat hier
kan gelden is criterium 2: een duidelijk identificeerbare entiteit "that can be described
using serious and publicly available references".

Die referenties ontbreken op dit moment. Een item dat alleen naar de eigen website
verwijst, kan worden voorgedragen voor verwijdering. Het resultaat is dan een `sameAs` die
naar een verwijderde pagina wijst, en dat is slechter dan geen `sameAs`.

Bron: [Wikidata:Notability](https://www.wikidata.org/wiki/Wikidata:Notability).

## De volgorde

### 1. Zenodo: de dataset publiceren met een DOI

De sterkste externe bron die binnen handbereik ligt. Zenodo is gratis, draait bij CERN in
Europa, en levert een DOI. Een DOI is precies wat Wikidata een "serious, publicly
available reference" noemt, is meteen bruikbaar als anker in het schema, en wordt door
onderzoekers en taalmodellen behandeld als citeerbaar.

De meetdata staat al onder CC BY 4.0, dus licentietechnisch hoeft er niets te veranderen.

Wat er in de publicatie hoort:

- de zeven sectorbestanden `data/results*.json` van de betreffende meetweek;
- de meetmethode: wekelijkse footer-check op een link naar een toegankelijkheidsverklaring,
  met de kanttekening dat een gevonden link niets zegt over de werkelijke toegankelijkheid;
- de statusdefinities, waaronder dat een mislukte scrape "niet te controleren" is en nooit
  "geen verklaring";
- versienummering per meetweek, zodat een verwijzing naar een specifieke week blijft
  kloppen.

### 2. LinkedIn-bedrijfspagina

Kost een kwartier, geen drempel, en is een veelgebruikt `sameAs`-anker.

### 3. Wikidata, met de DOI als bron

Pas hierna. Met een DOI onder de statements overleeft het item een deletion-discussie.

## Wikidata: de procedure

Dit vraagt een account op naam van Julia en is een publicatie naar buiten, dus het gaat
niet via een agent.

1. Account aanmaken via `Special:CreateAccount` op wikidata.org.
2. Nieuw item via `Special:NewItem`.
3. Label **EAA Monitor**. Beschrijving Nederlands: "Nederlandse website die wekelijks meet
   of organisaties een toegankelijkheidsverklaring publiceren". Engels vergelijkbaar. Geen
   wervende taal; dat is de snelste route naar een verwijderingsvoorstel.
4. Statements toevoegen. De zoekvelden vullen zichzelf aan.

   | Property | Waarde |
   | --- | --- |
   | instance of (P31) | website (Q35127) |
   | official website (P856) | `https://eaa-monitor.nl/` |
   | country (P17) | Nederland |
   | language of work or name (P407) | Nederlands, Engels |
   | inception (P571) | 2026 |
   | copyright license (P275) | Creative Commons Attribution 4.0 International (Q20007257) |
   | main subject (P921) | digitale toegankelijkheid |

   De Q-nummers voor website en de licentie zijn nagetrokken op 22 augustus 2026. Zoek de
   overige waarden op in het invoerveld zelf en neem ze niet over uit een lijstje.

5. Onder elke statement een bron zetten met "add reference" en `reference URL` (P854).
   Statements zonder bron worden als eerste aangevochten.

Eén ding om open over te zijn: dit is een item over het eigen project. Wikidata verbiedt
dat niet zoals Wikipedia dat doet. Houd de beschrijving feitelijk en laat de bronnen het
werk doen.

## Wat er daarna in de code moet

Zodra er een Q-id, een LinkedIn-URL of een DOI is, gaat `sameAs` in het
`Organization`-blok van `public/index.html`, in het `@graph` bij `#organization`. Dat blok
is handgeschreven, dus het is een directe wijziging in dat bestand.

Bij een DOI hoort daarnaast een `citation`- of `distribution`-verwijzing in het
`Dataset`-blok dat `tools/scrape_footer.py` in de pagina bakt. Let op: dat blok staat
tussen de `JSONLD-DATASET`-markers en wordt bij elke scrape overschreven, dus de wijziging
hoort in de scraper en niet in de HTML.

## Openstaande punten

- Zenodo-publicatie voorbereiden en uploaden.
- LinkedIn-bedrijfspagina aanmaken of de bestaande URL doorgeven.
- Wikidata-item aanmaken zodra er een DOI is.
- `sameAs` in het schema zetten zodra er minstens één URL is.
