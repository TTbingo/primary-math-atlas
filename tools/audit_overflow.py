# -*- coding: utf-8 -*-
"""锚点感知溢出扫描：找真实溢出到视口外的元素。

「锚点感知」= 以元素自身的定位锚点为参照判断是否溢出，
而不是简单地拿 boundingRect 与视口比——transform 过的元素
（如旋转的图形）boundingRect 会变大，但实际并没有溢出。

用法：python tools/audit_overflow.py [端口]
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 锚点感知：判断元素的某个锚点是否在视口内
JS = """() => {
  const vw = document.documentElement.clientWidth;
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') return;
    if (st.position === 'fixed') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    // 跳过滚动容器内部（横向溢出是设计意图）
    let p = el.parentElement, inScroll = false;
    while (p) {
      const ps = getComputedStyle(p);
      if (ps.overflowX === 'auto' || ps.overflowX === 'scroll' ||
          ps.overflowX === 'hidden' || ps.overflowX === 'clip') { inScroll = true; break; }
      p = p.parentElement;
    }
    if (inScroll) return;
    // skip-link 是故意藏在屏幕外的无障碍跳转链接（left: -9999px），
    // 聚焦时才显现——不是溢出
    const cls = (el.className && el.className.toString()) || '';
    if (cls.includes('skip-link')) return;
    if (r.right < -1000) return;   // 深度藏在屏幕外的元素（视觉隐藏）
    // 锚点感知：transform 会放大 boundingRect，但元素实际锚点可能没越界。
    // 做法：取元素自身坐标系的原点（不受 transform 影响的布局坐标）来判。
    const hasTransform = st.transform && st.transform !== 'none';
    let ax = 0, node = el;
    while (node && node !== document.body) {
      ax += node.offsetLeft; node = node.offsetParent;
    }
    // 对有 transform 的元素，用「未变换前的宽度」参与计算
    const rawW = hasTransform ? el.offsetWidth : r.width;
    const rawLeft = hasTransform ? r.left - (r.width - el.offsetWidth) / 2 : r.left;
    if (rawLeft + rawW > vw + 2 || rawLeft < -2) {
      out.push({
        tag: el.tagName,
        cls: (el.className && el.className.toString()).slice(0, 50),
        left: Math.round(rawLeft), w: Math.round(rawW), vw: vw,
        transform: hasTransform,
        text: (el.textContent || '').trim().slice(0, 40)
      });
    }
  });
  return out;
}"""


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8914"
    base = f"http://127.0.0.1:{port}"
    pages = ["/", "/m1/", "/m2/", "/m3/", "/m4/"]
    for d in sorted((ROOT / "dist" / "t").glob("*")):
        pages.append(f"/t/{d.name}/")
    for d in sorted((ROOT / "dist" / "points").glob("*")):
        pages.append(f"/points/{d.name}/")

    bad = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for vw in (1280, 390):
            pg = b.new_page(viewport={"width": vw, "height": 900})
            for p in pages:
                try:
                    pg.goto(base + p, wait_until="domcontentloaded", timeout=30000)
                    pg.wait_for_timeout(120)
                    res = pg.evaluate(JS)
                except Exception as e:
                    bad.append((p, vw, [f"加载失败: {str(e)[:60]}"]))
                    continue
                if res:
                    bad.append((p, vw, res[:4]))
            pg.close()
        b.close()
    print(f"【溢出扫描】{len(pages)} 个页面 × 2 种视口（1280 / 390），发现 {len(bad)} 处溢出")
    for p, vw, items in bad[:25]:
        print(f"  ✗ {p} @{vw}px")
        for it in items:
            print(f"      {it}")


if __name__ == "__main__":
    main()
