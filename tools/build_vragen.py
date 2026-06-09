#!/usr/bin/env python3
"""
Generator voor de pagina 'Vragen uit de praktijk' (WAT-framework, Layer 3: Tool).

Rendert data/vragen.json naar een server-rendered vraag-en-antwoordpagina in
public/vragen.html. Server-rendered, zodat de antwoorden vindbaar zijn in
zoekmachines en AI-zoekmachines (GEO). Elke vraag krijgt FAQPage JSON-LD mee.

Ondernemers stellen anoniem een vraag via public/vraag-stellen.html. De
bezwaar-Worker mailt die naar Julia (route POST /vraag). Julia legt de vraag
namens de vrager voor aan de toezichthouder en publiceert het antwoord hier.

Deelt de head/header/footer met de artikelgenerator (tools/build_articles.py),
zodat navigatie en stijl overal gelijk zijn.

Gebruik:
    python tools/build_vragen.py

Format van data/vragen.json (lijst van objecten, nieuwste eerst is niet nodig;
deze tool sorteert zelf op datum, nieuwste boven):
    [
      {
        "vraag": "Geldt de EAA ook voor een webshop die alleen aan bedrijven verkoopt?",
        "antwoord": "Tekst van het antwoord. Lege regels worden aparte alinea's.",
        "toezichthouder": "ACM",
        "datum": "2026-06-20",
        "thema": "scope",
        "bron": { "titel": "ACM: ...", "url": "https://www.acm.nl/..." }
      }
    ]
Alleen 'vraag' en 'antwoord' zijn verplicht; de rest is optioneel.

Belangrijk: publiceer hier nooit cijfers, namen of e-mailadressen die niet
bevestigd zijn. Markeer een onbevestigde claim als zodanig.
"""

import html
import json
import sys
from datetime import date as _date
from pathlib import Path

# Gedeelde partials hergebruiken uit de artikelgenerator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import (  # noqa: E402
    shared_head,
    site_header,
    site_footer,
    nl_date,
    BASE_URL,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "vragen.json"
OUT_FILE = ROOT / "public" / "vragen.html"

ACTIVE_PATH = "/vragen.html"
URL = f"{BASE_URL}/vragen.html"
TITLE = "Vragen uit de praktijk over de EAA — EAA Monitor"
DESCRIPTION = (
    "Ondernemers stellen anoniem hun vragen over de European Accessibility Act. "
    "Wij leggen ze voor aan de toezichthouder en publiceren de antwoorden hier."
)


def _parse_date(value):
    """Datum-string (YYYY-MM-DD) of date -> date, of None bij ontbreken/onzin."""
    if isinstance(value, _date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return _date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _antwoord_html(antwoord):
    """Plat antwoord -> alinea's. Lege regels scheiden alinea's; veilig geescaped."""
    text = str(antwoord or "").strip()
    if not text:
        return "<p>—</p>"
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    paras = []
    for b in blocks:
        # Enkele regeleindes binnen een alinea -> <br>.
        inner = "<br>".join(html.escape(line) for line in b.split("\n"))
        paras.append(f"<p>{inner}</p>")
    return "\n".join(paras)


def _meta_line(item):
    """Toezichthouder + datum onder de vraag, indien aanwezig."""
    bits = []
    toez = str(item.get("toezichthouder", "")).strip()
    if toez:
        bits.append(f"Beantwoord door {html.escape(toez)}")
    d = _parse_date(item.get("datum"))
    if d:
        bits.append(f"op {nl_date(d)}")
    if not bits:
        return ""
    return (
        '<p class="mt-1 text-sm text-gray-500">' + " ".join(bits) + "</p>"
    )


def _bron_line(item):
    bron = item.get("bron")
    if not isinstance(bron, dict):
        return ""
    url = str(bron.get("url", "")).strip()
    titel = str(bron.get("titel", "")).strip() or url
    if not url:
        return ""
    return (
        '<p class="mt-3 text-sm">Bron: '
        f'<a href="{html.escape(url)}" class="link" rel="nofollow noopener" '
        f'target="_blank">{html.escape(titel)}</a></p>'
    )


def _items_html(vragen):
    blocks = []
    for item in vragen:
        vraag = html.escape(str(item.get("vraag", "")).strip())
        if not vraag:
            continue
        antwoord = _antwoord_html(item.get("antwoord"))
        meta = _meta_line(item)
        bron = _bron_line(item)
        blocks.append(
            f"""        <article class="card reveal p-7 md:p-8">
          <h2 class="text-xl font-extrabold text-navy leading-snug tracking-tight">{vraag}</h2>
          {meta}
          <div class="prose max-w-none mt-4">
{antwoord}
          </div>
          {bron}
        </article>"""
        )
    return "\n".join(blocks)


def _list_or_empty(vragen):
    if not vragen:
        return """
      <div class="card p-10 text-center text-gray-600">
        <p class="text-lg">Er zijn nog geen vragen beantwoord.</p>
        <p class="mt-2">Stel als eerste je vraag, dan leggen we hem voor aan de toezichthouder en publiceren we het antwoord hier.</p>
        <a href="/vraag-stellen.html" class="btn btn-primary mt-6">Stel je vraag anoniem</a>
      </div>"""
    return f"""
      <div class="grid gap-6">
{_items_html(vragen)}
      </div>"""


def _faq_jsonld(vragen):
    """FAQPage JSON-LD, alleen als er beantwoorde vragen zijn."""
    entries = []
    for item in vragen:
        vraag = str(item.get("vraag", "")).strip()
        antwoord = str(item.get("antwoord", "")).strip()
        if not vraag or not antwoord:
            continue
        # JSON-LD answer als platte tekst (regeleindes -> spaties).
        antwoord_txt = " ".join(antwoord.split())
        entries.append(
            {
                "@type": "Question",
                "name": vraag,
                "acceptedAnswer": {"@type": "Answer", "text": antwoord_txt},
            }
        )
    if not entries:
        return ""
    obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": f"{URL}#faq",
        "inLanguage": "nl-NL",
        "mainEntity": entries,
    }
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def render(vragen):
    head = shared_head(TITLE, DESCRIPTION, URL, extra_head=_faq_jsonld(vragen))
    return f"""{head}<body class="bg-white">
{site_header(ACTIVE_PATH)}
  <main id="main">

    <section class="bg-navy text-white on-dark">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        <h1 class="text-4xl md:text-6xl font-extrabold leading-[1.05] tracking-tight max-w-3xl">Vragen uit de praktijk</h1>
        <p class="mt-6 text-lg md:text-xl text-white/70 max-w-2xl leading-relaxed">Veel ondernemers hebben vragen over de European Accessibility Act, maar aarzelen om zich bij de toezichthouder te melden. Hier stel je je vraag anoniem. Wij leggen hem namens jou voor aan de juiste toezichthouder en publiceren het antwoord, zonder je naam.</p>
        <div class="mt-8 flex flex-wrap gap-3">
          <a href="/vraag-stellen.html" class="btn btn-on-dark">Stel je vraag anoniem</a>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-12 pb-4">
      <div class="prose max-w-prose">
        <h2>Hoe het werkt</h2>
        <p>Je stelt je vraag via het formulier. Je hoeft geen naam of bedrijf op te geven. We bundelen vragen, leggen ze voor aan de toezichthouder die erover gaat (zoals de ACM of de AFM) en zetten het antwoord hier neer. Zo profiteert iedereen van het antwoord, zonder dat jij jezelf bekend hoeft te maken.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-6" aria-label="Beantwoorde vragen">
      <h2 class="text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-6">Beantwoorde vragen</h2>
{_list_or_empty(vragen)}
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16">
      <div class="rounded-3xl bg-softblue ring-1 ring-brand-light p-8 md:p-10">
        <h2 class="text-2xl font-extrabold text-navy tracking-tight">Heb je zelf een vraag?</h2>
        <p class="mt-3 text-navy/70 leading-relaxed max-w-2xl">Stel hem anoniem. We controleren je vraag, leggen hem voor aan de toezichthouder en publiceren het antwoord op deze pagina. Je e-mailadres is optioneel en blijft altijd privé.</p>
        <a href="/vraag-stellen.html" class="btn btn-primary mt-6">Stel je vraag anoniem</a>
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
        vragen = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Ongeldige JSON in {DATA_FILE.name}: {exc}")
    if not isinstance(vragen, list):
        sys.exit(f"{DATA_FILE.name} moet een JSON-lijst zijn.")

    # Nieuwste boven; items zonder geldige datum onderaan in oorspronkelijke volgorde.
    def sort_key(i):
        d = _parse_date(i.get("datum"))
        return (0, d.isoformat()) if d else (1, "")

    vragen_sorted = sorted(vragen, key=sort_key, reverse=True)

    OUT_FILE.write_text(render(vragen_sorted), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(vragen)} vragen)")


if __name__ == "__main__":
    main()
