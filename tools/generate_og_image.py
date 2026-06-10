"""
Generate the Open Graph share image (public/static/og.png) for the EAA Monitor.

Renders a branded HTML card in the site's Coinbase-look (navy + brand blue,
Montserrat) and screenshots it at 1200x630 with Playwright (already a project
dependency). The card is site-wide and sector-neutral so it fits the homepage,
both monitors and every article. EAA Monitor stands on its own brand, with no
Proper Access attribution. Deterministic, no external API, no AI credits. Re-run
whenever the branding or tagline changes.

Usage:
    python tools/generate_og_image.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "static" / "og.png"
FONTS_DIR = ROOT / "public" / "static" / "fonts"

# Zelf-gehoste Montserrat (zelfde bestanden als de site zelf serveert)
FONT_FACES = "\n".join(
    f"@font-face {{ font-family: 'Montserrat'; font-style: normal; font-weight: {w}; "
    f"src: url('{(FONTS_DIR / f'montserrat-{w}-latin.woff2').as_uri()}') format('woff2'); }}"
    for w in (400, 500, 600, 700, 800)
)

# Site design tokens (tailwind.config.js) + Proper Access attribution color
NAVY = "#0A0E27"
NAVY_SOFT = "#141A3D"
BRAND = "#0052FF"
BRAND_BRIGHT = "#6EA8FF"
PILL = "#A30D4B"  # achtergrond van de url-pill

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
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_SOFT} 100%);
    color: #FFFFFF;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 72px 80px;
    position: relative;
    overflow: hidden;
  }}
  .accent {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 14px;
    background: {BRAND};
  }}
  .glow {{
    position: absolute;
    top: -160px; right: -160px;
    width: 520px; height: 520px;
    background: radial-gradient(circle, rgba(0,82,255,0.45) 0%, rgba(0,82,255,0) 70%);
    pointer-events: none;
  }}
  .brand {{
    font-size: 34px;
    font-weight: 800;
    letter-spacing: 0.5px;
    position: relative;
  }}
  .brand .e {{ color: {BRAND_BRIGHT}; }}
  h1 {{
    font-size: 72px;
    font-weight: 800;
    line-height: 1.06;
    max-width: 1000px;
    position: relative;
  }}
  h1 .hl {{ color: {BRAND_BRIGHT}; }}
  .tagline {{
    font-size: 30px;
    font-weight: 500;
    color: #C7D0E8;
    max-width: 920px;
    margin-top: 28px;
    position: relative;
  }}
  .footer {{
    display: flex;
    align-items: center;
    gap: 16px;
    position: relative;
  }}
  .pill {{
    background: {PILL};
    color: #FFFFFF;
    padding: 10px 24px;
    border-radius: 999px;
    font-size: 24px;
    font-weight: 700;
  }}
</style>
</head>
<body>
  <div class="accent"></div>
  <div class="glow"></div>
  <div class="brand"><span class="e">EAA</span> Monitor</div>
  <div>
    <h1>Alles over de <span class="hl">European Accessibility Act</span> in Nederland</h1>
    <p class="tagline">Wekelijkse data en heldere uitleg over de toegankelijkheidswet.</p>
  </div>
  <div class="footer">
    <span class="pill">eaa-monitor.nl</span>
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
