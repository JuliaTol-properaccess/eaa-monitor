#!/usr/bin/env python3
"""
Generator voor de volledige, server-rendered meetlijsten (WAT, Layer 3: Tool).

De monitorpagina's bouwen hun tabel client-side uit data/results*.json. Een
crawler zonder JavaScript ziet daar dus wel de cijfers, maar geen enkele naam.
Deze tool rendert dezelfde meting als platte HTML, zodat de volledige telling
leesbaar en citeerbaar is voor zoekmachines en AI-zoekmachines (GEO).

Per sector één pagina, behalve webshops: die lijst is te groot voor één pagina
en wordt gesplitst per beginletter.

Belangrijk: de filterregels moeten gelijk blijven aan public/app.js.
- Sites met een bezwaar (data/objections.json) vallen uit lijst én telling.
- scrape_status != "success" is "niet te controleren", nooit "geen verklaring".
- De WCAG-scan-status komt uit de overlay data/axe-results.json, gekoppeld op
  een genormaliseerde URL, en alleen bij sites met een verklaring.

Gebruik:
    python tools/build_lijsten.py
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import shared_head, site_header, site_footer, BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_DIR = ROOT / "public" / "lijst"
HUB_FILE = ROOT / "public" / "lijst.html"

# Zelfde volgorde als de Monitor-dropdown. split_letters=True splitst de lijst
# per beginletter; dat is alleen bij webshops nodig.
SECTOREN = [
    {
        "slug": "webshops", "results": "results.json", "monitor": "/monitor.html",
        "noun": "webshops", "label": "Webshops",
        "toezicht": "Autoriteit Consument en Markt", "split_letters": True,
    },
    {
        "slug": "financieel", "results": "results-financieel.json",
        "monitor": "/monitor-financieel.html", "noun": "financiële instellingen",
        "label": "Financiële sector", "toezicht": "Autoriteit Financiële Markten",
        "split_letters": False,
    },
    {
        "slug": "telecom", "results": "results-telecom.json",
        "monitor": "/monitor-telecom.html", "noun": "telecomaanbieders",
        "label": "Telecom", "toezicht": "Autoriteit Consument en Markt",
        "split_letters": False,
    },
    {
        "slug": "vervoer", "results": "results-vervoer.json",
        "monitor": "/monitor-vervoer.html", "noun": "vervoerders",
        "label": "Personenvervoer", "toezicht": "Inspectie Leefomgeving en Transport",
        "split_letters": False,
    },
    {
        "slug": "media", "results": "results-media.json",
        "monitor": "/monitor-media.html", "noun": "mediadiensten",
        "label": "Media en streaming", "toezicht": "Commissariaat voor de Media",
        "split_letters": False,
    },
    {
        "slug": "ebooks", "results": "results-ebooks.json",
        "monitor": "/monitor-ebooks.html", "noun": "e-bookplatforms",
        "label": "E-books", "toezicht": "Autoriteit Consument en Markt",
        "split_letters": False,
    },
    {
        "slug": "reizen", "results": "results-reizen.json",
        "monitor": "/monitor-reizen.html", "noun": "reisorganisaties",
        "label": "Reizen", "toezicht": "Autoriteit Consument en Markt",
        "split_letters": False,
    },
]

NL_MAANDEN = [
    "", "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

STATUS_LABEL = {
    "gevonden": "Verklaring gevonden",
    "niet-gevonden": "Geen verklaring gevonden",
    "onbekend": "Niet te controleren",
}
AXE_LABEL = {
    "fouten": "Fouten gevonden",
    "schoon": "Geen fouten gevonden",
    "niet-scanbaar": "Niet te scannen",
}


def normalize_url(url):
    """Gelijk aan normalizeUrl() in public/app.js."""
    if not url:
        return ""
    u = str(url).strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    if u.startswith("www."):
        u = u[4:]
    return u.rstrip("/")


def nl_datum(iso):
    datum = str(iso)[:10]
    jaar, maand, dag = datum.split("-")
    return f"{int(dag)} {NL_MAANDEN[int(maand)]} {jaar}"


def status_van(site):
    if site.get("scrape_status") != "success":
        return "onbekend"
    return "gevonden" if site.get("has_statement") else "niet-gevonden"


def letter_van(naam):
    """Groepeer op beginletter; alles buiten A-Z valt onder '0-9'."""
    for teken in str(naam).strip():
        boven = teken.upper()
        if "A" <= boven <= "Z":
            return boven
        return "0-9"
    return "0-9"


def laad_overlays():
    objections = set()
    pad = DATA / "objections.json"
    if pad.exists():
        try:
            for o in json.loads(pad.read_text(encoding="utf-8")):
                sleutel = normalize_url(o.get("url"))
                if sleutel:
                    objections.add(sleutel)
        except (json.JSONDecodeError, AttributeError, TypeError):
            print("Waarschuwing: objections.json onleesbaar, ga verder zonder.")
    axe = {}
    pad = DATA / "axe-results.json"
    if pad.exists():
        try:
            data = json.loads(pad.read_text(encoding="utf-8"))
            for entry in (data.get("sites") or {}).values():
                sleutel = normalize_url(entry.get("url"))
                if sleutel:
                    axe[sleutel] = entry.get("status", "")
        except (json.JSONDecodeError, AttributeError, TypeError):
            print("Waarschuwing: axe-results.json onleesbaar, ga verder zonder.")
    return objections, axe


def laad_sector(sector, objections):
    pad = DATA / sector["results"]
    if not pad.exists():
        return None
    data = json.loads(pad.read_text(encoding="utf-8"))
    sites = data.get("webshops") or data.get("sites") or []
    sites = [s for s in sites if normalize_url(s.get("url")) not in objections]
    sites.sort(key=lambda s: str(s.get("name", "")).strip().lower())
    return {"sites": sites, "last_updated": data.get("last_updated", "")}


def _rij(site, axe):
    naam = html.escape(str(site.get("name", "")).strip())
    url = str(site.get("url", "")).strip()
    status = status_van(site)
    verklaring_url = str(site.get("statement_url") or "").strip()

    naam_cel = (
        f'<a href="{html.escape(url)}" rel="nofollow noopener noreferrer">{naam}</a>'
        if url else naam
    )
    if status == "gevonden" and verklaring_url:
        status_cel = (
            f'{STATUS_LABEL[status]} &middot; '
            f'<a href="{html.escape(verklaring_url)}" rel="nofollow noopener noreferrer">verklaring</a>'
        )
    else:
        status_cel = STATUS_LABEL[status]

    scan = ""
    if status == "gevonden":
        scan = AXE_LABEL.get(axe.get(normalize_url(url), ""), "")
    return (
        "<tr>"
        f'<th scope="row">{naam_cel}</th>'
        f"<td>{status_cel}</td>"
        f'<td>{scan or "&mdash;"}</td>'
        f'<td>{html.escape(str(site.get("category", "")))}</td>'
        "</tr>"
    )


def _tabel(sites, axe, bijschrift):
    return f"""      <div class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="lijst-tabel">
            <caption class="sr-only">{html.escape(bijschrift)}</caption>
            <thead>
              <tr>
                <th scope="col">Naam</th>
                <th scope="col">Toegankelijkheidsverklaring</th>
                <th scope="col">WCAG-scan</th>
                <th scope="col">Categorie</th>
              </tr>
            </thead>
            <tbody>
{''.join(_rij(s, axe) for s in sites)}
            </tbody>
          </table>
        </div>
      </div>"""


def _getal(n):
    """Duizendtallen met een punt, zoals de schrijfwijzer voorschrijft."""
    return f"{n:,}".replace(",", ".")


def _telling(sites):
    telling = {"gevonden": 0, "niet-gevonden": 0, "onbekend": 0}
    for s in sites:
        telling[status_van(s)] += 1
    return telling


def _letterbalk(sector, letters, actief):
    knoppen = []
    for letter in letters:
        pad = f"/lijst/{sector['slug']}-{letter.lower().replace('0-9', '0-9')}.html"
        if letter == actief:
            knoppen.append(
                f'<span class="bron-filter" aria-current="page" aria-pressed="true">{letter}</span>'
            )
        else:
            knoppen.append(f'<a href="{pad}" class="bron-filter">{letter}</a>')
    return (
        '      <nav aria-label="Bladeren per beginletter" class="mt-8 flex flex-wrap gap-2">\n        '
        + "\n        ".join(knoppen)
        + "\n      </nav>"
    )


def _jsonld(url, naam, omschrijving, sites, datum):
    items = []
    for s in sites:
        site_url = str(s.get("url", "")).strip()
        site_naam = str(s.get("name", "")).strip()
        if not site_url or not site_naam:
            continue
        items.append({
            "@type": "ListItem",
            "position": len(items) + 1,
            "item": {"@type": "Organization", "name": site_naam, "url": site_url},
        })
    page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{url}#page",
        "url": url,
        "name": naam,
        "description": omschrijving,
        "inLanguage": "nl-NL",
        "isPartOf": {"@type": "WebSite", "name": "EAA Monitor", "url": BASE_URL},
    }
    if datum:
        page["dateModified"] = str(datum)[:10]
    # Alleen bij een korte lijst een ItemList meegeven. Bij 900 namen
    # verdubbelt die het paginagewicht en staat dezelfde informatie al in de
    # tabel, die een crawler gewoon leest.
    if items and len(items) <= 100:
        page["mainEntity"] = {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        }
    elif items:
        page["mainEntity"] = {"@type": "ItemList", "numberOfItems": len(items)}
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(page, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def render_lijst(sector, sites, alle_sites, datum, axe, *, letter=None, letters=None):
    slug = sector["slug"]
    bestandsnaam = f"{slug}-{letter.lower()}.html" if letter else f"{slug}.html"
    url = f"{BASE_URL}/lijst/{bestandsnaam}"
    telling = _telling(sites)
    totaal_telling = _telling(alle_sites)

    deel = f", namen met {letter}" if letter else ""
    titel = f"Alle gemeten {sector['noun']}{deel} — EAA Monitor"
    omschrijving = (
        f"De volledige meting van {len(sites)} {sector['noun']}{deel}: heeft de site een "
        f"toegankelijkheidsverklaring in de footer? Gemeten op {nl_datum(datum)} door EAA Monitor."
    )
    kop = f"Alle gemeten {sector['noun']}" + (f", namen met {letter}" if letter else "")

    letterbalk = _letterbalk(sector, letters, letter) if letters else ""
    # Alleen zinvol op een letterpagina: daar is "op deze pagina" een deel
    # van het geheel. Bij een sector op één pagina zijn ze hetzelfde.
    sector_regel = (
        f" Over de hele sector: {_getal(totaal_telling['gevonden'])} van de {_getal(len(alle_sites))}."
        if letter else ""
    )
    totaalregel = (
        f" Deze letter telt {_getal(len(sites))} van de {_getal(len(alle_sites))} gemeten {sector['noun']}."
        if letter else ""
    )

    head = shared_head(
        titel, omschrijving, url,
        extra_head=_jsonld(url, kop, omschrijving, sites, datum),
    )
    return bestandsnaam, f"""{head}<body class="bg-papier">
{site_header("")}
  <main id="main">

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pt-14 pb-6">
      <p class="eyebrow">Volledige meting</p>
      <h1 class="mt-3 font-display text-3xl md:text-4xl font-semibold text-navy leading-[1.1] tracking-tight">{html.escape(kop)}</h1>
      <p class="mt-5 text-lg text-gray-700 max-w-2xl leading-relaxed">Deze pagina toont de meting zonder JavaScript, zodat de hele lijst leesbaar is. Gemeten op <time datetime="{str(datum)[:10]}">{nl_datum(datum)}</time>. Toezicht in deze sector ligt bij de {html.escape(sector['toezicht'])}.{totaalregel}</p>
      <p class="mt-4 text-[15px] text-gray-700 max-w-2xl leading-relaxed">Op deze pagina: <strong>{telling['gevonden']}</strong> met een gevonden verklaring, <strong>{telling['niet-gevonden']}</strong> zonder, en <strong>{telling['onbekend']}</strong> die niet te controleren waren.{sector_regel}</p>
      <div class="notice notice-info mt-6 max-w-2xl">
        <p>Een gevonden verklaring betekent niet dat een site ook toegankelijk is. De meting kijkt of er in de footer een link naar een toegankelijkheidsverklaring staat, meer niet. "Niet te controleren" betekent dat de pagina niet geladen kon worden, bijvoorbeeld door bot-beveiliging of een wachtrij; dat telt nooit als "geen verklaring".</p>
        <p class="mt-3"><a href="{sector['monitor']}" class="link font-semibold">Naar het interactieve dashboard voor deze sector</a> &middot; <a href="/lijst.html" class="link font-semibold">Alle sectoren</a> &middot; <a href="/melden.html" class="link font-semibold">Klopt er iets niet?</a></p>
      </div>
{letterbalk}
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pb-8">
{_tabel(sites, axe, kop)}
    </section>

  </main>
{site_footer()}</body>
</html>
"""


def render_hub(overzicht):
    url = f"{BASE_URL}/lijst.html"
    totaal = sum(o["totaal"] for o in overzicht)
    omschrijving = (
        f"De volledige meting van {totaal} Nederlandse organisaties in zeven sectoren, "
        "als platte lijst zonder JavaScript. Per site: staat er een toegankelijkheidsverklaring "
        "in de footer?"
    )
    kaarten = []
    for o in overzicht:
        letters = ""
        if o["letters"]:
            links = " ".join(
                f'<a href="/lijst/{o["slug"]}-{l.lower()}.html" class="bron-filter">{l}</a>'
                for l in o["letters"]
            )
            letters = f'\n          <div class="mt-4 flex flex-wrap gap-2">{links}</div>'
        else:
            letters = (
                f'\n          <p class="mt-4"><a href="/lijst/{o["slug"]}.html" '
                f'class="link font-semibold">Bekijk de volledige lijst</a></p>'
            )
        kaarten.append(f"""        <li class="card p-6">
          <h2 class="font-display text-xl font-semibold text-navy">{html.escape(o['label'])}</h2>
          <p class="mt-2 text-sm text-gray-600">{o['totaal']} gemeten &middot; {o['gevonden']} met een gevonden verklaring</p>{letters}
        </li>""")

    head = shared_head("Alle metingen als lijst — EAA Monitor", omschrijving, url)
    return f"""{head}<body class="bg-papier">
{site_header("")}
  <main id="main">

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pt-14 pb-6">
      <p class="eyebrow">Volledige meting</p>
      <h1 class="mt-3 font-display text-3xl md:text-4xl font-semibold text-navy leading-[1.1] tracking-tight">Alle metingen als lijst</h1>
      <p class="mt-5 text-lg text-gray-700 max-w-2xl leading-relaxed">De dashboards bouwen hun tabel met JavaScript. Hier staat dezelfde meting als platte lijst, zodat je hem ook kunt lezen zonder script, kunt doorzoeken met de zoekfunctie van je browser en kunt citeren. In totaal {totaal} organisaties in zeven sectoren.</p>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pb-8">
      <ul class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
{chr(10).join(kaarten)}
      </ul>
    </section>

  </main>
{site_footer()}</body>
</html>
"""


def lijst_urls():
    """(pad, lastmod) van elke lijstpagina, voor de sitemap in build_articles.py.

    Leest dezelfde databestanden als main(), zodat de sitemap nooit naar een
    letterpagina wijst die niet bestaat.
    """
    objections, _ = laad_overlays()
    urls = [("/lijst.html", None)]
    for sector in SECTOREN:
        data = laad_sector(sector, objections)
        if not data or not data["sites"]:
            continue
        lastmod = str(data["last_updated"])[:10] or None
        if sector["split_letters"]:
            letters = {letter_van(s.get("name", "")) for s in data["sites"]}
            for letter in sorted(letters, key=lambda l: (l == "0-9", l)):
                urls.append((f"/lijst/{sector['slug']}-{letter.lower()}.html", lastmod))
        else:
            urls.append((f"/lijst/{sector['slug']}.html", lastmod))
    return urls


def main():
    objections, axe = laad_overlays()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overzicht, geschreven = [], 0

    for sector in SECTOREN:
        data = laad_sector(sector, objections)
        if not data or not data["sites"]:
            print(f"Overgeslagen (geen data): {sector['slug']}")
            continue
        sites, datum = data["sites"], data["last_updated"]
        telling = _telling(sites)

        if sector["split_letters"]:
            groepen = {}
            for s in sites:
                groepen.setdefault(letter_van(s.get("name", "")), []).append(s)
            letters = sorted(groepen, key=lambda l: (l == "0-9", l))
            for letter in letters:
                naam, pagina = render_lijst(
                    sector, groepen[letter], sites, datum, axe,
                    letter=letter, letters=letters,
                )
                (OUT_DIR / naam).write_text(pagina, encoding="utf-8")
                geschreven += 1
        else:
            letters = []
            naam, pagina = render_lijst(sector, sites, sites, datum, axe)
            (OUT_DIR / naam).write_text(pagina, encoding="utf-8")
            geschreven += 1

        overzicht.append({
            "slug": sector["slug"], "label": sector["label"],
            "totaal": len(sites), "gevonden": telling["gevonden"], "letters": letters,
        })

    HUB_FILE.write_text(render_hub(overzicht), encoding="utf-8")
    print(f"Geschreven: {geschreven} lijstpagina's + public/lijst.html")


if __name__ == "__main__":
    main()
