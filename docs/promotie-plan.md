# EAA Monitor: promotieplan

Levend document. Doel: de wekelijks verse data van het dashboard omzetten in een
herhaalbare promotie-engine die bereik geeft bij EAA-plichtige webshops en externe
vermeldingen oplevert (goed voor de vindbaarheid in AI-zoekmachines).

## Doel en strategie

De data is de marketing. Een eerlijk cijfer dat elke week verschuift (nu 13% van de
Nederlandse webshops met een toegankelijkheidsverklaring) is een reden om te blijven
volgen. Het ritme bouwt verwachting, de variatie houdt het fris, en de blog geeft de
externe vermeldingen die zoekmachines als autoriteit lezen.

Onderdeel van Proper Access. Geen cross-promotie met andere merken.

## Kanalen

- **LinkedIn (kern):** elke vrijdag een post. Julia post vanaf haar persoonlijke
  profiel, de Proper Access-pagina herdeelt binnen enkele uren met een zin kadertekst.
  Native posten voor maximaal organisch bereik.
- **Blog op properaccess.nl (maandelijks):** een dieper artikel dat de maand duidt,
  in `content/dutch/blog/`, categorie `de-eaa`. Cross-link naar en vanaf het dashboard.

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

## Maandelijkse blog

Een keer per maand een artikel op properaccess.nl dat de maand samenvat en duidt. De
LinkedIn-posts van die maand voeden het artikel; het artikel wordt zelf weer een
vrijdagpost (hoek D). Link altijd naar het dashboard, en zet op het dashboard een link
terug naar de blog.

Onderwerpen om uit te putten:
- Drie maanden EAA: wat de cijfers laten zien.
- Welke sectoren lopen achter en waarom.
- Van verklaring naar echt toegankelijk: de volgende stap.

## Contentkalender (eerste 8 weken, indicatief)

| Week | Vrijdag LinkedIn | Maandelijks |
|------|------------------|-------------|
| 1 | Lancering (launch): wij monitoren, stand nu 13% | |
| 2 | A. Statusupdate met eerste week-op-week verandering | |
| 3 | B. Sector-spotlight (koploper vs achterblijver) | |
| 4 | C. Goed voorbeeld (nieuw toegevoegde webshops) | Blog 1: Drie maanden EAA, de cijfers |
| 5 | D. Uitleg: wat is een toegankelijkheidsverklaring? | |
| 6 | A. Statusupdate | |
| 7 | B. Sector-spotlight (andere categorie) | |
| 8 | Mijlpaal of C. Goed voorbeeld | Blog 2: sectoren die achterlopen |

Na week 8 de rotatie A, B, C, D herhalen en de kalender bijsturen op wat het best werkt.

## Meten en bijsturen

- LinkedIn native analytics: bereik en interactie per post. Noteer welke invalshoek het
  best werkt en verschuif de rotatie daarheen.
- Optioneel later: privacy-vriendelijke analytics op het dashboard om verwijzingsverkeer
  te zien (los voorstel).
- Maandelijkse mini-review van 15 minuten: beste post, lessen, kalender aanscherpen.
