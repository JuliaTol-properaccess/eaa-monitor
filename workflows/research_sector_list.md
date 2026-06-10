# Workflow: sectorlijst samenstellen of uitbreiden

Voor het samenstellen van een nieuwe sectorlijst (`data/<sector>.json`) of het
uitbreiden van een bestaande. Kernregel: **nooit data verzinnen**. Elke entry
is geverifieerd en draagt een bron.

## Schema

```json
{ "name": "Naam", "url": "https://www.voorbeeld.nl", "category": "categorie", "bron": "https://bron-url" }
```

- `name` — het consumentenmerk, kort (zoals een bezoeker het kent)
- `url` — de canonieke https-URL van het Nederlandse consumentenkanaal
- `category` — uit de vaste lijst van de sector (zie `categoryLabels` in de
  bijbehorende `public/monitor-<sector>.html`)
- `bron` — **verplicht**: de URL van het register, de bronpagina of de eigen
  site waarmee de entry is geverifieerd

## Stappen

1. **Registerbron eerst.** Zoek het officiële register van de toezichthouder
   of branche en gebruik dat als startpunt:
   - Telecom: ACM-register van telecomaanbieders (acm.nl)
   - Personenvervoer: concessie-overzichten (DOVA, provincies, MRDH) + ILT
   - Media: CvdM-register commerciële media-instellingen (cvdm.nl)
   - E-books: geen register; vakbronnen (CB, KBb, eReaders.nl) + eigen
     platformpagina's. Markeer de lijst als handmatig en niet-uitputtend.
2. **Verifieer actualiteit per merk.** Merken fuseren en verdwijnen (Tele2 →
   Odido, Caiway → DELTA, BookSpot → gestopt). Check dat het merk nu bestaat
   en een eigen consumentenwebsite heeft. Submerken van één concern mogen als
   eigen entry als ze een eigen site hebben (Ben en Simpel onder Odido).
3. **Live-check elke URL** (curl of browser). Een 403/405 op curl is meestal
   bot-protectie en geen reden tot uitsluiting; de Playwright-scrape is de
   echte test. Een 404 of doorverwijzing naar een ander merk wél uitzoeken.
4. **Eén entry per domein per sector.** Subpagina's van hetzelfde domein
   (zelfde footer) niet dubbel opnemen. Overlap tussen sectoren mag wel als
   het inhoudelijk klopt (bol staat in webshops én e-books).
5. **Eerste scrape als end-to-end-test.** Na het mergen van de lijst:
   `python tools/scrape_footer.py --dataset <sector>`. Controleer:
   foutpercentage onder de 25%-drempel, en steekproef 3-5 bekende sites op
   een kloppende `has_statement`.
6. **Review-PR.** De lijst gaat altijd via een PR; vermeld uitgesloten
   kandidaten met reden in de PR-tekst zodat de afweging navolgbaar blijft.
