/* Subtiele scroll-reveal voor elementen met .reveal.
   Respecteert prefers-reduced-motion: dan direct zichtbaar, geen observer. */
(function () {
  var els = document.querySelectorAll('.reveal');
  if (!els.length) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) {
    els.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });

  els.forEach(function (el) { io.observe(el); });
})();
