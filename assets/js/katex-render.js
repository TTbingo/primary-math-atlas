(function () {
  if (typeof katex === 'undefined') return; // JS 未加载时保留可读 TeX 原文
  var nodes = document.querySelectorAll('.math, .math-display');
  Array.prototype.forEach.call(nodes, function (el) {
    var tex = el.getAttribute('data-tex');
    if (!tex) return;
    try {
      katex.render(tex, el, {
        displayMode: el.classList.contains('math-display'),
        throwOnError: false,
        strict: 'ignore',
        output: 'htmlAndMathml'
      });
    } catch (e) {
      el.classList.add('katex-error');
    }
  });
})();
