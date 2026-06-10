// Nieuwsbrief-opt-in in de footer. Post naar de bezwaar-Worker (/newsletter),
// die een bevestigingsmail stuurt (dubbele opt-in) en na bevestiging opslaat in
// Cloudflare KV. Werkt op elke pagina; de endpoint staat in data-endpoint.
(function () {
  "use strict";

  var form = document.getElementById("newsletter-form");
  if (!form) return;

  var endpoint = form.getAttribute("data-endpoint");
  var statusEl = document.getElementById("newsletter-status");
  var btn = document.getElementById("newsletter-submit");

  function show(type, msg) {
    statusEl.className =
      "mt-3 text-sm " + (type === "success" ? "text-white font-semibold" : "text-red-200");
    statusEl.textContent = msg;
    if (statusEl.focus) statusEl.focus();
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    if (!endpoint) return;

    btn.disabled = true;
    var label = btn.textContent;
    btn.textContent = "Bezig...";

    try {
      var res = await fetch(endpoint, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        form.reset();
        show(
          "success",
          "Bijna klaar. Check je inbox en bevestig je inschrijving via de link die we je net stuurden."
        );
      } else {
        var data = await res.json().catch(function () {
          return {};
        });
        show("error", (data && data.error) || "Er ging iets mis. Probeer het later opnieuw.");
      }
    } catch (err) {
      show("error", "Er ging iets mis. Controleer je verbinding en probeer het opnieuw.");
    }

    btn.disabled = false;
    btn.textContent = label;
  });
})();
