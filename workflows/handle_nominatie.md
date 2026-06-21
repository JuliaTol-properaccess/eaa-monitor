# Workflow: Eregalerij-nominatie verrijken of modereren

## Doel

Sinds 21 juni 2026 komen bevestigde nominaties **automatisch** in de
[eregalerij](../public/eregalerij.html): na de dubbele e-mail-opt-in commit de
Worker de nominatie direct naar `data/halloffame.json` op main (geen PR, geen
controle vooraf) en de deploy herbouwt de pagina. Er is dus geen poort meer om
doorheen te komen.

Deze workflow gaat over twee dingen die je *achteraf* kunt doen:

1. een al geplaatste vermelding **verrijken** met geverifieerde observaties en
   codevoorbeelden, zodat ontwikkelaars zien hóe het kan;
2. een vermelding **modereren** (verwijderen) als het spam of misbruik is.

Beide zijn gewone wijzigingen op `data/halloffame.json`, via een commit of PR.

## Een vermelding verrijken met observaties (optioneel)

Een nominatie staat live met alleen de motivatie-quote van de inzender. Wil je er
de waardevolle code-voorbeelden bij zetten:

1. **Doe een korte toegankelijkheidscheck.** Mini-auditniveau: werkt de site met
   alleen het toetsenbord (focus zichtbaar, geen vallen), klopt de basis voor
   schermlezers (koppen, landmarks, labels, alt-teksten), en klopt de flow die de
   inzender noemt?

2. **Schrijf 2-3 geverifieerde observaties** in het veld `observaties` van de
   entry in `data/halloffame.json`:

   ```json
   {
     "titel": "Echte knoppen in de winkelwagen",
     "beschrijving": "De plus- en minknoppen zijn echte buttons met een toegankelijk label, dus schermlezers lezen ze als 'Aantal verhogen, knop'.",
     "code": "<button type=\"button\" aria-label=\"Aantal verhogen\">+</button>",
     "wcag": "4.1.2"
   }
   ```

   - **Verzin nooit code.** Knip de snippet uit de echte broncode van de site;
     inkorten en opschonen mag, verzinnen niet.
   - `titel` is verplicht; `beschrijving`, `code` en `wcag` zijn optioneel maar
     maken de observatie veel waardevoller.

3. **Redigeer de rest van de entry.** Haal herleidbare gegevens uit de
   `motivatie`-quote, breng hem op nlds-toon en zet eventueel een `categorie`
   (vrij label, bijvoorbeeld `webshop`, `bank`, `overheid`, `media`). Laat `slug`
   ongewijzigd: de stemtellers hangen eraan.

4. **Bouw de pagina opnieuw en commit:**

   ```bash
   python tools/build_halloffame.py
   python tools/build_articles.py   # ververst de sitemap
   ```

## Een vermelding modereren (verwijderen)

Omdat er geen controle vooraf is, kan er spam of een ongepaste vermelding tussen
staan. Verwijderen:

1. Haal de entry uit `data/halloffame.json`.
2. Draai `python tools/build_halloffame.py` en commit (de deploy zet de
   bijgewerkte pagina live; de CI bouwt de eregalerij ook zelf opnieuw).
3. Eventuele stemmen op die `slug` blijven in KV staan maar tellen nergens meer
   mee; je kunt ze laten staan.

De dubbele e-mail-opt-in is de enige rem op de instroom: zonder klik op de
bevestigingslink komt een nominatie niet live.

## Let op

- De toon volgt de nlds-schrijfwijzer: je-vorm, geen jargon, geen em-dashes.
- **Nooit e-mailadressen** in `data/halloffame.json`; de repo is openbaar. Het
  adres van de inzender leeft alleen kort in KV (`hof:pending:<uuid>`, TTL 7
  dagen) en in de bevestigingsmail.
- Stemmen zijn sociaal bewijs, geen ranglijst met gevolgen. Ziet een teller er
  verdacht uit (plotselinge piek), dan kun je de KV-sleutels `hof:vote:<slug>:*`
  en `hof:count:<slug>` bekijken en de teller handmatig bijstellen (let op de
  quoted-key gotchas, zie memory/DEPLOY.md).
- Eigen-domein-stemmen weigert de Worker al; een zelfnominatie komt wel gewoon
  live (de Worker vlagt hem niet meer apart, want er is geen reviewstap).
