(function () {
  try {
    var s = localStorage.getItem('mathsite:theme') || 'auto';
    var t = (s === 'auto')
      ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : s;
    document.documentElement.setAttribute('data-theme', t);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
