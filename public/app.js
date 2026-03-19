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

  const CATEGORY_LABELS = {
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
      color: "#15803D",
      bgColor: "#F0FDF4",
      dotClass: "bg-status-found",
    },
    notfound: {
      label: "Zonder verklaring",
      color: "#A30D4B",
      bgColor: "#FDF2F8",
      dotClass: "bg-magenta",
    },
    error: {
      label: "Fout bij controle",
      color: "#6B7280",
      bgColor: "#F9FAFB",
      dotClass: "bg-gray-400",
    },
  };

  // ── Data loading ──

  async function loadData() {
    try {
      let response = await fetch("data/results.json");
      if (!response.ok) {
        response = await fetch("../data/results.json");
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      console.error("Kan data niet laden:", err);
      return null;
    }
  }

  // ── Stats ──

  function getStats(data) {
    const total = data.total || 0;
    const withStatement = data.with_statement || 0;
    const errors = data.errors || 0;
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

  function updateStats(stats, lastUpdated) {
    document.getElementById("stat-total").textContent = stats.total;
    document.getElementById("stat-percentage").textContent =
      stats.pctWith + "%";
    document.getElementById("stat-percentage-without").textContent =
      stats.pctWithout + "%";
    document.getElementById("chart-total").textContent = stats.total;

    if (lastUpdated) {
      const date = new Date(lastUpdated);
      const formatted = date.toLocaleDateString("nl-NL", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      document.getElementById("last-updated").textContent =
        "Laatst bijgewerkt: " + formatted;
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
        <div class="flex items-center gap-4">
          <div class="w-40 sm:w-48 flex-shrink-0">
            <div class="flex items-center gap-2">
              <span class="status-dot ${cfg.dotClass}" aria-hidden="true"></span>
              <span class="text-sm font-semibold">${cfg.label}</span>
            </div>
          </div>
          <div class="flex-1 flex items-center gap-3">
            <div class="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
              <div class="chart-bar h-full rounded-full flex items-center px-3" style="width: ${barWidth}%; background-color: ${cfg.color};">
                ${row.count > 0 ? `<span class="text-white text-xs font-bold">${row.count}</span>` : ""}
              </div>
            </div>
            <span class="text-sm font-bold text-gray-600 w-12 text-right">${row.pct}%</span>
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
        <tr class="border-b border-gray-100">
          <td class="py-3 px-2">
            <span class="flex items-center gap-2">
              <span class="status-dot ${cfg.dotClass}" aria-hidden="true"></span>
              ${cfg.label}
            </span>
          </td>
          <td class="py-3 px-2 text-right font-semibold">${row.count}</td>
          <td class="py-3 px-2 text-right">${row.pct}%</td>
        </tr>`;
      })
      .join("");

    // Total row
    tableBody.innerHTML += `
      <tr class="border-t-2 border-gray-300 font-bold">
        <td class="py-3 px-2">Totaal</td>
        <td class="py-3 px-2 text-right">${stats.total}</td>
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
        <button class="category-card bg-white rounded-xl border border-gray-200 p-4 text-left hover:border-petrol hover:shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-petrol" data-category="${escapeHtml(cat)}">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">${escapeHtml(label)}</p>
          <p class="text-2xl font-extrabold font-heading mt-1 text-darkblue">${data.total}</p>
          <div class="mt-2 w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div class="h-full rounded-full bg-status-found" style="width: ${pct}%;"></div>
          </div>
          <p class="text-xs text-gray-500 mt-1">${data.found} van ${data.total} met verklaring</p>
        </button>`;
      })
      .join("");

    // Click handler: filter table by category
    container.querySelectorAll(".category-card").forEach((card) => {
      card.addEventListener("click", () => {
        const cat = card.dataset.category;
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
      textClass: "text-magenta",
      sortValue: 1,
    };
  }

  function filterWebshops() {
    const search = document
      .getElementById("filter-search")
      .value.toLowerCase()
      .trim();
    const category = document.getElementById("filter-category").value;
    const status = document.getElementById("filter-status").value;

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
        pages.push(`<span class="inline-flex items-center justify-center w-9 h-9 rounded-md bg-petrol text-white font-semibold text-sm" aria-current="page">${p}</span>`);
      } else {
        pages.push(`<button class="page-btn inline-flex items-center justify-center w-9 h-9 rounded-md border border-gray-300 text-sm text-darkblue hover:bg-gray-100" data-page="${p}" aria-label="Ga naar pagina ${p}">${p}</button>`);
      }
    };

    addPage(1);
    if (currentPage > 3) pages.push('<span class="px-1 text-gray-400">...</span>');
    for (let p = Math.max(2, currentPage - 1); p <= Math.min(totalPages - 1, currentPage + 1); p++) {
      addPage(p);
    }
    if (currentPage < totalPages - 2) pages.push('<span class="px-1 text-gray-400">...</span>');
    if (totalPages > 1) addPage(totalPages);

    const prevDisabled = currentPage === 1;
    const nextDisabled = currentPage === totalPages;

    nav.innerHTML = `
      <p class="text-sm text-gray-600">${start}–${end} van ${totalItems} webshops</p>
      <div class="flex items-center gap-1">
        <button class="page-prev inline-flex items-center justify-center w-9 h-9 rounded-md border border-gray-300 text-sm text-darkblue hover:bg-gray-100 ${prevDisabled ? "opacity-40 cursor-default" : ""}" ${prevDisabled ? "disabled" : ""} aria-label="Vorige pagina">&lsaquo;</button>
        ${pages.join("")}
        <button class="page-next inline-flex items-center justify-center w-9 h-9 rounded-md border border-gray-300 text-sm text-darkblue hover:bg-gray-100 ${nextDisabled ? "opacity-40 cursor-default" : ""}" ${nextDisabled ? "disabled" : ""} aria-label="Volgende pagina">&rsaquo;</button>
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
        ? `${filtered.length} webshops`
        : `${filtered.length} van ${allWebshops.length} webshops`;

    if (sorted.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="py-12 text-center text-gray-400">Geen resultaten gevonden</td></tr>';
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
          shop.has_statement && shop.statement_url
            ? `<a href="${escapeHtml(shop.statement_url)}" target="_blank" rel="noopener noreferrer" class="text-petrol underline hover:text-magenta text-sm">Bekijk verklaring</a>`
            : '<span class="text-gray-300">-</span>';

        const rowBg = i % 2 === 0 ? "" : "bg-gray-50";

        return `<tr class="${rowBg} border-b border-gray-100 hover:bg-petrol-light transition-colors">
          <td class="py-3 px-4">
            <a href="${escapeHtml(shop.url)}" target="_blank" rel="noopener noreferrer" class="text-petrol hover:text-magenta font-semibold">${escapeHtml(shop.name)}</a>
          </td>
          <td class="py-3 px-4 hidden sm:table-cell text-sm text-gray-600">${escapeHtml(catLabel)}</td>
          <td class="py-3 px-4">
            <span class="inline-flex items-center gap-2 ${status.textClass}">
              <span class="status-dot ${status.dotClass}" aria-hidden="true"></span>
              <span class="text-sm font-semibold">${escapeHtml(status.text)}</span>
            </span>
          </td>
          <td class="py-3 px-4 hidden md:table-cell">${statementLink}</td>
          <td class="py-3 px-4 hidden lg:table-cell text-sm text-gray-600">${checkedDate}</td>
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

  // ── Setup ──

  const SORT_LABELS = {
    name: "webshop naam",
    category: "categorie",
    status: "status",
    date: "datum",
  };

  function updateSortAriaLabels() {
    document.querySelectorAll(".sort-btn").forEach((btn) => {
      const key = btn.dataset.sort;
      const label = SORT_LABELS[key] || key;
      if (currentSort.key === key) {
        const dir = currentSort.direction === "asc" ? "oplopend" : "aflopend";
        btn.setAttribute(
          "aria-label",
          `Sorteer op ${label}, huidige sortering: ${dir}`
        );
      } else {
        btn.setAttribute("aria-label", `Sorteer op ${label}`);
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
  }

  // ── Init ──

  async function init() {
    const data = await loadData();
    if (!data) {
      document.getElementById("results-body").innerHTML =
        '<tr><td colspan="5" class="py-12 text-center text-red-600">Fout bij het laden van data.</td></tr>';
      return;
    }

    allWebshops = data.webshops || [];
    const stats = getStats(data);

    updateStats(stats, data.last_updated);
    renderStatusChart(stats);
    renderCategoryCards(allWebshops);
    populateCategories(allWebshops);
    setupToggle();
    setupSorting();
    setupFilters();
    renderTable();

    const nameBtn = document.querySelector('[data-sort="name"]');
    if (nameBtn) nameBtn.classList.add("asc");
    updateSortAriaLabels();
  }

  init();
})();
