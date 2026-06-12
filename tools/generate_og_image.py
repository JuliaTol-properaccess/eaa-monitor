"""
Generate the Open Graph share image (public/static/og.png) for the EAA Monitor.

Renders a branded HTML card in the site's "De Telling"-stijl (papier, loofgroen,
okergeel; Fraunces + Atkinson Hyperlegible + IBM Plex Mono) and screenshots it
at 1200x630 with Playwright (already a project dependency). The card is
site-wide and sector-neutral so it fits the homepage, both monitors and every
article. EAA Monitor stands on its own brand, with no Proper Access
attribution. Deterministic, no external API, no AI credits. Re-run whenever the
branding or tagline changes.

Usage:
    python tools/generate_og_image.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "static" / "og.png"
FONTS_DIR = ROOT / "public" / "static" / "fonts"

# Zelf-gehoste fonts (zelfde bestanden als de site zelf serveert)
FONT_FACES = "\n".join([
    "@font-face { font-family: 'Fraunces Variable'; font-style: normal; font-weight: 100 900; "
    f"src: url('{(FONTS_DIR / 'fraunces-latin-wght-normal.woff2').as_uri()}') format('woff2-variations'); }}",
    "@font-face { font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: 400; "
    f"src: url('{(FONTS_DIR / 'atkinson-hyperlegible-latin-400-normal.woff2').as_uri()}') format('woff2'); }}",
    "@font-face { font-family: 'IBM Plex Mono'; font-style: normal; font-weight: 500; "
    f"src: url('{(FONTS_DIR / 'ibm-plex-mono-latin-500-normal.woff2').as_uri()}') format('woff2'); }}",
])

# Site design tokens (tailwind.config.js)
PAPIER = "#FAF7F1"
INKT = "#20281F"
STEUNGRIJS = "#46524B"
LOOFGROEN = "#1A5632"
DENNENGROEN = "#0D2B1F"
OKER = "#F4C84B"

CARD_HTML = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<style>
{FONT_FACES}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 1200px; height: 630px; }}
  body {{
    font-family: 'Atkinson Hyperlegible', 'Helvetica Neue', Arial, sans-serif;
    background: {PAPIER};
    color: {INKT};
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 64px 80px 56px;
    position: relative;
    overflow: hidden;
  }}
  .tellijn {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 12px;
    background: {OKER};
  }}
  .brand {{ display: flex; align-items: center; gap: 20px; position: relative; }}
  .tegel {{
    width: 72px; height: 72px; border-radius: 16px;
    background: {DENNENGROEN};
    display: flex; flex-direction: column; justify-content: center; gap: 7px;
    padding: 0 15px;
  }}
  .tegel .regel {{ height: 8px; border-radius: 4px; background: {PAPIER}; }}
  .tegel .spoor {{ height: 8px; border-radius: 4px; background: rgba(250,247,241,.25); position: relative; }}
  .tegel .spoor::before {{
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 42%; border-radius: 4px; background: {OKER};
  }}
  .woordmerk {{
    font-family: 'Fraunces Variable', Georgia, serif;
    font-size: 40px; font-weight: 400; letter-spacing: -0.5px;
  }}
  .woordmerk strong {{ font-weight: 600; }}
  .woordmerk .punt {{ color: {LOOFGROEN}; font-weight: 600; }}
  h1 {{
    font-family: 'Fraunces Variable', Georgia, serif;
    font-size: 68px;
    font-weight: 600;
    line-height: 1.08;
    letter-spacing: -1px;
    max-width: 1020px;
    position: relative;
  }}
  h1 .hl {{ background: {OKER}; padding: 0 10px; }}
  .tagline {{
    font-size: 30px;
    color: {STEUNGRIJS};
    max-width: 920px;
    margin-top: 26px;
    position: relative;
  }}
  .footer {{ display: flex; align-items: center; gap: 16px; position: relative; }}
  .stempel {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 2px;
    color: {PAPIER};
    background: {DENNENGROEN};
    padding: 10px 24px;
    border-radius: 10px;
  }}
</style>
</head>
<body>
  <div class="tellijn"></div>
  <div class="brand">
    <div class="tegel"><div class="regel"></div><div class="regel"></div><div class="spoor"></div></div>
    <div class="woordmerk"><strong>EAA</strong> Monitor<span class="punt">.</span></div>
  </div>
  <div>
    <h1>Snap de toegankelijkheidswet.<br><span class="hl">Zie waar Nederland staat.</span></h1>
    <p class="tagline">Elke maandag een verse telling in zes sectoren, plus uitleg in gewone taal.</p>
  </div>
  <div class="footer">
    <span class="stempel">eaa-monitor.nl &middot; Gemeten, niet beweerd</span>
  </div>
</body>
</html>
"""


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(CARD_HTML, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(OUTPUT))
        browser.close()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
