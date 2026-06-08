/* Mobiele navigatie: de hamburgerknop toggelt het menu onder de lg-breakpoint.
   Toegankelijk: aria-expanded, aria-label, sluiten met Escape en na een kliklink. */
(function () {
  var btn = document.getElementById("nav-toggle");
  var panel = document.getElementById("mobile-nav");
  if (!btn || !panel) return;

  function setOpen(open) {
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "Menu sluiten" : "Menu openen");
    panel.classList.toggle("hidden", !open);
  }

  btn.addEventListener("click", function () {
    setOpen(btn.getAttribute("aria-expanded") !== "true");
  });

  // Sluit het menu wanneer een navigatielink wordt gekozen.
  panel.addEventListener("click", function (e) {
    if (e.target.closest("a")) setOpen(false);
  });

  // Sluit met Escape en geef de focus terug aan de knop.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") {
      setOpen(false);
      btn.focus();
    }
  });
})();
