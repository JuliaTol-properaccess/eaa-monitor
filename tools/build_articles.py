#!/usr/bin/env python3
"""
Artikelgenerator voor de EAA Hub (WAT-framework, Layer 3: Tool).

Rendert markdown-artikelen uit content/artikelen/*.md naar server-rendered HTML
in public/artikelen/<slug>.html, bouwt het Kennisbank-overzicht
public/artikelen.html, regenereert public/sitemap.xml en patcht de
artikellijst-regio in public/llms.txt.

Server-rendered HTML is bewust: het is cruciaal voor SEO en GEO (citability door
AI-zoekmachines). Elk artikel krijgt Article JSON-LD mee.

Designrichting: Coinbase-look. Tokens staan centraal in public/static/theme.js
en public/static/site.css; deze tool emit alleen de gedeelde head/nav/footer en
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

BASE_URL = "https://eaa-monitor.nl"

# /feedback-route van de bezwaar-Worker (zie worker/src/index.js). Het inline
# feedbackformulier onder elk artikel post hier naartoe. Leeg laten valt terug
# op een mailto in de markup.
FEEDBACK_ENDPOINT = "https://eaa-bezwaar.juliatol.workers.dev/feedback"

# /newsletter-route van de bezwaar-Worker: nieuwsbrief-opt-in met dubbele
# opt-in. Het footerformulier post hiernaartoe; de Worker mailt een
# bevestigingslink en slaat na bevestiging op in Cloudflare KV.
NEWSLETTER_ENDPOINT = "https://eaa-bezwaar.juliatol.workers.dev/newsletter"

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
# dropdown. De Monitor-dropdown bundelt de twee dashboards plus de over-pagina.
NAV_ITEMS = [
    ("Home", "/"),
    ("Monitor", [
        ("E-commerce", "/monitor.html"),
        ("Financiële sector", "/monitor-financieel.html"),
        ("Over", "/over.html"),
    ]),
    ("Kennisbank", "/artikelen.html"),
    ("Bronnen", "/bronnen.html"),
    ("Vragen", "/vragen.html"),
    ("WCAG-audit", "/wcag-audit.html"),
]


def shared_head(title, description, canonical, *, extra_head="", og_type="website"):
    """Gedeelde <head>. depth-onafhankelijk via absolute /static-paden."""
    return f"""<!DOCTYPE html>
<html lang="nl">
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
  <meta property="og:locale" content="nl_NL">
  <meta property="og:image" content="{BASE_URL}/static/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)}">
  <meta name="twitter:description" content="{html.escape(description)}">
  <meta name="twitter:image" content="{BASE_URL}/static/og.png">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="/static/theme.js"></script>
  <link rel="stylesheet" href="/static/site.css">
{extra_head}</head>
"""


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
    return f"""  <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:bg-brand focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:z-50">Ga naar hoofdinhoud</a>

  <header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-line">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <a href="/" class="flex items-center gap-2 font-extrabold text-lg text-navy tracking-tight">
        <span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-brand text-white text-sm">EAA</span>
        <span>Monitor</span>
      </a>
      <nav aria-label="Hoofdnavigatie" class="hidden lg:flex items-center gap-7">
          {desktop_html}
      </nav>
      <button type="button" id="nav-toggle" class="lg:hidden inline-flex items-center justify-center w-10 h-10 -mr-2 rounded-lg text-navy hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand" aria-expanded="false" aria-controls="mobile-nav" aria-label="Menu openen">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
    </div>
    <nav id="mobile-nav" aria-label="Hoofdnavigatie (mobiel)" class="lg:hidden hidden border-t border-line px-4 sm:px-6 py-2">
        {mobile_html}
    </nav>
  </header>
"""


def site_footer():
    return f"""  <footer class="bg-navy text-white mt-24 on-dark">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-14">
      <div class="mb-10 pb-10 border-b border-white/10 grid gap-6 md:grid-cols-2 md:items-center">
        <div>
          <p class="font-extrabold text-lg tracking-tight">Blijf op de hoogte van de EAA</p>
          <p class="mt-2 text-sm text-white/60 max-w-sm leading-relaxed">Af en toe een update: nieuwe cijfers, antwoorden van toezichthouders en praktische uitleg. Geen spam, afmelden kan altijd.</p>
        </div>
        <form id="newsletter-form" data-endpoint="{NEWSLETTER_ENDPOINT}" novalidate>
          <div class="hidden" aria-hidden="true">
            <label>Laat dit veld leeg<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label>
          </div>
          <label for="newsletter-email" class="block text-sm font-semibold text-white/90 mb-1.5">Je e-mailadres</label>
          <div class="flex flex-col sm:flex-row gap-2">
            <input type="email" id="newsletter-email" name="email" required autocomplete="email" placeholder="jij@voorbeeld.nl" class="flex-1 rounded-xl px-4 py-3 bg-white text-ink placeholder:text-gray-400 focus:outline-none focus:ring-4 focus:ring-brand/40">
            <button type="submit" id="newsletter-submit" class="btn btn-on-dark whitespace-nowrap">Inschrijven</button>
          </div>
          <p class="mt-2 text-xs text-white/50">We gebruiken je adres alleen voor de nieuwsbrief en je kunt je op elk moment afmelden.</p>
          <div id="newsletter-status" role="status" aria-live="polite" tabindex="-1" class="empty:hidden mt-3 text-sm"></div>
        </form>
      </div>
      <div class="grid gap-10 md:grid-cols-4">
        <div class="md:col-span-2">
          <p class="flex items-center gap-2 font-extrabold text-lg tracking-tight">
            <span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-brand text-white text-sm">EAA</span>
            <span>Monitor</span>
          </p>
          <p class="mt-4 text-sm text-white/60 max-w-sm leading-relaxed">De Nederlandse hub over de European Accessibility Act: wekelijkse data en heldere uitleg over wie de wet raakt, wie toezicht houdt en wat werkt.</p>
        </div>
        <div>
          <p class="text-sm font-semibold text-white/90 mb-3">Monitor &amp; uitleg</p>
          <ul class="space-y-2 text-sm text-white/60">
            <li><a href="/monitor.html" class="hover:text-white">Webshopmonitor</a></li>
            <li><a href="/monitor-financieel.html" class="hover:text-white">Financiële monitor</a></li>
            <li><a href="/artikelen.html" class="hover:text-white">Kennisbank</a></li>
            <li><a href="/bronnen.html" class="hover:text-white">Bronnen</a></li>
          </ul>
        </div>
        <div>
          <p class="text-sm font-semibold text-white/90 mb-3">Meedoen &amp; info</p>
          <ul class="space-y-2 text-sm text-white/60">
            <li><a href="/vragen.html" class="hover:text-white">Vragen uit de praktijk</a></li>
            <li><a href="/over.html" class="hover:text-white">Over dit dashboard</a></li>
            <li><a href="/bezwaren.html" class="hover:text-white">Ingediende bezwaren</a></li>
            <li><a href="/bezwaar.html" class="hover:text-white">Bezwaar maken</a></li>
          </ul>
        </div>
      </div>
      <p class="mt-12 pt-6 border-t border-white/10 text-xs text-white/60">De controle vindt wekelijks plaats. Een link naar een verklaring betekent niet automatisch dat een website ook daadwerkelijk toegankelijk is.</p>
    </div>
    <script src="/static/newsletter.js"></script>
  </footer>

  <script src="/static/nav.js"></script>
  <script src="/static/reveal.js"></script>
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
    return meta


def article_jsonld(meta: dict, url: str) -> str:
    obj = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "datePublished": meta["date"].isoformat(),
        "dateModified": meta["date"].isoformat(),
        "inLanguage": "nl-NL",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@type": "Organization", "name": "EAA Monitor", "url": BASE_URL},
        "publisher": {"@type": "Organization", "name": "EAA Monitor", "url": BASE_URL},
    }
    if meta.get("keywords"):
        obj["keywords"] = ", ".join(meta["keywords"])
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


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

            <div>
              <label for="feedback-bericht" class="block text-sm font-semibold text-navy mb-1.5">Wat klopt er niet?</label>
              <textarea id="feedback-bericht" name="bericht" rows="4" required class="w-full rounded-xl border border-field px-4 py-3 text-navy placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand" placeholder="Beschrijf kort wat er niet klopt. Heb je een bron? Plak die er gerust bij."></textarea>
            </div>

            <div>
              <label for="feedback-email" class="block text-sm font-semibold text-navy mb-1.5">E-mailadres <span class="font-normal text-gray-500">(optioneel, alleen als je een reactie wilt)</span></label>
              <input type="email" id="feedback-email" name="email" autocomplete="email" class="w-full rounded-xl border border-field px-4 py-3 text-navy placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand" placeholder="jij@voorbeeld.nl">
            </div>

            <button type="submit" id="feedback-submit" class="btn btn-primary">Versturen</button>
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

    return f"""{head}<body class="bg-white">
{site_header("/artikelen.html")}
  <main id="main">

    <div class="bg-navy text-white on-dark">
      <div class="max-w-prose mx-auto px-4 sm:px-6 pt-14 pb-16">
        <a href="/artikelen.html" class="text-sm font-semibold text-white/70 hover:text-white">&larr; Kennisbank</a>
        <p class="mt-6 inline-block text-xs font-bold uppercase tracking-wider text-brand-bright bg-white/5 px-3 py-1 rounded-full ring-1 ring-white/15">{html.escape(theme_label)}</p>
        <h1 class="mt-4 text-3xl md:text-5xl font-extrabold leading-tight tracking-tight">{html.escape(meta["title"])}</h1>
        <p class="mt-4 text-lg text-white/70 leading-relaxed">{html.escape(meta["description"])}</p>
        <p class="mt-6 text-sm text-white/50">Gepubliceerd op {nl_date(meta["date"])}</p>
      </div>
    </div>

    <article class="max-w-prose mx-auto px-4 sm:px-6 py-14">
      <div class="prose">
{meta["body_html"]}
      </div>
{sources_block(meta)}

      <div class="mt-14 rounded-3xl bg-softblue ring-1 ring-brand-light p-8 md:p-10">
        <h2 class="text-2xl font-extrabold text-navy tracking-tight">Wil je weten waar je staat?</h2>
        <p class="mt-3 text-navy/70 leading-relaxed">Een onafhankelijke audit brengt in kaart of je website voldoet aan de WCAG en de European Accessibility Act. Bekijk de auditbureaus in Nederland, of zoek je eigen webshop op in de monitor.</p>
        <div class="mt-6 flex flex-wrap gap-3">
          <a href="/wcag-audit.html" class="btn btn-primary">Bekijk auditbureaus</a>
          <a href="/monitor.html" class="btn btn-ghost">Check jouw webshop in de monitor</a>
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

    <div class="bg-navy text-white on-dark">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        <h1 class="text-4xl md:text-6xl font-extrabold leading-[1.05] tracking-tight max-w-3xl">Alles over de<br>European Accessibility Act</h1>
        <p class="mt-6 text-lg md:text-xl text-white/70 max-w-2xl leading-relaxed">Heldere uitleg zonder paniek of jargon. Voor wie de wet geldt, wie toezicht houdt, wat de boetes zijn en wat echt werkt.</p>
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
        <a href="/bronnen.html" class="btn btn-primary whitespace-nowrap self-start sm:self-auto">Naar de bronnen</a>
      </div>
      <p class="mt-10 text-sm text-gray-500 leading-relaxed max-w-2xl">Deze kennisbank is samengesteld uit openbare bronnen: publicaties van toezichthouders, nieuwsberichten en vakartikelen. Het is algemene uitleg, geen juridisch advies. Zie je een fout? Onderaan elk artikel kun je het ons laten weten.</p>
    </section>

  </main>
{site_footer()}</body>
</html>
"""


# ── Sitemap & llms.txt ─────────────────────────────────────────────────────────

def write_sitemap(articles: list):
    static_urls = [
        (f"{BASE_URL}/", "weekly", "1.0"),
        (f"{BASE_URL}/monitor.html", "weekly", "0.9"),
        (f"{BASE_URL}/monitor-financieel.html", "weekly", "0.9"),
        (f"{BASE_URL}/artikelen.html", "weekly", "0.8"),
        (f"{BASE_URL}/bronnen.html", "weekly", "0.7"),
        (f"{BASE_URL}/vragen.html", "weekly", "0.7"),
        (f"{BASE_URL}/vraag-stellen.html", "monthly", "0.6"),
        (f"{BASE_URL}/wcag-audit.html", "monthly", "0.7"),
        (f"{BASE_URL}/over.html", "monthly", "0.5"),
        (f"{BASE_URL}/bezwaren.html", "weekly", "0.4"),
    ]
    rows = []
    for loc, freq, prio in static_urls:
        rows.append(
            f"  <url>\n    <loc>{loc}</loc>\n    "
            f"<changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        )
    for meta in articles:
        loc = f"{BASE_URL}/artikelen/{meta['slug']}.html"
        rows.append(
            f"  <url>\n    <loc>{loc}</loc>\n    "
            f"<lastmod>{meta['date'].isoformat()}</lastmod>\n    "
            f"<changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
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

    write_sitemap(articles_sorted)
    patch_llms_articles(articles_sorted)
    print(f"\nKlaar: {len(articles)} artikelen gebouwd.")


if __name__ == "__main__":
    main()
