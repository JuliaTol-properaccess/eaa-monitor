#!/usr/bin/env python3
"""
Generator voor de bronnenpagina (WAT-framework, Layer 3: Tool).

Rendert data/bronnen.json naar een server-rendered, filterbare lijst van
externe bronnen over de EAA in public/bronnen.html. Server-rendered, zodat de
lijst vindbaar is in zoekmachines en AI-zoekmachines (GEO); de categoriefilters
en het zoekveld werken client-side bovenop de volledige lijst.

Deelt de head/header/footer met de artikelgenerator (tools/build_articles.py),
zodat navigatie en stijl overal gelijk zijn.

Gebruik:
    python tools/build_bronnen.py

Format van data/bronnen.json (lijst van objecten, volgorde = volgorde op pagina):
    [
      {
        "title": "Titel van de bron",
        "url": "https://www.voorbeeld.nl/artikel",
        "author": "Organisatie of auteur",
        "category": "toezichthouders"
      }
    ]
"""

import html
import json
import sys
from pathlib import Path

# Gedeelde partials hergebruiken uit de artikelgenerator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import shared_head, site_header, site_footer, BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "bronnen.json"
OUT_FILE = ROOT / "public" / "bronnen.html"

ACTIVE_PATH = "/bronnen.html"
URL = f"{BASE_URL}/bronnen.html"
TITLE = "Bronnen over de EAA — EAA Monitor"
DESCRIPTION = (
    "Een doorzoekbaar overzicht van bronnen over de European Accessibility Act: "
    "toezichthouders, overheid, financiële sector, juristen, bureaus en vakmedia. "
    "Filter op brontype."
)

# Categorieën in weergavevolgorde. Slug moet matchen met het veld 'category'
# in data/bronnen.json.
CATEGORIES = [
    ("toezichthouders", "Toezichthouders"),
    ("overheid", "Overheid & wetgeving"),
    ("financieel", "Financieel"),
    ("belangen", "Belangenorganisaties"),
    ("juristen", "Juristen"),
    ("bureaus", "Bureaus"),
    ("vakmedia", "Vakmedia"),
    ("onderwijs", "Onderwijs"),
    ("uitgevers", "Uitgevers"),
    ("internationaal", "Internationaal"),
]
CAT_LABELS = dict(CATEGORIES)

# Maanden voor Nederlandse datumweergave.
NL_MONTHS = [
    "", "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def nl_date(iso: str) -> str:
    """ISO-datum (YYYY-MM-DD) naar '24 maart 2026'. Leeg bij ongeldige invoer."""
    try:
        y, m, d = (int(x) for x in str(iso).split("-")[:3])
        return f"{d} {NL_MONTHS[m]} {y}"
    except (ValueError, IndexError):
        return ""


def _filter_buttons(sources):
    counts = {slug: 0 for slug, _ in CATEGORIES}
    for s in sources:
        cat = str(s.get("category", ""))
        if cat in counts:
            counts[cat] += 1

    buttons = [
        '        <button type="button" class="bron-filter" data-cat="all" '
        f'aria-pressed="true">Alle <span class="bron-count">{len(sources)}</span></button>'
    ]
    for slug, label in CATEGORIES:
        if not counts[slug]:
            continue
        buttons.append(
            f'        <button type="button" class="bron-filter" data-cat="{slug}" '
            f'aria-pressed="false">{html.escape(label)} '
            f'<span class="bron-count">{counts[slug]}</span></button>'
        )
    return "\n".join(buttons)


def _items(sources):
    rows = []
    for s in sources:
        title = html.escape(str(s.get("title", "")).strip())
        url = str(s.get("url", "")).strip()
        author = html.escape(str(s.get("author", "")).strip())
        cat = str(s.get("category", "")).strip()
        label = html.escape(CAT_LABELS.get(cat, cat))
        iso = str(s.get("date", "")).strip()
        date_str = nl_date(iso)
        # data-text voert het client-side zoeken; titel + auteur, lowercase.
        search_text = html.escape(f"{s.get('title', '')} {s.get('author', '')}".lower())
        meta_left = f'<span class="text-gray-600">{author or "&mdash;"}</span>'
        if date_str:
            meta_left += (
                '<span class="text-gray-300" aria-hidden="true"> · </span>'
                f'<time datetime="{html.escape(iso)}" class="text-gray-500">{html.escape(date_str)}</time>'
            )
        rows.append(
            f'        <li class="bron-item card p-5 flex flex-col gap-2" data-cat="{html.escape(cat)}" data-text="{search_text}">\n'
            f'          <a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer" '
            f'class="font-bold text-navy hover:text-brand leading-snug">{title or url}'
            f'<span class="sr-only"> (opent in een nieuw tabblad)</span></a>\n'
            f'          <div class="flex items-center justify-between gap-3 text-sm">\n'
            f'            <span>{meta_left}</span>\n'
            f'            <span class="bron-badge">{label}</span>\n'
            f'          </div>\n'
            f'        </li>'
        )
    return "\n".join(rows)


def render(sources):
    head = shared_head(TITLE, DESCRIPTION, URL)
    return f"""{head}<body class="bg-white">
{site_header(ACTIVE_PATH)}
  <main id="main">

    <section class="bg-navy text-white on-dark">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        <h1 class="text-4xl md:text-6xl font-extrabold leading-[1.05] tracking-tight max-w-3xl">Bronnen over de EAA</h1>
        <p class="mt-6 text-lg md:text-xl text-white/70 max-w-2xl leading-relaxed">Een doorzoekbaar overzicht van artikelen en bronnen over de European Accessibility Act. Filter op brontype, van toezichthouders tot vakmedia.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 -mt-10 relative z-10 pb-2">
      <div class="prose max-w-prose">
        <h2>Hoe lees je deze lijst?</h2>
        <p>Bovenaan staan de gezaghebbende bronnen: toezichthouders, overheid en de wettekst zelf. Die wegen het zwaarst. Veel bureau- en blogartikelen zijn inhoudelijk prima, maar de cijfers wisselen, dus check een claim altijd tegen de primaire bron. Dit is een vindlijst, geen factcheck.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-8" aria-label="Bronnen">
      <div class="mb-6 space-y-4">
        <div>
          <label for="bron-search" class="block text-sm font-semibold text-navy mb-1.5">Zoek in bronnen</label>
          <input type="search" id="bron-search" placeholder="Zoek op titel of organisatie" autocomplete="off"
                 class="w-full sm:max-w-md rounded-lg border border-line px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand">
        </div>
        <div class="flex flex-wrap gap-2" role="group" aria-label="Filter op brontype" id="bron-filters">
{_filter_buttons(sources)}
        </div>
      </div>

      <p id="bron-result-count" class="text-sm text-gray-600 mb-4" role="status" aria-live="polite"></p>

      <ul id="bron-list" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 list-none p-0 m-0">
{_items(sources)}
      </ul>

      <div id="bron-empty" class="card p-10 text-center text-gray-600 hidden">
        <p>Geen bronnen gevonden voor deze filter of zoekterm.</p>
      </div>
    </section>

  </main>
{site_footer()}  <script src="/static/bronnen.js"></script>
</body>
</html>
"""


def main():
    if not DATA_FILE.exists():
        sys.exit(f"Geen databestand gevonden: {DATA_FILE}")
    try:
        sources = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Ongeldige JSON in {DATA_FILE.name}: {exc}")
    if not isinstance(sources, list):
        sys.exit(f"{DATA_FILE.name} moet een JSON-lijst zijn.")

    OUT_FILE.write_text(render(sources), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(sources)} bronnen)")


if __name__ == "__main__":
    main()
