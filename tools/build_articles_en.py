#!/usr/bin/env python3
"""
Engelse artikelgenerator (WAT-framework, Layer 3: Tool).

Rendert content/articles-en/*.md naar public/en/articles/<slug>.html en bouwt
het overzicht public/en/articles.html.

De Engelse kant van de site bestond alleen uit de monitorpagina's; "Knowledge
base" in de Engelse navigatie wees naar de Nederlandse kennisbank. Voor een
Engelstalige lezer, en voor een AI-zoekmachine die een Engelse vraag krijgt,
viel er dus niets te lezen of te citeren.

Engelse artikelen worden apart geschreven en zijn geen vertaling van de
Nederlandse. Ze staan daarom in een eigen map en hebben geen hreflang-koppeling
met een Nederlands artikel.

Gebruik:
    python tools/build_articles_en.py

Frontmatter is gelijk aan de Nederlandse generator: title, slug, description,
date, theme, optioneel answer, keywords en sources.
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import (  # noqa: E402
    BASE_URL, LOGO_LICHT, LOGO_DONKER, parse_article, shared_head,
)

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "articles-en"
OUT_DIR = ROOT / "public" / "en" / "articles"
INDEX_FILE = ROOT / "public" / "en" / "articles.html"

THEMES_EN = {
    "scope": "Who it applies to",
    "toezicht": "Enforcement",
    "praktijk": "In practice",
    "mythes": "Myths and misunderstandings",
}

EN_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Zelfde structuur als de Engelse pagina's die er al staan. Links zonder /en/
# krijgen "(NL)" mee, zodat een lezer niet onaangekondigd op een Nederlandse
# pagina belandt.
NAV_EN = [
    ("Home", "/en/"),
    ("Monitor", [
        ("E-commerce", "/en/monitor.html"),
        ("Financial sector", "/en/monitor-financieel.html"),
        ("Telecom", "/en/monitor-telecom.html"),
        ("Passenger transport", "/en/monitor-vervoer.html"),
        ("Media &amp; streaming", "/en/monitor-media.html"),
        ("E-books", "/en/monitor-ebooks.html"),
        ("Travel", "/en/monitor-reizen.html"),
    ]),
    ("Knowledge base", "/en/articles.html"),
    ("Sources (NL)", "/bronnen.html"),
]


def en_date(d):
    return f"{d.day} {EN_MONTHS[d.month]} {d.year}"


def header_en(active_path):
    chevron = (
        '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="6 9 12 15 18 9"></polyline></svg>'
    )
    desktop, mobile = [], []
    for label, target in NAV_EN:
        if isinstance(target, list):
            actief = any(href == active_path for _, href in target)
            pcls = "text-brand" if actief else "text-navy hover:text-brand"
            d_kind, m_kind = [], []
            for clabel, chref in target:
                ccls = "text-brand" if chref == active_path else "text-navy hover:text-brand"
                cur = ' aria-current="page"' if chref == active_path else ""
                d_kind.append(
                    f'<a href="{chref}" class="block px-4 py-2 text-sm font-semibold {ccls} hover:bg-softblue transition-colors"{cur}>{clabel}</a>'
                )
                m_kind.append(
                    f'<a href="{chref}" class="block py-2.5 text-base font-semibold {ccls}"{cur}>{clabel}</a>'
                )
            desktop.append(
                f'''<div class="relative" data-dropdown>
            <button type="button" data-dropdown-toggle class="text-sm font-semibold {pcls} transition-colors inline-flex items-center gap-1" aria-expanded="false" aria-haspopup="true">{label}{chevron}</button>
            <div data-dropdown-menu class="hidden absolute left-0 top-full pt-2 z-50">
              <div class="min-w-[12rem] bg-white rounded-xl shadow-lg ring-1 ring-line py-2">
              {"".join(d_kind)}
              </div>
            </div>
          </div>'''
            )
            mobile.append(
                f'''<div data-dropdown>
          <button type="button" data-dropdown-toggle class="w-full flex items-center justify-between py-2.5 text-base font-semibold {pcls}" aria-expanded="false">{label}{chevron}</button>
          <div data-dropdown-menu class="hidden pl-4 ml-1 border-l border-line">{"".join(m_kind)}</div>
        </div>'''
            )
        else:
            actief = target == active_path
            cur = ' aria-current="page"' if actief else ""
            cls = "text-brand" if actief else "text-navy hover:text-brand"
            lang = ' hreflang="nl" lang="nl"' if not target.startswith("/en/") else ""
            desktop.append(
                f'<a href="{target}" class="text-sm font-semibold {cls} transition-colors"{cur}{lang}>{label}</a>'
            )
            mobile.append(
                f'<a href="{target}" class="block py-2.5 text-base font-semibold {cls}"{cur}{lang}>{label}</a>'
            )
    return f"""  <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:bg-oker focus:text-inkt focus:font-bold focus:px-4 focus:py-2 focus:rounded-lg focus:z-50">Skip to main content</a>

  <header class="sticky top-0 z-40 bg-papier/90 backdrop-blur">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <a href="/en/" class="flex items-center">
        {LOGO_LICHT}
      </a>
      <nav aria-label="Main navigation" class="hidden lg:flex items-center gap-7">
          {"".join(desktop)}
          <a href="/" class="lang-switch inline-flex items-center gap-1.5 text-sm font-semibold text-navy border border-field rounded-lg px-2.5 py-1 hover:text-brand hover:border-brand transition-colors" hreflang="nl" lang="nl" aria-label="Deze pagina in het Nederlands"><span aria-hidden="true">&#127760;</span> NL</a>
      </nav>
      <button type="button" id="nav-toggle" class="lg:hidden inline-flex items-center justify-center w-10 h-10 -mr-2 rounded-lg text-navy hover:bg-zachtgroen focus:outline-none focus:ring-2 focus:ring-brand" aria-expanded="false" aria-controls="mobile-nav" aria-label="Open menu">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
    </div>
    <nav id="mobile-nav" aria-label="Main navigation (mobile)" class="lg:hidden hidden border-t border-line px-4 sm:px-6 py-2">
        {"".join(mobile)}
        <a href="/" class="block py-2.5 text-base font-semibold text-navy hover:text-brand" hreflang="nl" lang="nl">&#127760; Nederlands</a>
    </nav>
    <div class="h-[3px] bg-oker" aria-hidden="true"></div>
  </header>
"""


def footer_en():
    return f"""  <footer class="bg-navy text-white mt-24 on-dark">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-14">
      <div class="grid gap-10 md:grid-cols-3">
        <div>
          {LOGO_DONKER}
          <p class="mt-4 text-sm text-white max-w-sm leading-relaxed">EAA Monitor is the independent count of digital accessibility in the Netherlands: a fresh measurement every Monday across seven sectors, plus plain-language explanation of who the law covers, who enforces it and what works. <span class="text-brand-bright font-semibold">Measured, not claimed.</span></p>
        </div>
        <div>
          <p class="text-sm font-semibold text-white mb-3">Monitor &amp; explanation</p>
          <ul class="space-y-2 text-sm text-white">
            <li><a href="/en/monitor.html" class="hover:text-white">E-commerce monitor</a></li>
            <li><a href="/en/monitor-financieel.html" class="hover:text-white">Financial monitor</a></li>
            <li><a href="/en/monitor-telecom.html" class="hover:text-white">Telecom monitor</a></li>
            <li><a href="/en/monitor-vervoer.html" class="hover:text-white">Transport monitor</a></li>
            <li><a href="/en/monitor-media.html" class="hover:text-white">Media monitor</a></li>
            <li><a href="/en/monitor-ebooks.html" class="hover:text-white">E-books monitor</a></li>
            <li><a href="/en/monitor-reizen.html" class="hover:text-white">Travel monitor</a></li>
            <li><a href="/en/articles.html" class="hover:text-white">Knowledge base</a></li>
          </ul>
        </div>
        <div>
          <p class="text-sm font-semibold text-white mb-3">More</p>
          <ul class="space-y-2 text-sm text-white">
            <li><a href="/" class="hover:text-white" hreflang="nl" lang="nl">Nederlandse versie</a></li>
            <li><a href="/tools.html" class="hover:text-white" hreflang="nl" lang="nl">Tools (NL)</a></li>
            <li><a href="/bronnen.html" class="hover:text-white" hreflang="nl" lang="nl">Sources (NL)</a></li>
            <li><a href="/vragen.html" class="hover:text-white" hreflang="nl" lang="nl">Questions (NL)</a></li>
            <li><a href="/lijst.html" class="hover:text-white" hreflang="nl" lang="nl">Full measurement lists (NL)</a></li>
          </ul>
        </div>
      </div>
      <div class="mt-12 pt-8 border-t border-white/10 text-xs text-white leading-relaxed">
        <p class="max-w-3xl">The weekly check looks for a link to an accessibility statement in a site's footer. A link found does not mean a site is actually accessible. Figures and underlying data are free to use under CC BY 4.0, with a link back to EAA Monitor.</p>
      </div>
    </div>
  </footer>
  <script src="/static/reveal.js" defer></script>
"""


def article_jsonld_en(meta, url):
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "inLanguage": "en",
        "datePublished": meta["date"].isoformat(),
        "dateModified": (meta.get("updated") or meta["date"]).isoformat(),
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@id": f"{BASE_URL}/#organization"},
        "publisher": {"@id": f"{BASE_URL}/#organization"},
        "image": f"{BASE_URL}/static/og.png",
    }
    if meta.get("keywords"):
        data["keywords"] = ", ".join(meta["keywords"])
    blokken = [data]
    if meta.get("answer"):
        blokken.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "@id": f"{url}#faq",
            "mainEntity": [{
                "@type": "Question",
                "name": meta["title"],
                "acceptedAnswer": {"@type": "Answer", "text": meta["answer"]},
            }],
        })
    graph = {"@context": "https://schema.org", "@graph": []}
    for b in blokken:
        b.pop("@context", None)
        graph["@graph"].append(b)
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(graph, ensure_ascii=False, indent=2)
        + "\n  </script>\n"
    )


def sources_en(meta):
    if not meta.get("sources"):
        return ""
    items = "\n".join(
        f'          <li><a href="{html.escape(s["url"])}" rel="noopener noreferrer">{html.escape(s["title"])}</a></li>'
        for s in meta["sources"] if s.get("url") and s.get("title")
    )
    return f"""
      <div class="mt-12 pt-8 border-t border-line">
        <h2 class="font-display text-lg font-semibold text-navy">Sources</h2>
        <ul class="mt-3 space-y-2 text-sm text-gray-700 list-disc pl-5">
{items}
        </ul>
        <p class="mt-4 text-sm text-gray-600">This article explains the law in plain language. It is not legal advice. Where a claim comes from trade sources rather than from a regulator, it says so.</p>
      </div>"""


def render_article_en(meta):
    slug = meta["slug"]
    url = f"{BASE_URL}/en/articles/{slug}.html"
    head = shared_head(
        f"{meta['title']} — EAA Monitor", meta["description"], url,
        extra_head=article_jsonld_en(meta, url), og_type="article", lang="en",
    )
    antwoord = (
        f'\n        <div class="notice notice-info mt-8"><p><strong>In short:</strong> {html.escape(meta["answer"])}</p></div>'
        if meta.get("answer") else ""
    )
    return f"""{head}<body class="bg-papier">
{header_en("/en/articles.html")}
  <main id="main">
    <article>
      <div class="max-w-3xl mx-auto px-4 sm:px-6 pt-14 pb-4">
        <p class="eyebrow">{html.escape(THEMES_EN.get(meta['theme'], meta['theme']))}</p>
        <h1 class="mt-3 font-display text-3xl md:text-4xl font-semibold text-navy leading-[1.12] tracking-tight">{html.escape(meta['title'])}</h1>
        <p class="mt-4 text-sm text-gray-600">Published <time datetime="{meta['date'].isoformat()}">{en_date(meta['date'])}</time>. Written in English, not translated from the Dutch edition.</p>{antwoord}
      </div>
      <div class="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
        <div class="prose">
{meta['body_html']}
        </div>
{sources_en(meta)}
        <p class="mt-10 text-sm"><a href="/en/articles.html" class="link font-semibold">Back to the knowledge base</a></p>
      </div>
    </article>
  </main>
{footer_en()}</body>
</html>
"""


def render_index_en(articles):
    url = f"{BASE_URL}/en/articles.html"
    beschrijving = (
        "Plain-language explanation of the European Accessibility Act in the Netherlands: "
        "who it applies to, which of the six regulators enforces it, and what the law actually "
        "requires."
    )
    kaarten = []
    for meta in articles:
        kaarten.append(f"""        <a href="/en/articles/{meta['slug']}.html" class="card card-hover p-7 flex flex-col">
          <p class="eyebrow">{html.escape(THEMES_EN.get(meta['theme'], meta['theme']))}</p>
          <h2 class="mt-3 font-display text-xl font-semibold text-navy leading-snug">{html.escape(meta['title'])}</h2>
          <p class="mt-3 text-[15px] text-gray-700 leading-relaxed">{html.escape(meta['description'])}</p>
          <p class="mt-auto pt-5 text-sm text-gray-600"><time datetime="{meta['date'].isoformat()}">{en_date(meta['date'])}</time></p>
        </a>""")
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{url}#page",
        "url": url,
        "name": "EAA knowledge base",
        "description": beschrijving,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": "EAA Monitor", "url": BASE_URL},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(articles),
            "itemListElement": [
                {
                    "@type": "ListItem", "position": i + 1,
                    "url": f"{BASE_URL}/en/articles/{m['slug']}.html", "name": m["title"],
                }
                for i, m in enumerate(articles)
            ],
        },
    }
    head = shared_head(
        "EAA knowledge base — EAA Monitor", beschrijving, url, lang="en",
        extra_head='  <script type="application/ld+json">\n  '
                   + json.dumps(jsonld, ensure_ascii=False, indent=2) + "\n  </script>\n",
    )
    return f"""{head}<body class="bg-papier">
{header_en("/en/articles.html")}
  <main id="main">

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pt-14 pb-6">
      <p class="eyebrow">Knowledge base</p>
      <h1 class="mt-3 font-display text-3xl md:text-4xl font-semibold text-navy leading-[1.1] tracking-tight">The European Accessibility Act, explained</h1>
      <p class="mt-5 text-lg text-gray-700 max-w-2xl leading-relaxed">Who the law applies to, which of the six Dutch regulators enforces it, and what it actually requires. Written in English rather than translated, because the Dutch edition answers Dutch questions.</p>
      <p class="mt-4 text-[15px] text-gray-700 max-w-2xl leading-relaxed">The <a href="/artikelen.html" class="link font-semibold" hreflang="nl" lang="nl">Dutch knowledge base</a> is larger and covers more ground.</p>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 pb-8">
      <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
{chr(10).join(kaarten)}
      </div>
    </section>

  </main>
{footer_en()}</body>
</html>
"""


def main():
    if not CONTENT_DIR.exists():
        sys.exit(f"No content directory: {CONTENT_DIR}")
    paden = sorted(CONTENT_DIR.glob("*.md"))
    if not paden:
        sys.exit(f"No articles found in {CONTENT_DIR}")

    artikelen, slugs = [], set()
    for p in paden:
        meta = parse_article(p)
        if meta["slug"] in slugs:
            sys.exit(f"Duplicate slug: {meta['slug']} ({p.name})")
        slugs.add(meta["slug"])
        artikelen.append(meta)

    artikelen.sort(key=lambda m: m["date"], reverse=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for meta in artikelen:
        (OUT_DIR / f"{meta['slug']}.html").write_text(render_article_en(meta), encoding="utf-8")
    INDEX_FILE.write_text(render_index_en(artikelen), encoding="utf-8")
    print(f"Geschreven: {len(artikelen)} Engelse artikelen + public/en/articles.html")


def en_urls():
    """URL's voor de sitemap in build_articles.py."""
    urls = [("/en/articles.html", None)]
    if CONTENT_DIR.exists():
        for p in sorted(CONTENT_DIR.glob("*.md")):
            meta = parse_article(p)
            lastmod = (meta.get("updated") or meta["date"]).isoformat()
            urls.append((f"/en/articles/{meta['slug']}.html", lastmod))
    return urls


if __name__ == "__main__":
    main()
