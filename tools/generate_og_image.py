"""
Generate the Open Graph share image (public/static/og.png) for the EAA Monitor.

Renders a branded HTML card in Proper Access colors and screenshots it at
1200x630 with Playwright (already a project dependency). Deterministic, no
external API, no AI credits. Re-run whenever the branding or tagline changes.

Usage:
    python tools/generate_og_image.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "static" / "og.png"

# Proper Access brand colors
MAGENTA = "#A30D4B"
PETROL = "#004050"
DARKBLUE = "#1F2937"

CARD_HTML = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 1200px; height: 630px; }}
  body {{
    font-family: 'Nunito Sans', 'Helvetica Neue', Arial, sans-serif;
    background: {PETROL};
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
    background: {MAGENTA};
  }}
  .brand {{
    font-size: 34px;
    font-weight: 800;
    letter-spacing: 0.5px;
  }}
  .brand .dot {{ color: #FFFFFF; opacity: 0.55; }}
  h1 {{
    font-size: 78px;
    font-weight: 800;
    line-height: 1.05;
    max-width: 960px;
  }}
  .tagline {{
    font-size: 30px;
    font-weight: 600;
    opacity: 0.92;
    max-width: 920px;
    margin-top: 28px;
  }}
  .footer {{
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 24px;
    font-weight: 600;
  }}
  .pill {{
    background: {MAGENTA};
    color: #FFFFFF;
    padding: 10px 22px;
    border-radius: 999px;
    font-size: 22px;
    font-weight: 700;
  }}
</style>
</head>
<body>
  <div class="accent"></div>
  <div class="brand">EAA Monitor</div>
  <div>
    <h1>Hebben Nederlandse webshops een toegankelijkheidsverklaring?</h1>
    <p class="tagline">Wekelijkse controle op naleving van de European Accessibility Act.</p>
  </div>
  <div class="footer">
    <span class="pill">Een initiatief van Proper Access</span>
    <span style="opacity:0.85">eaa-monitor.nl</span>
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
        page.screenshot(path=str(OUTPUT))
        browser.close()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
