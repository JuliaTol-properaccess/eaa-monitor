#!/usr/bin/env python3
"""
Generator voor de Eregalerij (WAT-framework, Layer 3: Tool).

Rendert data/halloffame.json naar public/eregalerij.html: een server-rendered
overzicht van websites die bezoekers als digitaal toegankelijk ervaren.
Consumenten nomineren via public/nomineren.html (Worker-route POST /hof/nominate);
na e-mailbevestiging commit de Worker de nominatie direct naar data/halloffame.json
op main (geen PR, geen controle, besluit 21 juni 2026) en de CI bouwt deze pagina
opnieuw. Julia kan een entry later verrijken met geverifieerde observaties.

Stemmen lopen via de Worker (POST /hof/vote, dubbele opt-in per e-mail) en staan
in KV, niet in dit databestand. De pagina haalt de tellers client-side op via
GET /hof/votes (public/static/halloffame.js); zonder JavaScript blijven de
tellers en stemformulieren verborgen.

Deelt de head/header/footer met de artikelgenerator (tools/build_articles.py).

Gebruik:
    python tools/build_halloffame.py

Format van data/halloffame.json (lijst van objecten; deze tool sorteert zelf
op datum, nieuwste boven):
    [
      {
        "naam": "Voorbeeldshop",
        "url": "https://www.voorbeeldshop.nl",
        "slug": "voorbeeldshop.nl",
        "categorie": "webshop",
        "datum": "2026-06-15",
        "motivatie": "Ik kon met VoiceOver zonder hulp afrekenen.",
        "hulptechnologie": "VoiceOver op iOS",
        "observaties": [
          {
            "titel": "Echte knoppen in de winkelwagen",
            "beschrijving": "De plus- en minknoppen zijn echte buttons met een toegankelijk label.",
            "code": "<button type=\\"button\\" aria-label=\\"Aantal verhogen\\">+</button>",
            "wcag": "4.1.2"
          }
        ]
      }
    ]

Verplicht voor rendering: naam, url, slug en datum. Observaties zijn optioneel;
staan ze er, dan tonen we het blok "Wat doet deze website goed?" met
codevoorbeelden. De slug komt van de Worker en is het anker voor de stemtellers;
wijzig hem niet na publicatie. Nooit e-mailadressen in dit bestand (de repo is
openbaar).
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
DATA_FILE = ROOT / "data" / "halloffame.json"
OUT_FILE = ROOT / "public" / "eregalerij.html"

ACTIVE_PATH = "/eregalerij.html"
URL = f"{BASE_URL}/eregalerij.html"
TITLE = "Eregalerij: websites die echt toegankelijk zijn — EAA Monitor"
DESCRIPTION = (
    "Een toegankelijkheidsverklaring zegt niets over echte toegankelijkheid. "
    "In de eregalerij staan websites die bezoekers als digitaal toegankelijk "
    "ervaren en daarom nomineren."
)

# Basis-URL van de bezwaar-Worker (zie worker/DEPLOY.md). De stemroutes zijn
# /hof/vote en /hof/votes; public/static/halloffame.js plakt die er zelf achter.
HOF_ENDPOINT_BASE = "https://eaa-monitor.nl/api"


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


def _valid_entries(entries):
    """Filtert entries die compleet genoeg zijn om te publiceren.

    Nominaties worden zonder controle geplaatst (besluit 21 juni 2026), dus een
    ontbrekende observatie is geen reden meer om over te slaan. Naam, url, slug
    en datum blijven verplicht; zonder die kan de kaart niet gerenderd worden.
    """
    ok = []
    for item in entries:
        naam = str(item.get("naam", "")).strip()
        url = str(item.get("url", "")).strip()
        slug = str(item.get("slug", "")).strip()
        datum = _parse_date(item.get("datum"))
        if not (naam and url and slug and datum):
            print(f"Waarschuwing: entry overgeslagen (naam/url/slug/datum mist): {naam or url or slug or '?'}")
            continue
        ok.append(item)
    return ok


def _observatie_html(obs):
    titel = html.escape(str(obs.get("titel", "")).strip())
    beschrijving = html.escape(str(obs.get("beschrijving", "")).strip())
    code = str(obs.get("code", "")).strip()
    wcag = str(obs.get("wcag", "")).strip()

    parts = []
    if beschrijving:
        parts.append(f'<p class="mt-3 text-gray-700 leading-relaxed">{beschrijving}</p>')
    if code:
        parts.append(f'<pre class="hof-code" tabindex="0"><code>{html.escape(code)}</code></pre>')
    if wcag:
        parts.append(
            f'<p class="mt-2 text-sm text-gray-500">Raakt aan succescriterium {html.escape(wcag)}.</p>'
        )
    body = "\n            ".join(parts)
    return f"""          <details class="hof-details">
            <summary>{titel}</summary>
            {body}
          </details>"""


def _entry_html(item):
    naam = html.escape(str(item.get("naam", "")).strip())
    url = str(item.get("url", "")).strip()
    slug = str(item.get("slug", "")).strip()
    slug_attr = html.escape(slug, quote=True)
    categorie = str(item.get("categorie", "")).strip()
    datum = _parse_date(item.get("datum"))
    motivatie = str(item.get("motivatie", "")).strip()
    hulptech = str(item.get("hulptechnologie", "")).strip()

    badge = f'<span class="bron-badge">{html.escape(categorie)}</span>' if categorie else ""
    meta_bits = [f"Opgenomen op {nl_date(datum)}"]
    if hulptech:
        meta_bits.append(f"getest door de nominator met {html.escape(hulptech)}")
    meta = ", ".join(meta_bits)

    quote = ""
    if motivatie:
        quote = f"""        <figure class="mt-4">
          <blockquote class="border-l-4 border-brand-light pl-4 text-gray-700 leading-relaxed italic">{html.escape(motivatie)}</blockquote>
          <figcaption class="mt-1 text-sm text-gray-500">Uit de nominatie van een bezoeker</figcaption>
        </figure>"""

    observaties_items = [
        o for o in item.get("observaties") or []
        if isinstance(o, dict) and str(o.get("titel", "")).strip()
    ]
    observaties_block = ""
    if observaties_items:
        observaties_html = "\n".join(_observatie_html(o) for o in observaties_items)
        observaties_block = f"""
        <div class="mt-5">
          <h4 class="text-sm font-bold text-navy uppercase tracking-wide">Wat doet deze website goed?</h4>
          <p class="mt-1 text-sm text-gray-500">Met voorbeelden uit de code van de site zelf.</p>
{observaties_html}
        </div>"""

    return f"""      <article class="card reveal p-7 md:p-8" id="{slug_attr}">
        <div class="flex items-start justify-between gap-4">
          <h3 class="text-xl font-extrabold text-navy leading-snug tracking-tight">
            <a href="{html.escape(url, quote=True)}" class="hover:text-brand" rel="noopener" target="_blank">{naam}<span class="sr-only"> (opent in een nieuw tabblad)</span></a>
          </h3>
          {badge}
        </div>
        <p class="mt-1 text-sm text-gray-500">{meta}</p>
{quote}{observaties_block}
        <div class="mt-6 pt-5 border-t border-line flex flex-wrap items-center gap-4" data-hof-vote-block hidden>
          <span class="text-sm font-semibold text-navy" data-hof-count="{slug_attr}"></span>
          <details class="hof-details hof-vote">
            <summary>Stem op deze website</summary>
            <form data-hof-slug="{slug_attr}" class="mt-3" novalidate>
              <div class="hp-field" aria-hidden="true">
                <label>Laat dit veld leeg<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label>
              </div>
              <label for="vote-email-{slug_attr}" class="block text-sm font-semibold text-navy mb-1">Je e-mailadres</label>
              <div class="flex flex-col sm:flex-row gap-2">
                <input type="email" id="vote-email-{slug_attr}" name="email" required autocomplete="email" placeholder="jij@voorbeeld.nl" class="flex-1 border border-field rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand">
                <button type="submit" class="btn btn-primary whitespace-nowrap">Stem</button>
              </div>
              <p class="mt-2 text-xs text-gray-500">Je bevestigt je stem via een link in je mail. Eén stem per adres; we publiceren je adres nooit. Stemmen vanaf het domein van de website zelf tellen niet mee.</p>
              <div role="status" aria-live="polite" tabindex="-1" class="empty:hidden mt-3 text-sm" data-hof-status></div>
            </form>
          </details>
        </div>
      </article>"""


def _list_or_empty(entries):
    if not entries:
        return """
      <div class="card p-10 text-center text-gray-600">
        <p class="text-lg">Er staat nog niemand in de eregalerij.</p>
        <p class="mt-2">Ken jij een website die echt toegankelijk is? Nomineer hem, dan zetten we hem hier in het zonnetje.</p>
        <a href="/nomineren.html" class="btn btn-primary mt-6">Nomineer een website</a>
      </div>"""
    return f"""
      <div class="grid gap-6">
{chr(10).join(_entry_html(i) for i in entries)}
      </div>"""


def _itemlist_jsonld(entries):
    if not entries:
        return ""
    items = []
    for pos, item in enumerate(entries, start=1):
        items.append(
            {
                "@type": "ListItem",
                "position": pos,
                "name": str(item.get("naam", "")).strip(),
                "url": str(item.get("url", "")).strip(),
            }
        )
    obj = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{URL}#lijst",
        "name": "Eregalerij: aantoonbaar toegankelijke websites",
        "inLanguage": "nl-NL",
        "itemListElement": items,
    }
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def render(entries):
    head = shared_head(TITLE, DESCRIPTION, URL, extra_head=_itemlist_jsonld(entries))
    return f"""{head}<body class="bg-white">
{site_header(ACTIVE_PATH)}
  <main id="main" data-hof-endpoint="{HOF_ENDPOINT_BASE}">

    <section>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        <h1 class="text-4xl md:text-5xl font-semibold text-navy leading-[1.08] tracking-tight max-w-3xl">Eregalerij</h1>
        <p class="mt-6 text-lg md:text-xl text-gray-600 max-w-2xl leading-relaxed">Een toegankelijkheidsverklaring zegt niets over hoe toegankelijk een website echt is. In deze hall of fame staan websites die bezoekers als digitaal toegankelijk ervaren en daarom nomineren.</p>
        <div class="mt-8 flex flex-wrap gap-3">
          <a href="/nomineren.html" class="btn btn-primary">Nomineer een website</a>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-12 pb-4">
      <div class="prose max-w-prose">
        <h2>Hoe het werkt</h2>
        <p>Kom je een website tegen die je als digitaal toegankelijk ervaart? Nomineer hem via het formulier. Je bevestigt je nominatie via een link in je mail en daarna plaatsen we de website in de eregalerij.</p>
        <p>Iedereen kan op een vermelding stemmen. Eén stem per e-mailadres, bevestigd via je mail. Stemmen vanaf het domein van de website zelf tellen we niet mee.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-6" aria-label="Opgenomen websites">
      <h2 class="text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-6">In de eregalerij</h2>
{_list_or_empty(entries)}
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-16">
      <div class="rounded-3xl bg-softblue ring-1 ring-brand-light p-8 md:p-10">
        <h2 class="text-2xl font-extrabold text-navy tracking-tight">Ken jij een website die hier hoort?</h2>
        <p class="mt-3 text-navy/70 leading-relaxed max-w-2xl">Nomineer hem. Vertel wat de website goed doet en met welke hulptechnologie je hem gebruikte. Na je bevestiging plaatsen we de nominatie; je e-mailadres gebruiken we alleen voor de bevestiging en publiceren we nooit.</p>
        <a href="/nomineren.html" class="btn btn-primary mt-6">Nomineer een website</a>
      </div>
    </section>

  </main>
{site_footer()}  <script src="/static/halloffame.js"></script>
</body>
</html>
"""


def main():
    if not DATA_FILE.exists():
        sys.exit(f"Geen databestand gevonden: {DATA_FILE}")
    try:
        entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Ongeldige JSON in {DATA_FILE.name}: {exc}")
    if not isinstance(entries, list):
        sys.exit(f"{DATA_FILE.name} moet een JSON-lijst zijn.")

    publishable = _valid_entries(entries)

    # Nieuwste boven; de stabiele sort bewaart de volgorde bij gelijke datum.
    publishable.sort(key=lambda i: _parse_date(i.get("datum")).isoformat(), reverse=True)

    OUT_FILE.write_text(render(publishable), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(publishable)} van {len(entries)} entries)")


if __name__ == "__main__":
    main()
