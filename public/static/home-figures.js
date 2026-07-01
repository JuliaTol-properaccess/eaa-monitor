/* Live sector figures for the English hub homepage.
   The Dutch homepage bakes these numbers via the scraper (STAT markers); the
   English page has no baked markers, so it fills them client-side from the same
   results JSON. Elements opt in with data-figure ("total"|"pctWith"|
   "pctWithout") + data-src (a results JSON URL). The last-updated line opts in
   with data-lastupdated-src. Mirrors computeStats() in app.js. */
(function () {
  "use strict";
  var cache = {};

  function load(src) {
    if (!cache[src]) {
      cache[src] = fetch(src)
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return cache[src];
  }

  function stats(data) {
    var arr = (data && data.webshops) || [];
    var total = arr.length, withS = 0, err = 0;
    arr.forEach(function (s) {
      if (s.scrape_status !== "success") err++;
      else if (s.has_statement) withS++;
    });
    var without = total - withS - err;
    return {
      total: total,
      pctWith: total ? Math.round((withS / total) * 100) : 0,
      pctWithout: total ? Math.round((without / total) * 100) : 0,
    };
  }

  var els = Array.prototype.slice.call(
    document.querySelectorAll("[data-figure][data-src]")
  );
  var srcs = {};
  els.forEach(function (el) { srcs[el.dataset.src] = true; });
  var lu = document.querySelector("[data-lastupdated-src]");
  if (lu) srcs[lu.dataset.lastupdatedSrc] = true;

  var jobs = Object.keys(srcs).map(function (src) {
    return load(src).then(function (d) { return { src: src, data: d }; });
  });

  Promise.all(jobs).then(function (results) {
    var bySrc = {};
    results.forEach(function (r) { bySrc[r.src] = { data: r.data, st: r.data ? stats(r.data) : null }; });

    els.forEach(function (el) {
      var r = bySrc[el.dataset.src];
      if (!r || !r.st) return;
      var v = r.st[el.dataset.figure];
      if (v === undefined) return;
      el.textContent = el.dataset.figure === "total" ? v.toLocaleString("en-GB") : v + "%";
    });

    if (lu) {
      var r = bySrc[lu.dataset.lastupdatedSrc];
      if (r && r.data && r.data.last_updated) {
        var d = new Date(r.data.last_updated);
        lu.textContent = "Last updated: " + d.toLocaleDateString("en-GB", {
          year: "numeric", month: "long", day: "numeric",
        });
      }
    }

    // Fill the count bars now that the percentages are in place.
    document.querySelectorAll("[data-telbalk]").forEach(function (balk) {
      var kaart = balk.closest("a");
      var bron = kaart && kaart.querySelector(".telbalk-pct");
      var pct = bron ? parseInt(bron.textContent, 10) : NaN;
      if (pct >= 0 && pct <= 100 && balk.firstElementChild) {
        balk.firstElementChild.style.width = pct + "%";
      }
    });
  });
})();
