(function () {
  var KEY = 'mathsite:done';
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; }
  }
  function save(a) { try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} }

  var done = load();

  // 知识点页的勾选框
  var cb = document.querySelector('.done-cb');
  if (cb) {
    var id = cb.getAttribute('data-id');
    cb.checked = done.indexOf(id) >= 0;
    if (cb.checked) document.body.classList.add('done-checked');
    cb.addEventListener('change', function () {
      var i = done.indexOf(id);
      if (cb.checked && i < 0) done.push(id);
      if (!cb.checked && i >= 0) done.splice(i, 1);
      save(done);
      document.body.classList.toggle('done-checked', cb.checked);
    });
  }

  // 卡片上的进度标记
  Array.prototype.forEach.call(document.querySelectorAll('.point-card'), function (c) {
    if (done.indexOf(c.getAttribute('data-id')) >= 0) c.classList.add('is-done');
  });

  // 计数
  var el = document.querySelector('.done-count');
  if (el) el.textContent = String(done.length);

  // 首页筛选
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip[data-filter]'));
  var cards = Array.prototype.slice.call(document.querySelectorAll('.point-card'));
  var emptyNote = document.getElementById('empty-note');
  if (chips.length && cards.length) {
    chips.forEach(function (ch) {
      ch.addEventListener('click', function () {
        var f = ch.getAttribute('data-filter');
        chips.forEach(function (x) { x.classList.toggle('chip-on', x === ch); });
        var shown = 0;
        cards.forEach(function (c) {
          var ok = (f === 'all') || c.getAttribute('data-' + f.split(':')[0]) === f.split(':')[1];
          c.hidden = !ok;
          if (ok) shown++;
        });
        if (emptyNote) emptyNote.hidden = shown > 0;
      });
    });
  }
})();
