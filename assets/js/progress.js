(function () {
  var KEY = 'mathsite:state';
  var OLD = 'mathsite:done';
  var VALID = { review: 1, mastered: 1 };

  function save(o) { try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }
  function normalize(raw) {
    var o = {};
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return o;
    Object.keys(raw).forEach(function (k) { if (VALID[raw[k]] && typeof k === 'string') o[k] = raw[k]; });
    return o;
  }
  // 旧版 mathsite:done 是 id 数组，全部迁移为「已掌握」；旧键保留不删，便于回滚
  function load() {
    var raw = null;
    try { raw = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) return normalize(raw);
    var old = null;
    try { old = JSON.parse(localStorage.getItem(OLD) || '[]'); } catch (e) {}
    var state = {};
    if (Array.isArray(old)) old.forEach(function (id) { if (typeof id === 'string') state[id] = 'mastered'; });
    if (Object.keys(state).length) save(state);
    return state;
  }
  var state = load();

  function count() {
    var m = 0, r = 0;
    Object.keys(state).forEach(function (k) {
      if (state[k] === 'mastered') m++;
      else if (state[k] === 'review') r++;
    });
    return { m: m, r: r };
  }

  function apply() {
    var picker = document.querySelector('.state-picker');
    if (picker) {
      var id = picker.getAttribute('data-state-id');
      var cur = state[id] || '';
      Array.prototype.forEach.call(picker.querySelectorAll('.state-btn'), function (b) {
        var on = (b.getAttribute('data-state') || '') === cur;
        b.classList.toggle('state-on', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
    Array.prototype.forEach.call(document.querySelectorAll('[data-id]'), function (el) {
      var s = state[el.getAttribute('data-id')];
      el.classList.toggle('is-mastered', s === 'mastered');
      el.classList.toggle('is-review', s === 'review');
    });
    var c = count();
    var dc = document.querySelector('.done-count'); if (dc) dc.textContent = String(c.m);
    var rc = document.querySelector('.review-count'); if (rc) rc.textContent = String(c.r);
    document.body.classList.toggle('has-review', c.r > 0);
    if (picker) {
      var curState = state[picker.getAttribute('data-state-id')] || '';
      document.body.classList.toggle('state-review', curState === 'review');
      document.body.classList.toggle('state-mastered', curState === 'mastered');
    }
  }

  function closestBtn(node) {
    while (node && node !== document) {
      if (node.classList && node.classList.contains('state-btn')) return node;
      node = node.parentNode;
    }
    return null;
  }

  Array.prototype.forEach.call(document.querySelectorAll('.state-picker'), function (picker) {
    picker.addEventListener('click', function (e) {
      var b = closestBtn(e.target);
      if (!b || !picker.contains(b)) return;
      var id = picker.getAttribute('data-state-id');
      var v = b.getAttribute('data-state') || '';
      if (v) state[id] = v; else delete state[id];
      save(state);
      apply();
    });
  });

  // 进度 JSON 导出 / 导入
  var exp = document.querySelector('[data-progress-export]');
  if (exp) exp.addEventListener('click', function () {
    var payload = { app: 'primary-math-atlas', version: 1,
                    exported: new Date().toISOString(), state: state };
    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'math-atlas-progress.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  var imp = document.querySelector('[data-progress-import]');
  var file = document.querySelector('.progress-file');
  if (imp && file) {
    imp.addEventListener('click', function () { file.click(); });
    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        var next = {};
        try {
          var d = JSON.parse(String(reader.result));
          next = normalize(d && d.state ? d.state : d);
        } catch (err) { next = {}; }
        if (!Object.keys(next).length) {
          window.alert('导入失败：文件中没有可识别的进度记录。');
        } else {
          state = next;
          save(state);
          apply();
          var c = count();
          window.alert('进度已导入：已掌握 ' + c.m + ' 篇，需复习 ' + c.r + ' 篇。');
        }
        file.value = '';
      };
      reader.readAsText(f);
    });
  }

  // 精简 / 完整视图切换：auto 按学段（1/2 精简、3 完整），手动选择写入本地
  var viewButtons = Array.prototype.slice.call(document.querySelectorAll('[data-view-set]'));
  function paintView() {
    var pref = document.documentElement.getAttribute('data-view-pref') || 'auto';
    viewButtons.forEach(function (b) {
      b.classList.toggle('view-on', b.getAttribute('data-view-set') === pref);
    });
  }
  viewButtons.forEach(function (b) {
    b.addEventListener('click', function () {
      var pref = b.getAttribute('data-view-set');
      try { localStorage.setItem('mathsite:view', pref); } catch (e) {}
      var seg = parseInt(document.body.className.match(/seg-(\d)/) ? document.body.className.match(/seg-(\d)/)[1] : '3', 10);
      var actual = pref === 'auto' ? (seg <= 2 ? 'simple' : 'full') : pref;
      document.documentElement.setAttribute('data-view', actual);
      document.documentElement.setAttribute('data-view-pref', pref);
      paintView();
    });
  });
  paintView();

  // 先思后看：本页一键展开 / 收起；打印时强制展开，结束后恢复原状
  var folds = Array.prototype.slice.call(document.querySelectorAll('details.ex-answer, details.pitfall'));
  var foldBtn = document.querySelector('[data-fold-all]');
  if (foldBtn && folds.length) {
    foldBtn.addEventListener('click', function () {
      var open = folds.some(function (d) { return !d.open; });
      folds.forEach(function (d) { d.open = open; });
      foldBtn.textContent = open ? '收起全部解答' : '展开全部解答';
      foldBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  var snapshot = null;
  window.addEventListener('beforeprint', function () {
    snapshot = folds.map(function (d) { return d.open; });
    folds.forEach(function (d) { d.open = true; });
  });
  window.addEventListener('afterprint', function () {
    if (!snapshot) return;
    folds.forEach(function (d, i) { d.open = snapshot[i]; });
    snapshot = null;
  });

  apply();
})();
