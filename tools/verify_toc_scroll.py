#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「点左侧目录分项后列表回顶」已修复。

判据（比像素相等更严谨）：落地页侧栏最上面那条可见分项应与点击前一致；
列表不能被甩回顶部（原 scrollTop>0 时落地后仍 >0）。
另含：展开分组不收起、从别处进入时当前分项可见、右侧本页目录、移动端抽屉。
"""
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "8933"
B = "http://127.0.0.1:%s" % PORT
fails = []


def check(name, ok, detail=""):
    print(("  ✓ " if ok else "  ✗ ") + name + (("  " + detail) if detail else ""))
    if not ok:
        fails.append(name)


STATE = """() => {
  const s = document.getElementById('sidebar');
  const r = s.getBoundingClientRect();
  const key = h => {
    let m = /\/(?:points|t)\/([a-z0-9-]+)\/index\.html/.exec(h || '');
    if (m) return (h.indexOf('/points/') >= 0 ? 'p:' : 't:') + m[1];
    m = /\/m(\d+)\/index\.html/.exec(h || '');
    return m ? 'm:m' + m[1] : null;
  };
  let anchor = null, off = 0;
  for (const a of s.querySelectorAll('a[href]')) {
    const b = a.getBoundingClientRect();
    if (b.bottom > r.top + 1) { anchor = key(a.getAttribute('href')); off = Math.round(b.top - r.top); break; }
  }
  return {top: Math.round(s.scrollTop), sh: s.scrollHeight,
          open: [...s.querySelectorAll('details')].map(d => d.open),
          anchor: anchor, off: off};
}
"""


def state(p):
    return p.evaluate(STATE)


with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--no-proxy-server"])

    # ---------- 1. 桌面：展开分组 + 滚动 + 点侧栏分项 ----------
    p = b.new_page(viewport={"width": 1440, "height": 760})
    p.goto(B + "/points/m1-01-02-num-1-to-20/index.html", wait_until="load")
    p.click("details.side-group:nth-of-type(2) > summary")
    p.click("details.side-group:nth-of-type(3) > summary")
    p.wait_for_timeout(150)
    p.evaluate("document.getElementById('sidebar').scrollTop = 400")
    p.wait_for_timeout(200)
    before = state(p)
    print("步骤1 点击前：top=%d 首条可见=%s(偏移%d) 分组=%s"
          % (before["top"], before["anchor"], before["off"], before["open"]))

    p.click("#sidebar .side-term a[href$='t/m3-01/index.html']")
    p.wait_for_load_state("load")
    p.wait_for_timeout(400)
    after = state(p)
    print("步骤1 点击后：top=%d 首条可见=%s(偏移%d) 分组=%s  url=%s"
          % (after["top"], after["anchor"], after["off"], after["open"],
             p.url.split("8933")[-1]))
    check("列表未回顶", after["top"] > 0 or before["top"] == 0,
          "top %d → %d" % (before["top"], after["top"]))
    # 落地页可能没有同一分项（侧栏只列当前主题），此时允许退到所属主题/模块
    same = after["anchor"] == before["anchor"]
    landmark = before["anchor"] and (after["anchor"] == "t:" + before["anchor"][2:7]
                                     or after["anchor"] == "m:m" + before["anchor"][2:4])
    check("首条可见分项停在原地（或就近地标）", same or landmark,
          "%s(%d) → %s(%d)" % (before["anchor"], before["off"], after["anchor"], after["off"]))
    check("展开的分组未收起", after["open"] == before["open"])

    # 连续点第二个，模拟「接着往下看」
    p.click("#sidebar .side-term a[href$='t/m3-02/index.html']")
    p.wait_for_load_state("load")
    p.wait_for_timeout(350)
    a2 = state(p)
    check("连续点击仍不回顶", a2["top"] > 0 and a2["anchor"] == after["anchor"],
          "top=%d 首条=%s" % (a2["top"], a2["anchor"]))

    # ---------- 2. 新会话直接打开 ----------
    ctx2 = b.new_context(viewport={"width": 1440, "height": 760})
    q = ctx2.new_page()
    q.goto(B + "/points/m4-04-01-pigeonhole-and-worst-case/index.html", wait_until="load")
    q.wait_for_timeout(300)
    vis = q.evaluate("""() => {
      const s = document.getElementById('sidebar');
      const a = s.querySelector('a[aria-current="page"]');
      const r = s.getBoundingClientRect(), b = a.getBoundingClientRect();
      return {ok: b.top >= r.top - 1 && b.bottom <= r.bottom + 1, top: Math.round(s.scrollTop)};
    }""")
    check("直接进入时当前分项在视口内", vis["ok"], "scrollTop=%d" % vis["top"])

    # ---------- 3. 右侧本页目录仍精确跳转、自身不滚 ----------
    p.goto(B + "/points/m1-01-02-num-1-to-20/index.html", wait_until="load")
    ok_all = True
    for h in ["#examples", "#pitfalls", "#related"]:
        p.click(".toc a[href='%s']" % h)
        p.wait_for_timeout(300)
        r = p.evaluate("""() => ({
          rb: document.getElementById('rightbar').scrollTop,
          tgt: Math.round(document.querySelector(location.hash).getBoundingClientRect().top)
        })""")
        ok_all = ok_all and r["rb"] == 0 and 0 <= r["tgt"] <= 140
    check("页内目录跳转精准且自身不滚动", ok_all)

    # ---------- 4. 移动端抽屉 ----------
    m = b.new_page(viewport={"width": 390, "height": 844})
    m.goto(B + "/points/m1-01-02-num-1-to-20/index.html", wait_until="load")
    m.click("#drawer-btn")
    m.wait_for_timeout(250)
    m.click(".side-item a >> nth=3")
    m.wait_for_load_state("load")
    m.wait_for_timeout(350)
    check("移动端点击后抽屉关闭",
          m.evaluate("!document.body.classList.contains('drawer-open')"))

    b.close()

print()
print("结论：" + ("全部通过" if not fails else "失败 %d 项：%s" % (len(fails), fails)))
sys.exit(1 if fails else 0)
