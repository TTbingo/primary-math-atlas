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
    var t = item.t || '', s = item.s || '', k = (item.k || []).join(' ');
    var n = 0;
    if (t.indexOf(q) >= 0) n += 5;
    if (k.indexOf(q) >= 0) n += 3;
    if ((item.d || '').indexOf(q) >= 0 || (item.c || '').indexOf(q) >= 0) n += 2;
    if (s.indexOf(q) >= 0) n += 2;
    var bl = item.bl || [];
    for (var i = 0; i < bl.length; i++) {
      if (bl[i].t.indexOf(q) >= 0) { n += 1; break; }
    }
    return n;
  }

  // 问句预处理：剥掉口语疑问词，用核心词再搜一遍。不做拼音、不做同义词表、
  // 不做模糊容错——实测短核心词（鸡兔/相遇/植树）命中率已够，失效的主要是问句式。
  function coreQuery(q) {
    var s = q.replace(/^(请问|请|我想知道|想知道|帮忙)\s*/, '');
    s = s.replace(/^(什么是|什么叫|怎么|怎样|如何|为什么|求一下|求)\s*/, '');
    s = s.replace(/(是什么意思|的意思|是什么|怎么算|怎么求|怎么做|怎么算的|如何计算|如何求|为什么)\s*$/, '');
    return s.trim();
  }
  function queries(q) {
    var c = coreQuery(q);
    return c && c !== q ? [q, c] : [q];
  }
  function scoreAny(item, qs, orig) {
    var best = 0;
    for (var i = 0; i < qs.length; i++) {
      var n = score(item, qs[i]);
      // 核心词命中时略降权，避免「通分怎么算」压过直接搜「通分」的结果
      if (i > 0 && n) n = Math.max(1, n - 1);
      if (n > best) best = n;
    }
    return best;
  }

  // 在全文分块里定位第一次命中，返回「板块名 + 前后文」，让结果可解释
  function snippet(item, q) {
    var blocks = item.bl || [];
    for (var i = 0; i < blocks.length; i++) {
      var pos = blocks[i].t.indexOf(q);
      if (pos < 0) continue;
      var text = blocks[i].t;
      var from = Math.max(0, pos - 22), to = Math.min(text.length, pos + q.length + 34);
      return blocks[i].s + ' · …' + (from > 0 ? '…' : '') + text.slice(from, to) + '…';
    }
    return null;
  }

  function run() {
    var q = input.value.trim().toLowerCase();
    list.innerHTML = '';
    sel = -1;
    if (!q) { cur = []; modal.querySelector('.search-tip').textContent = '输入关键词，回车打开第一条'; return; }
    var qs = queries(q);
    var hit = IDX.map(function (i) { return { i: i, n: scoreAny(i, qs, q) }; })
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
      // 正文命中时显示「板块名 + 上下文」，否则退回知识点摘要
      var sn = null;
      for (var k = 0; k < qs.length && !sn; k++) sn = snippet(x.i, qs[k]);
      a.querySelector('.sr-s').textContent = sn || (x.i.s || '').replace(/\$/g, '');
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
