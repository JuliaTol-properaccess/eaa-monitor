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

/* Dropdownmenu's (zoals Monitor): de knop toggelt het bijbehorende menu.
   Toegankelijk: aria-expanded, sluiten met Escape en met een klik buiten het menu. */
(function () {
  var dropdowns = Array.prototype.slice.call(
    document.querySelectorAll("[data-dropdown]")
  );
  if (!dropdowns.length) return;

  function close(dd) {
    var toggle = dd.querySelector("[data-dropdown-toggle]");
    var menu = dd.querySelector("[data-dropdown-menu]");
    if (!toggle || !menu) return;
    toggle.setAttribute("aria-expanded", "false");
    menu.classList.add("hidden");
  }

  function closeAll(except) {
    dropdowns.forEach(function (dd) {
      if (dd !== except) close(dd);
    });
  }

  dropdowns.forEach(function (dd) {
    var toggle = dd.querySelector("[data-dropdown-toggle]");
    var menu = dd.querySelector("[data-dropdown-menu]");
    if (!toggle || !menu) return;

    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      closeAll(dd);
      toggle.setAttribute("aria-expanded", open ? "false" : "true");
      menu.classList.toggle("hidden", open);
    });
  });

  // Sluit alle dropdowns bij een klik buiten een dropdown.
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-dropdown]")) closeAll(null);
  });

  // Sluit met Escape en geef de focus terug aan de bijbehorende knop.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    dropdowns.forEach(function (dd) {
      var toggle = dd.querySelector("[data-dropdown-toggle]");
      if (toggle && toggle.getAttribute("aria-expanded") === "true") {
        close(dd);
        toggle.focus();
      }
    });
  });
})();
