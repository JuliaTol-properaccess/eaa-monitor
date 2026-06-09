/**
 * EAA Monitor — Bezwaren
 * Laadt data/objections.json en toont de webshops die bezwaar hebben gemaakt.
 */

(function () {
  "use strict";

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
      console.error("Kan bezwaren niet laden:", err);
      return null;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (isNaN(date.getTime())) return escapeHtml(value);
    return date.toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  function displayUrl(url) {
    return url.replace(/^https?:\/\//, "").replace(/\/+$/, "");
  }

  async function init() {
    const tbody = document.getElementById("objections-body");
    const countEl = document.getElementById("objection-count");

    const objections = await loadObjections();

    if (objections === null) {
      tbody.innerHTML =
        '<tr><td colspan="2" class="py-12 text-center text-red-600">Fout bij het laden van de bezwaren.</td></tr>';
      return;
    }

    if (objections.length === 0) {
      countEl.textContent = "Er zijn nog geen bezwaren ingediend.";
      tbody.innerHTML =
        '<tr><td colspan="2" class="py-12 text-center text-gray-600">Nog geen webshops hebben bezwaar gemaakt.</td></tr>';
      return;
    }

    // Nieuwste bezwaar bovenaan.
    const sorted = [...objections].sort((a, b) =>
      (b.date || "").localeCompare(a.date || "")
    );

    countEl.textContent =
      sorted.length === 1
        ? "1 webshop heeft bezwaar gemaakt."
        : `${sorted.length} webshops hebben bezwaar gemaakt.`;

    tbody.innerHTML = sorted
      .map((o, i) => {
        const rowBg = i % 2 === 0 ? "" : "bg-gray-50";
        const name = escapeHtml(o.name || "Onbekend");
        const nameCell = o.url
          ? `<a href="${escapeHtml(o.url)}" target="_blank" rel="noopener noreferrer" class="text-brand hover:text-brand-dark font-semibold">${name}</a>
             <span class="block text-xs text-gray-500">${escapeHtml(displayUrl(o.url))}</span>`
          : name;
        return `<tr class="${rowBg} border-b border-line">
          <td class="py-3 px-4">${nameCell}</td>
          <td class="py-3 px-4 text-sm text-gray-600">${formatDate(o.date)}</td>
        </tr>`;
      })
      .join("");
  }

  init();
})();
