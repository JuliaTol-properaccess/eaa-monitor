# Workflow: Bezwaar tegen vermelding verwerken

## Doel

Een binnengekomen bezwaar van een webshop-eigenaar verwerken: controleren of het verzoek legitiem is, de webshop uit het dashboard halen en op de openbare bezwarenpagina plaatsen.

We controleren de inhoudelijke criteria niet. Het is een eigen verklaring. We controleren alleen of het verzoek echt van de webshop komt, om misbruik namens een concurrent te voorkomen.

## Inputs

- Een e-mail van Formspree met de velden uit `public/bezwaar.html`:
  - bedrijfsnaam
  - webadres
  - e-mailadres
  - drie verklaringen (minder dan 10 medewerkers, omzet onder € 2 miljoen, uitsluitend B2B)
  - optionele toelichting

## Stappen

1. **Controleer de legitimiteit.** Komt het verzoek plausibel van de webshop zelf? Let op:
   - Past het e-maildomein bij het webadres, of is het een herkenbaar persoonlijk adres van de eigenaar?
   - Zijn alle drie de verklaringen aangevinkt? Zonder alle drie is er geen geldige grond.
   - Bij twijfel: mail de eigenaar via het opgegeven adres ter bevestiging voordat je verder gaat.

2. **Voeg een entry toe aan `data/objections.json`.** Dit bestand is een JSON-array. Voeg één object toe. **Neem het e-mailadres NIET op** (de repo is openbaar).

   ```json
   {
     "name": "Voorbeeld B.V.",
     "url": "https://www.voorbeeld.nl",
     "date": "2026-06-06",
     "declared": { "under_10_fte": true, "under_2m_turnover": true, "b2b_only": true }
   }
   ```

   - `name`: bedrijfsnaam zoals opgegeven.
   - `url`: het webadres. Neem het bij voorkeur exact over zoals het in het dashboard staat. De matching is ongevoelig voor hoofdletters, `http`/`https`, een leidend `www.` en een trailing slash, dus kleine verschillen zijn geen probleem.
   - `date`: datum van het bezwaar in het formaat `JJJJ-MM-DD`.
   - `declared`: de drie verklaringen, altijd `true` (zonder alle drie verwerk je het bezwaar niet).

3. **Commit en push** (op een branch, niet direct naar `main`).

   ```bash
   git checkout -b bezwaar/voorbeeld-bv
   git add data/objections.json
   git commit -m "Bezwaar verwerkt: Voorbeeld B.V."
   git push -u origin bezwaar/voorbeeld-bv
   # daarna een pull request, of na akkoord mergen naar main
   ```

4. **Controleer de deploy.** Na de merge naar `main` draait `deploy.yml` automatisch. Controleer daarna op de live site:
   - De webshop staat niet meer in de dashboardtabel en telt niet meer mee in de cijfers.
   - De webshop staat wel op `bezwaren.html` met naam, link en datum.

## Hoe de uitsluiting werkt

- `data/objections.json` is een overlay bovenop `data/results.json`. De scraper blijft alle webshops controleren; de uitsluiting gebeurt in de browser.
- `public/app.js` haalt `objections.json` op, bouwt een set van genormaliseerde URL's en laat die webshops weg uit de tabel én herberekent alle statistieken.
- `public/bezwaren.js` toont dezelfde lijst op de openbare bezwarenpagina.

## Bezwaar intrekken

Wil een webshop terug in het dashboard? Verwijder het bijbehorende object uit `data/objections.json`, commit en push. De webshop verschijnt dan weer in het dashboard bij de eerstvolgende deploy.

## Aandachtspunten

- Verwerk een bezwaar nooit zonder dat alle drie de verklaringen zijn aangevinkt.
- Zet nooit een e-mailadres in `data/objections.json`; de repo is openbaar.
- De Formspree-endpoint staat in `public/bezwaar.html` in het `action`-attribuut van het formulier: `https://formspree.io/f/mdavapbl`.
