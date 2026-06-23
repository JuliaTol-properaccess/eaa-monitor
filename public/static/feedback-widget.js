/**
 * Zwevende "Klopt iets niet?"-knop. Injecteert een echte link naar /melden.html
 * (dus toetsenbordbereikbaar, met de gedeelde focus-outline, geen focus-trap).
 * Progressive enhancement: zonder JavaScript is de meldpagina nog steeds
 * bereikbaar via de monitor en de footer. Verschijnt niet op de meldpagina zelf.
 */
(function () {
  "use strict";

  var path = window.location.pathname;
  if (path === "/melden.html" || path === "/melden") return;

  function init() {
    if (document.querySelector(".feedback-fab")) return;
    var a = document.createElement("a");
    a.className = "feedback-fab";
    a.href = "/melden.html";
    a.setAttribute("aria-label", "Klopt iets niet? Meld het ons");
    a.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="10"></circle><path d="M12 8v5"></path>' +
      '<path d="M12 16h.01"></path></svg>' +
      '<span class="feedback-fab-text">Klopt iets niet?</span>';
    document.body.appendChild(a);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
