# SOP: een melding via "Klopt iets niet?" verwerken

Meldingen komen binnen via `public/melden.html` → de bezwaar-Worker (route `POST /melden`)
→ mail naar `NOTIFY_EMAIL` (`info@eaa-monitor.nl`). Geen opslag, geen PR: de mail is de
hele inbox. Twee soorten meldingen:

1. **"Mijn organisatie staat op zonder verklaring, maar ik heb er wel een."** Met een
   opgegeven `verklaring_url`. Dit is de belangrijkste: de eigenaar wijst ons de plek aan
   die de automatische meting miste (link verstopt in een menu, achter een cookiemelding,
   in een pdf, of via JavaScript opgebouwd).
2. **Een algemene correctie** (verkeerde categorie, dubbele vermelding, enzovoort).

## Stap 1: verifieer de verklaring-URL

Open de opgegeven `verklaring_url` (of zoek hem op de genoemde website). Controleer met de hand:

- Staat er een **echte toegankelijkheidsverklaring**, niet alleen een aanvraag-/contactformulier?
  Hallmarks: verwijzing naar WCAG of EN 301 549, een nalevingsstatus ("voldoet (gedeeltelijk) aan"),
  benoemde tekortkomingen, een contact-/handhavingsprocedure.
- Staat de verklaring op het **eigen domein** van de organisatie (of een duidelijk eigen
  subdomein/pdf), niet op een overlay-vendor (accessibe.com, userway.org)?
- Klopt de **website-URL** met een vermelding in de monitor? Zoek de organisatie op in de
  juiste `data/<sector>.json` of `data/webshops.json`.

Klopt er iets niet of twijfel je? Mail de melder terug (als er een e-mailadres bij zit) en vraag door.
**Nooit een verklaring aannemen die je niet zelf hebt gezien.**

## Stap 2: zet de site op de bevestigd-groen-lijst

Voeg een entry toe aan de juiste confirmed-lijst (`data/confirmed.json` voor webshops; voor
sectoren bestaat nog geen aparte confirmed-lijst, zet die dan in de sectorlijst-aanpak of
overleg). Schema:

```json
{
  "name": "Naam van de organisatie",
  "url": "https://www.voorbeeld.nl",
  "statement_url": "https://www.voorbeeld.nl/toegankelijkheid",
  "statement_link_text": "Toegankelijkheidsverklaring",
  "confirmed": "JJJJ-MM-DD"
}
```

- `url` exact zoals in de invoerlijst (`tools/sync_confirmed.py` normaliseert bij het matchen).
- `confirmed` is de datum van vandaag (de dag dat jij het verifieerde).
- De scraper slaat deze site daarna `REVERIFY_DAYS` (30) dagen over en houdt hem op "met
  verklaring", ook als een transiente bot-challenge of een gemiste link hem anders zou laten
  wegvallen. Na 30 dagen herverifieert de scraper vanzelf.

Commit met een duidelijke boodschap (bijvoorbeeld `Bevestigd groen: <naam> (melding)`),
wacht op expliciete bevestiging voordat je pusht. De eerstvolgende deploy/scrape toont de site
als "met verklaring".

## Stap 3: laat het de melder weten (optioneel)

Zat er een e-mailadres bij, stuur dan kort terug wat je hebt aangepast. Het e-mailadres komt
nooit in de repo of op de website.

## Let op

- **Geen e-mailadressen in `data/`** (de repo is openbaar).
- Is de melding een echte correctie maar geen verklaring (bv. verkeerde categorie), pas dan de
  betreffende `data/<sector>.json`/`webshops.json` aan in plaats van `confirmed.json`.
- Valt de organisatie buiten de wet (micro-onderneming, B2B), verwijs dan naar
  `public/bezwaar.html` en `workflows/handle_objection.md` in plaats van confirmed-groen.
