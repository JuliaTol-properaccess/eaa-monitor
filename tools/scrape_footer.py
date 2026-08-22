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
import threading
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Optioneel: psutil laat de per-site-watchdog een wedged chromium-proces killen
# (zie _kill_browser_processes). Ontbreekt het, dan valt de cap stil terug op
# alleen SIGALRM, zodat de tool zonder psutil blijft werken.
try:
    import psutil
except ImportError:
    psutil = None

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
    "reizen": {
        "key": "reizen",
        "input_file": DATA_DIR / "reizen.json",
        "results_file": DATA_DIR / "results-reizen.json",
        "history_file": DATA_DIR / "history-reizen.json",
        "target_html": PUBLIC_DIR / "monitor-reizen.html",
        "llms_region": "REIZEN-MEASUREMENT",
        "llms_label": "Reisorganisaties (ACM-toezicht)",
        "llms_noun": "reisorganisaties",
        "hub_prefix": "reizen",
        "toezichthouder": "ACM",
        "noun": "reisorganisaties",
        "summary_heading": "Reisorganisaties · ACM-toezicht",
        "dataset_id": "https://eaa-monitor.nl/monitor-reizen.html#dataset",
        "dataset_name": "Toegankelijkheidsverklaringen Nederlandse reisorganisaties",
        "content_url": "https://eaa-monitor.nl/data/results-reizen.json",
        "rescan_copy": "De monitor controleert alle reisorganisaties elke maandagochtend automatisch opnieuw, dus deze cijfers zijn nooit ouder dan een week.",
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

# De foutdrempel is een storings-vangnet, geen bot-wall-detector. Op een kleine
# sectorlijst (bv. ebooks: 10 sites) vormen een paar permanent bot-beschermde
# sites al 25%+, waardoor de guard elke week aansloeg en niets meer publiceerde.
# Naast het percentage eisen we daarom een absolute foutenondergrens: pas boven
# dit aantal fouten is een echte storing aannemelijk. Kleine lijsten met een
# handvol bekende bot-walls publiceren zo gewoon door; een storm op de
# webshoplijst (honderden fouten) trekt de guard nog steeds.
ERROR_COUNT_FLOOR = 8

# Wachten op de footer i.p.v. een vaste 2s: de meeste sites hebben de footer al
# bij domcontentloaded, dan kost dit vrijwel niets. De settle vangt links die
# ná het verschijnen van de footer nog door JS worden geïnjecteerd; 500ms bleek
# te kort voor overlay-widgets (Lyca Mobile en Transavia flipten tussen runs),
# 1500ms is stabiel en per site nog steeds korter dan de oude vaste 2s.
FOOTER_WAIT_TIMEOUT = 2000
FOOTER_SETTLE_MS = 1500

# Render-waarborg voor de verklaring-pagina (zie _verify_statement_page). Onder
# beide drempels tegelijk beschouwen we de pagina als niet gerenderd, en telt de
# site als "niet te controleren" i.p.v. "zonder verklaring". De link-drempel is
# dezelfde als in classify_html; de tekstdrempel ligt ver onder een echte
# verklaring (HEMA 2253 tekens, Roostershop 2381) en ver boven een lege render
# (Bruynzeel 33, De Telegraaf 19).
MIN_RENDERED_TEXT = 200
MIN_RENDERED_LINKS = 5

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

# Trapsgewijze marge bovenop PER_SITE_CAP_S. Na 1x grace kilt de watchdog-thread
# chromium; na 2x grace herstart een reaper de shard vanaf de volgende site.
# SIGALRM krijgt zo eerst de kans op een nette Python-timeout, dan de
# chromium-kill (voor een driver-wedge), en pas als ook dat de hang niet breekt
# de harde reaper.
KILL_GRACE_S = 30

# Cap op het browserherstel na een cap-hit of fout (zie _recover_page). Ruimer
# dan een normale context.close() nodig heeft, krap genoeg dat een wedged
# browser de shard niet ophoudt.
RECOVERY_CAP_S = 20

# Hoe vaak een shard zichzelf mag herstarten na een onbreekbare hang. Ruim boven
# de 1-2 hangers die we per shard zien, laag genoeg dat een pathologische lijst
# niet eindeloos doorstart. Daarboven sluit de shard af met wat hij heeft.
MAX_SHARD_RESTARTS = 5


class SiteTimeout(BaseException):
    """Opgeworpen door de per-site-watchdog wanneer PER_SITE_CAP_S verstrijkt.

    Erft bewust van BaseException, niet van Exception. check_webshop en de
    helpers eromheen vangen brede `except Exception` af om losse site-fouten op
    te vangen; een Exception-subclass werd daar opgeslokt en teruggegeven als
    gewoon 'error'-resultaat. De `except SiteTimeout` in de hoofdlus vuurde dan
    nooit, en dus draaide ook het browserherstel (_fresh_page) niet. Eén wedged
    browser bleef zo wedged: elke volgende site liep de volle cap vol, waarna de
    shard de jobcap tikte en rood ging (crons van 27 juli en 3 augustus 2026,
    shard 6 resp. shard 1). Als BaseException glipt de cap net als
    KeyboardInterrupt door elk `except Exception`-vangnet heen, ook door
    vangnetten die later worden toegevoegd.
    """


def _raise_site_timeout(signum, frame):
    raise SiteTimeout()


def _kill_browser_processes():
    """Kill de chromium-childprocessen van deze shard. Returnt True als er één omging.

    Tweede verdedigingslinie naast SIGALRM. Hangt een site diep in de
    Playwright-driver (wedged chromium of een vastgelopen IPC-kanaal), dan kan
    SIGALRM de geblokkeerde sync-call in de main thread niet breken: de exception
    belandt in de asyncio-greenlet i.p.v. op de call-site. Zo bleef shard 9 op
    29 juni 2026 bijna 3 uur hangen tot de 200-min-jobcap hem cancelde.

    Een aparte thread die het chromium-proces kilt, laat de IPC-wait wél
    terugkeren, met een disconnect-fout ("browser has been disconnected" /
    "Connection closed") die als crash herkend wordt en via _fresh_page herstelt.
    We raken bewust geen Playwright-objecten aan (die zijn niet thread-safe) en
    laten de node-driver leven, zodat chromium opnieuw gestart kan worden.
    """
    if psutil is None:
        return False
    killed = False
    try:
        children = psutil.Process().children(recursive=True)
    except psutil.Error:
        return False
    for child in children:
        try:
            name = (child.name() or "").lower()
        except psutil.Error:
            continue
        if "chrom" in name or "headless_shell" in name:
            try:
                child.kill()
                killed = True
            except psutil.Error:
                pass
    return killed


class site_deadline:
    """Contextmanager: harde per-site wall-clock-cap in drie lagen.

    Eén laag is niet genoeg gebleken (shard 9, 29 + 30 juni 2026):
    - SIGALRM (main thread, Unix) breekt pure-Python- en netwerk-hangs netjes af
      met een SiteTimeout. Vuurt niet tijdens een C-call (bv. een geblokkeerde
      Playwright-IPC-wait of een lange parse).
    - Een watchdog-thread kilt na KILL_GRACE_S het chromium-proces, voor een
      driver-wedge die SIGALRM niet kan breken. Helpt niet bij een CPU-hang die
      niet op chromium wacht.
    - Een reaper-thread sluit na 2x KILL_GRACE_S de hele shard af (on_giveup):
      flusht de tot dan verzamelde resultaten en doet os._exit(0). Een aparte
      thread werkt ongeacht waar de main thread vastzit, dus dit vangt ELKE
      onbreekbare hang. De shard eindigt schoon (exit 0, geflushte deel-data
      gaat mee in de merge) i.p.v. de 200-min-jobcap te tikken en rood te gaan.

    Valt SIGALRM weg (geen SIGALRM, of niet de main thread), dan blijven de
    thread-lagen over; ontbreekt psutil, dan de per-call-timeouts van Playwright
    plus de reaper. Zo blijft de tool overal werken.
    """

    def __init__(self, seconds, on_giveup=None):
        self.seconds = seconds
        self.on_giveup = on_giveup
        self.enabled = hasattr(signal, "SIGALRM")
        self._old_handler = None
        self._killer = None
        self._reaper = None

    def __enter__(self):
        # Laag 2: kill chromium. Laag 3: reap de shard. Beide cancelen vanzelf
        # bij nette afloop (__exit__), dus ze raken alleen een echte hang.
        if psutil is not None:
            self._killer = threading.Timer(self.seconds + KILL_GRACE_S, _kill_browser_processes)
            self._killer.daemon = True
            self._killer.start()
        if self.on_giveup is not None:
            self._reaper = threading.Timer(self.seconds + 2 * KILL_GRACE_S, self.on_giveup)
            self._reaper.daemon = True
            self._reaper.start()
        if self.enabled:
            try:
                self._old_handler = signal.signal(signal.SIGALRM, _raise_site_timeout)
                signal.alarm(self.seconds)
            except (ValueError, OSError):
                # Niet de main thread: cap uitschakelen, thread-lagen blijven.
                self.enabled = False
        return self

    def __exit__(self, *exc):
        if self.enabled:
            signal.alarm(0)
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        if self._killer is not None:
            self._killer.cancel()
        if self._reaper is not None:
            self._reaper.cancel()
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

    Een kapotte href (bv. een onafgesloten IPv6-haakje als ``http://[``) laat
    ``urljoin`` een ``ValueError: Invalid IPv6 URL`` opwerpen. Onafgevangen sloopte
    dat een hele scrape-shard (29 juni 2026): één foute footer-link nam ~850 shops
    mee. We behandelen zo'n href net als een geweigerde scheme: geen link.
    """
    try:
        resolved = urljoin(base_url, href)
    except ValueError:
        return None
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


# Woorden die op een echte toegankelijkheidsverklaring of -pagina wijzen. Eén
# treffer volstaat. Twee groepen:
# 1. Formele verklaring-termen (WCAG, EN 301 549, nalevingsstatus, ...).
# 2. Inhoudelijke toegankelijkheidstermen in gewone taal (schermlezer, hulpmiddel,
#    ondertiteling, ...). Die tweede groep vangt echte verklaringen die de formele
#    woorden mijden, zoals Klaverblads "Toegankelijkheid van onze dienstverlening".
# Een aanvraag-/contactformulier (Decathlon: "vraag een toegankelijke versie aan")
# of een cart-/homepage bevat geen van deze inhoudelijke termen en sneuvelt dus.
# De losse termen "verklaring"/"toegankelijk" laten we bewust weg: die staan ook
# op privacy-/cookiepagina's en aanvraagformulieren.
STATEMENT_CONTENT_MARKERS = [
    # Formele verklaring-vocabulaire
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
    # Inhoudelijke toegankelijkheidstermen (gewone taal)
    "schermlezer",
    "screenreader",
    "voorleessoftware",
    "hulptechnologie",
    "assistieve technologie",
    "ondertiteling",
    "gebarentaal",
    "braille",
    "toetsenbedien",
    "met het toetsenbord",
    "tekst vergroten",
    "lettergrootte",
]


def page_looks_unrendered(soup, text: str) -> bool:
    """Rendert deze pagina echt, of kijken we naar een lege huls?

    Een bot-challenge, wachtrij of JS-only pagina levert bijna geen tekst en
    bijna geen links. Zo'n pagina bewijst niets: we hebben de verklaring niet
    gezien, niet vastgesteld dat hij ontbreekt.

    Beide signalen moeten wijzen op een lege render, niet één van de twee. Een
    echte pagina zonder verklaring-inhoud (het Decathlon-geval, waar de
    content-check voor gebouwd is) heeft juist wél tekst en links, en moet
    afgekeurd blijven worden.
    """
    return (len(text) < MIN_RENDERED_TEXT
            and len(soup.find_all("a", href=True)) < MIN_RENDERED_LINKS)


def statement_page_has_statement(text: str) -> bool:
    """True als de tekst van een gelinkte pagina verklaring-inhoud bevat.

    Pure, deterministisch testbare functie (geen netwerk). Gebruikt door de
    content-check die een footer-link naar een 'toegankelijkheid'-pagina verifieert:
    staat er alleen een aanvraag-/contactformulier en geen verklaring, dan telt het
    niet als 'met verklaring'.
    """
    low = (text or "").lower()
    return any(marker in low for marker in STATEMENT_CONTENT_MARKERS)


# Maximaal aantal subpagina's dat de content-check naloopt onder een hub.
STATEMENT_SUBPAGE_LIMIT = 5


def accessibility_subpages(hub_url, html, limit=STATEMENT_SUBPAGE_LIMIT):
    """Kind-pagina's van een toegankelijkheidshub op hetzelfde domein.

    Sommige sites (bv. Ziggo) linken vanuit één /toegankelijkheid-hub door naar
    losse subpagina's (visuele/auditieve/... toegankelijkheid) die pas de echte
    verklaring-inhoud bevatten; de hub zelf zakt dan voor de content-check.
    Deze functie levert de subpagina-URL's op zodat de content-check ze kan
    nalopen voordat hij 'zonder verklaring' concludeert: alleen kinderen van het
    hubpad (zelfde domein, PDF's uitgezonderd, gededupliceerd), in bronvolgorde
    en afgetopt op ``limit``. Puur/deterministisch testbaar (geen netwerk).

    Het kind-van-hubpad-criterium houdt dit strak op de hub-en-subpagina-vorm:
    globale navigatie- of footerlinks (ander pad) worden niet gevolgd, dus de
    check kan een 'zonder' alleen opwaarderen bij een echte doorverwijzing.
    """
    hub_path = urlparse(hub_url).path.rstrip("/").lower()
    if not hub_path:
        return []
    prefix = hub_path + "/"
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    out = []
    for a in soup.find_all("a", href=True):
        sub, _ = urldefrag(urljoin(hub_url, a["href"]))
        if not _same_site(hub_url, sub):
            continue
        sub_path = urlparse(sub).path
        if sub_path.lower().endswith(".pdf"):
            continue
        if not sub_path.rstrip("/").lower().startswith(prefix):
            continue
        key = _normalize_url(sub)
        if key in seen:
            continue
        seen.add(key)
        out.append(sub)
        if len(out) >= limit:
            break
    return out


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
    if len(all_links) < MIN_RENDERED_LINKS:
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


def _recover_page(p, browser, old_context, on_giveup):
    """Verse (browser, context, page) na een cap-hit of fout, zelf onder een cap.

    _fresh_page draait in de except-takken van de hoofdlus, dus buiten de
    per-site-deadline: die is bij het verlaten van de with-block al opgeheven.
    En _fresh_page kan wel degelijk blijven hangen, want old_context.close()
    blokkeert op een wedged browser (gemeten met faulthandler: de main thread
    staat stil in playwright's _sync vanuit context.close()). Zonder eigen cap
    hangt de shard daar voorgoed, precies de hang die we juist wilden opheffen.

    Lukt netjes sluiten niet binnen de cap, dan laten we de oude context los,
    killen we chromium en starten we een verse browser. Komt ook die niet op
    tijd omhoog, dan is de playwright-driver zelf stuk en is er binnen dit
    proces niets meer te redden: dan roepen we on_giveup aan, die de shard
    herstart.

    Die laatste tak is geen theorie. In de run van 7 augustus 2026 sneuvelden
    shard 4 (Managementboek.nl) en shard 9 (Life Outdoor Living) er allebei op:
    de cap tijdens p.chromium.launch ontsnapte ongevangen en nam de shard mee,
    want de reaper van dit site_deadline was bij het verlaten van de with-block
    al gecanceld. Een SiteTimeout mag hier dus nooit naar buiten lekken.
    """
    try:
        with site_deadline(RECOVERY_CAP_S, on_giveup=on_giveup):
            return _fresh_page(p, browser, old_context)
    except SiteTimeout:
        print("herstel hangt, verse browser...", end=" ", flush=True)

    try:
        with site_deadline(RECOVERY_CAP_S, on_giveup=on_giveup):
            try:
                _kill_browser_processes()
            except Exception:
                pass
            browser = p.chromium.launch(headless=True)
            return _fresh_page(p, browser, None)
    except SiteTimeout:
        print("herstel mislukt, shard herstart...", flush=True)
        on_giveup()
        # on_giveup hoort niet terug te keren (execv of os._exit). Doet hij dat
        # toch, faal dan luid i.p.v. None terug te geven aan de hoofdlus.
        raise


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
        hub_html = page.content()
        hub_soup = BeautifulSoup(hub_html, "html.parser")
        text = hub_soup.get_text(" ", strip=True)

        # Render-waarborg. Een pagina die niet echt rendert (bot-challenge,
        # wachtrij, JS-only pagina) levert bijna geen tekst en bijna geen links
        # op. Die mag niet als "zonder verklaring" tellen: we hebben de
        # verklaring niet gezien, niet vastgesteld dat hij ontbreekt. Zelfde
        # regel als in classify_html (< 5 links = niet te controleren) en de
        # axe-scan (< 50 DOM-elementen = niet gerenderd).
        #
        # Beide signalen moeten wijzen op een lege render, niet één van de
        # twee: een echte pagina zonder verklaring-inhoud (het Decathlon-geval,
        # waar deze check voor gebouwd is) heeft juist wél tekst en links en
        # moet afgekeurd blijven worden.
        #
        # Gemeten op de run van 7 augustus 2026: Bruynzeel Keukens leverde 33
        # tekens, De Telegraaf Webshop 19. Beide telden als "zonder verklaring"
        # terwijl ze een echte verklaring-pagina hebben.
        if page_looks_unrendered(hub_soup, text):
            print("verklaring-pagina niet gerenderd...", end=" ", flush=True)
            return result

        if statement_page_has_statement(text):
            return result
        # De gelinkte pagina zelf heeft geen verklaring-inhoud. Sommige sites
        # (bv. Ziggo) verdelen de verklaring over subpagina's van een
        # toegankelijkheidshub. Loop die kinderen na voordat we 'zonder
        # verklaring' concluderen; de hub blijft de bewaarde statement_url.
        for sub in accessibility_subpages(statement_url, hub_html):
            try:
                page.goto(sub, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
                _dismiss_cookie_wall(page)
                page.wait_for_timeout(FOOTER_SETTLE_MS)
                sub_text = BeautifulSoup(page.content(), "html.parser").get_text(" ", strip=True)
            except Exception:
                continue
            if statement_page_has_statement(sub_text):
                print("verklaring op subpagina...", end=" ", flush=True)
                return {**result, "statement_link_url": sub}
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


def _resume_argv(argv, resume_at, restarts):
    """Bouw de argv voor een zelfherstart: eigen vlaggen eruit, verse erin.

    Strippen is nodig omdat een tweede hang anders een tweede --resume-from op
    de commandline zou stapelen; argparse pakt dan de laatste, maar de lijst
    groeit bij elke herstart. Hanteert zowel "--resume-from=5" als de
    losse-waardevorm "--resume-from 5".
    """
    out = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg in ("--resume-from", "--restarts"):
            skip_next = True
            continue
        if arg.startswith("--resume-from=") or arg.startswith("--restarts="):
            continue
        out.append(arg)
    return out + [f"--resume-from={resume_at}", f"--restarts={restarts}"]


def _timeout_entry(shop, now, error):
    """Resultaat-entry voor een site die we niet konden controleren.

    'timeout' (= niet te controleren), nooit "zonder verklaring": een site die
    hangt of ons blokkeert mag niet als overtreder in de cijfers belanden.
    """
    return {
        "name": shop["name"],
        "url": shop["url"],
        "category": shop.get("category", "overig"),
        "has_statement": False,
        "statement_url": None,
        "statement_link_text": None,
        "last_checked": now,
        "scrape_status": "timeout",
        "error": error,
    }


def scrape_webshops(webshops, now, confirmed=None, flush_path=None,
                    resume_from=0, prior_results=None, restarts=0):
    """Scrape a list of webshops sequentially and return the result entries.

    Sites op de bevestigd-groen-lijst (confirmed) die binnen REVERIFY_DAYS
    geverifieerd zijn, slaan we over: we nemen het bewaarde resultaat direct over
    zonder browser. Zo blijft de wekelijkse run licht en blijven geverifieerde
    greens stabiel; na REVERIFY_DAYS valt de site vanzelf weer in de scrape.

    resume_from/prior_results dienen de zelfherstart na een onbreekbare hang
    (zie _reap_shard): de lijst blijft dezelfde, we beginnen alleen verderop en
    nemen de al verzamelde resultaten mee.
    """
    confirmed = confirmed or {}
    results = list(prior_results or [])
    skipped = 0
    # Waar de main thread nu mee bezig is. De reaper draait in een eigen thread
    # en leest dit uit om de hangende site vast te leggen en erna te hervatten.
    current = {"index": resume_from, "shop": None}

    def _reap_shard():
        """Laatste vangnet: één site hangt onbreekbaar (SIGALRM noch chromium-kill
        kreeg de main thread los). We kunnen die hang binnen dit proces niet meer
        breken, dus herstarten we de shard vanaf de volgende site: de hangende
        site gaat als 'timeout' de resultaten in, alles wordt geflusht en het
        proces vervangt zichzelf via execv.

        Eerder sloot dit de hele shard af (os._exit(0)). Dat kostte per hangende
        site ~400 van de 856 sites aan dekking; op 27 juli en 3 augustus 2026
        zakte de merge daardoor onder de 90%-drempel en werd er niets
        gepubliceerd. execv i.p.v. sys.exit omdat de main thread vastzit: alleen
        het procesbeeld vervangen komt daar nog langs.
        """
        hanger = current["shop"]
        if hanger is not None:
            results.append(_timeout_entry(
                hanger, now,
                f"Onbreekbare hang > {PER_SITE_CAP_S + 2 * KILL_GRACE_S}s; shard hervat"))
        name = hanger["url"] if hanger else "onbekend"

        if flush_path:
            try:
                _write_atomic(Path(flush_path), json.dumps(
                    {"last_updated": now, "webshops": results}, indent=2, ensure_ascii=False))
            except Exception:
                pass

        resume_at = current["index"] + 1
        if restarts >= MAX_SHARD_RESTARTS or not flush_path or resume_at >= len(webshops):
            print(f"\nWATCHDOG: {name} hangt onbreekbaar; shard afgesloten met "
                  f"{len(results)} resultaten (geen herstart meer over).", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)

        print(f"\nWATCHDOG: {name} hangt onbreekbaar; shard hervat bij site "
              f"{resume_at + 1}/{len(webshops)} "
              f"(herstart {restarts + 1}/{MAX_SHARD_RESTARTS}).", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()

        # Chromium eerst opruimen: execv vervangt alleen dit proces, de
        # childprocessen zouden anders blijven draaien en geheugen opeten.
        try:
            _kill_browser_processes()
        except Exception:
            pass

        argv = _resume_argv(sys.argv, resume_at, restarts + 1)
        os.execv(sys.executable, [sys.executable] + argv)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser, context, page = _fresh_page(p, browser)

        for i, shop in enumerate(webshops):
            if i < resume_from:
                continue
            name = shop["name"]
            url = shop["url"]
            current["index"] = i
            current["shop"] = shop

            # Bevestigd groen en nog vers? Overslaan, bewaarde status overnemen.
            entry = confirmed.get(_normalize_url(url))
            if entry and _confirmed_is_fresh(entry.get("confirmed"), now):
                results.append(_confirmed_result_for(shop, entry))
                skipped += 1
                continue

            print(f"  [{i + 1}/{len(webshops)}] {name} ({url})...", end=" ", flush=True)

            # Periodiek een verse context: rem op geheugengroei in lange runs.
            if i and i % CONTEXT_RECYCLE_EVERY == 0:
                browser, context, page = _recover_page(p, browser, context, _reap_shard)

            # Harde per-site-cap rond de hele retry-keten: geen enkele site mag
            # een shard laten hangen (zie PER_SITE_CAP_S). De reaper (on_giveup)
            # is het vangnet voor een hang die SIGALRM noch de chromium-kill breekt.
            try:
                with site_deadline(PER_SITE_CAP_S, on_giveup=_reap_shard):
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
                # Onder eigen cap, want dit herstel kan zelf hangen.
                browser, context, page = _recover_page(p, browser, context, _reap_shard)
            except Exception as e:
                # Vangnet: geen enkele losse site-fout mag een hele shard doden
                # (zie de IPv6-href-crash van 29 juni 2026, die 3 shards meenam).
                # Leg de site vast als 'error' en ga door; de page/context kan
                # corrupt zijn, dus vers beginnen.
                print(f"onverwachte fout, doorgaan... ({type(e).__name__})", end=" ", flush=True)
                result = {
                    "has_statement": False,
                    "statement_url": None,
                    "statement_link_text": None,
                    "scrape_status": "error",
                    "error": f"{type(e).__name__}: {e}",
                }
                browser, context, page = _recover_page(p, browser, context, _reap_shard)

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
    if (
        output["total"]
        and output["errors"] > ERROR_COUNT_FLOOR
        and output["errors"] / output["total"] > ERROR_RATE_THRESHOLD
    ):
        sys.exit(
            f"FOUT: {output['errors']} van de {output['total']} checks faalden "
            f"({output['errors'] / output['total']:.0%}, drempel {ERROR_RATE_THRESHOLD:.0%} "
            f"boven {ERROR_COUNT_FLOOR} fouten). "
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
    # Zelfherstart na een onbreekbare hang; zet de reaper zelf (zie _reap_shard).
    parser.add_argument("--resume-from", type=int, default=0,
                        help=argparse.SUPPRESS)
    parser.add_argument("--restarts", type=int, default=0,
                        help=argparse.SUPPRESS)
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

    # Hervat na een zelfherstart: de reaper heeft alles tot en met de hangende
    # site al naar flush_path geschreven, dus die lezen we terug en we beginnen
    # bij de site erna.
    prior_results = []
    if args.resume_from and flush_path and Path(flush_path).exists():
        try:
            with open(flush_path) as f:
                prior_results = json.load(f).get("webshops", [])
            print(f"Hervat bij site {args.resume_from + 1}/{len(entries)} "
                  f"met {len(prior_results)} eerdere resultaten "
                  f"(herstart {args.restarts}/{MAX_SHARD_RESTARTS})")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Waarschuwing: deelbestand onleesbaar bij hervatten ({exc}); "
                  f"begin opnieuw vanaf site {args.resume_from + 1}")

    results = scrape_webshops(entries, now, confirmed, flush_path=flush_path,
                              resume_from=args.resume_from,
                              prior_results=prior_results,
                              restarts=args.restarts)

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
