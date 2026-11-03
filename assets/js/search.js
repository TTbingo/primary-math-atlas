(function () {
  var IDX = window.__SEARCH_INDEX__ || [];
  var modal = document.getElementById('search-modal');
  var btn = document.getElementById('search-btn');
  var input = document.getElementById('search-input');
  var closeBtn = document.getElementById('search-close');
  var list = document.getElementById('search-results');
  if (!modal || !input) return;

  var depth = parseInt(document.body.getAttribute('data-depth') || '0', 10);
  // 注意去掉尾部斜杠，否则拼出来是 ../../ /points/ 这种双斜杠
  var root = depth === 0 ? '.' : '../'.repeat(depth).replace(/\/$/, '');
  // 三类条目路径：知识点 /points/{id}/，主题 /t/{id}/，模块 /{m1}/
  function url(id, ty) {
    if (ty === 't') return root + '/t/' + id + '/index.html';
    if (ty === 'm') return root + '/' + id + '/index.html';
    return root + '/points/' + id + '/index.html';
  }
  var TYPE_LABEL = { p: '知识点', t: '主题', m: '模块' };

  var sel = -1;
  var cur = [];

  function score(item, q) {
    var t = item.t || '', s = item.s || '', k = (item.k || []).join(' '), b = item.b || '';
    var n = 0;
    if (t.indexOf(q) >= 0) n += 5;
    if (k.indexOf(q) >= 0) n += 3;
    if ((item.d || '').indexOf(q) >= 0 || (item.c || '').indexOf(q) >= 0) n += 2;
    if (s.indexOf(q) >= 0) n += 2;
    if (b.indexOf(q) >= 0) n += 1;
    return n;
  }

  function run() {
    var q = input.value.trim().toLowerCase();
    list.innerHTML = '';
    sel = -1;
    if (!q) { cur = []; modal.querySelector('.search-tip').textContent = '输入关键词，回车打开第一条'; return; }
    var hit = IDX.map(function (i) { return { i: i, n: score(i, q.toLowerCase()) }; })
      .filter(function (x) { return x.n > 0; })
      .sort(function (a, b) { return b.n - a.n; })
      .slice(0, 20);
    cur = hit;
    modal.querySelector('.search-tip').textContent = '找到 ' + hit.length + ' 条';
    hit.forEach(function (x, idx) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = url(x.i.id, x.i.ty);
      a.innerHTML = '<span class="sr-t"></span><span class="sr-s"></span><span class="sr-m"></span>';
      a.querySelector('.sr-t').textContent = x.i.t;
      // 摘要里的公式只去掉 $ 定界符，搜索列表不排版公式
      a.querySelector('.sr-s').textContent = (x.i.s || '').replace(/\$/g, '');
      a.querySelector('.sr-m').textContent = [TYPE_LABEL[x.i.ty || 'p'],
        x.i.d, x.i.c].filter(Boolean).join(' · ');
      li.appendChild(a);
      list.appendChild(li);
    });
    if (hit.length) { sel = 0; paint(); }
  }

  function paint() {
    Array.prototype.forEach.call(list.children, function (li, i) {
      li.classList.toggle('sel', i === sel);
    });
  }

  function open() { modal.hidden = false; input.focus(); input.select(); }
  function close() { modal.hidden = true; }

  btn && btn.addEventListener('click', open);
  closeBtn && closeBtn.addEventListener('click', close);
  modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
  input.addEventListener('input', run);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, cur.length - 1); paint(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); paint(); e.preventDefault(); }
    else if (e.key === 'Enter') {
      if (cur[sel]) { location.href = url(cur[sel].i.id, cur[sel].i.ty); }
      e.preventDefault();
    } else if (e.key === 'Escape') { close(); }
  });
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { open(); e.preventDefault(); }
    if (e.key === 'Escape' && !modal.hidden) close();
  });
})();
