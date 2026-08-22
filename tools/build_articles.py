#!/usr/bin/env python3
"""
Artikelgenerator voor de EAA Hub (WAT-framework, Layer 3: Tool).

Rendert markdown-artikelen uit content/artikelen/*.md naar server-rendered HTML
in public/artikelen/<slug>.html, bouwt het Kennisbank-overzicht
public/artikelen.html, regenereert public/sitemap.xml en patcht de
artikellijst-regio in public/llms.txt.

Server-rendered HTML is bewust: het is cruciaal voor SEO en GEO (citability door
AI-zoekmachines). Elk artikel krijgt Article JSON-LD mee.

Designrichting: "De Telling" (docs/rebranding/). Tokens staan centraal in tailwind.config.js
(gebouwd naar public/static/tailwind.css via `npm run build:css`) en
public/static/site.css; deze tool emit alleen de gedeelde head/nav/footer en
verwijst naar die bestanden.

Gebruik:
    python tools/build_articles.py            # volledige herbuild uit content/
    python tools/build_articles.py --check    # alleen valideren, niets schrijven

Frontmatter per artikel (YAML):
    ---
    title: "Valt mijn webshop onder de EAA?"
    slug: "valt-mijn-webshop-onder-de-eaa"
    description: "Korte SEO/social-omschrijving."
    date: 2026-06-08
    theme: "scope"        # scope | toezicht | praktijk | mythes
    keywords: [eaa, scope]
    sources:
      - { title: "ACM: ...", url: "https://www.acm.nl/..." }
    ---
"""

import argparse
import html
import json
import re
import sys
from datetime import date as _date
from pathlib import Path

try:
    import yaml
    import markdown as md_lib
except ImportError as exc:  # pragma: no cover
    sys.exit(
        f"Ontbrekende dependency: {exc.name}. "
        "Installeer met: pip install -r requirements.txt"
    )

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "artikelen"
OUT_DIR = ROOT / "public" / "artikelen"
KENNISBANK_FILE = ROOT / "public" / "artikelen.html"
SITEMAP_FILE = ROOT / "public" / "sitemap.xml"
LLMS_FILE = ROOT / "public" / "llms.txt"
LLMS_FULL_FILE = ROOT / "public" / "llms-full.txt"

BASE_URL = "https://eaa-monitor.nl"

# /feedback-route van de bezwaar-Worker (zie worker/src/index.js). Het inline
# feedbackformulier onder elk artikel post hier naartoe. Leeg laten valt terug
# op een mailto in de markup.
FEEDBACK_ENDPOINT = "https://eaa-monitor.nl/api/feedback"

# /newsletter-route van de bezwaar-Worker: nieuwsbrief-opt-in met dubbele
# opt-in. Het footerformulier post hiernaartoe; de Worker mailt een
# bevestigingslink en slaat na bevestiging op in Cloudflare KV.
NEWSLETTER_ENDPOINT = "https://eaa-monitor.nl/api/newsletter"

THEMES = {
    "scope": "Voor wie geldt het",
    "toezicht": "Toezicht & handhaving",
    "praktijk": "In de praktijk",
    "mythes": "Mythes & misverstanden",
}

# Maanden voor Nederlandse datumweergave
NL_MONTHS = [
    "", "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def nl_date(d: _date) -> str:
    return f"{d.day} {NL_MONTHS[d.month]} {d.year}"


# ── Gedeelde HTML-partials (single source of truth voor de hele site) ──────────

# Nav-items: (label, href) voor een gewone link, of (label, [kinderen]) voor een
# dropdown. De Monitor-dropdown bundelt de zeven sectordashboards plus de over-pagina.
NAV_ITEMS = [
    ("Home", "/"),
    ("Monitor", [
        ("E-commerce", "/monitor.html"),
        ("Financiële sector", "/monitor-financieel.html"),
        ("Telecom", "/monitor-telecom.html"),
        ("Personenvervoer", "/monitor-vervoer.html"),
        ("Media & streaming", "/monitor-media.html"),
        ("E-books", "/monitor-ebooks.html"),
        ("Reizen", "/monitor-reizen.html"),
        ("Over de monitor", "/over.html"),
    ]),
    ("Kennisbank", "/artikelen.html"),
    ("Bronnen", "/bronnen.html"),
    ("Vragen", "/vragen.html"),
    ("Tools", "/tools.html"),
    ("Eregalerij", "/eregalerij.html"),
]


def shared_head(title, description, canonical, *, extra_head="", og_type="website", lang="nl"):
    """Gedeelde <head>. depth-onafhankelijk via absolute /static-paden.

    lang zet het taalattribuut en de og:locale, zodat de Engelse pagina's
    dezelfde head kunnen gebruiken zonder een tweede kopie van dit blok.
    """
    locale = "en_GB" if lang == "en" else "nl_NL"
    return f"""<!DOCTYPE html>
<html lang="{lang}" class="utrecht-theme theme-telling">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="canonical" href="{canonical}">

  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">

  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:site_name" content="EAA Monitor">
  <meta property="og:locale" content="{locale}">
  <meta property="og:image" content="{BASE_URL}/static/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)}">
  <meta name="twitter:description" content="{html.escape(description)}">
  <meta name="twitter:image" content="{BASE_URL}/static/og.png">

  <link rel="preload" href="/static/fonts/fraunces-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/static/fonts/atkinson-hyperlegible-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/static/fonts.css">
  <link rel="stylesheet" href="/static/tailwind.css">
  <link rel="stylesheet" href="/static/utrecht-tokens.css">
  <link rel="stylesheet" href="/static/utrecht.css">
  <link rel="stylesheet" href="/static/utrecht-theme.css">
  <link rel="stylesheet" href="/static/site.css">

  <!-- Privacy-friendly analytics by Plausible -->
  <script async src="https://plausible.io/js/pa-oCJ6R9bzu6l8fcjrJ8_xA.js"></script>
  <script>
    window.plausible=window.plausible||function(){{(plausible.q=plausible.q||[]).push(arguments)}},plausible.init=plausible.init||function(i){{plausible.o=i||{{}}}};
    plausible.init()
  </script>
{extra_head}</head>
"""


# Woordmerk + telbalk-beeldmerk, inline zodat het woordmerk de Fraunces-webfont
# gebruikt (een externe <img> kan niet bij de pagina-fonts). Bestandsversies
# met title/desc staan in public/static/logo.svg en logo-donker.svg.
def _logo_svg(tekstkleur, puntkleur, css_class):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 432 96" class="{css_class}" '
        f'role="img" aria-label="EAA Monitor" color="{tekstkleur}">'
        '<g><rect x="6" y="16" width="64" height="64" rx="14" fill="#0D2B1F" stroke="#FAF7F1" stroke-width="2"/>'
        '<rect x="20" y="32" width="36" height="7" rx="3.5" fill="#FAF7F1"/>'
        '<rect x="20" y="45" width="36" height="7" rx="3.5" fill="#FAF7F1"/>'
        '<rect x="20" y="58" width="36" height="7" rx="3.5" fill="#FAF7F1" opacity="0.25"/>'
        '<rect x="20" y="58" width="15" height="7" rx="3.5" fill="#F4C84B"/></g>'
        '<text x="90" y="62" font-family="\'Fraunces Variable\', Georgia, \'Times New Roman\', serif" '
        'font-size="40" letter-spacing="-0.5" fill="currentColor">'
        '<tspan font-weight="600">EAA</tspan><tspan dx="10">Monitor</tspan>'
        f'<tspan fill="{puntkleur}" font-weight="600">.</tspan></text></svg>'
    )


LOGO_LICHT = _logo_svg("#20281F", "#1A5632", "h-9 w-auto")
LOGO_DONKER = _logo_svg("#FAF7F1", "#F4C84B", "h-9 w-auto")


def site_header(active_path):
    """Sticky responsieve header: nav op lg+, hamburger op tablet/mobiel.
    active_path = huidige nav-pad (of "" als de pagina niet in de nav staat)."""
    chevron = (
        '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="6 9 12 15 18 9"></polyline></svg>'
    )
    desktop, mobile = [], []
    for label, target in NAV_ITEMS:
        if isinstance(target, list):
            group_active = any(href == active_path for _, href in target)
            pcls = "text-brand" if group_active else "text-navy hover:text-brand"
            d_children, m_children = [], []
            for clabel, chref in target:
                cactive = chref == active_path
                ccur = ' aria-current="page"' if cactive else ""
                ccls = "text-brand" if cactive else "text-navy hover:text-brand"
                d_children.append(
                    f'<a href="{chref}" class="block px-4 py-2 text-sm font-semibold {ccls} hover:bg-softblue transition-colors"{ccur}>{clabel}</a>'
                )
                m_children.append(
                    f'<a href="{chref}" class="block py-2.5 text-base font-semibold {ccls}"{ccur}>{clabel}</a>'
                )
            d_children_html = "\n              ".join(d_children)
            m_children_html = "\n            ".join(m_children)
            desktop.append(
                f'''<div class="relative" data-dropdown>
            <button type="button" data-dropdown-toggle class="text-sm font-semibold {pcls} transition-colors inline-flex items-center gap-1" aria-expanded="false" aria-haspopup="true">{label}{chevron}</button>
            <div data-dropdown-menu class="hidden absolute left-0 top-full pt-2 z-50">
              <div class="min-w-[12rem] bg-white rounded-xl shadow-lg ring-1 ring-line py-2">
              {d_children_html}
              </div>
            </div>
          </div>'''
            )
            mobile.append(
                f'''<div data-dropdown>
          <button type="button" data-dropdown-toggle class="w-full flex items-center justify-between py-2.5 text-base font-semibold {pcls}" aria-expanded="false">{label}{chevron}</button>
          <div data-dropdown-menu class="hidden pl-4 ml-1 border-l border-line">
            {m_children_html}
          </div>
        </div>'''
            )
        else:
            href = target
            is_active = href == active_path
            cur = ' aria-current="page"' if is_active else ""
            cls = "text-brand" if is_active else "text-navy hover:text-brand"
            desktop.append(
                f'<a href="{href}" class="text-sm font-semibold {cls} transition-colors"{cur}>{label}</a>'
            )
            mobile.append(
                f'<a href="{href}" class="block py-2.5 text-base font-semibold {cls}"{cur}>{label}</a>'
            )
    desktop_html = "\n          ".join(desktop)
    mobile_html = "\n        ".join(mobile)
    return f"""  <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:bg-oker focus:text-inkt focus:font-bold focus:px-4 focus:py-2 focus:rounded-lg focus:z-50">Ga naar hoofdinhoud</a>

  <header class="sticky top-0 z-40 bg-papier/90 backdrop-blur">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <a href="/" class="flex items-center">
        {LOGO_LICHT}
      </a>
      <nav aria-label="Hoofdnavigatie" class="hidden lg:flex items-center gap-7">
          {desktop_html}
      </nav>
      <button type="button" id="nav-toggle" class="lg:hidden inline-flex items-center justify-center w-10 h-10 -mr-2 rounded-lg text-navy hover:bg-zachtgroen focus:outline-none focus:ring-2 focus:ring-brand" aria-expanded="false" aria-controls="mobile-nav" aria-label="Menu openen">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
    </div>
    <nav id="mobile-nav" aria-label="Hoofdnavigatie (mobiel)" class="lg:hidden hidden border-t border-line px-4 sm:px-6 py-2">
        {mobile_html}
    </nav>
    <div class="h-[3px] bg-oker" aria-hidden="true"></div>
  </header>
"""


def site_footer():
    return f"""  <footer class="bg-navy text-white mt-24 on-dark">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-14">
      <div class="mb-10 pb-10 border-b border-white/10 grid gap-6 md:grid-cols-2 md:items-center">
        <div>
          <p class="font-display font-semibold text-xl tracking-tight">De maandagmeting in je inbox</p>
          <p class="mt-2 text-sm text-white max-w-sm leading-relaxed">Af en toe een update: nieuwe cijfers, antwoorden van toezichthouders en praktische uitleg. Geen spam, geen verkooppraatjes.</p>
        </div>
        <form id="newsletter-form" data-endpoint="{NEWSLETTER_ENDPOINT}" novalidate>
          <div class="hidden" aria-hidden="true">
            <label>Laat dit veld leeg<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label>
          </div>
          <label for="newsletter-email" class="block text-sm font-semibold text-white mb-1.5">Je e-mailadres</label>
          <div class="flex flex-col sm:flex-row gap-2">
            <input type="email" id="newsletter-email" name="email" required autocomplete="email" placeholder="jij@voorbeeld.nl" class="utrecht-textbox flex-1">
            <button type="submit" id="newsletter-submit" class="utrecht-button utrecht-button--primary-action whitespace-nowrap">Houd me op de hoogte</button>
          </div>
          <p class="mt-2 text-xs text-white">We gebruiken je adres alleen voor deze nieuwsbrief. Afmelden kan met één klik, op elk moment.</p>
          <div id="newsletter-status" role="status" aria-live="polite" tabindex="-1" class="empty:hidden mt-3 text-sm"></div>
        </form>
      </div>
      <div class="grid gap-10 md:grid-cols-4">
        <div class="md:col-span-2">
          {LOGO_DONKER}
          <p class="mt-4 text-sm text-white max-w-sm leading-relaxed">EAA Monitor is de onafhankelijke telling van digitaal toegankelijk Nederland: elke maandag een verse meting in zes sectoren, plus uitleg in gewone taal over wie de wet raakt, wie toezicht houdt en wat werkt. <span class="text-brand-bright font-semibold">Gemeten, niet beweerd.</span></p>
        </div>
        <div>
          <p class="text-sm font-semibold text-white mb-3">Monitor &amp; uitleg</p>
          <ul class="space-y-2 text-sm text-white">
            <li><a href="/monitor.html" class="hover:text-white">Webshopmonitor</a></li>
            <li><a href="/monitor-financieel.html" class="hover:text-white">Financiële monitor</a></li>
            <li><a href="/monitor-telecom.html" class="hover:text-white">Telecommonitor</a></li>
            <li><a href="/monitor-vervoer.html" class="hover:text-white">Vervoermonitor</a></li>
            <li><a href="/monitor-media.html" class="hover:text-white">Mediamonitor</a></li>
            <li><a href="/monitor-ebooks.html" class="hover:text-white">E-booksmonitor</a></li>
            <li><a href="/monitor-reizen.html" class="hover:text-white">Reismonitor</a></li>
            <li><a href="/artikelen.html" class="hover:text-white">Kennisbank</a></li>
            <li><a href="/bronnen.html" class="hover:text-white">Bronnen</a></li>
            <li><a href="/tools.html" class="hover:text-white">Tools</a></li>
          </ul>
        </div>
        <div>
          <p class="text-sm font-semibold text-white mb-3">Meedoen &amp; info</p>
          <ul class="space-y-2 text-sm text-white">
            <li><a href="/vragen.html" class="hover:text-white">Vragen uit de praktijk</a></li>
            <li><a href="/eregalerij.html" class="hover:text-white">Eregalerij</a></li>
            <li><a href="/nomineren.html" class="hover:text-white">Nomineer een website</a></li>
            <li><a href="/over.html" class="hover:text-white">Over dit dashboard</a></li>
            <li><a href="/bezwaren.html" class="hover:text-white">Ingediende bezwaren</a></li>
            <li><a href="/bezwaar.html" class="hover:text-white">Bezwaar maken</a></li>
          </ul>
        </div>
      </div>
      <div class="mt-12 pt-8 border-t border-white/10 grid gap-8 md:grid-cols-2 text-xs text-white leading-relaxed">
        <div>
          <p class="font-semibold mb-2">Europese infrastructuur</p>
          <p class="max-w-md">Deze website draait volledig op Europese diensten. De servers staan bij Hetzner in Duitsland, het domein loopt via SIDN in Nederland, de bezoekersstatistieken komen van Plausible in Europa en e-mail versturen we met AhaSend uit Nederland. Je bezoek raakt geen Amerikaanse dienst.</p>
        </div>
        <div>
          <p class="font-semibold mb-2">Goed om te weten</p>
          <p class="max-w-md">De controle vindt wekelijks plaats. Een link naar een verklaring betekent niet automatisch dat een website ook daadwerkelijk toegankelijk is.</p>
        </div>
      </div>
      <div class="mt-10 pt-6 border-t border-white/10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs text-white">
        <p>Vragen of een correctie? Mail <a href="mailto:info@eaa-monitor.nl" class="font-semibold underline underline-offset-2 hover:text-white">info@eaa-monitor.nl</a></p>
        <nav aria-label="Juridisch" class="flex flex-wrap gap-x-5 gap-y-1">
          <a href="/colofon.html" class="hover:text-white">Colofon</a>
          <a href="/privacy.html" class="hover:text-white">Privacy</a>
          <a href="/over.html" class="hover:text-white">Over de monitor</a>
        </nav>
      </div>
    </div>
    <script src="/static/newsletter.js"></script>
  </footer>

  <script src="/static/nav.js"></script>
  <script src="/static/reveal.js"></script>
  <script src="/static/feedback-widget.js"></script>
"""


# ── Markdown ──────────────────────────────────────────────────────────────────

def parse_article(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not m:
        raise ValueError(f"{path.name}: ontbrekende of ongeldige frontmatter")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2)

    for key in ("title", "slug", "description", "date", "theme"):
        if key not in meta:
            raise ValueError(f"{path.name}: frontmatter mist '{key}'")
    if meta["theme"] not in THEMES:
        raise ValueError(
            f"{path.name}: onbekend thema '{meta['theme']}' "
            f"(kies uit: {', '.join(THEMES)})"
        )

    md = md_lib.Markdown(
        extensions=["extra", "attr_list", "sane_lists", "toc"],
        output_format="html5",
    )
    meta["body_html"] = md.convert(body_md)
    meta["_path"] = path
    if isinstance(meta["date"], str):
        meta["date"] = _date.fromisoformat(meta["date"])
    if meta.get("updated") and isinstance(meta["updated"], str):
        meta["updated"] = _date.fromisoformat(meta["updated"])
    return meta


ORG_ID = f"{BASE_URL}/#organization"


def article_jsonld(meta: dict, url: str) -> str:
    """Article + BreadcrumbList JSON-LD. Auteur en uitgever verwijzen via @id
    naar de Organization-node op de homepage (één entiteit, één keer beschreven).
    dateModified komt uit het optionele frontmatter-veld 'updated'."""
    modified = meta.get("updated") or meta["date"]
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "image": f"{BASE_URL}/static/og.png",
        "datePublished": meta["date"].isoformat(),
        "dateModified": modified.isoformat(),
        "inLanguage": "nl-NL",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@id": ORG_ID},
        "publisher": {"@id": ORG_ID},
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": ["h1", ".article-answer"],
        },
    }
    if meta.get("keywords"):
        article["keywords"] = ", ".join(meta["keywords"])
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Kennisbank", "item": f"{BASE_URL}/artikelen.html"},
            {"@type": "ListItem", "position": 3, "name": meta["title"], "item": url},
        ],
    }
    out = []
    for obj in (article, breadcrumb):
        out.append(
            '  <script type="application/ld+json">\n  '
            + json.dumps(obj, ensure_ascii=False, indent=2)
            + "\n  </script>\n"
        )
    return "".join(out)


def sources_block(meta: dict) -> str:
    sources = meta.get("sources") or []
    if not sources:
        return ""
    items = "\n".join(
        f'        <li><a href="{html.escape(s["url"])}" class="link" rel="nofollow">{html.escape(s["title"])}</a></li>'
        for s in sources
    )
    return f"""
      <aside class="mt-14 pt-8 border-t border-line" aria-labelledby="bronnen">
        <h2 id="bronnen" class="text-lg font-bold text-navy mb-3">Bronnen</h2>
        <ul class="space-y-2 text-sm">
{items}
        </ul>
      </aside>"""


DISCLAIMER_TEXT = (
    "Deze kennisbank is samengesteld uit openbare bronnen: publicaties van "
    "toezichthouders, nieuwsberichten en vakartikelen. We houden de uitleg zo "
    "actueel en accuraat mogelijk, maar de EAA is volop in beweging en je kunt "
    "aan deze teksten geen rechten ontlenen. Het is algemene uitleg, geen "
    "juridisch advies."
)


def feedback_block(meta: dict) -> str:
    """Bron-disclaimer plus inline feedbackformulier onder elk artikel.

    Het formulier post naar de /feedback-route van de bezwaar-Worker, die de
    opmerking naar Julia mailt. Geen e-mailadres in de pagina; geen opslag."""
    slug = meta["slug"]
    title = meta["title"]
    url = f"{BASE_URL}/artikelen/{slug}.html"
    return f"""
      <section class="mt-14 pt-10 border-t border-line" aria-labelledby="feedback-titel">
        <p class="text-sm text-gray-500 leading-relaxed">{DISCLAIMER_TEXT}</p>

        <div class="mt-8 rounded-2xl bg-white ring-1 ring-line p-6 md:p-8">
          <h2 id="feedback-titel" class="text-xl font-extrabold text-navy tracking-tight">Klopt er iets niet?</h2>
          <p class="mt-2 text-sm text-gray-600 leading-relaxed">Zie je een fout, een verouderd cijfer of mist er een bron? Laat het ons weten, dan kijken we ernaar.</p>

          <div id="feedback-status" tabindex="-1" class="empty:hidden"></div>

          <form id="feedback-form" class="mt-5 space-y-4" novalidate>
            <input type="hidden" name="artikel_titel" value="{html.escape(title)}">
            <input type="hidden" name="artikel_slug" value="{html.escape(slug)}">
            <input type="hidden" name="artikel_url" value="{html.escape(url)}">
            <div class="hidden" aria-hidden="true">
              <label>Laat dit veld leeg<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label>
            </div>

            <div class="utrecht-form-field">
              <label for="feedback-bericht" class="utrecht-form-label">Wat klopt er niet?</label>
              <textarea id="feedback-bericht" name="bericht" rows="4" required class="utrecht-textarea w-full" placeholder="Beschrijf kort wat er niet klopt. Heb je een bron? Plak die er gerust bij."></textarea>
            </div>

            <div class="utrecht-form-field">
              <label for="feedback-email" class="utrecht-form-label">E-mailadres <span class="font-normal text-gray-500">(optioneel, alleen als je een reactie wilt)</span></label>
              <input type="email" id="feedback-email" name="email" autocomplete="email" class="utrecht-textbox w-full" placeholder="jij@voorbeeld.nl">
            </div>

            <button type="submit" id="feedback-submit" class="utrecht-button utrecht-button--primary-action">Versturen</button>
          </form>
        </div>
      </section>"""


def feedback_script() -> str:
    """Inline submit-handler voor het feedbackformulier (per artikel)."""
    return f"""  <script>
    (function () {{
      "use strict";
      const FEEDBACK_ENDPOINT = "{FEEDBACK_ENDPOINT}";
      const form = document.getElementById("feedback-form");
      if (!form) return;
      const statusEl = document.getElementById("feedback-status");
      const submitBtn = document.getElementById("feedback-submit");

      function showStatus(type, html) {{
        statusEl.className = (type === "success" ? "notice notice-info" : "notice notice-warning") + " mt-4";
        statusEl.innerHTML = html;
        statusEl.focus();
      }}

      form.addEventListener("submit", async function (e) {{
        e.preventDefault();
        if (!form.checkValidity()) {{ form.reportValidity(); return; }}

        submitBtn.disabled = true;
        submitBtn.textContent = "Bezig met versturen...";

        try {{
          const response = await fetch(FEEDBACK_ENDPOINT, {{
            method: "POST",
            body: new FormData(form),
            headers: {{ Accept: "application/json" }},
          }});
          if (response.ok) {{
            form.classList.add("hidden");
            showStatus("success", "<strong>Bedankt voor je feedback.</strong> We bekijken je opmerking en passen het artikel aan als dat nodig is.");
          }} else {{
            const data = await response.json().catch(() => ({{}}));
            showStatus("error", (data && data.error) || "Er ging iets mis bij het versturen. Probeer het later opnieuw of mail naar info@eaa-monitor.nl.");
            submitBtn.disabled = false;
            submitBtn.textContent = "Versturen";
          }}
        }} catch (err) {{
          showStatus("error", "Er ging iets mis bij het versturen. Controleer je internetverbinding en probeer het opnieuw, of mail naar info@eaa-monitor.nl.");
          submitBtn.disabled = false;
          submitBtn.textContent = "Versturen";
        }}
      }});
    }})();
  </script>
"""


def render_article(meta: dict) -> str:
    slug = meta["slug"]
    url = f"{BASE_URL}/artikelen/{slug}.html"
    theme_label = THEMES[meta["theme"]]
    extra_head = article_jsonld(meta, url)

    head = shared_head(
        f'{meta["title"]} — EAA Monitor',
        meta["description"],
        url,
        extra_head=extra_head,
        og_type="article",
    )

    # Samenvattend antwoord direct onder de H1: het eerste wat een lezer (en een
    # AI-zoekmachine) ziet, los citeerbaar. Optioneel via frontmatter 'answer'.
    answer_html = ""
    if meta.get("answer"):
        answer_html = (
            '\n        <p class="article-answer mt-5 text-lg text-inkt leading-relaxed '
            'border-l-4 border-brand bg-softblue rounded-r-xl px-5 py-4">'
            f'{html.escape(meta["answer"])}</p>'
        )

    datum_html = f"Gepubliceerd op {nl_date(meta['date'])}"
    if meta.get("updated") and meta["updated"] != meta["date"]:
        datum_html += f" · bijgewerkt op {nl_date(meta['updated'])}"

    return f"""{head}<body class="bg-white">
{site_header("/artikelen.html")}
  <main id="main">

    <div>
      <div class="max-w-prose mx-auto px-4 sm:px-6 pt-14 pb-4">
        <a href="/artikelen.html" class="text-sm font-semibold text-brand">&larr; Kennisbank</a>
        <p class="mt-6"><span class="chip-toezicht">{html.escape(theme_label)}</span></p>
        <h1 class="mt-4 text-3xl md:text-5xl font-semibold text-navy leading-tight tracking-tight">{html.escape(meta["title"])}</h1>
        <p class="mt-4 text-lg text-gray-600 leading-relaxed">{html.escape(meta["description"])}</p>{answer_html}
        <p class="mt-6 font-mono text-xs font-medium uppercase tracking-[0.08em] text-gray-600">{datum_html}</p>
      </div>
    </div>

    <article class="max-w-prose mx-auto px-4 sm:px-6 py-14">
      <div class="prose">
{meta["body_html"]}
      </div>
{sources_block(meta)}

      <div class="mt-14 rounded-xl bg-softblue ring-1 ring-brand-light p-8 md:p-10">
        <h2 class="text-2xl font-semibold text-navy tracking-tight">Wil je weten waar je staat?</h2>
        <p class="mt-3 text-navy leading-relaxed">De monitor meet wekelijks of organisaties in zes sectoren een toegankelijkheidsverklaring publiceren. Zoek je eigen organisatie op, of lees verder in de kennisbank.</p>
        <div class="mt-6 flex flex-wrap gap-3">
          <a href="/monitor.html" class="utrecht-button utrecht-button--primary-action">Zoek je organisatie in de monitor</a>
          <a href="/artikelen.html" class="utrecht-button utrecht-button--secondary-action">Naar de kennisbank</a>
        </div>
      </div>
{feedback_block(meta)}
    </article>

  </main>
{site_footer()}{feedback_script()}</body>
</html>
"""


def render_kennisbank(articles: list) -> str:
    url = f"{BASE_URL}/artikelen.html"
    head = shared_head(
        "Kennisbank — alles over de EAA — EAA Monitor",
        "Heldere uitleg over de European Accessibility Act: voor wie de wet geldt, "
        "wie toezicht houdt, de boetes, en wat wel en niet werkt.",
        url,
    )

    cards = []
    for meta in articles:
        slug = meta["slug"]
        theme_label = THEMES[meta["theme"]]
        cards.append(f"""        <a href="/artikelen/{slug}.html" class="card card-hover reveal p-7 flex flex-col">
          <span class="text-xs font-bold uppercase tracking-wider text-brand">{html.escape(theme_label)}</span>
          <h2 class="mt-3 text-xl font-extrabold text-navy leading-snug tracking-tight">{html.escape(meta["title"])}</h2>
          <p class="mt-3 text-sm text-gray-600 leading-relaxed flex-1">{html.escape(meta["description"])}</p>
          <span class="mt-5 text-sm font-semibold text-brand">Lees verder &rarr;</span>
        </a>""")
    cards_html = "\n".join(cards)

    return f"""{head}<body class="bg-white">
{site_header("/artikelen.html")}
  <main id="main">

    <div>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-10">
        <p class="eyebrow text-brand">Kennisbank</p>
        <h1 class="mt-3 text-4xl md:text-5xl font-semibold text-navy leading-[1.08] tracking-tight max-w-3xl">Alles over de<br>European Accessibility Act</h1>
        <p class="mt-6 text-lg md:text-xl text-gray-600 max-w-2xl leading-relaxed">Heldere uitleg zonder paniek of jargon. Voor wie de wet geldt, wie toezicht houdt, wat de boetes zijn en wat echt werkt.</p>
      </div>
    </div>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 -mt-10 relative z-10 pb-10">
      <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
{cards_html}
      </div>
      <div class="mt-10 card p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 bg-softblue">
        <div class="flex-1">
          <h2 class="text-lg font-extrabold text-navy tracking-tight">Op zoek naar de oorspronkelijke bronnen?</h2>
          <p class="mt-1.5 text-sm text-gray-600 leading-relaxed">Bekijk ons doorzoekbare overzicht van artikelen en publicaties over de EAA, van toezichthouders en overheid tot juristen, bureaus en vakmedia.</p>
        </div>
        <a href="/bronnen.html" class="utrecht-button utrecht-button--primary-action whitespace-nowrap self-start sm:self-auto">Naar de bronnen</a>
      </div>
      <p class="mt-10 text-sm text-gray-500 leading-relaxed max-w-2xl">Deze kennisbank is samengesteld uit openbare bronnen: publicaties van toezichthouders, nieuwsberichten en vakartikelen. Het is algemene uitleg, geen juridisch advies. Zie je een fout? Onderaan elk artikel kun je het ons laten weten.</p>
    </section>

  </main>
{site_footer()}</body>
</html>
"""


# ── Losse pagina's (colofon, privacy) ───────────────────────────────────────────

def render_simple_page(title: str, description: str, slug: str, body_html: str) -> str:
    """Eenvoudige inhoudspagina die head/header/footer deelt met de rest van de
    site. Gebruikt voor colofon en privacy, zodat die automatisch het NLDS-
    fundament, de actuele navigatie en de footer met contact erven."""
    url = f"{BASE_URL}/{slug}.html"
    head = shared_head(f"{title} — EAA Monitor", description, url)
    return f"""{head}<body class="bg-papier">
{site_header("")}
  <main id="main">
    <section>
      <div class="max-w-prose mx-auto px-4 sm:px-6 pt-14 pb-4">
        <h1 class="mt-3 text-3xl md:text-5xl font-semibold text-navy tracking-tight">{html.escape(title)}</h1>
      </div>
    </section>
    <article class="max-w-prose mx-auto px-4 sm:px-6 py-10 prose">
{body_html}
    </article>
  </main>
{site_footer()}</body>
</html>
"""


COLOFON_BODY = """      <p>De EAA Monitor is de onafhankelijke telling van digitaal toegankelijk Nederland. De site brengt alle praktische informatie over de European Accessibility Act samen: wekelijkse metingen in zes sectoren, uitleg in gewone taal, antwoorden van toezichthouders en een doorzoekbaar bronnenoverzicht.</p>

      <h2>Wie maakt de EAA Monitor?</h2>
      <p>De monitor wordt samengesteld en onderhouden door een klein team met jarenlange ervaring in digitale toegankelijkheid. We noemen geen namen, maar je kunt ons altijd bereiken. Hoe we meten en wat we wel en niet beweren, lees je op de pagina <a href="/over.html">over de monitor</a>.</p>

      <h2>Gebruik van de data</h2>
      <p>De meetcijfers en de onderliggende data zijn vrij te gebruiken onder de licentie Creative Commons Naamsvermelding 4.0 (CC BY 4.0). Verwijs bij gebruik naar de EAA Monitor met een link. De ruwe meetresultaten staan als open JSON op de site.</p>

      <h2>Techniek</h2>
      <p>De website draait volledig op Europese diensten: de servers staan bij Hetzner in Duitsland, het domein loopt via SIDN in Nederland, de bezoekersstatistieken komen van Plausible in Europa en e-mail versturen we met AhaSend uit Nederland. We gebruiken geen Amerikaanse diensten en geen volgcookies.</p>

      <h2>Contact</h2>
      <p>Vragen, een correctie of een tip? Mail <a href="mailto:info@eaa-monitor.nl">info@eaa-monitor.nl</a>. Hoe we omgaan met je gegevens lees je in de <a href="/privacy.html">privacyverklaring</a>.</p>"""


PRIVACY_BODY = """      <p>De EAA Monitor verzamelt zo min mogelijk gegevens. Op deze pagina lees je wat we wel en niet bewaren, en welke rechten je hebt.</p>

      <h2>Bezoekersstatistieken</h2>
      <p>We meten bezoek met Plausible, een privacyvriendelijke dienst in Europa. Plausible gebruikt geen cookies en verzamelt geen persoonsgegevens waarmee we je kunnen herkennen. We zien alleen geanonimiseerde aantallen, zoals welke pagina's bezocht worden.</p>

      <h2>Nieuwsbrief</h2>
      <p>Schrijf je je in voor de nieuwsbrief, dan vragen we je e-mailadres. We sturen je eerst een bevestigingsmail; pas als je daarop klikt, slaan we je adres op. We gebruiken het alleen voor de nieuwsbrief. Afmelden kan met één klik in elke mail, op elk moment. Je adres wordt versleuteld opgeslagen bij onze Europese diensten en niet gedeeld met anderen.</p>

      <h2>Formulieren</h2>
      <p>Stuur je een bezwaar, een vraag, een nominatie of feedback via een formulier, dan komt dat als e-mail bij ons binnen. We bewaren die berichten niet in een database en delen ze niet met anderen. Een e-mailadres in een formulier is altijd optioneel, behalve waar we het nodig hebben om je een bevestiging te sturen.</p>

      <h2>Stemmen in de eregalerij</h2>
      <p>Stem je op een website in de eregalerij, dan slaan we een versleutelde (gehashte) versie van je e-mailadres op. Zo voorkomen we dubbele stemmen, zonder je echte adres te bewaren.</p>

      <h2>Geen volgcookies</h2>
      <p>We plaatsen geen volgcookies en gebruiken geen advertentienetwerken. Je bezoek raakt geen Amerikaanse dienst.</p>

      <h2>Je rechten</h2>
      <p>Je hebt recht op inzage, correctie en verwijdering van je gegevens. Wil je weten wat we van je hebben, of wil je dat we iets verwijderen? Mail <a href="mailto:info@eaa-monitor.nl">info@eaa-monitor.nl</a>, dan regelen we dat.</p>"""


# ── Sitemap & llms.txt ─────────────────────────────────────────────────────────

DATA_DIR = ROOT / "data"


def _results_lastmod(filename: str):
    """Best-effort: lees de scrape-datum (YYYY-MM-DD) uit een results-bestand.
    Geeft None als het bestand ontbreekt of geen geldige datum heeft."""
    f = DATA_DIR / filename
    try:
        with open(f, encoding="utf-8") as fh:
            stamp = json.load(fh).get("last_updated")
        return stamp[:10] if stamp else None
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        return None


def write_sitemap(articles: list):
    # lastmod: voor home/monitorpagina's de scrape-datum uit het results-bestand;
    # voor de kennisbank de datum van het nieuwste artikel. lastmod is het enige
    # sitemapveld dat zoekmachines echt gebruiken voor recrawl-prioriteit, dus
    # juist bij wekelijks verversende cijfers waardevol.
    newest_article = (
        max(articles, key=lambda m: m["date"])["date"].isoformat() if articles else None
    )
    # Tweetalige paginaparen (NL-pad, EN-pad). Beide leden krijgen xhtml:link
    # alternates in de sitemap zodat zoekmachines de EN-variant koppelen.
    bilingual_pairs = [
        ("/", "/en/"),
        ("/monitor.html", "/en/monitor.html"),
        ("/monitor-financieel.html", "/en/monitor-financieel.html"),
        ("/monitor-telecom.html", "/en/monitor-telecom.html"),
        ("/monitor-vervoer.html", "/en/monitor-vervoer.html"),
        ("/monitor-media.html", "/en/monitor-media.html"),
        ("/monitor-ebooks.html", "/en/monitor-ebooks.html"),
        ("/monitor-reizen.html", "/en/monitor-reizen.html"),
    ]
    # loc -> lijst xhtml:link-regels (nl, en, x-default), voor beide leden.
    alt_map: dict = {}
    for nl_path, en_path in bilingual_pairs:
        links = (
            f'    <xhtml:link rel="alternate" hreflang="nl" href="{BASE_URL}{nl_path}"/>\n'
            f'    <xhtml:link rel="alternate" hreflang="en" href="{BASE_URL}{en_path}"/>\n'
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}{nl_path}"/>\n'
        )
        alt_map[f"{BASE_URL}{nl_path}"] = links
        alt_map[f"{BASE_URL}{en_path}"] = links

    # (loc, changefreq, priority, lastmod)
    static_urls = [
        (f"{BASE_URL}/", "weekly", "1.0", _results_lastmod("results.json")),
        (f"{BASE_URL}/monitor.html", "weekly", "0.9", _results_lastmod("results.json")),
        (f"{BASE_URL}/monitor-financieel.html", "weekly", "0.9", _results_lastmod("results-financieel.json")),
        (f"{BASE_URL}/monitor-telecom.html", "weekly", "0.9", _results_lastmod("results-telecom.json")),
        (f"{BASE_URL}/monitor-vervoer.html", "weekly", "0.9", _results_lastmod("results-vervoer.json")),
        (f"{BASE_URL}/monitor-media.html", "weekly", "0.9", _results_lastmod("results-media.json")),
        (f"{BASE_URL}/monitor-ebooks.html", "weekly", "0.9", _results_lastmod("results-ebooks.json")),
        (f"{BASE_URL}/monitor-reizen.html", "weekly", "0.9", _results_lastmod("results-reizen.json")),
        # Engelse tegenhangers (monitor + hub); zelfde meetdata via dezelfde JSON.
        (f"{BASE_URL}/en/", "weekly", "0.9", _results_lastmod("results.json")),
        (f"{BASE_URL}/en/monitor.html", "weekly", "0.8", _results_lastmod("results.json")),
        (f"{BASE_URL}/en/monitor-financieel.html", "weekly", "0.8", _results_lastmod("results-financieel.json")),
        (f"{BASE_URL}/en/monitor-telecom.html", "weekly", "0.8", _results_lastmod("results-telecom.json")),
        (f"{BASE_URL}/en/monitor-vervoer.html", "weekly", "0.8", _results_lastmod("results-vervoer.json")),
        (f"{BASE_URL}/en/monitor-media.html", "weekly", "0.8", _results_lastmod("results-media.json")),
        (f"{BASE_URL}/en/monitor-ebooks.html", "weekly", "0.8", _results_lastmod("results-ebooks.json")),
        (f"{BASE_URL}/en/monitor-reizen.html", "weekly", "0.8", _results_lastmod("results-reizen.json")),
        (f"{BASE_URL}/artikelen.html", "weekly", "0.8", newest_article),
        (f"{BASE_URL}/bronnen.html", "weekly", "0.7", None),
        (f"{BASE_URL}/vragen.html", "weekly", "0.7", None),
        (f"{BASE_URL}/tools.html", "monthly", "0.7", None),
        (f"{BASE_URL}/wcag-audit.html", "monthly", "0.5", None),
        (f"{BASE_URL}/vraag-stellen.html", "monthly", "0.6", None),
        (f"{BASE_URL}/melden.html", "monthly", "0.5", None),
        (f"{BASE_URL}/eregalerij.html", "weekly", "0.7", None),
        (f"{BASE_URL}/nomineren.html", "monthly", "0.6", None),
        (f"{BASE_URL}/over.html", "monthly", "0.5", None),
        (f"{BASE_URL}/colofon.html", "yearly", "0.3", None),
        (f"{BASE_URL}/privacy.html", "yearly", "0.3", None),
        (f"{BASE_URL}/bezwaren.html", "weekly", "0.4", None),
        (f"{BASE_URL}/bezwaar.html", "monthly", "0.4", None),
        (f"{BASE_URL}/vierogen-pact.html", "monthly", "0.4", None),
    ]
    # De volledige meetlijsten (public/lijst/) worden in de deploy gebouwd en
    # staan niet in git. De URL's komen uit dezelfde configuratie als die
    # generator, zodat de sitemap nooit naar een letterpagina wijst die er niet is.
    try:
        from build_lijsten import lijst_urls  # noqa: PLC0415

        for pad, lastmod_lijst in lijst_urls():
            static_urls.append((f"{BASE_URL}{pad}", "weekly", "0.6", lastmod_lijst))
    except Exception as exc:  # pragma: no cover
        print(f"Waarschuwing: lijstpagina's niet in de sitemap ({exc})")

    # Engelse kennisbank: aparte artikelen, geen vertaling, dus geen
    # hreflang-koppeling met een Nederlands artikel.
    try:
        from build_articles_en import en_urls  # noqa: PLC0415

        for pad, lastmod_en in en_urls():
            static_urls.append((f"{BASE_URL}{pad}", "monthly", "0.7", lastmod_en))
    except Exception as exc:  # pragma: no cover
        print(f"Waarschuwing: Engelse artikelen niet in de sitemap ({exc})")

    rows = []
    for loc, freq, prio, lastmod in static_urls:
        lastmod_xml = f"<lastmod>{lastmod}</lastmod>\n    " if lastmod else ""
        alt_xml = alt_map.get(loc, "")
        rows.append(
            f"  <url>\n    <loc>{loc}</loc>\n    "
            f"{lastmod_xml}<changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n{alt_xml}  </url>"
        )
    for meta in articles:
        loc = f"{BASE_URL}/artikelen/{meta['slug']}.html"
        lastmod = (meta.get("updated") or meta["date"]).isoformat()
        rows.append(
            f"  <url>\n    <loc>{loc}</loc>\n    "
            f"<lastmod>{lastmod}</lastmod>\n    "
            f"<changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    SITEMAP_FILE.write_text(xml, encoding="utf-8")
    print(f"Geschreven: {SITEMAP_FILE.relative_to(ROOT)} ({len(static_urls) + len(articles)} urls)")


LLMS_START = "<!-- ARTICLES:START -->"
LLMS_END = "<!-- ARTICLES:END -->"


def patch_llms_articles(articles: list):
    """Patcht alleen de artikellijst-regio in llms.txt (scraper bezit de rest)."""
    if not LLMS_FILE.exists():
        print(f"Overslaan llms.txt: {LLMS_FILE} bestaat niet")
        return
    lines = ["## Artikelen (Kennisbank)"]
    for meta in sorted(articles, key=lambda m: m["date"], reverse=True):
        url = f"{BASE_URL}/artikelen/{meta['slug']}.html"
        lines.append(f"- [{meta['title']}]({url}): {meta['description']}")
    inner = "\n" + "\n".join(lines) + "\n"

    text = LLMS_FILE.read_text(encoding="utf-8")
    block = f"{LLMS_START}{inner}{LLMS_END}"
    if LLMS_START in text and LLMS_END in text:
        text = re.sub(
            re.escape(LLMS_START) + r".*?" + re.escape(LLMS_END),
            lambda _m: block,
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    LLMS_FILE.write_text(text, encoding="utf-8")
    print(f"Bijgewerkt: {LLMS_FILE.relative_to(ROOT)} (artikellijst, {len(articles)} items)")


def _markdown_body(path: Path) -> str:
    """De markdown van een artikel zonder frontmatter en zonder ruwe HTML-blokken.

    De ruwe HTML in sommige artikelen is interactief, zoals de scope-checker.
    Die heeft in een tekstbestand geen betekenis en zou alleen ruis toevoegen.
    """
    tekst = path.read_text(encoding="utf-8")
    if tekst.startswith("---"):
        eind = tekst.find("\n---", 3)
        if eind != -1:
            tekst = tekst[eind + 4:]
    tekst = re.sub(r"<div\b.*?</div>", "", tekst, flags=re.DOTALL)
    tekst = re.sub(r"<script\b.*?</script>", "", tekst, flags=re.DOTALL)
    tekst = re.sub(r"\n{3,}", "\n\n", tekst)
    # Koppen twee niveaus omlaag: in dit bestand is de artikeltitel al een ###,
    # dus een ## uit het artikel zou boven zijn eigen titel uitkomen.
    tekst = re.sub(r"^(#{1,4}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ",
                   tekst, flags=re.MULTILINE)
    return tekst.strip()


def write_llms_full(articles: list):
    """Schrijft public/llms-full.txt: de volledige tekst van de kennisbank.

    llms.txt is een index met links. Een taalmodel dat die links niet ophaalt,
    heeft daar weinig aan. llms-full.txt zet de tekst zelf in één bestand, zodat
    de inhoud ook zonder crawlen te lezen is.

    Bewust géén meetcijfers: die veranderen elke week en staan met hun datum in
    llms.txt en op de monitorpagina's. Een getal zonder verse datum in een
    statisch tekstbestand wordt vanzelf onjuist.
    """
    delen = [
        "# EAA Monitor — volledige tekst van de kennisbank",
        "",
        "> De onafhankelijke telling van digitaal toegankelijk Nederland. Dit bestand bevat de",
        "> volledige tekst van de artikelen en de beantwoorde praktijkvragen, zodat een taalmodel",
        "> de inhoud kan lezen zonder elke pagina apart op te halen.",
        "",
        f"Bron: {BASE_URL}/ · Licentie: CC BY 4.0, verwijs bij gebruik naar EAA Monitor met een link.",
        "",
        "De wekelijkse meetcijfers staan bewust niet in dit bestand: die veranderen elke maandag.",
        f"Ze staan met hun peildatum in {BASE_URL}/llms.txt en op de monitorpagina's per sector.",
        "",
        "---",
        "",
        "## Artikelen",
        "",
    ]
    for meta in sorted(articles, key=lambda m: m["date"], reverse=True):
        url = f"{BASE_URL}/artikelen/{meta['slug']}.html"
        delen += [
            f"### {meta['title']}",
            "",
            f"Bron: {url} · Gepubliceerd: {meta['date'].isoformat()}"
            + (f" · Bijgewerkt: {meta['updated'].isoformat()}" if meta.get("updated") else ""),
            "",
        ]
        if meta.get("answer"):
            delen += [f"Kort antwoord: {meta['answer']}", ""]
        delen += [_markdown_body(Path(meta["_path"])), "", "---", ""]

    vragen_pad = ROOT / "data" / "vragen.json"
    if vragen_pad.exists():
        try:
            vragen = json.loads(vragen_pad.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            vragen = []
        if vragen:
            delen += ["## Vragen uit de praktijk", "",
                      f"Antwoorden van toezichthouders op anonieme vragen. Bron: {BASE_URL}/vragen.html", ""]
            for v in vragen:
                delen.append(f"### {v.get('vraag', '').strip()}")
                delen.append("")
                delen.append(str(v.get("antwoord", "")).strip())
                bron = " · ".join(
                    str(v[k]).strip() for k in ("toezichthouder", "datum") if v.get(k)
                )
                if bron:
                    delen += ["", f"Bron: {bron}"]
                delen += ["", "---", ""]

    LLMS_FULL_FILE.write_text("\n".join(delen).rstrip() + "\n", encoding="utf-8")
    grootte = LLMS_FULL_FILE.stat().st_size
    print(f"Geschreven: {LLMS_FULL_FILE.relative_to(ROOT)} ({grootte // 1024} kB)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Bouw artikelen voor de EAA Hub.")
    ap.add_argument("--check", action="store_true", help="Alleen valideren, niets schrijven.")
    args = ap.parse_args()

    if not CONTENT_DIR.exists():
        sys.exit(f"Geen contentmap gevonden: {CONTENT_DIR}")

    paths = sorted(CONTENT_DIR.glob("*.md"))
    if not paths:
        sys.exit(f"Geen artikelen gevonden in {CONTENT_DIR}")

    articles = []
    seen_slugs = set()
    for p in paths:
        meta = parse_article(p)
        if meta["slug"] in seen_slugs:
            sys.exit(f"Dubbele slug: {meta['slug']} ({p.name})")
        seen_slugs.add(meta["slug"])
        articles.append(meta)
        print(f"Gelezen: {p.name} -> {meta['slug']} ({meta['theme']})")

    if args.check:
        print(f"OK: {len(articles)} artikelen gevalideerd.")
        return

    # Nieuwste eerst voor het overzicht
    articles_sorted = sorted(articles, key=lambda m: m["date"], reverse=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for meta in articles:
        out = OUT_DIR / f"{meta['slug']}.html"
        out.write_text(render_article(meta), encoding="utf-8")
        print(f"Geschreven: {out.relative_to(ROOT)}")

    KENNISBANK_FILE.write_text(render_kennisbank(articles_sorted), encoding="utf-8")
    print(f"Geschreven: {KENNISBANK_FILE.relative_to(ROOT)}")

    colofon = render_simple_page(
        "Colofon",
        "Colofon van de EAA Monitor: wie de onafhankelijke telling maakt, hoe je de data mag gebruiken en hoe je ons bereikt.",
        "colofon", COLOFON_BODY,
    )
    (ROOT / "public" / "colofon.html").write_text(colofon, encoding="utf-8")
    print("Geschreven: public/colofon.html")

    privacy = render_simple_page(
        "Privacyverklaring",
        "Privacyverklaring van de EAA Monitor: welke gegevens we verzamelen, hoe we ermee omgaan en welke rechten je hebt. Zo min mogelijk, zonder volgcookies.",
        "privacy", PRIVACY_BODY,
    )
    (ROOT / "public" / "privacy.html").write_text(privacy, encoding="utf-8")
    print("Geschreven: public/privacy.html")

    write_sitemap(articles_sorted)
    patch_llms_articles(articles_sorted)
    write_llms_full(articles_sorted)
    print(f"\nKlaar: {len(articles)} artikelen gebouwd.")


if __name__ == "__main__":
    main()
