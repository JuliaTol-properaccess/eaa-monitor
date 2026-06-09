# Workflow: Anonieme EAA-vraag verwerken

## Doel

Een binnengekomen anonieme vraag over de European Accessibility Act voorleggen aan
de juiste toezichthouder en het antwoord publiceren op de pagina
[Vragen uit de praktijk](../public/vragen.html), zodat alle ondernemers er iets aan
hebben. De vrager blijft anoniem.

Het idee: veel ondernemers hebben vragen aan de toezichthouder, maar aarzelen om
zich te melden. Wij stellen de vraag namens hen en maken het antwoord openbaar.

## Inputs

Een e-mail van de bezwaar-Worker (route `POST /vraag`, zie `worker/src/index.js`)
op het adres `vragen@eaa-monitor.nl` (valt terug op `NOTIFY_EMAIL` als
`VRAGEN_EMAIL` niet is gezet). De mail bevat:

- de vraag,
- een sector/context (optioneel),
- een e-mailadres van de vrager (optioneel, om te laten weten dat de vraag
  beantwoord is). Dit adres is **vertrouwelijk**.

## Stappen

1. **Beoordeel de vraag.** Is het een echte, beantwoordbare vraag over de EAA? Filter
   spam en vragen die niet over de wet gaan. Bundel gerust meerdere vergelijkbare
   vragen tot één heldere vraag.

2. **Maak de vraag anoniem en herleidbaarheid-vrij.** Haal namen, bedrijven, URL's
   en andere herleidbare details eruit. Herformuleer tot een algemene vraag die voor
   meer ondernemers nuttig is.

3. **Bepaal de juiste toezichthouder.** Meestal de ACM (webshops, algemene
   e-commerce) of de AFM (financiële sector: banken, verzekeraars, betaaldiensten,
   leasemaatschappijen). Bij twijfel: check de kennisbank-artikelen over toezicht.

4. **Leg de vraag voor.** Stel de vraag namens de EAA Monitor aan de toezichthouder
   via hun officiële kanaal. Geef nooit de gegevens van de vrager door.

5. **Publiceer het antwoord.** Voeg een object toe aan `data/vragen.json`:

   ```json
   {
     "vraag": "Geldt de EAA ook als ik alleen aan andere bedrijven verkoop?",
     "antwoord": "Het antwoord van de toezichthouder, in heldere taal. Lege regels worden aparte alinea's.",
     "toezichthouder": "ACM",
     "datum": "2026-06-20",
     "thema": "scope",
     "bron": { "titel": "ACM: ...", "url": "https://www.acm.nl/..." }
   }
   ```

   Alleen `vraag` en `antwoord` zijn verplicht. Voeg een `bron` toe als het antwoord
   uit een publicatie of officiële reactie komt.

   - **Verzin nooit een antwoord.** Publiceer alleen wat de toezichthouder echt heeft
     gezegd. Is iets onbevestigd, markeer het dan als zodanig of publiceer het niet.
   - **Geen herleidbare gegevens.** Geen naam, bedrijf of e-mailadres van de vrager.

6. **Bouw de pagina opnieuw:**

   ```bash
   python tools/build_vragen.py
   ```

   Dit regenereert `public/vragen.html` met bijgewerkte FAQPage JSON-LD. Draai daarna
   ook `python tools/build_articles.py` als de sitemap moet worden ververst.

7. **Laat de vrager weten (optioneel).** Heeft de vrager een e-mailadres
   achtergelaten, stuur dan een kort bericht dat de vraag beantwoord is, met de link
   naar de pagina. Bewaar dat adres nergens in de repo.

8. **Commit en push** (na expliciete bevestiging, nooit direct naar `main`).

## Let op

- De toon volgt de nlds-schrijfwijzer: je-vorm, geen jargon, geen em-dashes.
- De pagina is server-rendered voor SEO en GEO. Antwoorden zijn dus publiek en
  vindbaar; schrijf ze zo dat ze los te lezen zijn.
- Zet in Cloudflare een rate-limit op `/vraag` (zoals op `/submit` en `/feedback`)
  om mailbommen te voorkomen. Zie `worker/DEPLOY.md`.
