# EAA Monitor: promotieplan

Levend document. Doel: de wekelijks verse data van het dashboard omzetten in een
herhaalbare promotie-engine die bereik geeft bij EAA-plichtige webshops en externe
vermeldingen oplevert (goed voor de vindbaarheid in AI-zoekmachines).

## Doel en strategie

De data is de marketing. Het aandeel Nederlandse webshops met een
toegankelijkheidsverklaring verschuift elke week, en dat is een reden om te blijven volgen.
Het ritme bouwt verwachting, de variatie houdt het fris, en de vermeldingen die de posts
opleveren lezen zoekmachines als autoriteit.

Onderdeel van Proper Access. Geen cross-promotie met andere merken.

### Cijfers in dit document

Hier staat geen stand. De bron is `data/history.json`, met een meetpunt per week; het laatste
meetpunt is wat het dashboard toont, en `tools/generate_linkedin_post.py` haalt het cijfer
daar op. Zet een stand dus niet in dit document: een getal in lopende tekst verschuift niet
mee en staat binnen een paar weken fout. Noem je een cijfer in een post of een stuk, zet dan
de meetdatum erbij.

## Kanalen

- **LinkedIn (kern):** elke vrijdag een post. Julia post vanaf haar persoonlijke
  profiel, de Proper Access-pagina herdeelt binnen enkele uren met een zin kadertekst.
  Native posten voor maximaal organisch bereik.
- **LinkedIn en Medium (maandelijks):** een dieper stuk dat de maand duidt. Afgeronde
  stukken gaan sinds 6 oktober 2026 naar LinkedIn en Medium, niet meer naar de blog op
  properaccess.nl. Cross-link naar en vanaf het dashboard.

## Het wekelijkse LinkedIn-systeem

Vaste tijd, advies vrijdag 11:00 tot 12:00. Vier roterende invalshoeken zodat het geen
sjabloon wordt. De tool kiest de hoek op basis van wat de data die week laat zien.

- **A. Statusupdate met verandering:** de week-op-week beweging is de haak.
- **B. Sector-spotlight:** een categorie die voorloopt of juist achterblijft.
- **C. Goed voorbeeld:** een webshop die deze week een verklaring plaatste.
- **D. Uitleg:** beantwoord een veelgestelde EAA-vraag (sluit aan op de FAQ op het dashboard).
- **Mijlpaal** (incidenteel): een rond getal of percentage.

### Post-stramien (4 tot 6 regels, scanbaar)

1. Haak met het cijfer of de verandering.
2. Een zin context: de EAA geldt sinds juni 2025, een verklaring is de eerste zichtbare stap.
3. Een concreet detail: categorie, nieuw toegevoegde webshop, of een uitschieter.
4. Zachte uitnodiging: link naar het dashboard, vraag om reactie. Geen verkooppraat.
5. Vaste afsluiter met 3 tot 5 hashtags.

## De post-generator

`tools/generate_linkedin_post.py` stelt het concept op. Cijfers komen automatisch uit de
data, dus altijd correct.

```bash
python tools/generate_linkedin_post.py            # tool kiest de invalshoek
python tools/generate_linkedin_post.py --angle B  # forceer een invalshoek (launch, A, B, C, D)
python tools/generate_linkedin_post.py --print    # alleen tonen, niets wegschrijven
```

Het concept komt in `.tmp/linkedin/<datum>.md` en bevat zowel de post (Julia) als de
herdelingszin (bedrijfspagina). De tool kiest "launch" zolang er nog geen eigen
week-op-week reeks is, daarna A tot en met D. Je redigeert het concept altijd zelf
voordat je het plaatst; volg daarbij de schrijfwijzer.

De databron is `data/history.json`, die de scraper elke maandag automatisch bijwerkt
(een meetpunt per week). Voor "deze week nieuw toegevoegd" vergelijkt de tool met de
data van vorige week uit de git-historie.

### Merkregels (bewaakt door de tool)

Je-vorm, nooit "u". Conversationeel en concreet, geen jargon. Geen emoji, geen em-dashes.
De tool markeert em-dashes, emoji en verboden jargon en schrijft het concept dan niet weg
zonder `--force`. Nooit data verzinnen: alle cijfers komen uit de meting.

## Het maandelijkse stuk

Een keer per maand een stuk dat de maand samenvat en duidt, op LinkedIn en Medium. De
LinkedIn-posts van die maand voeden het stuk; het stuk wordt zelf weer een vrijdagpost
(hoek D). Link altijd naar het dashboard, en zet op het dashboard een link terug naar het
stuk.

Het schrijven en de kanaalkeuze liggen bij de contentstroom, niet bij deze repo. Staat er
een cijfer in, haal het dan uit `data/history.json` en zet de meetdatum erbij.

Onderwerpen om uit te putten:
- Wat de cijfers over de eerste maanden van de EAA laten zien.
- Welke sectoren lopen achter en waarom.
- Van verklaring naar echt toegankelijk: de volgende stap.

## Contentkalender (eerste 8 weken, indicatief)

| Week | Vrijdag LinkedIn | Maandelijks |
|------|------------------|-------------|
| 1 | Lancering (launch): wij monitoren, met de stand uit `data/history.json` | |
| 2 | A. Statusupdate met eerste week-op-week verandering | |
| 3 | B. Sector-spotlight (koploper vs achterblijver) | |
| 4 | C. Goed voorbeeld (nieuw toegevoegde webshops) | Stuk 1: wat de cijfers laten zien |
| 5 | D. Uitleg: wat is een toegankelijkheidsverklaring? | |
| 6 | A. Statusupdate | |
| 7 | B. Sector-spotlight (andere categorie) | |
| 8 | Mijlpaal of C. Goed voorbeeld | Stuk 2: sectoren die achterlopen |

Na week 8 de rotatie A, B, C, D herhalen en de kalender bijsturen op wat het best werkt.

## Meten en bijsturen

- LinkedIn native analytics: bereik en interactie per post. Noteer welke invalshoek het
  best werkt en verschuif de rotatie daarheen.
- Optioneel later: privacy-vriendelijke analytics op het dashboard om verwijzingsverkeer
  te zien (los voorstel).
- Maandelijkse mini-review van 15 minuten: beste post, lessen, kalender aanscherpen.
