#!/usr/bin/env python3
"""
Stel een concept-LinkedIn-post op over de stand van de EAA Monitor.

Leest data/history.json (week-op-week) en data/results.json (categorieen), kiest
een invalshoek op basis van wat de data laat zien, en schrijft een Nederlands
concept naar .tmp/linkedin/<datum>.md. Jij redigeert en plaatst zelf.

Invalshoeken:
    launch  Lanceringspost (week 1, nog geen vergelijking)
    A       Statusupdate met week-op-week verandering
    B       Sector-spotlight (koploper vs achterblijver)
    C       Goed voorbeeld (webshops die net een verklaring plaatsten)
    D       Uitleg van een veelgestelde EAA-vraag

Gebruik:
    python tools/generate_linkedin_post.py            # tool kiest de hoek
    python tools/generate_linkedin_post.py --angle B  # forceer een hoek
    python tools/generate_linkedin_post.py --print    # alleen tonen, niets schrijven

Merkregels worden bewaakt: geen em-dashes, geen emoji, geen verboden jargon.
Bij een overtreding wordt het concept niet weggeschreven (tenzij --force).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = ROOT / "data" / "results.json"
OBJECTIONS_FILE = ROOT / "data" / "objections.json"
HISTORY_FILE = ROOT / "data" / "history.json"
OUT_DIR = ROOT / ".tmp" / "linkedin"

DASHBOARD_URL = "eaa-monitor.nl"
HASHTAGS = "#toegankelijkheid #EAA #webshop #digitaletoegankelijkheid"

CATEGORY_LABELS = {
    "marketplace": "marketplaces",
    "elektronica": "elektronica",
    "mode": "mode",
    "supermarkt": "supermarkten",
    "drogisterij": "drogisterijen",
    "wonen": "wonen",
    "sport": "sport",
    "boeken": "boeken",
    "speelgoed": "speelgoed",
    "overig": "overig",
}

MONTHS_NL = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

# Minimaal aantal webshops in een categorie voordat we er uitspraken over doen.
MIN_CATEGORY_SIZE = 10

# Verboden jargon (merkregel). Kleine, gerichte lijst.
JARGON = ["compliance", "stakeholder", "implementeren", "implementatie"]


# ── Data ──

def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _normalize_url(url):
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"/+$", "", u)
    return u


def _objection_urls():
    data = _load(OBJECTIONS_FILE, [])
    if isinstance(data, list):
        return {_normalize_url(o.get("url")) for o in data if o.get("url")}
    return set()


def _has(shop):
    return shop["has_statement"] and shop["scrape_status"] == "success"


def _date_nl(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS_NL[int(m) - 1]} {y}"


def public_webshops(results):
    objections = _objection_urls()
    return [r for r in results["webshops"] if _normalize_url(r["url"]) not in objections]


def stats_from(shops):
    total = len(shops)
    with_st = sum(1 for r in shops if _has(r))
    errors = sum(1 for r in shops if r["scrape_status"] != "success")
    without = total - with_st - errors
    pct = round(with_st / total * 100) if total else 0
    return {"total": total, "with": with_st, "without": without,
            "errors": errors, "pct": pct}


def category_breakdown(shops):
    cats = {}
    for r in shops:
        c = r["category"]
        cats.setdefault(c, {"total": 0, "found": 0})
        cats[c]["total"] += 1
        if _has(r):
            cats[c]["found"] += 1
    out = []
    for c, d in cats.items():
        pct = round(d["found"] / d["total"] * 100) if d["total"] else 0
        out.append({"key": c, "label": CATEGORY_LABELS.get(c, c),
                    "total": d["total"], "found": d["found"], "pct": pct})
    return out


def prev_week_results(current_date):
    """Vorige-week results.json uit de git-historie, of None."""
    try:
        hashes = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--format=%H", "--", "data/results.json"],
            capture_output=True, text=True, check=True,
        ).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    for h in hashes:
        try:
            blob = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{h}:data/results.json"],
                capture_output=True, text=True, check=True,
            ).stdout
            data = json.loads(blob)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        if data.get("last_updated", "")[:10] != current_date:
            return data
    return None


def newly_added(current_shops, prev_results):
    """Webshops waar has_statement deze week van nee naar ja ging."""
    if not prev_results:
        return []
    prev_has = {
        _normalize_url(r["url"]): _has(r) for r in prev_results.get("webshops", [])
    }
    fresh = []
    for r in current_shops:
        key = _normalize_url(r["url"])
        if _has(r) and not prev_has.get(key, False):
            fresh.append(r["name"])
    return fresh


# ── Invalshoek kiezen ──

def choose_angle(delta, breakdown, fresh, has_prev):
    if not has_prev:
        return "launch"
    if delta is not None and abs(delta) >= 1:
        return "A"
    big = [c for c in breakdown if c["total"] >= MIN_CATEGORY_SIZE]
    if big and (max(c["pct"] for c in big) - min(c["pct"] for c in big)) >= 15:
        return "B"
    if fresh:
        return "C"
    return "D"


# ── Posts ──

def _join_names(names, limit=3):
    shown = names[:limit]
    if len(shown) == 1:
        return shown[0]
    return ", ".join(shown[:-1]) + " en " + shown[-1]


def render(angle, cur, delta, prev_pct, breakdown, fresh):
    big = [c for c in breakdown if c["total"] >= MIN_CATEGORY_SIZE]
    leader = max(big, key=lambda c: c["pct"]) if big else None
    laggard = min(big, key=lambda c: c["pct"]) if big else None

    if angle == "launch":
        return (
            f"Hebben Nederlandse webshops een toegankelijkheidsverklaring? Wij houden het bij.\n\n"
            f"Van de {cur['total']} webshops die we volgen, heeft {cur['with']} ({cur['pct']}%) er nu een. "
            f"De rest nog niet.\n\n"
            f"Sinds juni 2025 moeten webshops hun digitale kanalen toegankelijk maken. "
            f"Een verklaring in de footer is de eerste zichtbare stap.\n\n"
            f"Bekijk de volledige stand per webshop op {DASHBOARD_URL}. Welke sector verrast jou?\n\n"
            f"{HASHTAGS}"
        )

    if angle == "A":
        if delta is None:
            trend = "De stand blijft deze week stabiel."
        elif delta > 0:
            trend = f"Een stijging van {delta} procentpunt. Langzaam, maar de goede kant op."
        elif delta < 0:
            trend = f"Een daling van {abs(delta)} procentpunt."
        else:
            trend = "Gelijk gebleven met vorige week."
        prev_line = f"Vorige week was dat {prev_pct}%. " if prev_pct is not None else ""
        return (
            f"Deze week heeft {cur['pct']}% van de Nederlandse webshops een toegankelijkheidsverklaring. "
            f"{prev_line}{trend}\n\n"
            f"Sinds juni 2025 moeten webshops hun digitale kanalen toegankelijk maken. "
            f"Een verklaring in de footer is de eerste zichtbare stap.\n\n"
            f"De volledige stand per webshop staat op {DASHBOARD_URL}. Wat denk jij, gaat dit snel genoeg?\n\n"
            f"{HASHTAGS}"
        )

    if angle == "B" and leader and laggard:
        return (
            f"In welke sector zijn webshops het verst met toegankelijkheid?\n\n"
            f"Koploper is {leader['label']}: {leader['pct']}% heeft een verklaring. "
            f"Achteraan staat {laggard['label']} met {laggard['pct']}%.\n\n"
            f"Sinds juni 2025 geldt de verplichting voor alle sectoren. "
            f"Het verschil laat zien dat het kan, en dat er nog werk is.\n\n"
            f"Bekijk hoe elke categorie ervoor staat op {DASHBOARD_URL}.\n\n"
            f"{HASHTAGS}"
        )

    if angle == "C" and fresh:
        return (
            f"Goed nieuws: deze week plaatsten weer webshops een toegankelijkheidsverklaring.\n\n"
            f"Onder andere {_join_names(fresh)}.\n\n"
            f"Sinds juni 2025 hoort die verklaring er te zijn. Mooi om te zien dat de lijst groeit.\n\n"
            f"De volledige stand staat op {DASHBOARD_URL}. Staat jouw webshop er al goed op?\n\n"
            f"{HASHTAGS}"
        )

    # Fallback en hoek D
    return (
        f"Wat is een toegankelijkheidsverklaring eigenlijk?\n\n"
        f"Het is een korte pagina waarop een webshop uitlegt hoe toegankelijk de site is "
        f"en welke stappen ze zetten. Sinds juni 2025 hoort die erbij.\n\n"
        f"Op dit moment heeft {cur['pct']}% van de Nederlandse webshops er een. "
        f"De rest dus nog niet.\n\n"
        f"Bekijk welke webshops wel en niet op {DASHBOARD_URL}.\n\n"
        f"{HASHTAGS}"
    )


def company_reshare(angle, cur):
    return (
        f"Onze oprichter Julia deelt de wekelijkse stand van de EAA Monitor: "
        f"{cur['pct']}% van de Nederlandse webshops heeft nu een toegankelijkheidsverklaring. "
        f"Volg de cijfers op {DASHBOARD_URL}."
    )


# ── Merkregel-bewaking ──

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F02F←-⇿⬀-⯿]"
)


def brand_issues(text):
    issues = []
    if "—" in text or "–" in text:
        issues.append("em-dash of en-dash gevonden (gebruik komma of twee zinnen)")
    if EMOJI_RE.search(text):
        issues.append("emoji gevonden (merkregel: geen emoji)")
    low = text.lower()
    for w in JARGON:
        if w in low:
            issues.append(f"jargon gevonden: '{w}'")
    return issues


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Genereer een concept-LinkedIn-post over de EAA Monitor")
    parser.add_argument("--angle", choices=["launch", "A", "B", "C", "D"], help="Forceer een invalshoek")
    parser.add_argument("--print", dest="only_print", action="store_true", help="Alleen tonen, niets wegschrijven")
    parser.add_argument("--force", action="store_true", help="Schrijf ook weg bij een merkregel-waarschuwing")
    args = parser.parse_args()

    results = _load(RESULTS_FILE, None)
    if not results:
        print("Kan data/results.json niet lezen.", file=sys.stderr)
        sys.exit(1)

    shops = public_webshops(results)
    cur = stats_from(shops)
    breakdown = sorted(category_breakdown(shops), key=lambda c: c["total"], reverse=True)
    cur_date = results["last_updated"][:10]

    history = _load(HISTORY_FILE, [])
    prev_pct = history[-2]["pct_with"] if len(history) >= 2 else None
    delta = (cur["pct"] - prev_pct) if prev_pct is not None else None

    prev_results = prev_week_results(cur_date)
    fresh = newly_added(shops, prev_results)
    # "launch" zolang we nog geen eigen week-op-week reeks hebben (history < 2).
    # De git-vergelijking voedt alleen 'nieuw toegevoegd', niet de hoekkeuze.
    has_week_over_week = prev_pct is not None

    angle = args.angle or choose_angle(delta, breakdown, fresh, has_week_over_week)
    if angle == "C" and not fresh:
        print("Let op: geen nieuw toegevoegde webshops gevonden, val terug op hoek D.", file=sys.stderr)
        angle = "D"

    post = render(angle, cur, delta, prev_pct, breakdown, fresh)
    reshare = company_reshare(angle, cur)

    issues = brand_issues(post) + brand_issues(reshare)

    header = (
        f"# LinkedIn-concept EAA Monitor\n"
        f"Datum: {_date_nl(date.today().isoformat())} | invalshoek: {angle} | "
        f"databron: meting {_date_nl(cur_date)}\n\n"
        f"## Post (Julia, persoonlijk)\n\n"
    )
    body = header + post + "\n\n## Herdeling (Proper Access-pagina)\n\n" + reshare + "\n"

    print(body)
    if issues:
        print("\n".join("WAARSCHUWING merkregel: " + i for i in issues), file=sys.stderr)

    if args.only_print:
        return
    if issues and not args.force:
        print("\nNiet weggeschreven wegens merkregel-waarschuwing. Gebruik --force om toch te schrijven.",
              file=sys.stderr)
        sys.exit(2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{date.today().isoformat()}.md"
    out_path.write_text(body, encoding="utf-8")
    print(f"\nConcept opgeslagen in {out_path}")


if __name__ == "__main__":
    main()
