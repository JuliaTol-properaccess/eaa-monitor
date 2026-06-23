#!/usr/bin/env python3
"""
Scrape Dutch webshop footers to check for accessibility statement links.
Uses Playwright (headless Chromium) to handle JavaScript-rendered pages.

Usage:
    python tools/scrape_footer.py
    python tools/scrape_footer.py --limit 5   # test with first 5 shops
"""

import json
import os
import re
import signal
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
OBJECTIONS_FILE = DATA_DIR / "objections.json"   # gedeeld door beide datasets
LLMS_FILE = PUBLIC_DIR / "llms.txt"              # gedeeld; elke dataset bezit één regio

# ── Datasets ──
# Dezelfde scrape- en bake-logica bedient alle sectorlijsten. Elke dataset
# wijst naar zijn eigen invoer/uitvoer, het HTML-bestand waarin de cijfers
# worden gebakken (target_html), de llms.txt-meetregio en de copy-velden.
# Default is "webshops", zodat bestaande aanroepen zonder --dataset
# ongewijzigd blijven werken.
#
# Sector-velden:
# - hub_prefix: marker-prefix van de compacte sectorkaart op index.html
#   (<!--STAT:{prefix}Total--> / <!--STAT:{prefix}PctWithout-->). None voor
#   webshops: index.html is daar al de target_html met de legacy ongeprefixte
#   markers (GEO-SUMMARY, STAT:total, ...).
# - llms_label: sectorlabel in het llms.txt-meetblok; None geeft de legacy
#   webshop-formulering "Laatste meting (...)".
# - llms_noun: kort zelfstandig naamwoord in het llms.txt-meetblok (kan
#   afwijken van noun, bv. fin: "instellingen").
# - toezichthouder: label voor hub-kaart en copy.
DATASETS = {
    "webshops": {
        "key": "webshops",
        "input_file": DATA_DIR / "webshops.json",
        "results_file": DATA_DIR / "results.json",
        "history_file": DATA_DIR / "history.json",
        "confirmed_file": DATA_DIR / "confirmed.json",
        "target_html": PUBLIC_DIR / "index.html",
        "llms_region": "MEASUREMENT",
        "llms_label": None,
        "llms_noun": "webshops",
        "hub_prefix": None,
        "toezichthouder": "ACM",
        "noun": "webshops",
        # Geen meetsamenvatting op de hub-homepage; de zes sectorkaarten
        # dragen de cijfers al. De GEO-SUMMARY-markers zijn uit index.html
        # verwijderd, dus deze patch moet uit blijven (anders harde fail).
        "geo_summary": False,
        "summary_heading": "E-commerce · ACM-toezicht",
        # Secundaire bake: het webshop-dashboard (monitor.html) zelf bevat geen
        # gebakken cijfers en is daardoor zonder JavaScript leeg voor crawlers.
        # We bakken er een GEO-SUMMARY-blok in (alleen de samenvatting; de
        # Dataset JSON-LD blijft op de homepage, monitor.html linkt ernaar via
        # mainEntity). Markers: GEO-SUMMARY:START/END in public/monitor.html.
        "summary_html": PUBLIC_DIR / "monitor.html",
        "dataset_id": "https://eaa-monitor.nl/#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse webshops",
        "content_url": "https://eaa-monitor.nl/data/results.json",
        "rescan_copy": "De monitor controleert alle webshops elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
    "financieel": {
        "key": "financieel",
        "input_file": DATA_DIR / "financieel.json",
        "results_file": DATA_DIR / "results-financieel.json",
        "history_file": DATA_DIR / "history-financieel.json",
        "target_html": PUBLIC_DIR / "monitor-financieel.html",
        "llms_region": "FIN-MEASUREMENT",
        "llms_label": "Financiële sector (AFM-toezicht)",
        "llms_noun": "instellingen",
        "hub_prefix": "fin",
        "toezichthouder": "AFM",
        "noun": "financiële instellingen",
        "summary_heading": "Financiële sector · AFM-toezicht",
        "dataset_id": "https://eaa-monitor.nl/monitor-financieel.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse financiële instellingen",
        "content_url": "https://eaa-monitor.nl/data/results-financieel.json",
        "rescan_copy": "De monitor controleert alle financiële instellingen elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
    "telecom": {
        "key": "telecom",
        "input_file": DATA_DIR / "telecom.json",
        "results_file": DATA_DIR / "results-telecom.json",
        "history_file": DATA_DIR / "history-telecom.json",
        "target_html": PUBLIC_DIR / "monitor-telecom.html",
        "llms_region": "TEL-MEASUREMENT",
        "llms_label": "Telecom (ACM-toezicht)",
        "llms_noun": "aanbieders",
        "hub_prefix": "tel",
        "toezichthouder": "ACM",
        "noun": "telecomaanbieders",
        "summary_heading": "Telecom · ACM-toezicht",
        "dataset_id": "https://eaa-monitor.nl/monitor-telecom.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse telecomaanbieders",
        "content_url": "https://eaa-monitor.nl/data/results-telecom.json",
        "rescan_copy": "De monitor controleert alle telecomaanbieders elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
    "vervoer": {
        "key": "vervoer",
        "input_file": DATA_DIR / "vervoer.json",
        "results_file": DATA_DIR / "results-vervoer.json",
        "history_file": DATA_DIR / "history-vervoer.json",
        "target_html": PUBLIC_DIR / "monitor-vervoer.html",
        "llms_region": "VERVOER-MEASUREMENT",
        "llms_label": "Personenvervoer (ILT-toezicht)",
        "llms_noun": "vervoerders",
        "hub_prefix": "vervoer",
        "toezichthouder": "ILT",
        "noun": "vervoerders",
        "summary_heading": "Personenvervoer · ILT-toezicht",
        "dataset_id": "https://eaa-monitor.nl/monitor-vervoer.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse personenvervoerders",
        "content_url": "https://eaa-monitor.nl/data/results-vervoer.json",
        "rescan_copy": "De monitor controleert alle vervoerders elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
    "media": {
        "key": "media",
        "input_file": DATA_DIR / "media.json",
        "results_file": DATA_DIR / "results-media.json",
        "history_file": DATA_DIR / "history-media.json",
        "target_html": PUBLIC_DIR / "monitor-media.html",
        "llms_region": "MEDIA-MEASUREMENT",
        "llms_label": "Media en streaming (toezicht Commissariaat voor de Media)",
        "llms_noun": "mediadiensten",
        "hub_prefix": "media",
        "toezichthouder": "Commissariaat voor de Media",
        "noun": "mediadiensten",
        "summary_heading": "Media & streaming · Commissariaat voor de Media",
        "dataset_id": "https://eaa-monitor.nl/monitor-media.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse mediadiensten",
        "content_url": "https://eaa-monitor.nl/data/results-media.json",
        "rescan_copy": "De monitor controleert alle mediadiensten elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
    "ebooks": {
        "key": "ebooks",
        "input_file": DATA_DIR / "ebooks.json",
        "results_file": DATA_DIR / "results-ebooks.json",
        "history_file": DATA_DIR / "history-ebooks.json",
        "target_html": PUBLIC_DIR / "monitor-ebooks.html",
        "llms_region": "EBOOKS-MEASUREMENT",
        "llms_label": "E-books (ACM-toezicht)",
        "llms_noun": "e-bookplatforms",
        "hub_prefix": "ebooks",
        "toezichthouder": "ACM",
        "noun": "e-bookplatforms",
        "summary_heading": "E-books · ACM-toezicht",
        "dataset_id": "https://eaa-monitor.nl/monitor-ebooks.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse e-bookplatforms",
        "content_url": "https://eaa-monitor.nl/data/results-ebooks.json",
        "rescan_copy": "De monitor controleert alle e-bookplatforms elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
    },
}

# Keywords to detect accessibility statement links (case-insensitive)
KEYWORDS_TEXT = [
    "toegankelijkheid",
    "toegankelijkheidsverklaring",
    "accessibility",
    "barrierefreiheit",
]
KEYWORDS_HREF = [
    "toegankelijkheid",
    "toegankelijkheidsverklaring",
    "accessibility",
    "a11y",
]
# Strenge subset voor de ruwe-HTML-fallback. Daar scannen we ook asset-URL's
# (a11y.js, accessibility.css), dus "accessibility"/"a11y" alleen zou massaal
# vals-positief zijn. Het volledige woord in een URL is vrijwel altijd echt.
KEYWORDS_HREF_STRONG = [
    "toegankelijkheidsverklaring",
    "accessibility-statement",
    "accessibilitystatement",
]

# Toegankelijkheids-overlay-widgets en plugin-vendors. Een link naar zo'n
# leverancier is een knop/marketingverwijzing, GEEN toegankelijkheidsverklaring;
# een treffer hier is altijd vals-positief. Host-suffix-match (ook subdomeinen).
OVERLAY_VENDOR_DOMAINS = {
    "accessibe.com",
    "acsbapp.com",
    "acsbap.com",
    "userway.org",
    "userway.com",
    "audioeye.com",
    "equalweb.com",
    "reciteme.com",
    "recite.me",
    "user1st.com",
    "allyable.com",
    "adally.com",
    "useaccessibility.com",
    "max-access.com",
    "dj-extensions.com",
}

# Een echt footer-/navigatielabel is kort ("Toegankelijkheidsverklaring"). Matcht
# het trefwoord in een veel langere linktekst, dan zit het woord in marketing- of
# bodytekst (bv. "...de populariteit komt voort uit de toegankelijkheid ervan"):
# dat is geen verklaring-link. Alleen op linktekst matchen onder deze lengte; de
# href-match (URL bevat het trefwoord) heeft geen lengtegrens nodig.
MAX_LINK_TEXT_LEN = 60

# Playwright settings
NAVIGATION_TIMEOUT = 15000  # 15 seconds

# Minimale dekking bij --merge: onder deze fractie van de invoerlijst wordt er
# niet gefinaliseerd (beschermt tegen publiceren van een deelmeting na shard-falen).
MERGE_COVERAGE_THRESHOLD = 0.9

# Maximaal foutpercentage in een run: daarboven wordt er niet gepubliceerd.
# Een browser- of netwerkstoring halverwege zou anders een week vol valse
# 'errors' live bakken en in history.json vastleggen. Normaal is ~10%.
ERROR_RATE_THRESHOLD = 0.25

# Wachten op de footer i.p.v. een vaste 2s: de meeste sites hebben de footer al
# bij domcontentloaded, dan kost dit vrijwel niets. De settle vangt links die
# ná het verschijnen van de footer nog door JS worden geïnjecteerd; 500ms bleek
# te kort voor overlay-widgets (Lyca Mobile en Transavia flipten tussen runs),
# 1500ms is stabiel en per site nog steeds korter dan de oude vaste 2s.
FOOTER_WAIT_TIMEOUT = 2000
FOOTER_SETTLE_MS = 1500

# Korte pauze tussen requests. Elke request gaat naar een ander domein, dus
# per-host rate limiting speelt niet; dit ontziet alleen de runner zelf.
REQUEST_PAUSE_S = 0.2

# Resources die we niet nodig hebben om footerlinks te vinden. Blokkeren
# scheelt het merendeel van de bandbreedte en laadtijd per site.
BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}

# Foutmeldingen die op een gecrashte tab/browser wijzen. Zonder herstel zou
# elke volgende site in de run onterecht als 'error' geteld worden.
CRASH_MARKERS = (
    "Target page, context or browser has been closed",
    "Target closed",
    "browser has been disconnected",
    "Connection closed",
)

# Vers context+page elke N sites, als rem op geheugengroei in lange runs.
CONTEXT_RECYCLE_EVERY = 200

# Tussentijds de verzamelde resultaten naar het shard-bestand wegschrijven elke N
# sites, zodat een shard die alsnog faalt of getimed wordt zijn werk niet verliest
# (de merge gebruikt dan het laatst geflushte deelbestand).
FLUSH_EVERY = 100

# Harde wall-clock-limiet per site, ongeacht welke operatie hangt (goto,
# wait_for_selector, cookie-wall-clicks, retries, recheck_unblocked). Zonder dit
# kon één trage of bot-beschermde site een shard tot de 6-uurslimiet van GitHub
# Actions laten hangen, waardoor de hele run werd geannuleerd en niets werd
# gepubliceerd (de oorzaak van de mislukte crons van 8, 15 en 22 juni 2026). Een
# cap-hit telt als "timeout" (= niet te controleren), nooit als "zonder verklaring".
PER_SITE_CAP_S = 90


class SiteTimeout(Exception):
    """Opgeworpen door de per-site-watchdog wanneer PER_SITE_CAP_S verstrijkt."""


def _raise_site_timeout(signum, frame):
    raise SiteTimeout()


class site_deadline:
    """Contextmanager: harde per-site wall-clock-cap via SIGALRM.

    Werkt in de main thread op Unix (zo draait de scrape in CI en op de VPS).
    Valt elders (geen SIGALRM, of niet de main thread) stil terug op alleen de
    per-call-timeouts van Playwright, zodat de tool overal blijft werken.
    """

    def __init__(self, seconds):
        self.seconds = seconds
        self.enabled = hasattr(signal, "SIGALRM")
        self._old_handler = None

    def __enter__(self):
        if self.enabled:
            try:
                self._old_handler = signal.signal(signal.SIGALRM, _raise_site_timeout)
                signal.alarm(self.seconds)
            except (ValueError, OSError):
                # Niet de main thread: cap uitschakelen, per-call-timeouts blijven.
                self.enabled = False
        return self

    def __exit__(self, *exc):
        if self.enabled:
            signal.alarm(0)
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False

# Bevestigd-groen-lijst: sites met een geverifieerde verklaring slaan we op de
# wekelijkse run over en herverifieren we pas na zoveel dagen. Bespaart werk en
# beschermt handmatig geverifieerde greens (bv. bol.com) tegen wegvallen door een
# transiente bot-challenge. Een verklaring die later weggehaald wordt, valt
# binnen dit venster alsnog op.
REVERIFY_DAYS = 30
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def find_footer_area(soup):
    """Find the footer area of the page. Returns a list of elements to search."""
    areas = []

    # 1. <footer> elements
    footers = soup.find_all("footer")
    if footers:
        areas.extend(footers)

    # 2. Elements with footer-like IDs or classes
    footer_patterns = re.compile(r"footer|site-footer|page-footer|main-footer", re.I)
    for el in soup.find_all(id=footer_patterns):
        if el not in areas:
            areas.append(el)
    for el in soup.find_all(class_=footer_patterns):
        if el not in areas:
            areas.append(el)

    return areas


def safe_statement_url(base_url, href):
    """Resolve href against the page URL; accept only http(s) results.

    Footer content is untrusted: a malicious site could otherwise smuggle a
    javascript:- or data:-URL into results.json, which the dashboard renders
    as a clickable "Bekijk verklaring" link.
    """
    resolved = urljoin(base_url, href)
    if resolved.lower().startswith(("http://", "https://")):
        return resolved
    return None


def is_overlay_vendor(url):
    """True als de URL naar een toegankelijkheids-overlay/plugin-vendor wijst."""
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OVERLAY_VENDOR_DOMAINS)


def check_links_for_statement(links, base_url):
    """Check a list of <a> tags for accessibility statement links."""
    for link in links:
        href = link.get("href", "")
        raw_text = link.get_text(strip=True)
        text = raw_text.lower()
        href_lower = href.lower()

        statement_url = safe_statement_url(base_url, href)
        if statement_url is None:
            continue

        # Overlay-widget/plugin-vendor: nooit een verklaring, dus overslaan.
        if is_overlay_vendor(statement_url):
            continue

        # Linktekst: alleen een kort, label-achtig label telt (anders matcht het
        # woord ook in lange marketing-/bodytekst).
        if len(raw_text) <= MAX_LINK_TEXT_LEN and any(kw in text for kw in KEYWORDS_TEXT):
            return {
                "has_statement": True,
                "statement_url": statement_url,
                "statement_link_text": raw_text,
            }

        # Check href (URL bevat het trefwoord) - geen lengtegrens nodig.
        if any(kw in href_lower for kw in KEYWORDS_HREF):
            return {
                "has_statement": True,
                "statement_url": statement_url,
                "statement_link_text": raw_text,
            }

    return None


def _same_site(base_url, candidate_url):
    """True if candidate lives on the same registrable-ish domain as base.

    Vergelijkt de laatste twee host-labels, zodat www.shop.nl en shop.nl matchen.
    Houdt de raw-HTML-fallback hieronder behoudend: een echte verklaring staat op
    het eigen domein van de winkel, niet op een externe toegankelijkheids-overlay
    (accessibe.com, userway.org), die anders een vals 'gevonden' zou opleveren.
    """
    try:
        a = (urlparse(base_url).hostname or "").lower()
        b = (urlparse(candidate_url).hostname or "").lower()
    except ValueError:
        return False
    if not a or not b:
        return False
    return a.split(".")[-2:] == b.split(".")[-2:]


# URL-fragmenten in embedded JSON gebruiken vaak / of \/ als slash; die
# normaliseren we eerst. Daarna pakken we absolute of root-relatieve URL's.
_RAW_URL_RE = re.compile(r"""(https?://[^\s"'<>\\)]+|/[A-Za-z0-9._~%/\-]+)""")
# Statische assets: een a11y.js of accessibility.css is code, geen verklaring.
_ASSET_EXT_RE = re.compile(
    r"\.(?:js|mjs|cjs|css|map|json|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|eot|mp4|webm)(?:$|[?#])",
    re.I,
)
_ASSET_DIR_RE = re.compile(
    r"/(?:wp-content|wp-includes|assets|static|dist|build|node_modules|js|css|fonts?)/",
    re.I,
)


def find_statement_in_raw_html(html, base_url):
    """Sterke fallback voor JS-framework-footers zonder platte <a>.

    Sommige sites (bv. de PWA van MediaMarkt) renderen de verklaring-link als
    knop of bewaren hem in embedded JSON, dus de <a>-scan mist hem. Hier zoeken
    we een URL waarvan het pad het volledige woord 'toegankelijkheidsverklaring'
    (of accessibility-statement) bevat. Behoudend om valse treffers te vermijden:
    nooit losse marketingtekst of de losse termen 'accessibility'/'a11y' (die in
    asset-bestanden zitten), alleen het eigen domein, en geen statische assets.
    """
    unescaped = html.replace("\\u002F", "/").replace("\\u002f", "/").replace("\\/", "/")
    for match in _RAW_URL_RE.finditer(unescaped):
        candidate = match.group(1).rstrip('",.')
        if not any(kw in candidate.lower() for kw in KEYWORDS_HREF_STRONG):
            continue
        resolved = safe_statement_url(base_url, candidate)
        if resolved is None or not _same_site(base_url, resolved):
            continue
        path = urlparse(resolved).path
        if _ASSET_EXT_RE.search(path) or _ASSET_DIR_RE.search(path):
            continue
        return {
            "has_statement": True,
            "statement_url": resolved,
            "statement_link_text": "Toegankelijkheidsverklaring",
        }
    return None


def _write_atomic(path, text):
    """Write via a tmp file + os.replace so a crash or kill mid-write never
    leaves a truncated (unparseable) file behind."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# Veelvoorkomende "accepteer cookies"-knoppen (grote consent-managers + losse
# tekstvarianten). Best-effort: een verkeerde of ontbrekende knop is onschadelijk.
COOKIE_ACCEPT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    "[data-testid='uc-accept-all-button']",
    "button[aria-label*='accept' i]",
    "button[aria-label*='akkoord' i]",
    ".cc-allow",
    ".cookie-accept",
]


def _dismiss_cookie_wall(page):
    """Best-effort: klik een veelvoorkomende cookie-accept-knop weg.

    Sommige consent-overlays renderen de footer (of de footerlinks) pas na een
    keuze. Kort getimed en in try/except: mislukt het, dan gaan we gewoon door,
    want de footer staat meestal toch al in de DOM.
    """
    for sel in COOKIE_ACCEPT_SELECTORS:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click(timeout=1000)
                page.wait_for_timeout(300)
                return
        except Exception:
            continue


def _scroll_to_bottom(page):
    """Scroll naar beneden zodat lazy-loaded footers/links renderen.

    Veel footers (en hun links) hangen aan een IntersectionObserver en verschijnen
    pas als ze in beeld komen. Eenmalig en goedkoop; de settle in _wait_for_footer
    vangt de render daarna op.
    """
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    except Exception:
        pass


def _wait_for_footer(page):
    """Wait until a footer(-like) element is in the DOM instead of a fixed 2s.

    Most sites already have the footer at domcontentloaded, so this returns
    almost immediately; JS-rendered footers get up to FOOTER_WAIT_TIMEOUT. The
    settle afterwards catches links that JS fills in right after the footer
    appears. No footer-like element at all: fall through, check_webshop scans
    all links on the page anyway.
    """
    _scroll_to_bottom(page)
    try:
        page.wait_for_selector(
            "footer, [class*='footer' i], [id*='footer' i]",
            timeout=FOOTER_WAIT_TIMEOUT,
            state="attached",
        )
    except PlaywrightTimeout:
        pass
    page.wait_for_timeout(FOOTER_SETTLE_MS)


def check_webshop(page, url):
    """Check a single webshop for an accessibility statement link."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
        _dismiss_cookie_wall(page)
        _wait_for_footer(page)
    except PlaywrightTimeout:
        # Retry once
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
            _dismiss_cookie_wall(page)
            _wait_for_footer(page)
        except PlaywrightTimeout:
            return {
                "has_statement": False,
                "statement_url": None,
                "statement_link_text": None,
                "scrape_status": "timeout",
                "error": f"Timeout after {NAVIGATION_TIMEOUT}ms (2 attempts)",
            }
        except Exception as e:
            return {
                "has_statement": False,
                "statement_url": None,
                "statement_link_text": None,
                "scrape_status": "error",
                "error": str(e),
            }
    except Exception as e:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": str(e),
        }

    try:
        html = page.content()
    except Exception as e:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": str(e),
        }

    return classify_html(html, url)


# Woorden die op een echte toegankelijkheidsverklaring wijzen. Bewust ruim, maar
# specifiek genoeg dat een aanvraag-/contactformulier (zoals de "Toegankelijkheid
# website"-pagina van Decathlon, die alleen een formulier toont) niet matcht. Eén
# treffer volstaat. We laten bewust de losse term "verklaring" weg: die staat ook
# op privacy-/cookie-pagina's en op aanvraagformulieren ("verklaring aanvragen").
STATEMENT_CONTENT_MARKERS = [
    "toegankelijkheidsverklaring",
    "accessibility statement",
    "barrierefreiheitserklärung",
    "wcag",
    "en 301 549",
    "web content accessibility",
    "voldoet aan",
    "voldoet niet",
    "voldoet gedeeltelijk",
    "nalevingsstatus",
    "compliance status",
    "toegankelijkheidsnorm",
    "tekortkomingen",
    "handhavingsprocedure",
    "feedback en contactgegevens",
]


def statement_page_has_statement(text: str) -> bool:
    """True als de tekst van een gelinkte pagina verklaring-inhoud bevat.

    Pure, deterministisch testbare functie (geen netwerk). Gebruikt door de
    content-check die een footer-link naar een 'toegankelijkheid'-pagina verifieert:
    staat er alleen een aanvraag-/contactformulier en geen verklaring, dan telt het
    niet als 'met verklaring'.
    """
    low = (text or "").lower()
    return any(marker in low for marker in STATEMENT_CONTENT_MARKERS)


def classify_html(html, url):
    """Bepaal de verklaring-status uit gerenderde HTML (geen Playwright nodig).

    Apart van check_webshop zodat de detectielogica deterministisch te testen is
    tegen opgeslagen HTML-fixtures (zie tests/). Volgorde: footer-area's eerst,
    dan alle <a> op de pagina, dan de ruwe-HTML-fallback voor JS-framework-links,
    en als laatste de bot-challenge-/lege-render-detectie.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try footer areas first
    footer_areas = find_footer_area(soup)
    if footer_areas:
        for area in footer_areas:
            links = area.find_all("a", href=True)
            result = check_links_for_statement(links, url)
            if result:
                result["scrape_status"] = "success"
                result["error"] = None
                return result

    # Fallback: check all links on the page
    all_links = soup.find_all("a", href=True)
    result = check_links_for_statement(all_links, url)
    if result:
        result["scrape_status"] = "success"
        result["error"] = None
        return result

    # Fallback 2: link verstopt in een JS-framework (knop/embedded JSON) in
    # plaats van een platte <a>. Vangt o.a. de PWA-footer van MediaMarkt.
    result = find_statement_in_raw_html(html, url)
    if result:
        result["scrape_status"] = "success"
        result["error"] = None
        return result

    # Een pagina met minder dan een handvol links is vrijwel zeker een
    # bot-challenge ("Challenge Validation", "Attention Required!"), wachtrij
    # ("Even geduld...") of lege render; een echte homepage heeft er
    # tientallen. Niet op footer-aanwezigheid filteren: interstitials hebben
    # vaak elementen met footer-achtige classes. "Geen verklaring" zou hier
    # geen eerlijke meting zijn: rapporteer "niet te controleren".
    if len(all_links) < 5:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": (
                f"Pagina heeft maar {len(all_links)} links; "
                "vermoedelijk bot-protectie, wachtrij of lege render"
            ),
        }

    return {
        "has_statement": False,
        "statement_url": None,
        "statement_link_text": None,
        "scrape_status": "success",
        "error": None,
    }


# ── GEO output: bake stats + schema into served HTML and llms.txt ──
#
# The dashboard renders all numbers client-side from results.json, so AI-crawlers
# that do not run JavaScript see empty placeholders. To stay citable we bake the
# headline numbers, a Dataset JSON-LD block and llms.txt at scrape time. The
# values mirror public/app.js exactly: webshops that filed an objection are
# excluded, and "met verklaring" means has_statement AND scrape_status success.

CATEGORY_LABELS = {
    "marketplace": "Marketplace",
    "elektronica": "Elektronica",
    "mode": "Mode",
    "supermarkt": "Supermarkt",
    "drogisterij": "Drogisterij",
    "wonen": "Wonen",
    "sport": "Sport",
    "boeken": "Boeken",
    "speelgoed": "Speelgoed",
    "overig": "Overig",
}

MONTHS_NL = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def _normalize_url(url):
    """Mirror app.js normalizeUrl: strip protocol, leading www, trailing slash."""
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"/+$", "", u)
    return u


def _load_objection_urls():
    """Return a set of normalized URLs that have filed an objection."""
    try:
        with open(OBJECTIONS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {_normalize_url(o.get("url")) for o in data if o.get("url")}
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return set()


def _load_confirmed(ds):
    """Lees de bevestigd-groen-lijst van een dataset als dict op genormaliseerde URL.

    Vorm per entry: {url, statement_url, statement_link_text, confirmed (YYYY-MM-DD)}.
    Geen bestand of geen confirmed_file in de dataset: lege dict (geen overslaan).
    """
    path = ds.get("confirmed_file")
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    sites = data.get("sites", data) if isinstance(data, dict) else data
    out = {}
    for e in sites if isinstance(sites, list) else []:
        if e.get("url") and e.get("confirmed"):
            out[_normalize_url(e["url"])] = e
    return out


def _confirmed_is_fresh(confirmed_date, now_iso):
    """True als de verklaring binnen REVERIFY_DAYS opnieuw is geverifieerd."""
    try:
        d = datetime.strptime(str(confirmed_date)[:10], "%Y-%m-%d").date()
        today = datetime.fromisoformat(now_iso).date()
    except ValueError:
        return False
    return (today - d).days < REVERIFY_DAYS


def _pct(n, total):
    return round(n / total * 100) if total else 0


def _public_stats(webshops):
    """Compute stats the way the dashboard shows them (objections already removed)."""
    total = len(webshops)
    with_statement = sum(
        1 for r in webshops if r["has_statement"] and r["scrape_status"] == "success"
    )
    errors = sum(1 for r in webshops if r["scrape_status"] != "success")
    without_statement = total - with_statement - errors
    return {
        "total": total,
        "with_statement": with_statement,
        "without_statement": without_statement,
        "errors": errors,
        "pct_with": _pct(with_statement, total),
        "pct_without": _pct(without_statement, total),
        "pct_error": _pct(errors, total),
    }


def _category_breakdown(webshops):
    """Per-category found/total, sorted by total descending (matches the cards)."""
    cats = {}
    for r in webshops:
        c = r["category"]
        cats.setdefault(c, {"total": 0, "found": 0})
        cats[c]["total"] += 1
        if r["has_statement"] and r["scrape_status"] == "success":
            cats[c]["found"] += 1
    return sorted(cats.items(), key=lambda kv: kv[1]["total"], reverse=True)


def _date_nl(iso):
    """Format an ISO timestamp as e.g. '6 juni 2026' (date part only, no version quirks)."""
    year, month, day = iso[:10].split("-")
    return f"{int(day)} {MONTHS_NL[int(month) - 1]} {year}"


def _replace_region(html, start, end, new_inner):
    """Replace everything between two literal marker strings, keeping the markers.

    Fails hard when the start marker is missing or duplicated, or the end marker
    is missing: a silent mismatch would leave stale numbers live while the cron
    stays green.
    """
    occurrences = html.count(start)
    if occurrences != 1:
        sys.exit(
            f"FOUT: marker {start!r} komt {occurrences}x voor in het doelbestand "
            f"(verwacht: precies 1x). Niets gepatcht."
        )
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    new_html, n = pattern.subn(lambda _m: start + new_inner + end, html, count=1)
    if n != 1:
        sys.exit(f"FOUT: eindmarker {end!r} na {start!r} niet gevonden. Niets gepatcht.")
    return new_html


def _geo_summary_inner(stats, date_nl, ds):
    """Alleen de samenvattingskaart. De section/grid-wrapper staat in de
    doel-HTML, zodat index.html twee kaarten (e-commerce + financieel) naast
    elkaar kan tonen en monitor-financieel.html er een toont."""
    noun = ds["noun"]
    heading = ds.get("summary_heading", "")
    heading_html = (
        f'<p class="eyebrow text-brand mb-3">{heading}</p>\n          '
        if heading else ""
    )
    return f"""
      <div class="rounded-xl bg-softblue ring-1 ring-brand-light p-7 md:p-9 text-ink h-full">
        <div class="max-w-3xl">
          {heading_html}<p class="text-lg leading-relaxed">
            Op <strong>{date_nl}</strong> controleerde de EAA Monitor
            <strong>{stats['total']} Nederlandse {noun}</strong> op een toegankelijkheidsverklaring:
          </p>
          <ul class="mt-4 space-y-2.5">
            <li class="flex items-start gap-3"><span class="status-dot bg-status-found mt-[7px]" aria-hidden="true"></span><span><strong>{stats['with_statement']} {noun} ({stats['pct_with']}%)</strong> publiceren een verklaring</span></li>
            <li class="flex items-start gap-3"><span class="status-dot bg-status-notfound mt-[7px]" aria-hidden="true"></span><span><strong>{stats['without_statement']} ({stats['pct_without']}%)</strong> doen dat niet</span></li>
            <li class="flex items-start gap-3"><span class="status-dot bg-status-error mt-[7px]" aria-hidden="true"></span><span>bij <strong>{stats['errors']} ({stats['pct_error']}%)</strong> kon de controle niet worden voltooid</span></li>
          </ul>
          <p class="mt-4 text-sm text-gray-500">Laatst bijgewerkt: {date_nl}. {ds['rescan_copy']}</p>
        </div>
      </div>
    """


def _dataset_jsonld(stats, date_nl, date_iso, ds):
    noun = ds["noun"]
    noun_cap = noun[0].upper() + noun[1:]
    # De pagina waar deze dataset gedocumenteerd staat: het deel van dataset_id
    # vóór het #-fragment (homepage voor webshops, de eigen monitorpagina voor de
    # sectoren). Zo wijst Dataset.url niet langer altijd naar de homepage.
    page_url = ds["dataset_id"].rsplit("#", 1)[0]
    obj = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": ds["dataset_id"],
        "name": ds["dataset_name"],
        "description": (
            f"Wekelijkse meting of {stats['total']} Nederlandse {noun} een "
            f"toegankelijkheidsverklaring publiceren. Op {date_nl}: "
            f"{stats['with_statement']} met verklaring, {stats['without_statement']} zonder, "
            f"{stats['errors']} niet te controleren."
        ),
        "url": page_url,
        "creator": {
            "@type": "Organization",
            "@id": "https://eaa-monitor.nl/#organization",
            "name": "EAA Monitor",
            "url": "https://eaa-monitor.nl/",
        },
        "spatialCoverage": {"@type": "Place", "name": "Nederland"},
        "keywords": [
            "European Accessibility Act",
            "toegankelijkheidsverklaring",
            noun,
            "digitale toegankelijkheid",
        ],
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "inLanguage": "nl-NL",
        "dateModified": date_iso,
        "temporalCoverage": f"2026-03/{date_iso[:7]}",
        "measurementTechnique": (
            "Geautomatiseerde controle van de footer op links naar een "
            "toegankelijkheidsverklaring"
        ),
        "variableMeasured": [
            {"@type": "PropertyValue", "name": f"Aantal gecontroleerde {noun}", "value": stats["total"]},
            {"@type": "PropertyValue", "name": f"{noun_cap} met toegankelijkheidsverklaring", "value": stats["with_statement"]},
            {"@type": "PropertyValue", "name": f"{noun_cap} zonder toegankelijkheidsverklaring", "value": stats["without_statement"]},
            {"@type": "PropertyValue", "name": f"{noun_cap} niet te controleren", "value": stats["errors"]},
            {"@type": "PropertyValue", "name": "Percentage met verklaring", "value": stats["pct_with"], "unitText": "PERCENT"},
        ],
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": ds["content_url"],
        }],
    }
    return (
        "\n  <script type=\"application/ld+json\">\n  "
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n  </script>\n  "
    )


def patch_target_html(stats, date_nl, date_iso, ds):
    """Bake current numbers and the Dataset JSON-LD into the dataset's served HTML."""
    target = ds["target_html"]
    html = target.read_text(encoding="utf-8")
    if ds.get("geo_summary", True):
        html = _replace_region(html, "<!-- GEO-SUMMARY:START -->", "<!-- GEO-SUMMARY:END -->",
                               _geo_summary_inner(stats, date_nl, ds))
    html = _replace_region(html, "<!--STAT:total-->", "<!--/STAT-->", str(stats["total"]))
    html = _replace_region(html, "<!--STAT:pctWith-->", "<!--/STAT-->", f"{stats['pct_with']}%")
    html = _replace_region(html, "<!--STAT:pctWithout-->", "<!--/STAT-->", f"{stats['pct_without']}%")
    html = _replace_region(html, "<!--LASTUPDATED-->", "<!--/LASTUPDATED-->",
                           f"Laatst bijgewerkt: {date_nl}")
    html = _replace_region(html, "<!-- JSONLD-DATASET:START -->", "<!-- JSONLD-DATASET:END -->",
                           _dataset_jsonld(stats, date_nl, date_iso, ds))
    _write_atomic(target, html)
    print(f"Patched {target}")


def patch_secondary_summary(stats, date_nl, ds):
    """Bak een GEO-SUMMARY-blok in een tweede HTML-bestand (ds['summary_html']).

    Gebruikt voor de webshops: de Dataset JSON-LD en de hero-cijfers staan op de
    homepage, maar het dashboard monitor.html had zelf geen gebakken cijfers en
    was daardoor zonder JavaScript leeg voor crawlers. We patchen hier alleen de
    GEO-SUMMARY-regio; ontbreekt die, dan faalt _replace_region hard (bewust).
    """
    target = ds.get("summary_html")
    if not target:
        return
    if not target.exists():
        print(f"Secundaire samenvatting overgeslagen: {target} bestaat niet")
        return
    html = target.read_text(encoding="utf-8")
    html = _replace_region(html, "<!-- GEO-SUMMARY:START -->", "<!-- GEO-SUMMARY:END -->",
                           _geo_summary_inner(stats, date_nl, ds))
    _write_atomic(target, html)
    print(f"Patched {target} (secundaire samenvatting)")


def patch_hub_card(stats, ds):
    """Vul de compacte sectorkaart op de hub-homepage (index.html).

    Markers: <!--STAT:{hub_prefix}Total--> en <!--STAT:{hub_prefix}PctWithout-->.
    Webshops (hub_prefix None) slaat dit over: index.html is daar al de
    target_html met de legacy ongeprefixte markers. Ontbreken béide markers,
    dan is de kaart nog niet uitgerold en slaan we over (bootstrap); bij een
    halve kaart faalt _replace_region hard.
    """
    prefix = ds.get("hub_prefix")
    if not prefix:
        return
    index = PUBLIC_DIR / "index.html"
    if not index.exists():
        return
    total_marker = f"<!--STAT:{prefix}Total-->"
    pct_marker = f"<!--STAT:{prefix}PctWithout-->"
    html = index.read_text(encoding="utf-8")
    if total_marker not in html and pct_marker not in html:
        print(f"Hub-kaart voor {ds['key']} nog niet aanwezig op index.html; overgeslagen")
        return
    html = _replace_region(html, total_marker, "<!--/STAT-->", str(stats["total"]))
    html = _replace_region(html, pct_marker, "<!--/STAT-->", f"{stats['pct_without']}%")
    _write_atomic(index, html)
    print(f"Patched {index} (hub-kaart {ds['key']})")


# llms.txt is een hand-onderhouden skelet (in git) met per sector een eigen
# meet-regio plus de artikellijst-regio van tools/build_articles.py. De scraper
# patcht alleen de inhoud van de eigen regio (ds["llms_region"]) en faalt hard
# als die regio ontbreekt: stil invoegen of het bestand herschrijven kan de
# hand-onderhouden secties en de regio-volgorde slopen.


def _llms_measurement_inner(stats, date_nl, ds):
    """De regelinhoud van een meet-regio (tussen de markers).

    llms_label None geeft de legacy webshop-formulering ("Laatste meting ...");
    met label wordt het "<label>, laatste meting ...". Byte-identiek aan de
    blokken die de oude webshop- en fin-specifieke functies schreven.
    """
    intro = f"{ds['llms_label']}, laatste meting" if ds.get("llms_label") else "Laatste meting"
    return (
        f"\n{intro} ({date_nl}): {stats['total']} {ds['llms_noun']} gecontroleerd,\n"
        f"{stats['with_statement']} ({stats['pct_with']}%) met toegankelijkheidsverklaring,\n"
        f"{stats['without_statement']} ({stats['pct_without']}%) zonder, en\n"
        f"{stats['errors']} ({stats['pct_error']}%) niet te controleren.\n"
    )


def patch_llms_measurement(stats, date_nl, ds):
    """Patch de meet-regio van deze dataset in public/llms.txt."""
    if not LLMS_FILE.exists():
        sys.exit(f"FOUT: {LLMS_FILE} bestaat niet; meet-regio {ds['llms_region']} niet gepatcht.")
    start = f"<!-- {ds['llms_region']}:START -->"
    end = f"<!-- {ds['llms_region']}:END -->"
    text = LLMS_FILE.read_text(encoding="utf-8")
    text = _replace_region(text, start, end, _llms_measurement_inner(stats, date_nl, ds))
    _write_atomic(LLMS_FILE, text)
    print(f"Patched {LLMS_FILE} ({ds['llms_region']})")


def update_history(stats, date_iso, ds):
    """Append a weekly summary to the dataset's history.json (idempotent per date).

    Append-only time series that feeds the LinkedIn post-generator (week-over-week
    deltas) and, later, a trend chart on the dashboard. Re-running on the same day
    overwrites that day's entry instead of duplicating it.
    """
    history_file = ds["history_file"]
    try:
        with open(history_file, encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []  # eerste run: legitiem leeg beginnen
    except json.JSONDecodeError as exc:
        # Nooit stil de complete meetgeschiedenis weggooien: hard falen zodat
        # iemand het bestand herstelt (het staat in git).
        sys.exit(f"FOUT: {history_file} is geen geldige JSON ({exc}); history niet bijgewerkt.")
    if not isinstance(history, list):
        sys.exit(f"FOUT: {history_file} moet een JSON-lijst zijn; history niet bijgewerkt.")

    entry = {
        "date": date_iso,
        "total": stats["total"],
        "with_statement": stats["with_statement"],
        "without_statement": stats["without_statement"],
        "errors": stats["errors"],
        "pct_with": stats["pct_with"],
    }

    history = [h for h in history if h.get("date") != date_iso]
    history.append(entry)
    history.sort(key=lambda h: h["date"])

    _write_atomic(history_file, json.dumps(history, ensure_ascii=False, indent=2))
    print(f"Updated {history_file} ({len(history)} meetpunten)")


def generate_geo_assets(output, ds):
    """Bake stats/schema into the dataset's served HTML and llms.txt."""
    objection_urls = _load_objection_urls()
    public_entries = [
        r for r in output["webshops"] if _normalize_url(r["url"]) not in objection_urls
    ]
    stats = _public_stats(public_entries)
    date_nl = _date_nl(output["last_updated"])
    date_iso = output["last_updated"][:10]
    patch_target_html(stats, date_nl, date_iso, ds)
    patch_secondary_summary(stats, date_nl, ds)
    patch_hub_card(stats, ds)
    patch_llms_measurement(stats, date_nl, ds)
    update_history(stats, date_iso, ds)


def _block_unneeded_resources(route):
    """Abort requests for resources we don't need to find footer links."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()


def _looks_like_crash(error):
    """True if the error string points at a dead tab/browser, not a bad site."""
    return bool(error) and any(marker in error for marker in CRASH_MARKERS)


def _fresh_page(p, browser, old_context=None):
    """Return (browser, context, page), relaunching the browser if it died."""
    if old_context is not None:
        try:
            old_context.close()
        except Exception:
            pass
    context_opts = {
        "user_agent": USER_AGENT,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "nl-NL",
    }
    try:
        context = browser.new_context(**context_opts)
    except Exception:
        # Het hele browserproces is weg; opnieuw starten.
        try:
            browser.close()
        except Exception:
            pass
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**context_opts)
    context.route("**/*", _block_unneeded_resources)
    context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
    context.set_default_timeout(NAVIGATION_TIMEOUT)
    page = context.new_page()
    return browser, context, page


def recheck_unblocked(browser, url):
    """Haal één URL opnieuw op met alle resources toegestaan (geen route-blok).

    Sites achter bot-management (bv. bol.com) zien onze geblokkeerde
    image/css/font-requests als bot-signatuur en serveren een vrijwel lege
    challenge-pagina. Dezelfde URL één keer met alle resources ophalen levert dan
    de echte pagina op. Alleen als fallback voor challenge-achtige resultaten, dus
    de extra kosten blijven klein.
    """
    context = None
    try:
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="nl-NL",
        )
        context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        context.set_default_timeout(NAVIGATION_TIMEOUT)
        page = context.new_page()
        return check_webshop(page, url)
    except Exception as e:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": str(e),
        }
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass


def _verify_statement_page(browser, base_url, result):
    """Controleer dat een gevonden verklaring-link ook echt naar een verklaring leidt.

    Decathlon linkt in de footer naar een 'Toegankelijkheid website'-pagina die geen
    verklaring bevat, alleen een aanvraagformulier; dat telde toch als 'met verklaring'.
    Voor een kandidaat op het EIGEN domein (HTML, geen PDF) halen we de pagina op met een
    NIET-geblokkeerde context (net als recheck_unblocked; anders kan resource-blocking een
    challenge/lege render triggeren bij bot-gevoelige sites zoals bol.com) en checken de
    tekst op verklaring-inhoud. Geen inhoud -> telt als 'zonder verklaring', met de gevonden
    link bewaard in `statement_link_url`. PDF- en cross-domein-links blijven sterk bewijs
    (gedrag ongewijzigd; die halen we niet op).
    """
    if not result.get("has_statement") or not result.get("statement_url"):
        return result
    statement_url = result["statement_url"]
    path = urlparse(statement_url).path.lower()
    if path.endswith(".pdf") or not _same_site(base_url, statement_url):
        return result
    context = None
    try:
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="nl-NL",
        )
        context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        context.set_default_timeout(NAVIGATION_TIMEOUT)
        page = context.new_page()
        page.goto(statement_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
        _dismiss_cookie_wall(page)
        page.wait_for_timeout(FOOTER_SETTLE_MS)
        text = BeautifulSoup(page.content(), "html.parser").get_text(" ", strip=True)
    except Exception:
        # Konden de pagina niet ophalen: geef de link het voordeel van de twijfel
        # (gedrag ongewijzigd t.o.v. vóór de content-check).
        return result
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
    if statement_page_has_statement(text):
        return result
    print("link zonder verklaring...", end=" ", flush=True)
    return {
        "has_statement": False,
        "statement_url": None,
        "statement_link_text": None,
        "statement_link_url": statement_url,
        "scrape_status": "success",
        "error": None,
        "note": "link gevonden, geen verklaring op de pagina",
    }


def _confirmed_result_for(shop, entry):
    """Bouw een resultaat-entry uit de bevestigd-groen-lijst, zonder te scrapen.

    Markeert met "confirmed": True zodat sync_confirmed weet dat dit een
    overgeslagen (cache-)resultaat is en de bevestigingsdatum niet aanraakt.
    """
    confirmed_iso = f"{str(entry['confirmed'])[:10]}T00:00:00+00:00"
    return {
        "name": shop["name"],
        "url": shop["url"],
        "category": shop.get("category", "overig"),
        "has_statement": True,
        "statement_url": entry.get("statement_url"),
        "statement_link_text": entry.get("statement_link_text"),
        "last_checked": confirmed_iso,
        "scrape_status": "success",
        "error": None,
        "confirmed": True,
    }


def scrape_webshops(webshops, now, confirmed=None, flush_path=None):
    """Scrape a list of webshops sequentially and return the result entries.

    Sites op de bevestigd-groen-lijst (confirmed) die binnen REVERIFY_DAYS
    geverifieerd zijn, slaan we over: we nemen het bewaarde resultaat direct over
    zonder browser. Zo blijft de wekelijkse run licht en blijven geverifieerde
    greens stabiel; na REVERIFY_DAYS valt de site vanzelf weer in de scrape.
    """
    confirmed = confirmed or {}
    results = []
    skipped = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser, context, page = _fresh_page(p, browser)

        for i, shop in enumerate(webshops):
            name = shop["name"]
            url = shop["url"]

            # Bevestigd groen en nog vers? Overslaan, bewaarde status overnemen.
            entry = confirmed.get(_normalize_url(url))
            if entry and _confirmed_is_fresh(entry.get("confirmed"), now):
                results.append(_confirmed_result_for(shop, entry))
                skipped += 1
                continue

            print(f"  [{i + 1}/{len(webshops)}] {name} ({url})...", end=" ", flush=True)

            # Periodiek een verse context: rem op geheugengroei in lange runs.
            if i and i % CONTEXT_RECYCLE_EVERY == 0:
                browser, context, page = _fresh_page(p, browser, context)

            # Harde per-site-cap rond de hele retry-keten: geen enkele site mag
            # een shard laten hangen (zie PER_SITE_CAP_S).
            try:
                with site_deadline(PER_SITE_CAP_S):
                    result = check_webshop(page, url)

                    # Gecrashte tab/browser? Herstel en probeer deze site één keer
                    # opnieuw; anders telt elke volgende site onterecht als 'error'.
                    if result["scrape_status"] == "error" and _looks_like_crash(result["error"]):
                        print("browser-crash, herstart...", end=" ", flush=True)
                        browser, context, page = _fresh_page(p, browser, context)
                        result = check_webshop(page, url)

                    # Wachtrij-/challenge-pagina's lossen vaak vanzelf op; één keer
                    # opnieuw proberen na een korte pauze haalt dan de echte pagina op.
                    if result["scrape_status"] == "error" and "wachtrij of lege render" in (result["error"] or ""):
                        print("interstitial, retry...", end=" ", flush=True)
                        time.sleep(3)
                        result = check_webshop(page, url)

                    # Nog steeds een challenge/lege render? Onze geblokkeerde resources
                    # kunnen zelf de bot-signatuur zijn (bv. bol.com). Eén keer ophalen
                    # met alle resources toegestaan haalt dan de echte pagina op.
                    if result["scrape_status"] == "error" and "wachtrij of lege render" in (result["error"] or ""):
                        print("no-block retry...", end=" ", flush=True)
                        alt = recheck_unblocked(browser, url)
                        if alt["scrape_status"] == "success":
                            result = alt

                    # Content-check: een gevonden verklaring-link op het eigen domein
                    # verifiëren op echte verklaring-inhoud (Decathlon-geval). Valt
                    # binnen de per-site-cap; gebruikt een niet-geblokkeerde context.
                    if result.get("has_statement") and result.get("statement_url"):
                        result = _verify_statement_page(browser, url, result)
            except SiteTimeout:
                print(f"per-site cap ({PER_SITE_CAP_S}s)...", end=" ", flush=True)
                result = {
                    "has_statement": False,
                    "statement_url": None,
                    "statement_link_text": None,
                    "scrape_status": "timeout",
                    "error": f"Per-site cap {PER_SITE_CAP_S}s overschreden",
                }
                # De page/context kan corrupt zijn na het alarm: vers beginnen.
                browser, context, page = _fresh_page(p, browser, context)

            entry = {
                "name": name,
                "url": url,
                "category": shop.get("category", "overig"),
                "has_statement": result["has_statement"],
                "statement_url": result["statement_url"],
                "statement_link_text": result["statement_link_text"],
                "last_checked": now,
                "scrape_status": result["scrape_status"],
                "error": result["error"],
            }
            # Alleen aanwezig bij een link-zonder-verklaring (Decathlon-geval),
            # zodat results.json voor de andere sites onveranderd blijft.
            if result.get("statement_link_url"):
                entry["statement_link_url"] = result["statement_link_url"]
            if result.get("note"):
                entry["note"] = result["note"]
            results.append(entry)

            status = "GEVONDEN" if result["has_statement"] else "niet gevonden"
            if result["scrape_status"] != "success":
                status = f"FOUT ({result['scrape_status']})"
            print(status)

            # Tussentijds het deelbestand wegschrijven, zodat een shard die later
            # alsnog faalt of getimed wordt zijn werk tot hier niet verliest.
            if flush_path and len(results) % FLUSH_EVERY == 0:
                _write_atomic(Path(flush_path), json.dumps(
                    {"last_updated": now, "webshops": results}, indent=2, ensure_ascii=False))

            # Korte pauze: elke request gaat naar een ander domein, dus
            # per-host beleefdheid speelt hier niet.
            if i < len(webshops) - 1:
                time.sleep(REQUEST_PAUSE_S)

        browser.close()
    if skipped:
        print(f"  ({skipped} overgeslagen: bevestigd groen, vers binnen {REVERIFY_DAYS} dagen)")
    return results


def build_output(results, now):
    """Build the results.json structure (stats + sorted webshops) from raw entries."""
    with_statement = sum(1 for r in results if r["has_statement"])
    errors = sum(1 for r in results if r["scrape_status"] != "success")
    without_statement = len(results) - with_statement - errors
    return {
        "last_updated": now,
        "total": len(results),
        "with_statement": with_statement,
        "without_statement": without_statement,
        "errors": errors,
        "webshops": sorted(results, key=lambda x: x["name"].lower()),
    }


def finalize(output, ds):
    """Write the dataset's results.json and (re)generate the GEO assets."""
    # Sanity-drempel: een browser- of netwerkstoring halverwege de run zou
    # anders een week vol valse 'errors' publiceren en in history vastleggen.
    if output["total"] and output["errors"] / output["total"] > ERROR_RATE_THRESHOLD:
        sys.exit(
            f"FOUT: {output['errors']} van de {output['total']} checks faalden "
            f"({output['errors'] / output['total']:.0%}, drempel {ERROR_RATE_THRESHOLD:.0%}). "
            f"Vermoedelijk een browser- of netwerkstoring; resultaten niet gepubliceerd."
        )
    results_file = ds["results_file"]
    results_file.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(results_file, json.dumps(output, indent=2, ensure_ascii=False))
    generate_geo_assets(output, ds)
    print(f"\nKlaar! Resultaten opgeslagen in {results_file}")
    print(f"  Totaal: {output['total']}")
    print(f"  Met verklaring: {output['with_statement']}")
    print(f"  Zonder verklaring: {output['without_statement']}")
    print(f"  Fouten: {output['errors']}")


def merge_parts(merge_dir, now, ds):
    """Combine all results.part-*.json files in a directory into final results.json.

    De-duplicates on normalized URL (keeping the first seen) in case shard ranges
    ever overlap, then finalizes as if it were one big run.
    """
    parts = sorted(Path(merge_dir).glob("results.part-*.json"))
    if not parts:
        print(f"Geen part-bestanden gevonden in {merge_dir}")
        sys.exit(1)
    seen = set()
    combined = []
    for part in parts:
        data = json.load(open(part))
        entries = data.get("webshops", data) if isinstance(data, dict) else data
        for r in entries:
            key = _normalize_url(r.get("url"))
            if key in seen:
                continue
            seen.add(key)
            combined.append(r)
        print(f"  {part.name}: {len(entries)} entries")
    print(f"Samengevoegd: {len(combined)} unieke entries uit {len(parts)} shards")

    # Dekkingsdrempel: zijn er shards mislukt (ontbrekende part-bestanden), dan
    # zou een sterk gekrompen dataset als dé weekmeting gepubliceerd worden.
    # Liever hard falen zodat de vorige (volledige) meting blijft staan.
    try:
        with open(ds["input_file"], encoding="utf-8") as f:
            expected = len(json.load(f))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Waarschuwing: dekkingscheck overgeslagen, {ds['input_file']} onleesbaar: {exc}")
        expected = 0
    if expected and len(combined) < MERGE_COVERAGE_THRESHOLD * expected:
        sys.exit(
            f"FOUT: {len(combined)} van de {expected} entries aanwezig "
            f"({len(combined) / expected:.0%}, drempel {MERGE_COVERAGE_THRESHOLD:.0%}). "
            f"Vermoedelijk zijn een of meer shards mislukt; niet gefinaliseerd."
        )
    finalize(build_output(combined, now), ds)


def main():
    parser = argparse.ArgumentParser(description="Scrape footers for accessibility statements")
    parser.add_argument("--dataset", choices=list(DATASETS), default="webshops",
                        help="Welke lijst scrapen: webshops (default) of financieel")
    parser.add_argument("--limit", type=int, help="Limit number of entries to check (for testing)")
    parser.add_argument("--shard", type=int, help="0-based index of this shard")
    parser.add_argument("--num-shards", type=int, help="Total number of shards")
    parser.add_argument("--out", help="Where to write partial results (shard mode)")
    parser.add_argument("--merge", help="Directory of results.part-*.json to merge into final results.json")
    args = parser.parse_args()

    ds = DATASETS[args.dataset]
    now = datetime.now(timezone.utc).isoformat()

    # Merge mode: combine shard outputs, generate assets, done.
    if args.merge:
        merge_parts(args.merge, now, ds)
        return

    # Load the dataset's input list
    with open(ds["input_file"]) as f:
        entries = json.load(f)

    if args.limit:
        entries = entries[: args.limit]

    # Shard mode: take every Nth entry so load spreads evenly across shards.
    sharded = args.shard is not None and args.num_shards
    if sharded:
        entries = entries[args.shard:: args.num_shards]
        print(f"Shard {args.shard}/{args.num_shards}: {len(entries)} entries")
    else:
        print(f"Checking {len(entries)} entries ({args.dataset})...")

    confirmed = _load_confirmed(ds)
    if confirmed:
        print(f"Bevestigd-groen-lijst: {len(confirmed)} sites (overslaan indien vers)")

    # In shard-modus schrijven we tussentijds naar het deelbestand, zodat een
    # shard die later faalt of getimed wordt zijn werk tot dan toe behoudt.
    flush_path = None
    if sharded:
        flush_path = Path(args.out) if args.out else ds["results_file"].parent / f"results.part-{args.shard}.json"
        flush_path.parent.mkdir(parents=True, exist_ok=True)

    results = scrape_webshops(entries, now, confirmed, flush_path=flush_path)

    # Shard mode writes a partial file for the merge step; it must NOT finalize
    # (that would clobber results.json and regenerate assets from a partial set).
    if sharded:
        _write_atomic(flush_path, json.dumps({"last_updated": now, "webshops": results},
                                             indent=2, ensure_ascii=False))
        print(f"\nShard {args.shard} klaar: {len(results)} resultaten -> {flush_path}")
        return

    finalize(build_output(results, now), ds)


if __name__ == "__main__":
    main()
