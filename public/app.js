/**
 * EAA Monitor — Frontend logic
 * Loads results.json and renders the dashboard with charts, category cards,
 * filters, sorting, and a full webshop table.
 */

(function () {
  "use strict";

  let allWebshops = [];
  let currentSort = { key: "name", direction: "asc" };
  let currentPage = 1;
  const PAGE_SIZE = 25;

  // WCAG-scan-overlay (data/axe-results.json): url -> "fouten"|"schoon"|
  // "niet-scanbaar". Alleen voor sites met een verklaring; los van de
  // footer-scrape zodat een nieuwe scrape de scanuitslag niet overschrijft.
  let axeStatusByUrl = {};
  let axeDetailUrl = "https://wcag-scan.eu/";

  // Dezelfde dashboard-logica bedient twee datasets (webshops en financiële
  // instellingen). De pagina zet window.EAA_MONITOR_CONFIG; zonder config gelden
  // de webshop-defaults, zodat monitor.html zich ongewijzigd gedraagt.
  const CFG = window.EAA_MONITOR_CONFIG || {};
  const DATA_URL = CFG.dataUrl || "data/results.json";
  const NOUN = CFG.noun || "webshops";

  const CATEGORY_LABELS = CFG.categoryLabels || {
    marketplace: "Marketplace",
    elektronica: "Elektronica",
    mode: "Mode",
    supermarkt: "Supermarkt",
    drogisterij: "Drogisterij",
    wonen: "Wonen",
    sport: "Sport",
    boeken: "Boeken",
    speelgoed: "Speelgoed",
    overig: "Overig",
  };

  const STATUS_CONFIG = {
    found: {
      label: "Met verklaring",
      color: "#1C6B3C",
      bgColor: "#EAF4EC",
      dotClass: "bg-status-found",
    },
    notfound: {
      label: "Zonder verklaring",
      color: "#B3261E",
      bgColor: "#FBEDEB",
      dotClass: "bg-status-notfound",
    },
    error: {
      label: "Fout bij controle",
      color: "#5B6560",
      bgColor: "#F2F4F1",
      dotClass: "bg-status-error",
    },
  };

  // ── Data loading ──

  async function loadData() {
    try {
      let response = await fetch(DATA_URL);
      if (!response.ok) {
        response = await fetch("../" + DATA_URL);
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      console.error("Kan data niet laden:", err);
      return null;
    }
  }

  async function loadObjections() {
    try {
      let response = await fetch("data/objections.json");
      if (!response.ok) {
        response = await fetch("../data/objections.json");
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      // Geen bezwaren-bestand of niet leesbaar: behandel als leeg.
      console.warn("Kan bezwaren niet laden, ga verder zonder:", err);
      return [];
    }
  }

  async function loadAxe() {
    try {
      let response = await fetch("data/axe-results.json");
      if (!response.ok) {
        response = await fetch("../data/axe-results.json");
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      // Geen scan-overlay of niet leesbaar: kolom blijft leeg, geen breuk.
      console.warn("Kan WCAG-scan-data niet laden, ga verder zonder:", err);
      return null;
    }
  }

  // Normaliseer een URL zodat matching robuust is, ook bij kleine verschillen
  // (hoofdletters, protocol, leidend "www.", trailing slash).
  function normalizeUrl(url) {
    if (!url) return "";
    return url
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .replace(/\/+$/, "");
  }

  // ── Stats ──

  function computeStats(webshops) {
    const total = webshops.length;
    let withStatement = 0;
    let errors = 0;
    webshops.forEach((shop) => {
      if (shop.scrape_status !== "success") {
        errors++;
      } else if (shop.has_statement) {
        withStatement++;
      }
    });
    const withoutStatement = total - withStatement - errors;
    const pctWith = total > 0 ? Math.round((withStatement / total) * 100) : 0;
    const pctWithout =
      total > 0 ? Math.round((withoutStatement / total) * 100) : 0;
    const pctError = total > 0 ? Math.round((errors / total) * 100) : 0;
    return {
      total,
      withStatement,
      withoutStatement,
      errors,
      pctWith,
      pctWithout,
      pctError,
    };
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function updateStats(stats, lastUpdated) {
    setText("stat-total", stats.total);
    setText("stat-percentage", stats.pctWith + "%");
    setText("stat-percentage-without", stats.pctWithout + "%");
    setText("chart-total", stats.total);

    if (lastUpdated) {
      const date = new Date(lastUpdated);
      const formatted = date.toLocaleDateString("nl-NL", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      setText("last-updated", "Laatst bijgewerkt: " + formatted);
    }
  }

  // ── Status chart ──

  function renderStatusChart(stats) {
    const chartEl = document.getElementById("status-chart");
    const maxCount = Math.max(
      stats.withStatement,
      stats.withoutStatement,
      stats.errors,
      1
    );

    const rows = [
      {
        key: "found",
        count: stats.withStatement,
        pct: stats.pctWith,
      },
      {
        key: "notfound",
        count: stats.withoutStatement,
        pct: stats.pctWithout,
      },
      {
        key: "error",
        count: stats.errors,
        pct: stats.pctError,
      },
    ];

    chartEl.innerHTML = rows
      .map((row) => {
        const cfg = STATUS_CONFIG[row.key];
        const barWidth =
          maxCount > 0 ? Math.max((row.count / maxCount) * 100, 2) : 0;
        return `
        <div class="flex items-center gap-3">
          <div class="w-32 sm:w-36 flex-shrink-0">
            <div class="flex items-center gap-2">
              <span class="status-dot ${cfg.dotClass}" aria-hidden="true"></span>
              <span class="text-sm font-semibold">${cfg.label}</span>
            </div>
          </div>
          <div class="flex-1 flex items-center gap-3 min-w-0">
            <div class="flex-1 bg-navy/10 rounded-full h-8 overflow-hidden">
              <div class="chart-bar h-full rounded-full" style="width: ${barWidth}%; background-color: ${cfg.color};"></div>
            </div>
            <span class="text-sm font-bold text-navy w-24 text-right font-mono whitespace-nowrap">${row.count.toLocaleString("nl-NL")} <span class="font-medium text-gray-600">(${row.pct}%)</span></span>
          </div>
        </div>`;
      })
      .join("");

    // Status table
    const tableBody = document.getElementById("status-table-body");
    tableBody.innerHTML = rows
      .map((row) => {
        const cfg = STATUS_CONFIG[row.key];
        return `
        <tr class="border-b border-line">
          <td class="py-3 px-2">
            <span class="flex items-center gap-2">
              <span class="status-dot ${cfg.dotClass}" aria-hidden="true"></span>
              ${cfg.label}
            </span>
          </td>
          <td class="py-3 px-2 text-right font-semibold tabular-nums">${row.count.toLocaleString("nl-NL")}</td>
          <td class="py-3 px-2 text-right tabular-nums">${row.pct}%</td>
        </tr>`;
      })
      .join("");

    // Total row
    tableBody.innerHTML += `
      <tr class="border-t-2 border-line font-bold">
        <td class="py-3 px-2">Totaal</td>
        <td class="py-3 px-2 text-right tabular-nums">${stats.total.toLocaleString("nl-NL")}</td>
        <td class="py-3 px-2 text-right">100%</td>
      </tr>`;
  }

  // ── Category cards ──

  function renderCategoryCards(webshops) {
    const categories = {};
    webshops.forEach((shop) => {
      const cat = shop.category || "overig";
      if (!categories[cat]) categories[cat] = { total: 0, found: 0 };
      categories[cat].total++;
      if (shop.has_statement && shop.scrape_status === "success") {
        categories[cat].found++;
      }
    });

    const sorted = Object.entries(categories).sort(
      (a, b) => b[1].total - a[1].total
    );

    const container = document.getElementById("category-cards");
    container.innerHTML = sorted
      .map(([cat, data]) => {
        const pct =
          data.total > 0 ? Math.round((data.found / data.total) * 100) : 0;
        const label = CATEGORY_LABELS[cat] || cat;
        return `
        <div class="bg-white rounded-2xl border border-line p-4">
          <h3 class="m-0">
            <button class="cat-filter-btn text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-brand focus:outline-none focus:ring-2 focus:ring-brand rounded transition-colors" data-category="${escapeHtml(cat)}">${escapeHtml(label)}</button>
          </h3>
          <p class="text-2xl font-extrabold mt-1 text-navy">${data.total}</p>
          <div class="mt-2 w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div class="h-full rounded-full bg-status-found" style="width: ${pct}%;"></div>
          </div>
          <p class="text-xs text-gray-500 mt-1">${data.found} van ${data.total} met verklaring</p>
        </div>`;
      })
      .join("");

    // Click handler: filter de tabel op categorie (de categorienaam is de knop).
    container.querySelectorAll(".cat-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.category;
        const select = document.getElementById("filter-category");
        select.value = select.value === cat ? "" : cat;
        select.dispatchEvent(new Event("change"));
        document
          .getElementById("results-table")
          .scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  // ── Chart/Table toggle ──

  function setupToggle() {
    const tabChart = document.getElementById("tab-chart");
    const tabTable = document.getElementById("tab-table");
    const chartView = document.getElementById("chart-view");
    const tableView = document.getElementById("table-view");

    tabChart.addEventListener("click", () => {
      tabChart.classList.add("active");
      tabChart.setAttribute("aria-selected", "true");
      tabTable.classList.remove("active");
      tabTable.setAttribute("aria-selected", "false");
      chartView.classList.remove("hidden");
      tableView.classList.add("hidden");
    });

    tabTable.addEventListener("click", () => {
      tabTable.classList.add("active");
      tabTable.setAttribute("aria-selected", "true");
      tabChart.classList.remove("active");
      tabChart.setAttribute("aria-selected", "false");
      tableView.classList.remove("hidden");
      chartView.classList.add("hidden");
    });
  }

  // ── Webshop table ──

  function populateCategories(webshops) {
    const categories = [...new Set(webshops.map((s) => s.category))].sort();
    const select = document.getElementById("filter-category");
    categories.forEach((cat) => {
      const option = document.createElement("option");
      option.value = cat;
      option.textContent = CATEGORY_LABELS[cat] || cat;
      select.appendChild(option);
    });
  }

  function getStatusInfo(shop) {
    if (shop.scrape_status !== "success") {
      return {
        dotClass: STATUS_CONFIG.error.dotClass,
        text: STATUS_CONFIG.error.label,
        textClass: "text-gray-500",
        sortValue: 2,
      };
    }
    if (shop.has_statement) {
      return {
        dotClass: STATUS_CONFIG.found.dotClass,
        text: STATUS_CONFIG.found.label,
        textClass: "text-status-found",
        sortValue: 0,
      };
    }
    return {
      dotClass: STATUS_CONFIG.notfound.dotClass,
      text: STATUS_CONFIG.notfound.label,
      textClass: "text-status-notfound",
      sortValue: 1,
    };
  }

  // ── WCAG-scan-kolom ──

  // Status van de WCAG-scan voor deze site, of "" als er geen verklaring is of
  // de site niet gescand is. We tonen het alleen bij sites met een verklaring.
  function axeStatus(shop) {
    if (!shop.has_statement) return "";
    return axeStatusByUrl[normalizeUrl(shop.url)] || "";
  }

  function axeSortValue(shop) {
    const order = { fouten: 0, schoon: 1, "niet-scanbaar": 2 };
    const v = order[axeStatus(shop)];
    return v === undefined ? 3 : v;
  }

  function axeCellHtml(shop) {
    const st = axeStatus(shop);
    if (st === "fouten") {
      return `<span class="inline-flex items-center gap-2 text-status-notfound">
            <span class="status-dot bg-status-notfound" aria-hidden="true"></span>
            <span class="text-sm font-semibold">Fouten gevonden</span>
          </span>
          <a href="${escapeHtml(axeDetailUrl)}" target="_blank" rel="noopener noreferrer" class="link text-xs block mt-1" aria-label="Bekijk de gevonden toegankelijkheidsfouten van ${escapeHtml(shop.name)} op wcag-scan.eu">Bekijk fouten</a>`;
    }
    if (st === "schoon") {
      return `<span class="inline-flex items-center gap-2 text-status-found">
            <span class="status-dot bg-status-found" aria-hidden="true"></span>
            <span class="text-sm font-semibold">Geen fouten gevonden</span>
          </span>`;
    }
    if (st === "niet-scanbaar") {
      return `<span class="inline-flex items-center gap-2 text-gray-500">
            <span class="status-dot bg-status-error" aria-hidden="true"></span>
            <span class="text-sm">Niet te scannen</span>
          </span>`;
    }
    return '<span class="text-gray-300">-</span>';
  }

  // Vult de samenvattingsnoot onder de tabel (#axe-note), als die bestaat.
  function renderAxeNote(axe) {
    const el = document.getElementById("axe-note");
    if (!el || !axe.summary) return;
    const s = axe.summary;
    const scanned = s.fouten + s.schoon;
    const datum = axe.generated
      ? new Date(axe.generated).toLocaleDateString("nl-NL", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      : "";
    el.innerHTML =
      `Van de ${scanned} sites met een verklaring die we konden scannen, bevat ` +
      `<strong>${s.pct_fouten_van_gescand}%</strong> minstens één automatisch ` +
      `detecteerbare WCAG-fout. Gemeten met ${escapeHtml(axe.engine || "axe-core")}` +
      (datum ? ` op ${datum}` : "") +
      `. Automatische checks dekken niet alle WCAG-eisen, dus "geen fouten gevonden" ` +
      `betekent niet automatisch volledig toegankelijk. Wil je weten wélke fouten een ` +
      `site bevat, gebruik dan <a href="${escapeHtml(axeDetailUrl)}" target="_blank" ` +
      `rel="noopener noreferrer" class="link">wcag-scan.eu</a>.`;
  }

  function filterWebshops() {
    const search = document
      .getElementById("filter-search")
      .value.toLowerCase()
      .trim();
    const category = document.getElementById("filter-category").value;
    const status = document.getElementById("filter-status").value;
    const wcagEl = document.getElementById("filter-wcag");
    const wcag = wcagEl ? wcagEl.value : "";

    let filtered = allWebshops;

    if (search) {
      filtered = filtered.filter((s) => s.name.toLowerCase().includes(search));
    }
    if (category) {
      filtered = filtered.filter((s) => s.category === category);
    }
    if (status === "found") {
      filtered = filtered.filter(
        (s) => s.has_statement && s.scrape_status === "success"
      );
    } else if (status === "not_found") {
      filtered = filtered.filter(
        (s) => !s.has_statement && s.scrape_status === "success"
      );
    } else if (status === "error") {
      filtered = filtered.filter((s) => s.scrape_status !== "success");
    }

    if (wcag) {
      filtered = filtered.filter((s) => axeStatus(s) === wcag);
    }

    return filtered;
  }

  function sortWebshops(webshops) {
    const { key, direction } = currentSort;
    const mod = direction === "asc" ? 1 : -1;
    return [...webshops].sort((a, b) => {
      let vA, vB;
      switch (key) {
        case "name":
          vA = a.name.toLowerCase();
          vB = b.name.toLowerCase();
          break;
        case "category":
          vA = CATEGORY_LABELS[a.category] || a.category;
          vB = CATEGORY_LABELS[b.category] || b.category;
          break;
        case "status":
          vA = getStatusInfo(a).sortValue;
          vB = getStatusInfo(b).sortValue;
          break;
        case "wcag":
          vA = axeSortValue(a);
          vB = axeSortValue(b);
          break;
        case "date":
          vA = a.last_checked || "";
          vB = b.last_checked || "";
          break;
        default:
          return 0;
      }
      if (vA < vB) return -1 * mod;
      if (vA > vB) return 1 * mod;
      return 0;
    });
  }

  function goToPage(page) {
    currentPage = page;
    renderTable();
    document.getElementById("results-table").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderPagination(totalItems) {
    const nav = document.getElementById("pagination");
    const totalPages = Math.ceil(totalItems / PAGE_SIZE);

    if (totalPages <= 1) {
      nav.innerHTML = "";
      return;
    }

    const start = (currentPage - 1) * PAGE_SIZE + 1;
    const end = Math.min(currentPage * PAGE_SIZE, totalItems);

    // Build page buttons
    const pages = [];
    const addPage = (p) => {
      if (p === currentPage) {
        pages.push(`<span class="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-brand text-white font-semibold text-sm" aria-current="page">${p}</span>`);
      } else {
        pages.push(`<button class="page-btn inline-flex items-center justify-center w-9 h-9 rounded-lg border border-field text-sm text-navy hover:bg-gray-100" data-page="${p}" aria-label="Ga naar pagina ${p}">${p}</button>`);
      }
    };

    addPage(1);
    if (currentPage > 3) pages.push('<span class="px-1 text-gray-500">...</span>');
    for (let p = Math.max(2, currentPage - 1); p <= Math.min(totalPages - 1, currentPage + 1); p++) {
      addPage(p);
    }
    if (currentPage < totalPages - 2) pages.push('<span class="px-1 text-gray-500">...</span>');
    if (totalPages > 1) addPage(totalPages);

    const prevDisabled = currentPage === 1;
    const nextDisabled = currentPage === totalPages;

    nav.innerHTML = `
      <p class="text-sm text-gray-600">${start}–${end} van ${totalItems} ${NOUN}</p>
      <div class="flex items-center gap-1">
        <button class="page-prev inline-flex items-center justify-center w-9 h-9 rounded-lg border border-field text-sm text-navy hover:bg-gray-100 ${prevDisabled ? "opacity-40 cursor-default" : ""}" ${prevDisabled ? "disabled" : ""} aria-label="Vorige pagina">&lsaquo;</button>
        ${pages.join("")}
        <button class="page-next inline-flex items-center justify-center w-9 h-9 rounded-lg border border-field text-sm text-navy hover:bg-gray-100 ${nextDisabled ? "opacity-40 cursor-default" : ""}" ${nextDisabled ? "disabled" : ""} aria-label="Volgende pagina">&rsaquo;</button>
      </div>`;

    nav.querySelectorAll(".page-btn").forEach((btn) =>
      btn.addEventListener("click", () => goToPage(Number(btn.dataset.page)))
    );
    const prevBtn = nav.querySelector(".page-prev");
    if (prevBtn && !prevDisabled) prevBtn.addEventListener("click", () => goToPage(currentPage - 1));
    const nextBtn = nav.querySelector(".page-next");
    if (nextBtn && !nextDisabled) nextBtn.addEventListener("click", () => goToPage(currentPage + 1));
  }

  function renderTable() {
    const filtered = filterWebshops();
    const sorted = sortWebshops(filtered);
    const tbody = document.getElementById("results-body");
    const totalPages = Math.ceil(sorted.length / PAGE_SIZE);

    // Clamp currentPage
    if (currentPage > totalPages) currentPage = Math.max(1, totalPages);

    document.getElementById("filter-count").textContent =
      filtered.length === allWebshops.length
        ? `${filtered.length} ${NOUN}`
        : `${filtered.length} van ${allWebshops.length} ${NOUN}`;

    // Zoek-/filterfeedback direct onder de zoekbalk (boven de vouw), met
    // aria-live zodat ook screenreaders de uitkomst horen. De resultatentabel
    // staat vaak onder de vouw; zonder deze melding lijkt zoeken niets te doen.
    const searchStatus = document.getElementById("search-status");
    if (searchStatus) {
      if (filtered.length === allWebshops.length) {
        searchStatus.textContent = "";
      } else if (filtered.length === 0) {
        searchStatus.textContent = "Geen resultaten gevonden";
      } else if (filtered.length === 1) {
        searchStatus.textContent = "1 resultaat gevonden";
      } else {
        searchStatus.textContent = `${filtered.length.toLocaleString("nl-NL")} resultaten gevonden`;
      }
    }

    if (sorted.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="py-12 text-center text-gray-600">Geen resultaten gevonden</td></tr>';
      renderPagination(0);
      return;
    }

    const pageStart = (currentPage - 1) * PAGE_SIZE;
    const pageItems = sorted.slice(pageStart, pageStart + PAGE_SIZE);

    tbody.innerHTML = pageItems
      .map((shop, i) => {
        const status = getStatusInfo(shop);
        const catLabel = CATEGORY_LABELS[shop.category] || shop.category;
        const checkedDate = shop.last_checked
          ? new Date(shop.last_checked).toLocaleDateString("nl-NL")
          : "-";

        const statementLink =
          shop.has_statement && safeHttpUrl(shop.statement_url)
            ? `<a href="${escapeHtml(safeHttpUrl(shop.statement_url))}" target="_blank" rel="noopener noreferrer" class="link text-sm">Bekijk verklaring</a>`
            : '<span class="text-gray-300">-</span>';

        const rowBg = i % 2 === 0 ? "" : "bg-gray-50";

        const objectionLink = `<a href="/bezwaar.html?name=${encodeURIComponent(shop.name)}&url=${encodeURIComponent(shop.url)}" class="link text-sm" aria-label="Bezwaar maken tegen vermelding van ${escapeHtml(shop.name)}">Bezwaar maken</a>`;

        // "Zonder verklaring"-rij: nodig de eigenaar uit hun verklaring te melden
        // als wij die gemist hebben (link verstopt, achter cookiemelding, in pdf).
        const isZonderVerklaring = shop.scrape_status === "success" && !shop.has_statement;
        const meldLink = isZonderVerklaring
          ? `<a href="/melden.html?url=${encodeURIComponent(shop.url)}" class="link text-sm" aria-label="Verklaring melden voor ${escapeHtml(shop.name)}">Verklaring melden</a>`
          : "";

        return `<tr class="${rowBg} border-b border-line hover:bg-softblue transition-colors">
          <td class="py-3 px-4">
            <a href="${escapeHtml(shop.url)}" target="_blank" rel="noopener noreferrer" class="text-brand hover:text-brand-dark font-semibold">${escapeHtml(shop.name)}</a>
          </td>
          <td class="py-3 px-4 hidden sm:table-cell text-sm text-gray-600">${escapeHtml(catLabel)}</td>
          <td class="py-3 px-4">
            <span class="inline-flex items-center gap-2 ${status.textClass}">
              <span class="status-dot ${status.dotClass}" aria-hidden="true"></span>
              <span class="text-sm font-semibold">${escapeHtml(status.text)}</span>
            </span>
          </td>
          <td class="py-3 px-4 hidden md:table-cell">${statementLink}</td>
          <td class="py-3 px-4 hidden md:table-cell">${axeCellHtml(shop)}</td>
          <td class="py-3 px-4 hidden lg:table-cell text-sm text-gray-600">${checkedDate}</td>
          <td class="py-3 px-4 hidden md:table-cell">
            <div class="flex flex-col gap-1">${objectionLink}${meldLink}</div>
          </td>
        </tr>`;
      })
      .join("");

    renderPagination(sorted.length);
  }

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Alleen http(s)-URL's als href renderen. De statement_url komt uit gescrapete
  // footers (onbetrouwbaar); escapeHtml blokkeert geen javascript:- of data:-scheme.
  function safeHttpUrl(url) {
    return url && /^https?:\/\//i.test(url) ? url : "";
  }

  // ── Setup ──

  // Labels gelijk aan de ZICHTBARE kolomtekst, zodat de toegankelijke naam de
  // zichtbare tekst bevat (WCAG 2.5.3 Label in Name).
  const SORT_LABELS = CFG.sortLabels || {
    name: "Webshop",
    category: "Categorie",
    status: "Status",
    date: "Gecontroleerd",
  };
  // Geldt op alle pagina's, ook die met een eigen sortLabels-config.
  if (!SORT_LABELS.wcag) SORT_LABELS.wcag = "WCAG-scan";

  function updateSortAriaLabels() {
    document.querySelectorAll(".sort-btn").forEach((btn) => {
      const key = btn.dataset.sort;
      const label = SORT_LABELS[key] || key;
      const th = btn.closest("th");
      if (currentSort.key === key) {
        const dir = currentSort.direction === "asc" ? "oplopend" : "aflopend";
        btn.setAttribute("aria-label", `Sorteer op ${label}, huidige sortering: ${dir}`);
        if (th) th.setAttribute("aria-sort", currentSort.direction === "asc" ? "ascending" : "descending");
      } else {
        btn.setAttribute("aria-label", `Sorteer op ${label}`);
        if (th) th.setAttribute("aria-sort", "none");
      }
    });
  }

  function setupSorting() {
    document.querySelectorAll(".sort-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.sort;
        if (currentSort.key === key) {
          currentSort.direction =
            currentSort.direction === "asc" ? "desc" : "asc";
        } else {
          currentSort.key = key;
          currentSort.direction = "asc";
        }
        document
          .querySelectorAll(".sort-btn")
          .forEach((b) => b.classList.remove("asc", "desc"));
        btn.classList.add(currentSort.direction);
        updateSortAriaLabels();
        currentPage = 1;
        renderTable();
      });
    });
  }

  function resetPageAndRender() {
    currentPage = 1;
    renderTable();
  }

  function setupFilters() {
    document
      .getElementById("filter-search")
      .addEventListener("input", resetPageAndRender);
    const searchBtn = document.getElementById("search-btn");
    if (searchBtn) {
      searchBtn.addEventListener("click", resetPageAndRender);
    }
    document
      .getElementById("filter-category")
      .addEventListener("change", resetPageAndRender);
    document
      .getElementById("filter-status")
      .addEventListener("change", resetPageAndRender);
    const wcagFilter = document.getElementById("filter-wcag");
    if (wcagFilter) {
      wcagFilter.addEventListener("change", resetPageAndRender);
    }
  }

  // ── Init ──

  async function init() {
    const [data, objections, axe] = await Promise.all([
      loadData(),
      loadObjections(),
      loadAxe(),
    ]);
    if (!data) {
      document.getElementById("results-body").innerHTML =
        '<tr><td colspan="7" class="py-12 text-center text-red-600">Fout bij het laden van data.</td></tr>';
      return;
    }

    // WCAG-scan-overlay indexeren op genormaliseerde URL en de samenvattingsnoot
    // vullen. Ontbreekt de overlay, dan blijft de kolom leeg (streepjes).
    if (axe && axe.sites) {
      if (axe.detail_url) axeDetailUrl = axe.detail_url;
      Object.values(axe.sites).forEach((entry) => {
        axeStatusByUrl[normalizeUrl(entry.url)] = entry.status;
      });
      renderAxeNote(axe);
    }

    // Webshops die bezwaar hebben gemaakt uitsluiten van tabel en cijfers.
    const objectionSet = new Set(
      objections.map((o) => normalizeUrl(o.url)).filter(Boolean)
    );
    allWebshops = (data.webshops || []).filter(
      (s) => !objectionSet.has(normalizeUrl(s.url))
    );
    const stats = computeStats(allWebshops);

    updateStats(stats, data.last_updated);
    renderStatusChart(stats);
    renderCategoryCards(allWebshops);
    populateCategories(allWebshops);
    setupToggle();
    setupSorting();
    setupFilters();

    // Zoekterm uit de URL (?q=...) overnemen, bijv. vanaf de homepage.
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    const searchInput = document.getElementById("filter-search");
    if (q && searchInput) searchInput.value = q;

    renderTable();

    const nameBtn = document.querySelector('[data-sort="name"]');
    if (nameBtn) nameBtn.classList.add("asc");
    updateSortAriaLabels();
  }

  init();
})();
