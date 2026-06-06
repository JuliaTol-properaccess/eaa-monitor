# GEO Audit Report: EAA Monitor

**Audit Date:** 2026-06-06
**URL:** https://eaa-monitor.nl
**Business Type:** Data Publisher / Original-research tool (single-purpose dashboard)
**Pages Analyzed:** 4 (index.html, over.html, bezwaar.html, bezwaren.html)

---

## Executive Summary

**Overall GEO Score: 38/100 (Critical)**

EAA Monitor sits on a goldmine of citable material: original research showing roughly 11% of 1,246 Dutch webshops publish an accessibility statement. That is exactly the kind of concrete, quotable statistic AI systems love to cite. The problem is that almost none of it is reachable by AI crawlers. The headline numbers and the entire webshop table are rendered client-side from `results.json`, so the raw HTML an AI crawler reads shows empty placeholders ("-", "Data laden..."). On top of that there is no schema markup, no `llms.txt`, no `sitemap.xml`, no `robots.txt`, and no Open Graph data anywhere on the site.

The good news: this is a young, technically clean, genuinely accessible site with honest methodology and a credible author behind it. Every gap here is a quick, cheap fix. Closing the top five would realistically move the score from Critical into the Fair-to-Good band, because the underlying content asset is strong; only the optimization layer is missing.

### Score Breakdown

| Category | Score | Weight | Weighted Score |
|---|---|---|---|
| AI Citability | 45/100 | 25% | 11.3 |
| Brand Authority | 25/100 | 20% | 5.0 |
| Content E-E-A-T | 55/100 | 20% | 11.0 |
| Technical GEO | 45/100 | 15% | 6.8 |
| Schema & Structured Data | 8/100 | 10% | 0.8 |
| Platform Optimization | 20/100 | 10% | 2.0 |
| **Overall GEO Score** | | | **38/100** |

---

## Critical Issues (Fix Immediately)

1. **The core data is invisible to AI crawlers (client-side rendering, no SSR).**
   The value of this site is the statistics and the per-webshop table, but both are injected by `app.js` via `fetch("data/results.json")`. GPTBot and most AI crawlers do not execute JavaScript, so they see empty placeholders. The single most quotable fact, "about 11% of Dutch webshops publish an accessibility statement", does not exist anywhere in the served HTML. Fix: bake the key numbers and a summary of the table into static HTML at build/scrape time.
   *Affected: [index.html](public/index.html) lines 106-116, 219-224.*

2. **Zero structured data on a site that is literally a dataset.**
   No JSON-LD anywhere. For a research dashboard, `Dataset` + `Organization` + `WebSite` schema is the highest-leverage markup you can add, and it is completely absent. This is the cheapest large win available.

3. **Stated update frequency does not match reality (trust failure).**
   The site promises checks "elke maandag" / "wekelijks", but `results.json` shows `last_updated: 2026-03-18`, roughly 12 weeks old at audit time. AI systems and human readers both penalize claims that the data contradicts. Either the weekly cron has stopped, or the promise needs to change. Fix the pipeline or soften the claim.
   *Affected: [.github/workflows/scrape.yml](.github/workflows/scrape.yml), [over.html](public/over.html) line 76.*

## High Priority Issues

4. **No `llms.txt` file.** There is no machine-readable summary telling AI systems what this site is, what the dataset covers, and how to reference it. For an original-data site this is high value.

5. **No `sitemap.xml`.** Nothing tells crawlers which pages exist. Trivial to add for a 4-page static site.

6. **No `robots.txt`.** Live URL returns 404. Nothing is blocked (so access is fine by default), but you also give no crawl guidance and no sitemap pointer. Add a permissive `robots.txt` that explicitly welcomes AI crawlers and links the sitemap.

7. **No question-answering content blocks / FAQ.** The H1 is a question ("Hebben Nederlandse webshops een toegankelijkheidsverklaring?") but the concrete answer is not in adjacent static text. AI Overviews and ChatGPT reward a tight question-then-answer pattern. No `FAQPage` content or schema exists.

8. **Thin author/entity signals despite a real expert behind it.** The Over page credits Proper Access and Julia Tol and references the DigiToegankelijk TOP programme, which is strong raw E-E-A-T. But there is no `Person`/`Organization` schema, no author bio depth, no publication or update date in the markup, and no contact route on the monitor itself.

## Medium Priority Issues

9. **No Open Graph or Twitter Card tags on any page.** Shared links render with no title, description, or image. This suppresses the social and Reddit signals that feed brand recognition for AI entity models.

10. **No canonical URLs.** Add `<link rel="canonical">` to each page to consolidate signals (eaa-monitor.nl vs www, trailing slashes, GitHub Pages origin).

11. **Brand has no third-party footprint.** "EAA Monitor" is not mentioned on Wikipedia, Reddit, LinkedIn, news, or industry blogs, so AI models have no corroborating sources to recognize it as an entity. Expected for a new site, but it is the main thing capping Brand Authority.

12. **Tailwind loaded from CDN at runtime.** `cdn.tailwindcss.com` is a render-time dependency and a performance/reliability cost. Fine for a prototype, but a compiled stylesheet is better for crawl speed and Core Web Vitals.

## Low Priority Issues

13. **No `image` for social/OG sharing.** No branded preview image exists to attach once OG tags are added.
14. **Meta description is solid but could state the headline finding** (the percentage) to improve snippet citability.
15. **No structured breadcrumbs** between dashboard, Over, bezwaar, and bezwaren pages.
16. **Last-updated timestamp is computed in JS only** (`#last-updated`), so it is invisible to crawlers along with the rest of the dynamic content.

---

## Category Deep Dives

### AI Citability (45/100)
The static prose that does exist is good: the "Wat is de EAA?" and "Methodologie" blocks are clear, self-contained, and quotable, and the honest caveat ("een link naar een verklaring betekent niet automatisch dat de website ook daadwerkelijk toegankelijk is") is exactly the kind of nuanced sentence AI likes to quote. The H1 is phrased as a real user question.

But the citability ceiling is capped hard by client-side rendering. The most valuable, most unique, most quotable assets, the live percentages and the 1,246-row table, never reach the HTML. An AI crawler asking "what share of Dutch webshops have an accessibility statement?" finds a placeholder dash, not "11%". Surfacing those numbers in static HTML is the single biggest citability lever on the entire site.

### Brand Authority (25/100)
"EAA Monitor" is a brand-new micro-brand with effectively no external footprint: no Wikipedia entry, no Reddit threads, no news coverage, no LinkedIn presence under that name. The borrowed authority from Proper Access and the DigiToegankelijk TOP reference helps, and is real, but it is only stated on-site, not corroborated by third parties. For AI entity recognition this is the weakest category, which is normal at launch. The path up is press, a LinkedIn post from Proper Access, and getting the dataset cited by accessibility and e-commerce communities.

### Content E-E-A-T (55/100)
This is the site's strongest dimension and it is underbuilt relative to its potential. Genuine signals: an identified expert author (Julia Tol, founder of an accessibility specialist firm), a credible track record reference (involvement in a government accessibility programme 2022-2025), a transparent methodology section, and intellectual honesty about the method's limits. That is a better Trust foundation than most sites have. What is missing is the machine-readable layer and freshness discipline: no author/organization schema, no visible dates, no bio depth, and a stale dataset that undercuts the "weekly" promise. Fixing freshness and adding `Person`/`Organization` markup would push this well into the 70s.

### Technical GEO (45/100)
Positives: valid HTTPS on a custom domain, lightweight semantic HTML, excellent accessibility (skip links, ARIA roles, table captions, labelled controls), correct `lang="nl"`, clean heading hierarchy. Negatives that matter for GEO: core content is JS-only with no server-side fallback, and the three machine-readable infrastructure files (`robots.txt`, `sitemap.xml`, `llms.txt`) are all absent. The runtime Tailwind CDN dependency is a minor speed and reliability drag. The fundamentals are healthy; the AI-facing plumbing simply has not been added yet.

### Schema & Structured Data (8/100)
There is no structured data of any kind on any page. For a dashboard that publishes original research data, this is the largest gap relative to opportunity. The high-value additions, in order: `Dataset` (describes the research and makes it eligible for dataset-aware answers), `Organization` (establishes EAA Monitor / Proper Access as an entity with `sameAs` links), `WebSite`, and `FAQPage` on the explanatory blocks. None require a backend; all can be inlined as JSON-LD in the static HTML.

### Platform Optimization (20/100)
No optimization for any AI surface. There is no FAQ schema or concise answer block for Google AI Overviews, no OG data to seed social and Reddit discovery, and no presence on the platforms (Wikipedia, Reddit, YouTube, LinkedIn) that models lean on for corroboration. Given the genuinely newsworthy finding (only ~11% compliance), this site is a strong candidate for a one-page write-up plus a LinkedIn/press push that would lift both this category and Brand Authority together.

---

## Quick Wins (Implement This Week)

1. **Bake the headline numbers into static HTML.** Have the scraper write the four key figures (total checked, % with statement, % without, last-updated date) directly into `index.html` so crawlers read "11%", not "-". This one change lifts Citability, Technical, and Platform at once.
2. **Add `Dataset` + `Organization` JSON-LD** to `index.html`. Describe the research, the 1,246 records, the publisher (Proper Access), and `sameAs: https://www.properaccess.nl`.
3. **Create `llms.txt`** at the site root summarizing what EAA Monitor is, what the dataset measures, the current headline figure, the methodology, and a citation line.
4. **Add `robots.txt` + `sitemap.xml`.** Permissive robots that welcome GPTBot/ClaudeBot/PerplexityBot and point to the sitemap; a 4-URL sitemap.
5. **Fix or restate the update cadence.** Either repair the weekly scrape cron so `last_updated` is current, or change the copy to match the real frequency. Stale data behind a "weekly" promise is a direct trust hit.

## 30-Day Action Plan

### Week 1: Make the data visible and machine-readable
- [ ] Update the scraper to inject the four headline stats and the last-updated date into static `index.html` (and ideally a static, crawlable summary of the table or a `data/results.html`).
- [ ] Add `Dataset` and `Organization` JSON-LD to `index.html`.
- [ ] Verify the weekly scrape workflow is running; fix it if `last_updated` is stale.

### Week 2: AI-facing infrastructure
- [ ] Publish `llms.txt`, `robots.txt`, and `sitemap.xml`.
- [ ] Add Open Graph + Twitter Card tags and a branded share image to all four pages.
- [ ] Add `<link rel="canonical">` to every page.

### Week 3: E-E-A-T and answer-structure
- [ ] Add `Person` (Julia Tol, with credentials) and `WebSite` schema.
- [ ] Convert the "Wat is de EAA?" and "Methodologie" blocks into a visible Q&A pattern and add `FAQPage` schema.
- [ ] Add a visible "Laatst bijgewerkt" date and a short methodology/update-frequency note in static HTML.

### Week 4: Brand authority and distribution
- [ ] Publish the finding as a short post on properaccess.nl and LinkedIn ("Slechts 11% van Nederlandse webshops heeft een toegankelijkheidsverklaring").
- [ ] Seek corroborating mentions: relevant subreddits, accessibility and e-commerce communities, and any press angle.
- [ ] Cross-link EAA Monitor from properaccess.nl so the entity association is explicit and crawlable.

---

## Appendix: Pages Analyzed

| URL | Title | GEO Issues |
|---|---|---|
| /index.html | EAA Monitor — Toegankelijkheidsverklaringen Nederlandse webshops | JS-rendered core data, no schema, no OG, no canonical |
| /over.html | Over dit dashboard — EAA Monitor | Stale "weekly" claim, no Person/Org schema, no dates, no OG |
| /bezwaar.html | Bezwaarformulier (Formspree) | Utility page; no schema, no OG (low priority) |
| /bezwaren.html | Ingediende bezwaren | JS-rendered list, no schema, no OG |
| /robots.txt | (404) | Missing |
| /sitemap.xml | (missing) | Missing |
| /llms.txt | (missing) | Missing |

**Site-wide infrastructure status:** robots.txt absent, sitemap.xml absent, llms.txt absent, JSON-LD absent on all pages, Open Graph absent on all pages, canonical absent on all pages.
