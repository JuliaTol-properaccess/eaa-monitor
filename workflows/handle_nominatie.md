# Workflow: Eregalerij-nominatie verwerken

## Doel

Een per e-mail bevestigde nominatie voor de [eregalerij](../public/eregalerij.html)
beoordelen en, als de website het verdient, publiceren met geverifieerde
observaties en codevoorbeelden. De PR is de poort: zonder merge verschijnt er
niets op de site, en de build-tool slaat entries zonder observaties over. Alleen
websites die een senior auditor zelf heeft gecontroleerd komen erin.

Het tweede doel van de eregalerij is ontwikkelaars laten zien hóe het kan: elke
vermelding bevat 2-3 concrete observaties met echte code van de site.

## Inputs

Een pull request van de bezwaar-Worker met branchprefix `hof/` op
`data/halloffame.json` (route `GET /hof/nominate/confirm`, zie
`worker/src/index.js`). De PR-body bevat:

- naam en URL van de genomineerde website,
- de motivatie van de inzender (mag als anonieme quote gepubliceerd worden;
  de inzender heeft daarvoor een vinkje gezet),
- de hulptechnologie waarmee de inzender de site gebruikte (optioneel),
- de vlag **zelfnominatie**: ja betekent dat het e-maildomein van de inzender
  gelijk is aan het domein van de site. Dat is geen diskwalificatie, maar weeg
  het mee: een zelfnominatie moet de check dubbel zo overtuigend doorstaan.

Het e-mailadres van de inzender staat **nooit** in de PR of de repo; het leeft
alleen kort in KV (`hof:pending:<uuid>`, TTL 7 dagen) en in de bevestigingsmail.

## Stappen

1. **Beoordeel de nominatie.** Is het een echte website, geen spam, en staat hij
   niet al in de eregalerij of in een open `hof/`-PR? Is de motivatie serieus?
   Twijfel of duidelijk misbruik: sluit de PR met een korte, vriendelijke
   toelichting.

2. **Doe een korte toegankelijkheidscheck.** Mini-auditniveau, geen volledige
   audit. Controleer minimaal:

   - werkt de site volledig met alleen het toetsenbord (focus zichtbaar, geen
     vallen, logische volgorde);
   - klopt de basis voor schermlezers (koppenstructuur, landmarks, labels op
     formuliervelden en knoppen, alternatieve teksten);
   - de flow die de inzender noemt in de motivatie (bijvoorbeeld afrekenen met
     VoiceOver): klopt die claim?

   Onvoldoende? Sluit de PR met een vriendelijke toelichting. De lat ligt hoog:
   de eregalerij is alleen geloofwaardig als elke vermelding klopt.

3. **Schrijf 2-3 geverifieerde observaties.** Vul in de PR-branch het veld
   `observaties` van de entry in `data/halloffame.json`:

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
     maken de observatie veel waardevoller voor ontwikkelaars.
   - Schrijf de beschrijving zo dat een ontwikkelaar zonder WCAG-kennis snapt
     waarom dit goed is.

4. **Redigeer de rest van de entry.** Haal herleidbare gegevens uit de
   `motivatie`-quote, breng hem op nlds-toon en zet een `categorie` (vrij label,
   bijvoorbeeld `webshop`, `bank`, `overheid`, `media`). Controleer dat `slug`
   ongewijzigd blijft: de stemtellers hangen eraan.

5. **Bouw de pagina opnieuw** op de PR-branch en commit het resultaat mee:

   ```bash
   python tools/build_halloffame.py
   python tools/build_articles.py   # ververst de sitemap
   ```

   De build-tool waarschuwt en slaat de entry over zolang `observaties` leeg is;
   dat hoort, het is de vangrail tegen te vroeg mergen.

6. **Merge de PR.** De deploy-workflow zet de nieuwe eregalerij live. Vanaf dat
   moment kan er op de vermelding gestemd worden (de stemroute valideert tegen
   de live `data/halloffame.json`).

7. **Bedank de inzender (optioneel).** Het adres staat alleen in de
   oorspronkelijke Worker-flow, niet in de repo; bewaar het nergens.

## Let op

- De toon volgt de nlds-schrijfwijzer: je-vorm, geen jargon, geen em-dashes.
- **Nooit e-mailadressen** in `data/halloffame.json` of de PR; de repo is openbaar.
- Stemmen zijn sociaal bewijs, geen ranglijst met gevolgen. Ziet een teller er
  verdacht uit (plotselinge piek), dan kun je de KV-sleutels `hof:vote:<slug>:*`
  en `hof:count:<slug>` bekijken en de teller handmatig bijstellen met
  `npx wrangler kv key put` (let op de quoted-key gotchas, zie memory/DEPLOY.md).
- Eigen-domein-stemmen weigert de Worker al; zelfnominaties komen wel door maar
  gevlagd. Jij bent de laatste poort.
