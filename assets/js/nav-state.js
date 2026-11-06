/* 左侧目录（.sidebar）位置保持
 *
 * 症状：点左侧目录里的分项，整页跳转后目录列表回到顶部，用户丢失浏览位置。
 * 根因：侧栏是 overflow-y:auto 的独立滚动容器，<details> 分组又是折叠状态；
 *      整站是多页静态站，浏览器只还原「窗口」滚动，不还原内部容器，
 *      于是容器 scrollTop 归零、分组一并收起。
 *
 * 做法：离开前记下「最上面那条可见分项」的 key 与偏移，落地页把它摆回原处。
 *  - 不记像素：各页侧栏条目数不同（只展开当前主题的知识点），像素会被夹边。
 *  - key 做归一化（p:m1-01-10 / t:m3-01 / m:m2），因为各页相对路径深度不同
 *    （首页 ../、知识点页 ../../）。
 *  - 原分项在新页面可能不存在（换了主题），此时按 分项→所属主题→所属模块
 *    逐级退到还存在的最近地标，保证列表停在原来那一段。
 */
(function () {
  var box = document.getElementById('sidebar');
  if (!box) return;

  var K_POS = 'mathsite:side-pos';    // {key, topic, module, off, top}
  var K_OPEN = 'mathsite:side-open';  // 展开的分组
  var K_KEEP = 'mathsite:side-keep';  // 本次跳转是否来自侧栏点击

  function read(k, d) {
    try { var v = sessionStorage.getItem(k); return v === null ? d : JSON.parse(v); }
    catch (e) { return d; }
  }
  function write(k, v) {
    try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
  }

  // href → 稳定 key：p:m1-01-10 / t:m3-01 / m:m2 / null
  function keyOfHref(h) {
    var m = /\/(?:points|t)\/([a-z0-9-]+)\/index\.html/.exec(h || '');
    if (m) return (h.indexOf('/points/') >= 0 ? 'p:' : 't:') + m[1];
    m = /\/m(\d+)\/index\.html/.exec(h || '');
    return m ? 'm:m' + m[1] : null;
  }
  function topicOfKey(k) { return k && k.slice(0, 2) === 'p:' ? 't:' + k.slice(2, 7) : k; }
  function moduleOfKey(k) {
    var m = k && /^[pt]:m(\d)-\d\d$/.exec(k);
    return m ? 'm:m' + m[1] : null;
  }

  var groups = Array.prototype.slice.call(box.querySelectorAll('details'));

  // 分组键取模块 id（summary 链接形如 ../../m1/index.html）
  function groupKey(d) {
    var a = d.querySelector('summary a');
    var k = a && keyOfHref(a.getAttribute('href'));
    return k || 'd' + groups.indexOf(d);
  }

  function links() { return box.querySelectorAll('a[href]'); }

  function firstVisible() {
    var r = box.getBoundingClientRect();
    var all = links();
    for (var i = 0; i < all.length; i++) {
      var b = all[i].getBoundingClientRect();
      if (b.bottom > r.top + 1) {
        return {key: keyOfHref(all[i].getAttribute('href')),
                off: Math.round(b.top - r.top)};
      }
    }
    return null;
  }

  function snapshot() {
    var t = firstVisible();
    write(K_POS, {
      key: t ? t.key : null,
      topic: t ? topicOfKey(t.key) : null,
      module: t ? moduleOfKey(t.key) : null,
      off: t ? t.off : 0,
      top: Math.round(box.scrollTop)
    });
    write(K_OPEN, groups.filter(function (d) { return d.open; }).map(groupKey));
  }

  function scrollToKey(key, off) {
    if (!key) return false;
    var all = links();
    for (var i = 0; i < all.length; i++) {
      if (keyOfHref(all[i].getAttribute('href')) === key) {
        var rb = box.getBoundingClientRect(), hb = all[i].getBoundingClientRect();
        box.scrollTop += (hb.top - rb.top) - off;   // 越界自动夹到边界
        return true;
      }
    }
    return false;
  }

  // ---- 还原 ----
  var savedOpen = read(K_OPEN, null);
  if (savedOpen) {
    groups.forEach(function (d) { d.open = savedOpen.indexOf(groupKey(d)) >= 0; });
  }
  // 当前页所在分组一定展开，否则落地后看不见自己在哪
  groups.forEach(function (d) {
    if (d.querySelector('a[aria-current="page"]')) d.open = true;
  });

  var pos = read(K_POS, null);
  if (read(K_KEEP, false) && pos) {
    write(K_KEEP, false);
    // 分项 → 主题 → 模块，逐级退到还存在的最近地标
    var done = scrollToKey(pos.key, pos.off) ||
               scrollToKey(pos.topic, pos.off) ||
               scrollToKey(pos.module, pos.off);
    if (!done) box.scrollTop = pos.top;
  } else {
    // 从搜索/上一页/直接打开进来：当前分项不在视口就最小幅度滚过去
    var cur = box.querySelector('a[aria-current="page"]');
    if (cur) {
      var b = cur.getBoundingClientRect(), r = box.getBoundingClientRect();
      if (b.top < r.top || b.bottom > r.bottom) {
        box.scrollTop += (b.top - r.top) - (r.height - b.height) / 2;
      }
    }
  }

  // ---- 记录 ----
  var ticking = false;
  box.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { snapshot(); ticking = false; });
  }, { passive: true });

  // toggle 不冒泡，只能逐组监听
  groups.forEach(function (d) { d.addEventListener('toggle', snapshot); });

  // 点分项：导航前把位置与展开状态写实，并标记「保持位置」
  box.addEventListener('click', function (e) {
    if (!e.target.closest('a')) return;
    snapshot();
    write(K_KEEP, true);
  });
})();
