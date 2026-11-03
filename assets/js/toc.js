(function () {
  var toc = document.querySelector('.toc');
  if (!toc) return;
  var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
  if (!links.length) return;

  // 移动端：标题可点击展开
  if (window.innerWidth < 800) {
    var h = toc.querySelector('.toc-h');
    if (h) h.addEventListener('click', function () { toc.classList.toggle('open'); });
  }

  var map = {};
  var targets = [];
  links.forEach(function (a) {
    var el = document.getElementById(a.getAttribute('href').slice(1));
    if (el) { map[el.id] = a; targets.push(el); }
  });
  if (!targets.length) return;

  function mark(id) {
    links.forEach(function (a) { a.removeAttribute('aria-current'); });
    if (map[id]) map[id].setAttribute('aria-current', 'location');
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      var vis = entries.filter(function (e) { return e.isIntersecting; });
      if (vis.length) {
        vis.sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top; });
        mark(vis[0].target.id);
      }
    }, { rootMargin: '-72px 0px -70% 0px', threshold: 0 });
    targets.forEach(function (t) { io.observe(t); });
  } else {
    window.addEventListener('scroll', function () {
      var best = null;
      targets.forEach(function (t) {
        if (t.getBoundingClientRect().top <= 100) best = t;
      });
      if (best) mark(best.id);
    });
  }
})();
