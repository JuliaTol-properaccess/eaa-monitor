# Workflow: Bezwaar tegen vermelding verwerken

## Doel

Een binnengekomen bezwaar van een webshop-eigenaar verwerken: controleren of het verzoek legitiem is, de webshop uit het dashboard halen en op de openbare bezwarenpagina plaatsen.

We controleren de inhoudelijke criteria niet. Het is een eigen verklaring. We controleren alleen of het verzoek echt van de webshop komt, om misbruik namens een concurrent te voorkomen.

## Twee routes

Sinds juni 2026 lopen bezwaren via de bezwaar-Worker (`worker/`). Die kiest automatisch een van twee routes:

1. **Automatische route (domein-geverifieerd).** Staat het opgegeven e-mailadres op het webshop-domein zelf (bijvoorbeeld `info@webshop.nl` bij `webshop.nl`), dan stuurt de Worker een bevestigingslink naar dat adres. Klikt de aanvrager die link, dan opent de Worker een pull request op `data/objections.json`. Een concurrent kan die mail niet ontvangen, dus de legitimiteit is daarmee aangetoond. Jij hoeft alleen de PR kort te bekijken en te mergen. De stappen hieronder hoef je dan niet handmatig te doen, de Worker heeft de entry al gemaakt.

2. **Handmatige route (geen domeinmatch).** Staat het e-mailadres niet op het webshop-domein (bijvoorbeeld een gmail-adres), dan maakt de Worker geen PR maar stuurt hij een mail naar Julia. Verwerk dat bezwaar dan met de stappen hieronder.

De stappen in dit document gelden voor de handmatige route, en als naslag voor wat de Worker in de automatische route doet.

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
- De automatische route loopt via de bezwaar-Worker. Code en uitrolinstructies staan in `worker/` (zie `worker/DEPLOY.md`). De frontend wijst naar de Worker via de constante `BEZWAAR_ENDPOINT` in `public/bezwaar.html`. Is die leeg, dan valt het formulier terug op Formspree (`https://formspree.io/f/mdavapbl`).
- De Worker dedupliceert: een al vermelde webshop of een al ingediend bezwaar levert geen tweede PR op. Bij een PR uit de automatische route hoef je de entry niet zelf te schrijven, alleen te controleren en te mergen.
