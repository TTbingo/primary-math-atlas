(function () {
  var KEY = 'mathsite:theme';
  var btn = document.getElementById('theme-btn');
  var ORDER = ['auto', 'light', 'dark'];
  var LABEL = { auto: '自动', light: '浅色', dark: '深色' };

  function get() {
    try { return localStorage.getItem(KEY) || 'auto'; } catch (e) { return 'auto'; }
  }
  function apply(v) {
    var t = (v === 'auto')
      ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : v;
    document.documentElement.setAttribute('data-theme', t);
    if (btn) { btn.title = '主题：' + LABEL[v]; btn.setAttribute('aria-label', '主题：' + LABEL[v]); }
  }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} apply(v); }

  apply(get());
  if (btn) {
    btn.addEventListener('click', function () {
      var i = ORDER.indexOf(get());
      set(ORDER[(i + 1) % ORDER.length]);
    });
  }
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var on = mq.addEventListener ? function (f) { mq.addEventListener('change', f); } : function (f) { mq.addListener(f); };
    on(function () { if (get() === 'auto') apply('auto'); });
  }
})();
