/* Eregalerij: stemtellers ophalen en stemmen versturen.
 * Progressive enhancement: zonder JavaScript (of als de Worker niet
 * bereikbaar is) blijven de stemblokken verborgen en is de pagina
 * gewoon leesbaar. Endpoint staat als data-hof-endpoint op <main>
 * (gezet door tools/build_halloffame.py). */
(function () {
  "use strict";

  var main = document.querySelector("[data-hof-endpoint]");
  if (!main) return;
  var endpoint = main.getAttribute("data-hof-endpoint");
  if (!endpoint) return;

  function countLabel(n) {
    if (!n) return "Nog geen stemmen. Stem als eerste.";
    if (n === 1) return "1 stem";
    return n + " stemmen";
  }

  // Tellers ophalen; pas daarna de stemblokken tonen.
  fetch(endpoint + "/hof/votes", { headers: { Accept: "application/json" } })
    .then(function (res) {
      if (!res.ok) throw new Error("status " + res.status);
      return res.json();
    })
    .then(function (counts) {
      document.querySelectorAll("[data-hof-count]").forEach(function (el) {
        var slug = el.getAttribute("data-hof-count");
        el.textContent = countLabel((counts && counts[slug]) || 0);
      });
      document.querySelectorAll("[data-hof-vote-block]").forEach(function (el) {
        el.hidden = false;
      });
    })
    .catch(function () {
      /* Worker niet bereikbaar: stemblokken blijven verborgen. */
    });

  // Stemformulieren: POST naar /hof/vote, daarna bevestigingsinstructie tonen.
  document.querySelectorAll("form[data-hof-slug]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      var statusEl = form.querySelector("[data-hof-status]");
      var button = form.querySelector("button[type=submit]");
      var data = new FormData(form);
      data.append("slug", form.getAttribute("data-hof-slug"));

      button.disabled = true;
      button.textContent = "Bezig...";

      fetch(endpoint + "/hof/vote", {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" },
      })
        .then(function (res) {
          return res
            .json()
            .catch(function () { return {}; })
            .then(function (body) { return { ok: res.ok, body: body }; });
        })
        .then(function (result) {
          if (result.ok) {
            form.innerHTML =
              '<p class="text-sm font-semibold text-navy" role="status">Bijna klaar. Bevestig je stem via de link in je mail; pas dan telt hij mee.</p>';
          } else {
            statusEl.textContent =
              (result.body && result.body.error) ||
              "Er ging iets mis. Probeer het later opnieuw.";
            statusEl.classList.add("text-status-notfound");
            button.disabled = false;
            button.textContent = "Stem";
          }
        })
        .catch(function () {
          statusEl.textContent = "Er ging iets mis. Controleer je internetverbinding en probeer het opnieuw.";
          statusEl.classList.add("text-status-notfound");
          button.disabled = false;
          button.textContent = "Stem";
        });
    });
  });
})();
