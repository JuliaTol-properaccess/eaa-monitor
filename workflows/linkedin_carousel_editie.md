# Workflow: LinkedIn-carousel met de cijfers van de EAA-monitor

## Doel

Elke drie weken een LinkedIn-documentbericht met de actuele stand van de telling:
een PDF van 5 slides (1080x1350) en een posttekst. Eén script maakt alles uit de
data op `origin/main`. Julia controleert, vult één alinea zelf in en plaatst het
bericht met de hand op LinkedIn.

Geen maker-attributie op de slides of in de post, en geen verwijzing naar Proper
Access.

## Wanneer

- **Elke drie weken op dinsdag**, nadat de WCAG-scan van die dag binnen is. De
  scrape draait maandag 08:00 UTC (`scrape.yml`), de WCAG-scan dinsdag 06:00 UTC
  (`scan-axe.yml`). De scan zet een commit `Update WCAG-scan JJJJ-MM-DD` op `main`.
- **Is het weer tijd?** Kijk naar de nieuwste map `social-posts/*_eaa-monitor-editie/`.
  De datum in de mapnaam is de peildatum (de maandag van de meting). Is die 21 dagen
  of ouder, dan is er een nieuwe editie nodig.
- **Publiceren**: woensdag, of de maandag erna. Die dagen werken het best op Julia's
  LinkedIn.

Eerste editie: peildatum 23 november 2026. De volgende heeft peildatum 14 december
2026 en wordt dinsdag 15 december gemaakt.

## Stappen

1. **Controleer of de scan binnen is.**

   ```bash
   git fetch origin
   git log origin/main --oneline -20 | grep "Update WCAG-scan $(date +%F)"
   ```

   Geen regel? Dan draait de scan nog of is hij mislukt. Wacht, of kijk in de
   Actions-tab van de repo. Maak de editie niet op de scan van vorige week.

2. **Maak de editie in een worktree.**

   ```bash
   git worktree add -b carousel-editie-<peildatum> ~/git/.EAA_Dashboard-wt-editie origin/main
   cd ~/git/.EAA_Dashboard-wt-editie
   python3 tools/maak_carousel.py
   ```

   Het script leest standaard van `origin/main` en schrijft naar
   `social-posts/<peildatum>_eaa-monitor-editie/`:

   - `carousel.pdf`, 5 pagina's, getagd;
   - `carousel.html`, het gevulde sjabloon;
   - `cijfers.json`, alle getallen;
   - `post.md`, de concept-posttekst met `status: concept`.

   Playwright met Chromium moet geïnstalleerd zijn (`requirements.txt`). Met
   `--geen-pdf` slaat het script de PDF over.

3. **Kijk naar de uitvoer van het script.** Het meldt waarschuwingen, ook in
   `cijfers.json` onder `waarschuwingen`. Twee soorten:

   - een sector waarvan de laatste meting niet op de peildatum valt: de scrape van
     die sector is mislukt of loopt achter. Zoek uit waarom voordat je verder gaat;
   - metingen die niet in alle sectoren staan: die vallen buiten de totaallijn op
     slide 3. Dat is geen fout, maar de lijn heeft dan een punt minder.

   Controleer ook de PDF: `pdfinfo carousel.pdf` moet `Pages: 5` geven.

4. **Julia controleert de cijfers tegen de site.** Open de PDF en eaa-monitor.nl
   naast elkaar:

   - slide 1 (totaal en aandeel met verklaring) tegen de kerncijfers op de homepage;
   - slide 2 (per sector) tegen de monitorpagina van elke sector;
   - slide 4 (WCAG-scan) tegen het kerncijfer op `monitor.html`.

   De site telt bezwaren niet mee (`objections.json`), de carousel rekent op de
   history-bestanden. Een verschil van een paar sites kan daardoor komen. Een groter
   verschil: niet publiceren, eerst uitzoeken.

   De percentages op de slides zijn berekend over de sites die we konden
   controleren, niet over het totaal. Daardoor kunnen ze afwijken van een percentage
   op de site dat over alle sites gaat.

5. **Julia vult "wat viel op" in.** In `post.md` staat `[WAT VIEL OP: vul zelf in]`.
   Daaronder staan in een HTML-commentaar kandidaten die het script uit de cijfers
   heeft gerekend: verschillen van 3 procentpunt of meer bij sectoren van 30 sites
   of meer, de groei van het totaal en een verandering in de noemer. Het script
   verzint geen observaties; de alinea schrijft Julia.

   Let bij een kleine sector (onder de 30 sites, `klein: true`) op: één site
   verschil is daar al meerdere procentpunten.

   Controleer daarna de posttekst op de schrijfverboden:

   ```bash
   grep -n -i -e $'\xe2\x80\x94' -e 'eerl[i]jk' social-posts/<peildatum>_eaa-monitor-editie/post.md
   ```

   Dit zoekt naar het gedachtestreepje (U+2014, in UTF-8 de bytes E2 80 94) en naar het verboden woord; de
   schrijfwijze in het commando is zo gekozen dat het commando zelf niet als treffer
   telt. Draai het in zsh. Geen uitvoer is goed.

6. **Commit en merge.** Commit alleen de editiemap, via een branch en een pull
   request:

   ```bash
   git add social-posts/<peildatum>_eaa-monitor-editie/
   git commit -m "Carousel-editie <peildatum>"
   git push -u origin carousel-editie-<peildatum>
   gh pr create --fill
   ```

   Merge en ruim de worktree op met `git worktree remove`.

7. **Julia plaatst het bericht met de hand op LinkedIn.** Niet via Buffer (zie
   hieronder).

   - Begin een nieuw bericht en voeg `carousel.pdf` toe als document.
   - Geef het document als titel de `titel` uit de frontmatter van `post.md`.
     LinkedIn zet die titel boven de slides.
   - Plak de posttekst: alles onder `## Posttekst`, zonder het HTML-commentaar.
   - Plan het bericht in voor woensdag of de maandag erna.

8. **Zet de status bij.** Na publicatie in de frontmatter van `post.md`:
   `status: gepubliceerd`, `gepubliceerd: JJJJ-MM-DD` en `url:` met de link naar
   het bericht. Commit dat via een kleine pull request.

## Waarom niet via Buffer

`tools/post_buffer.py` in de marketingrepo kan een PDF als document plaatsen, maar
zet de PDF en de omslag daarvoor op properaccess.nl. Buffer haalt het bestand pas
op bij het publiceren, dus het moet tot dan op een vaste URL staan. Dat koppelt de
EAA-monitor aan Proper Access. Julia koos op 24 november 2026 voor met de hand
uploaden in LinkedIn.

## Randgevallen

- **`post.md` bestaat al.** Het script overschrijft `post.md` niet, zodat de
  alinea van Julia blijft staan. `carousel.pdf`, `carousel.html` en `cijfers.json`
  worden wel opnieuw gemaakt. Wil je de posttekst opnieuw laten maken, verwijder
  `post.md` dan eerst.
- **De cijfers op een bepaalde datum nodig.** `python3 tools/carousel_cijfers.py`
  geeft alleen de JSON. `--ref werkmap` leest de bestanden op schijf in plaats
  van `origin/main`. `--vanaf` zet het begin van de lijn (standaard 2026-09-07,
  het begin van de wekelijkse reeks).
- **Het format.** Vast: 5 slides, alleen de cijfers wisselen. Het sjabloon staat in
  `social-posts/carousel-sjabloon/carousel.html`. Wijzig je het, controleer dan het
  contrast opnieuw (minimaal 4,5:1, groot 3:1).
