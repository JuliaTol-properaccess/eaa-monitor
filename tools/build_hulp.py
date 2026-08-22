#!/usr/bin/env python3
"""
Generator voor de hulppagina (WAT-framework, Layer 3: Tool).

Rendert data/hulptools.json naar public/hulp.html: een overzicht van tools
waarmee je zelf aan de toegankelijkheid van je website en documenten kunt
werken, gegroepeerd per categorie. Server-rendered, zodat de lijst vindbaar is
in zoekmachines en AI-zoekmachines (GEO).

Deelt de head/header/footer met de artikelgenerator (tools/build_articles.py),
zodat navigatie en stijl overal gelijk zijn.

Gebruik:
    python tools/build_hulp.py

Format van data/hulptools.json (lijst van objecten, volgorde = volgorde op pagina):
    [
      {
        "naam": "WCAG Radar",
        "url": "https://testtoegankelijkheid.nl/wcag-radar",
        "aanbieder": "Proper Access",
        "categorie": "in-pagina",
        "wat": "Wat de tool doet.",
        "grens": "Wat de tool niet doet of niet vindt.",
        "prijs": "Gratis.",
        "platform": "Chrome, Firefox",
        "eigen": true
      }
    ]

Het veld "eigen" markeert een tool van Proper Access, de maker van EAA Monitor.
Die vermelding is bewust zichtbaar: de monitor staat los van dat merk, dus een
lezer moet kunnen zien waar een tool vandaan komt.
"""

import html
import json
import sys
from pathlib import Path

# Gedeelde partials hergebruiken uit de artikelgenerator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import shared_head, site_header, site_footer, BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "hulptools.json"
OUT_FILE = ROOT / "public" / "hulp.html"

ACTIVE_PATH = "/hulp.html"
URL = f"{BASE_URL}/hulp.html"
TITLE = "Hulp bij digitale toegankelijkheid: tools en waar je begint — EAA Monitor"
DESCRIPTION = (
    "Waar begin je als je website of PDF toegankelijk moet zijn? Een overzicht van "
    "tools om zelf te controleren: in-pagina checkers, contrastmeters, schermlezers "
    "en documenttools, met per tool wat hij niet vindt."
)

# Categorieën in weergavevolgorde. De slug moet matchen met het veld
# 'categorie' in data/hulptools.json.
CATEGORIES = [
    (
        "in-pagina",
        "Een pagina zelf controleren",
        "Deze zet je aan op de pagina die je op dat moment bekijkt. Je ziet het resultaat "
        "meteen in de pagina zelf. Begin hier als je nog niet weet waar je staat.",
    ),
    (
        "contrast",
        "Kleur en contrast meten",
        "Voor tekst op een effen achtergrond doet een in-pagina checker dit al. Deze twee "
        "heb je nodig zodra tekst op een foto of op een verloop staat.",
    ),
    (
        "structuur",
        "Koppen en structuur bekijken",
        "De koppenstructuur bepaalt hoe iemand met een schermlezer door je pagina navigeert. "
        "Fouten daarin zie je niet aan de opmaak.",
    ),
    (
        "schermlezer",
        "Schermlezers",
        "Een schermlezer is geen meetinstrument. Het is de manier waarop een deel van je "
        "bezoekers je site werkelijk gebruikt. Je zet hem dus niet aan om iets af te vinken, "
        "maar om te horen wat er gebeurt.",
    ),
    (
        "documenten",
        "PDF en documenten",
        "Een PDF op je site valt onder dezelfde eisen als de site zelf. In de auditpraktijk is "
        "dit het onderdeel dat het vaakst wordt overgeslagen.",
    ),
]


def _badge(text, extra=""):
    return f'<span class="bron-badge {extra}">{html.escape(text)}</span>'


def _card(tool):
    naam = html.escape(str(tool.get("naam", "")).strip())
    url = str(tool.get("url", "")).strip()
    aanbieder = html.escape(str(tool.get("aanbieder", "")).strip())
    wat = html.escape(str(tool.get("wat", "")).strip())
    grens = html.escape(str(tool.get("grens", "")).strip())
    prijs = html.escape(str(tool.get("prijs", "")).strip())
    platform = html.escape(str(tool.get("platform", "")).strip())
    eigen = bool(tool.get("eigen"))

    titel = (
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer" '
        f'class="text-brand hover:text-brand-dark">{naam}'
        f'<span class="sr-only"> (opent in een nieuw tabblad)</span></a>'
        if url
        else naam
    )
    eigen_regel = (
        '\n          <p class="mt-3 text-sm text-gray-700 bg-zachtgroen rounded-lg px-3 py-2">'
        "Van Proper Access, de maker van EAA Monitor. We noemen het erbij, zodat je weet "
        "waar deze tool vandaan komt.</p>"
        if eigen
        else ""
    )
    meta = " &middot; ".join(p for p in (aanbieder, platform) if p)
    return f"""        <li class="card p-6 flex flex-col">
          <h3 class="font-display text-xl font-semibold text-navy leading-snug">{titel}</h3>
          <p class="mt-1 text-sm text-gray-600">{meta}</p>
          <p class="mt-4 text-[15px] text-gray-700 leading-relaxed">{wat}</p>
          <p class="mt-4 text-[15px] text-gray-700 leading-relaxed"><strong class="text-navy font-semibold">Wat hij niet doet:</strong> {grens}</p>{eigen_regel}
          <p class="mt-auto pt-5 text-sm text-gray-700"><span class="font-semibold text-navy">Prijs:</span> {prijs}</p>
        </li>"""


def _sections(tools):
    blocks = []
    for slug, kop, intro in CATEGORIES:
        groep = [t for t in tools if str(t.get("categorie", "")).strip() == slug]
        if not groep:
            continue
        cards = "\n".join(_card(t) for t in groep)
        blocks.append(
            f"""    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16" aria-labelledby="cat-{slug}">
      <h2 id="cat-{slug}" class="font-display text-2xl md:text-3xl font-semibold text-navy tracking-tight">{html.escape(kop)}</h2>
      <p class="mt-3 text-gray-700 max-w-2xl leading-relaxed">{html.escape(intro)}</p>
      <ul class="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
{cards}
      </ul>
    </section>"""
        )
    return "\n\n".join(blocks)


def _jsonld(tools):
    """CollectionPage met ItemList van de tools, voor AI- en zoekmachines."""
    items = []
    for t in tools:
        naam = str(t.get("naam", "")).strip()
        url = str(t.get("url", "")).strip()
        if not naam or not url:
            continue
        app = {
            "@type": "SoftwareApplication",
            "name": naam,
            "url": url,
            "applicationCategory": "DeveloperApplication",
            "description": str(t.get("wat", "")).strip(),
        }
        aanbieder = str(t.get("aanbieder", "")).strip()
        if aanbieder:
            app["publisher"] = {"@type": "Organization", "name": aanbieder}
        items.append(
            {"@type": "ListItem", "position": len(items) + 1, "item": app}
        )
    page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{URL}#page",
        "url": URL,
        "name": "Hulp bij digitale toegankelijkheid",
        "description": DESCRIPTION,
        "inLanguage": "nl-NL",
        "isPartOf": {"@type": "WebSite", "name": "EAA Monitor", "url": BASE_URL},
    }
    if items:
        page["mainEntity"] = {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        }
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(page, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def render(tools):
    head = shared_head(TITLE, DESCRIPTION, URL, extra_head=_jsonld(tools))
    return f"""{head}<body class="bg-papier">
{site_header(ACTIVE_PATH)}
  <main id="main">

    <section>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-12">
        <p class="eyebrow">Zelf aan de slag</p>
        <h1 class="mt-3 font-display text-4xl md:text-5xl font-semibold text-navy leading-[1.08] tracking-tight max-w-3xl">Hulp bij digitale toegankelijkheid</h1>
        <p class="mt-6 text-lg md:text-xl text-gray-700 max-w-2xl leading-relaxed">Je site of je PDF moet toegankelijk zijn, en je weet nog niet waar je staat. Hieronder staan de tools waarmee je dat zelf kunt nakijken, gegroepeerd naar wat je wilt weten. Bij elke tool staat er ook bij wat hij niet vindt, want dat is het deel waar het misgaat.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6">
      <div class="notice notice-warning max-w-3xl">
        <p><strong>Een tool ziet ongeveer 30% van de succescriteria.</strong> WCAG 2.2 telt op niveau A en AA samen 55 succescriteria. Een geautomatiseerde scan herkent daar ongeveer 30% van. Dat cijfer is een schatting uit het vakgebied en geen meting van ons, dus neem het als orde van grootte.</p>
        <p class="mt-3">Wat een tool kan meten is wat meetbaar is: ontbreekt er een alt-attribuut, zakt de contrastverhouding onder 4,5:1, heeft een knop een toegankelijke naam. Wat geen tool beoordeelt is betekenis. Of die alt-tekst klopt bij de afbeelding. Of de volgorde waarin een schermlezer voorleest logisch is. Of je met het toetsenbord weer uit een dialoogvenster komt.</p>
        <p class="mt-3">Nul fouten in een scan is dus geen bewijs. <a href="/artikelen/toezicht-en-boetes.html" class="link">Wat de toezichthouder wel doet</a>, staat in de kennisbank.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-12">
      <div class="prose max-w-prose">
        <h2 class="mt-0">Wat de combinatie is die werkt</h2>
        <p>Wil je het zelf doen, dan kom je het verst met drie dingen naast elkaar: een tool die de meetbare fouten voor je opzoekt, een schermlezer erbij, en een doorloop van je pagina met alleen je toetsenbord. Die laatste kost niets en vindt de problemen die het zwaarst wegen voor je bezoeker.</p>
        <p>Begin bij de pagina's waar het om gaat. Voor een webshop is dat het hele afrekenproces, van product in het mandje tot betaling. Dat is ook het pad dat de Autoriteit Consument en Markt doorloopt bij een controle.</p>
      </div>
    </section>

{_sections(tools)}

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16">
      <div class="grid gap-6 md:grid-cols-2">
        <div class="card p-6">
          <h2 class="font-display text-xl font-semibold text-navy">Overlays staan er niet bij</h2>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">Een overlay is een stuk JavaScript dat bovenop je site draait en daar dingen aanpast: contrast verhogen, tekst vergroten, een voorleesknop toevoegen. Wat het niet doet, is de code eronder repareren. Een knop zonder toegankelijke naam blijft een knop zonder toegankelijke naam.</p>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed"><a href="/artikelen/overlay-tools-werken-niet.html" class="link font-semibold">Lees waarom een overlay je probleem niet oplost</a></p>
        </div>
        <div class="card p-6">
          <h2 class="font-display text-xl font-semibold text-navy">Liever iemand die het voor je doet</h2>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">Een onderzoek door een mens vindt de andere 70%: de leesvolgorde, de foutmeldingen, de bediening met alleen een toetsenbord, en of een alternatief klopt. Val je onder het Besluit digitale toegankelijkheid overheid, dan is dat ook de enige route naar een verklaring in het Register, want dat accepteert alleen onderzoek volgens WCAG-EM.</p>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed"><a href="/wcag-audit.html" class="link font-semibold">Vind een auditbureau</a></p>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16 mb-4">
      <div class="prose max-w-prose">
        <h2 class="mt-0">Hoe een tool op deze lijst komt</h2>
        <p>Niemand betaalt voor een plek hier. De lijst bestaat uit tools die in de Nederlandse auditpraktijk worden gebruikt, en bij elke tool staat wat hij niet vindt. Zonder die tweede regel wordt een lijst als deze een reclamefolder.</p>
        <p>Twee tools op deze pagina komen van Proper Access, de maker van EAA Monitor: de WCAG Radar en pdf-toegankelijk.nl. Die staan er met dezelfde vermelding als de rest, en met een label erbij zodat je ziet waar ze vandaan komen. Deze monitor staat verder los van dat merk.</p>
        <p>Mis je een tool, of klopt er iets niet meer? <a href="/melden.html" class="link">Laat het weten</a>.</p>
      </div>
    </section>

  </main>
{site_footer()}</body>
</html>
"""


def main():
    if not DATA_FILE.exists():
        sys.exit(f"Geen databestand gevonden: {DATA_FILE}")
    try:
        tools = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Ongeldige JSON in {DATA_FILE.name}: {exc}")
    if not isinstance(tools, list):
        sys.exit(f"{DATA_FILE.name} moet een JSON-lijst zijn.")

    bekend = {slug for slug, _, _ in CATEGORIES}
    onbekend = sorted(
        {str(t.get("categorie", "")).strip() for t in tools} - bekend - {""}
    )
    if onbekend:
        sys.exit(
            "Onbekende categorie in hulptools.json: "
            + ", ".join(onbekend)
            + ". Voeg hem toe aan CATEGORIES in build_hulp.py."
        )
    zonder = [str(t.get("naam", "?")) for t in tools if not str(t.get("categorie", "")).strip()]
    if zonder:
        sys.exit("Tool zonder categorie: " + ", ".join(zonder))

    OUT_FILE.write_text(render(tools), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(tools)} tools)")


if __name__ == "__main__":
    main()
