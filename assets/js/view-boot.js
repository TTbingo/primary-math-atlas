(function () {
  // __DEFAULT_VIEW__ 由 build.py 按本篇学段注入：1/2 段 simple，3 段 full；非知识点页恒为 full
  var def = '__DEFAULT_VIEW__';
  try {
    var pref = localStorage.getItem('mathsite:view') || 'auto';
    document.documentElement.setAttribute('data-view', pref === 'auto' ? def : (pref === 'simple' ? 'simple' : 'full'));
    document.documentElement.setAttribute('data-view-pref', pref);
  } catch (e) {
    document.documentElement.setAttribute('data-view', def);
    document.documentElement.setAttribute('data-view-pref', 'auto');
  }
})();
