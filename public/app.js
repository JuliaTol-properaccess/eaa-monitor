/**
 * EAA Monitor — Frontend logic
 * Loads results.json and renders the dashboard table with filters and sorting.
 */

(function () {
  "use strict";

  let allWebshops = [];
  let currentSort = { key: "name", direction: "asc" };

  // Category labels (Dutch)
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

  async function loadData() {
    try {
      // Try relative path (deployed), then parent path (local dev from public/)
      let response = await fetch("data/results.json");
      if (!response.ok) {
        response = await fetch("../data/results.json");
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      return data;
    } catch (err) {
      console.error("Kan data niet laden:", err);
      return null;
    }
  }

  function updateStats(data) {
    document.getElementById("stat-total").textContent = data.total;
    document.getElementById("stat-with").textContent = data.with_statement;
    document.getElementById("stat-without").textContent = data.without_statement;

    const percentage =
      data.total > 0
        ? Math.round((data.with_statement / data.total) * 100)
        : 0;
    document.getElementById("stat-percentage").textContent = percentage + "%";

    // Progress bar
    const withPct =
      data.total > 0 ? (data.with_statement / data.total) * 100 : 0;
    const errorPct = data.total > 0 ? (data.errors / data.total) * 100 : 0;
    document.getElementById("progress-with").style.width = withPct + "%";
    document.getElementById("progress-error").style.width = errorPct + "%";

    const progressLabel = `${data.with_statement} van ${data.total} webshops heeft een toegankelijkheidsverklaring (${percentage}%)`;
    document.getElementById("progress-label").textContent = progressLabel;
    document
      .getElementById("progress-container")
      .setAttribute("aria-label", progressLabel);

    // Last updated
    if (data.last_updated) {
      const date = new Date(data.last_updated);
      document.getElementById("last-updated").textContent =
        "Laatst bijgewerkt: " +
        date.toLocaleDateString("nl-NL", {
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
    }
  }

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
        icon: "⚠",
        text: "Fout bij controle",
        class: "text-gray-500",
        sortValue: 2,
      };
    }
    if (shop.has_statement) {
      return {
        icon: "✓",
        text: "Gevonden",
        class: "text-green-700",
        sortValue: 0,
      };
    }
    return {
      icon: "✗",
      text: "Niet gevonden",
      class: "text-magenta",
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
    const modifier = direction === "asc" ? 1 : -1;

    return [...webshops].sort((a, b) => {
      let valA, valB;

      switch (key) {
        case "name":
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
          break;
        case "category":
          valA = CATEGORY_LABELS[a.category] || a.category;
          valB = CATEGORY_LABELS[b.category] || b.category;
          break;
        case "status":
          valA = getStatusInfo(a).sortValue;
          valB = getStatusInfo(b).sortValue;
          break;
        case "date":
          valA = a.last_checked || "";
          valB = b.last_checked || "";
          break;
        default:
          return 0;
      }

      if (valA < valB) return -1 * modifier;
      if (valA > valB) return 1 * modifier;
      return 0;
    });
  }

  function renderTable() {
    const filtered = filterWebshops();
    const sorted = sortWebshops(filtered);
    const tbody = document.getElementById("results-body");

    document.getElementById("filter-count").textContent =
      filtered.length === allWebshops.length
        ? `${filtered.length} webshops`
        : `${filtered.length} van ${allWebshops.length} webshops`;

    if (sorted.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="py-8 text-center text-gray-500">Geen resultaten gevonden</td></tr>';
      return;
    }

    tbody.innerHTML = sorted
      .map((shop) => {
        const status = getStatusInfo(shop);
        const categoryLabel = CATEGORY_LABELS[shop.category] || shop.category;
        const checkedDate = shop.last_checked
          ? new Date(shop.last_checked).toLocaleDateString("nl-NL")
          : "-";

        const statementLink =
          shop.has_statement && shop.statement_url
            ? `<a href="${escapeHtml(shop.statement_url)}" target="_blank" rel="noopener noreferrer" class="text-petrol underline hover:text-magenta">${escapeHtml(shop.statement_link_text || "Bekijk")}</a>`
            : '<span class="text-gray-400">-</span>';

        return `<tr class="border-b border-gray-100 hover:bg-lightgrey">
          <td class="py-3 px-2">
            <a href="${escapeHtml(shop.url)}" target="_blank" rel="noopener noreferrer" class="text-petrol underline hover:text-magenta font-medium">${escapeHtml(shop.name)}</a>
          </td>
          <td class="py-3 px-2">${escapeHtml(categoryLabel)}</td>
          <td class="py-3 px-2">
            <span class="${status.class} font-medium">
              <span aria-hidden="true">${status.icon}</span> ${escapeHtml(status.text)}
            </span>
          </td>
          <td class="py-3 px-2">${statementLink}</td>
          <td class="py-3 px-2 hidden md:table-cell text-gray-500">${checkedDate}</td>
        </tr>`;
      })
      .join("");
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
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

        // Update visual indicators
        document.querySelectorAll(".sort-btn").forEach((b) => {
          b.classList.remove("asc", "desc");
        });
        btn.classList.add(currentSort.direction);

        renderTable();
      });
    });
  }

  function setupFilters() {
    document
      .getElementById("filter-search")
      .addEventListener("input", renderTable);
    document
      .getElementById("filter-category")
      .addEventListener("change", renderTable);
    document
      .getElementById("filter-status")
      .addEventListener("change", renderTable);
  }

  async function init() {
    const data = await loadData();
    if (!data) {
      document.getElementById("results-body").innerHTML =
        '<tr><td colspan="5" class="py-8 text-center text-red-600">Fout bij het laden van data. Controleer of data/results.json bestaat.</td></tr>';
      return;
    }

    allWebshops = data.webshops || [];
    updateStats(data);
    populateCategories(allWebshops);
    setupSorting();
    setupFilters();
    renderTable();

    // Set initial sort indicator
    const nameBtn = document.querySelector('[data-sort="name"]');
    if (nameBtn) nameBtn.classList.add("asc");
  }

  init();
})();
