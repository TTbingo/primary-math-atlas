(function () {
  var btn = document.getElementById('drawer-btn');
  var mask = document.getElementById('sidebar-mask');
  if (!btn) return;
  var sidebar = document.getElementById('sidebar');

  function open() {
    document.body.classList.add('drawer-open');
    btn.setAttribute('aria-expanded', 'true');
    if (mask) mask.hidden = false;
  }
  function close() {
    document.body.classList.remove('drawer-open');
    btn.setAttribute('aria-expanded', 'false');
    if (mask) mask.hidden = true;
  }
  btn.addEventListener('click', function () {
    document.body.classList.contains('drawer-open') ? close() : open();
  });
  if (mask) mask.addEventListener('click', close);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  window.addEventListener('resize', function () { if (window.innerWidth >= 800) close(); });
  if (sidebar) {
    sidebar.addEventListener('click', function (e) {
      if (e.target.closest('a') && window.innerWidth < 800) close();
    });
  }
})();
