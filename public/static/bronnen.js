// Client-side filteren en zoeken voor de bronnenpagina (public/bronnen.html).
// De volledige lijst staat server-rendered in de HTML; dit script verbergt
// alleen items die niet matchen, zodat de pagina zonder JS ook bruikbaar is.
(function () {
  'use strict';

  var list = document.getElementById('bron-list');
  if (!list) return;

  var items = Array.prototype.slice.call(list.querySelectorAll('.bron-item'));
  var filterBar = document.getElementById('bron-filters');
  var search = document.getElementById('bron-search');
  var countEl = document.getElementById('bron-result-count');
  var emptyEl = document.getElementById('bron-empty');

  var selectedCat = 'all';
  var query = '';

  function apply() {
    var visible = 0;
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var matchesCat = selectedCat === 'all' || item.getAttribute('data-cat') === selectedCat;
      var matchesText = query === '' || (item.getAttribute('data-text') || '').indexOf(query) !== -1;
      var show = matchesCat && matchesText;
      item.hidden = !show;
      if (show) visible++;
    }

    if (emptyEl) emptyEl.classList.toggle('hidden', visible !== 0);
    if (countEl) {
      countEl.textContent = visible === 1 ? '1 bron' : visible + ' bronnen';
    }
  }

  if (filterBar) {
    filterBar.addEventListener('click', function (e) {
      var btn = e.target.closest('.bron-filter');
      if (!btn) return;
      selectedCat = btn.getAttribute('data-cat') || 'all';
      var buttons = filterBar.querySelectorAll('.bron-filter');
      for (var i = 0; i < buttons.length; i++) {
        buttons[i].setAttribute('aria-pressed', buttons[i] === btn ? 'true' : 'false');
      }
      apply();
    });
  }

  if (search) {
    search.addEventListener('input', function () {
      query = search.value.trim().toLowerCase();
      apply();
    });
  }

  // De zoekknop filtert ook expliciet; live filteren blijft werken zonder klik.
  var searchForm = document.getElementById('bron-search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (search) query = search.value.trim().toLowerCase();
      apply();
    });
  }

  apply();
})();
