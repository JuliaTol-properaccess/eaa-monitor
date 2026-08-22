#!/usr/bin/env python3
"""
Generator voor de hulppagina (WAT-framework, Layer 3: Tool).

Rendert data/hulptools.json naar public/tools.html: een overzicht van tools
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
        "platform": "Chrome, Firefox"
      }
    ]

Met "uitleg" hang je een artikel aan een tool, bijvoorbeeld een handleiding
op een andere site:

    "uitleg": { "titel": "Zo gebruik je NVDA", "url": "https://..." }

"categorie" mag ook een lijst zijn. De tool verschijnt dan in elke genoemde
categorie. Met "varianten" geef je per categorie een eigen "wat" en "grens",
zodat een kaart vertelt wat de tool in dat rijtje doet:

    "categorie": ["in-pagina", "contrast"],
    "varianten": { "contrast": { "wat": "...", "grens": "..." } }
"""

import html
import json
import subprocess
import sys
from pathlib import Path

# Gedeelde partials hergebruiken uit de artikelgenerator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import shared_head, site_header, site_footer, BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "hulptools.json"
OUT_FILE = ROOT / "public" / "tools.html"

ACTIVE_PATH = "/tools.html"
URL = f"{BASE_URL}/tools.html"
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
        "Een PDF op je site valt onder dezelfde eisen als de site zelf. Een document dat je alleen "
        "aanbiedt om te downloaden telt dus gewoon mee.",
    ),
]


NL_MAANDEN = [
    "", "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def _laatst_gewijzigd():
    """Datum van de laatste inhoudelijke wijziging aan data/hulptools.json.

    Uit git, niet uit de klok: een herbouw zonder wijziging mag de pagina niet
    verser laten lijken dan hij is. Lukt git niet, dan komt er geen datum op de
    pagina en geen dateModified in de JSON-LD. Een ontbrekende datum is beter
    dan een datum die niet klopt.
    """
    try:
        uit = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(DATA_FILE)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return uit or None


def _nl_datum(iso):
    jaar, maand, dag = iso.split("-")
    return f"{int(dag)} {NL_MAANDEN[int(maand)]} {jaar}"


# Veelgestelde vragen. Antwoorden staan zowel in de pagina als in FAQPage
# JSON-LD, zodat een AI-zoekmachine het antwoord los kan citeren. Elk antwoord
# moet op zichzelf kloppen, ook als het uit de pagina wordt getild.
FAQ = [
    (
        "Is een geautomatiseerde scan genoeg om aan de European Accessibility Act te voldoen?",
        "Nee. De European Accessibility Act vraagt een toegankelijke website of app en schrijft geen "
        "onderzoek voor. Een scan herkent ongeveer 30% van de checkpunten onder WCAG, dus nul fouten in "
        "een scan zegt niets over de rest. Val je onder het Besluit digitale toegankelijkheid overheid, "
        "dan heb je bovendien een verklaring in het Register nodig, en dat accepteert alleen onderzoek "
        "volgens WCAG-EM.",
    ),
    (
        "Welke tool kan ik gebruiken als ik geen developer ben?",
        "Begin met de gratis versie van de WCAG Radar. Die heeft een apart tabblad voor redactie, met "
        "12 thema's die je op elke pagina moet toetsen, en zet het resultaat in de pagina zelf. Je "
        "hebt er geen account voor nodig. WAVE geeft het "
        "snelste visuele overzicht, maar om te beoordelen wat een melding daar betekent heb je "
        "behoorlijk wat technische kennis nodig.",
    ),
    (
        "Wat kost een toegankelijkheidstool?",
        "De meeste kosten niets. WAVE, Lighthouse, ANDI, Accessibility Insights, de WebAIM Contrast "
        "Checker, de Colour Contrast Analyser, HeadingsMap, NVDA en PAC 2024 zijn gratis, en VoiceOver en "
        "TalkBack zitten in het besturingssysteem. Betaald zijn JAWS, Adobe Acrobat Pro met € 285 per "
        "jaar, de licentie van de WCAG Radar vanaf € 119 per jaar en pdf-toegankelijk.nl vanaf € 29 per "
        "maand voor meer dan twee documenten.",
    ),
    (
        "Helpt een toegankelijkheidsoverlay?",
        "Niet voor het probleem waarvoor ze worden verkocht. Een overlay is JavaScript dat bovenop je site "
        "draait en daar dingen aanpast, zoals contrast verhogen of tekst vergroten. De code eronder "
        "repareert het niet. Een knop zonder toegankelijke naam blijft een knop zonder toegankelijke naam.",
    ),
    (
        "Kan ik een PDF toegankelijk maken zonder hem opnieuw op te maken?",
        "Voor een deel. Met pdf-toegankelijk.nl of Adobe Acrobat Pro breng je een tagstructuur aan in een "
        "bestaand document. Wat geen van beide vaststelt is of de leesorde klopt en of een alternatieve "
        "tekst de afbeelding dekt. Een gerepareerde codelaag is dus nog geen toegankelijk document.",
    ),
]


def _badge(text, extra=""):
    return f'<span class="bron-badge {extra}">{html.escape(text)}</span>'


def _categorieen(tool):
    """categorie mag een string of een lijst zijn."""
    waarde = tool.get("categorie", "")
    if isinstance(waarde, list):
        return [str(c).strip() for c in waarde if str(c).strip()]
    return [str(waarde).strip()] if str(waarde).strip() else []


def _card(tool, categorie):
    # Een tool die in meerdere categorieën staat, kan per categorie een eigen
    # tekst hebben: in het contrastrijtje vertel je wat hij met contrast doet.
    variant = (tool.get("varianten") or {}).get(categorie, {})
    naam = html.escape(str(tool.get("naam", "")).strip())
    url = str(tool.get("url", "")).strip()
    aanbieder = html.escape(str(tool.get("aanbieder", "")).strip())
    wat = html.escape(str(variant.get("wat") or tool.get("wat", "")).strip())
    grens = html.escape(str(variant.get("grens") or tool.get("grens", "")).strip())
    prijs = html.escape(str(tool.get("prijs", "")).strip())
    platform = html.escape(str(tool.get("platform", "")).strip())

    titel = (
        f'<a href="{html.escape(url)}" rel="noopener noreferrer" '
        f'class="text-brand hover:text-brand-dark">{naam}</a>'
        if url
        else naam
    )
    uitleg = tool.get("uitleg") or {}
    uitleg_url = str(uitleg.get("url", "")).strip()
    uitleg_titel = html.escape(str(uitleg.get("titel", "")).strip())
    uitleg_regel = (
        f'\n          <p class="mt-3 text-[15px]"><a href="{html.escape(uitleg_url)}" '
        f'rel="noopener noreferrer" class="link font-semibold">{uitleg_titel}</a></p>'
        if uitleg_url and uitleg_titel
        else ""
    )
    meta = " &middot; ".join(p for p in (aanbieder, platform) if p)
    return f"""        <li class="card p-6 flex flex-col">
          <h3 class="font-display text-xl font-semibold text-navy leading-snug">{titel}</h3>
          <p class="mt-1 text-sm text-gray-600">{meta}</p>
          <p class="mt-4 text-[15px] text-gray-700 leading-relaxed">{wat}</p>
          <p class="mt-4 text-[15px] text-gray-700 leading-relaxed"><strong class="text-navy font-semibold">Wat hij niet doet:</strong> {grens}</p>{uitleg_regel}
          <p class="mt-auto pt-5 text-sm text-gray-700"><span class="font-semibold text-navy">Prijs:</span> {prijs}</p>
        </li>"""


def _faq_html():
    blokken = []
    for vraag, antwoord in FAQ:
        blokken.append(
            '        <div class="card p-6">\n'
            f'          <h3 class="font-display text-lg font-semibold text-navy leading-snug">{html.escape(vraag)}</h3>\n'
            f'          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">{html.escape(antwoord)}</p>\n'
            "        </div>"
        )
    return "\n".join(blokken)


def _sections(tools):
    blocks = []
    for slug, kop, intro in CATEGORIES:
        groep = [t for t in tools if slug in _categorieen(t)]
        if not groep:
            continue
        cards = "\n".join(_card(t, slug) for t in groep)
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
    gewijzigd = _laatst_gewijzigd()
    if gewijzigd:
        page["dateModified"] = gewijzigd
    if items:
        page["mainEntity"] = {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        }
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": f"{URL}#faq",
        "url": URL,
        "inLanguage": "nl-NL",
        "mainEntity": [
            {
                "@type": "Question",
                "name": vraag,
                "acceptedAnswer": {"@type": "Answer", "text": antwoord},
            }
            for vraag, antwoord in FAQ
        ],
    }
    graph = {"@context": "https://schema.org", "@graph": [page, faq]}
    graph["@graph"][1].pop("@context", None)
    page.pop("@context", None)
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(graph, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def render(tools):
    head = shared_head(TITLE, DESCRIPTION, URL, extra_head=_jsonld(tools))
    gewijzigd = _laatst_gewijzigd()
    datumregel = (
        f'\n        <p class="mt-4 text-sm text-gray-600">Deze lijst telt {len(tools)} tools '
        f'en is bijgewerkt op <time datetime="{gewijzigd}">{_nl_datum(gewijzigd)}</time>. '
        "Prijzen en functies veranderen; controleer ze bij de aanbieder zelf.</p>"
        if gewijzigd
        else ""
    )
    return f"""{head}<body class="bg-papier">
{site_header(ACTIVE_PATH)}
  <main id="main">

    <section>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-12">
        <p class="eyebrow">Zelf aan de slag</p>
        <h1 class="mt-3 font-display text-4xl md:text-5xl font-semibold text-navy leading-[1.08] tracking-tight max-w-3xl">Hulp bij digitale toegankelijkheid</h1>
        <p class="mt-6 text-lg md:text-xl text-gray-700 max-w-2xl leading-relaxed">Je site of je PDF moet toegankelijk zijn, en je weet nog niet waar je staat. Hieronder staan de tools waarmee je dat zelf kunt nakijken, met de beperkingen die elke tool heeft.</p>{datumregel}
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6">
      <div class="notice notice-warning max-w-3xl">
        <p><strong>Een geautomatiseerde scan herkent ongeveer 30% van alle checkpunten onder WCAG.</strong> Dat cijfer is een schatting uit het vakgebied. Wat overblijft is alles waar betekenis bij komt kijken: of een alt-tekst klopt bij de afbeelding, of de leesvolgorde logisch is, of je met het toetsenbord weer uit een dialoogvenster komt. Nul fouten in een scan is dus geen bewijs: Proper Access onderzocht een site die in de scan nul fouten gaf en leverde een rapport op met <a href="https://www.properaccess.nl/blog/nul-fouten-scan-ruim-honderd-bevindingen-audit/" rel="noopener noreferrer" class="link">ruim honderd bevindingen</a>.</p>
      </div>
    </section>

{_sections(tools)}

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-20">
      <div class="prose max-w-prose">
        <h2 class="mt-0">De combinatie die werkt</h2>
        <p>Wil je het zelf doen, dan kom je het verst met drie dingen naast elkaar: een tool die de meetbare fouten voor je opzoekt, een schermlezer erbij, en een doorloop van je pagina met alleen je toetsenbord. Die laatste kost niets en vindt de problemen die het zwaarst wegen voor je bezoeker.</p>
        <p>Begin bij de pagina's waar het om gaat. Voor een webshop is dat het hele afrekenproces, van product in het mandje tot betaling. Dat is ook het pad dat de Autoriteit Consument en Markt doorloopt bij een controle. <a href="/artikelen/toezicht-en-boetes.html" class="link">Wat de toezichthouder verder doet</a>, staat in de kennisbank.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-12">
      <div class="grid gap-6 md:grid-cols-2">
        <div class="card p-6">
          <h2 class="font-display text-xl font-semibold text-navy">Overlays staan er niet bij</h2>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">Een overlay is een stuk JavaScript dat bovenop je site draait en daar dingen aanpast: contrast verhogen, tekst vergroten, een voorleesknop toevoegen. Wat het niet doet, is de code eronder repareren. Een knop zonder toegankelijke naam blijft een knop zonder toegankelijke naam.</p>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed"><a href="/artikelen/overlay-tools-werken-niet.html" class="link font-semibold">Lees waarom een overlay je probleem niet oplost</a></p>
        </div>
        <div class="card p-6">
          <h2 class="font-display text-xl font-semibold text-navy">Liever een compleet beeld door een expert?</h2>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">Een onderzoek door een mens vindt de andere 70%: de leesvolgorde, de foutmeldingen, de bediening met alleen een toetsenbord, en of een alternatief klopt. Val je onder het Besluit digitale toegankelijkheid overheid, dan is dat ook de enige route naar een verklaring in het Register, want dat accepteert alleen onderzoek volgens WCAG-EM.</p>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed"><a href="/wcag-audit.html" class="link font-semibold">Vind een auditbureau</a></p>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16 mb-4" aria-labelledby="vragen">
      <h2 id="vragen" class="font-display text-2xl md:text-3xl font-semibold text-navy tracking-tight">Veelgestelde vragen</h2>
      <div class="mt-8 grid gap-6 md:grid-cols-2">
{_faq_html()}
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
    gebruikt = {c for t in tools for c in _categorieen(t)}
    onbekend = sorted(gebruikt - bekend)
    if onbekend:
        sys.exit(
            "Onbekende categorie in hulptools.json: "
            + ", ".join(onbekend)
            + ". Voeg hem toe aan CATEGORIES in build_hulp.py."
        )
    zonder = [str(t.get("naam", "?")) for t in tools if not _categorieen(t)]
    if zonder:
        sys.exit("Tool zonder categorie: " + ", ".join(zonder))

    OUT_FILE.write_text(render(tools), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(tools)} tools)")


if __name__ == "__main__":
    main()
