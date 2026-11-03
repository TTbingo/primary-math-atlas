"""配图体检：越界、文字压字、三角形内角、直角符号是否与图形相符。

用法: python tools/check_figs.py [目录]   默认 content/media
判定为「疑似问题」的条目需人工复核，不是每条都一定是错。
"""
import glob
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

JS = r"""
() => {
  const svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal;
  const W = vb.width || svg.width.baseVal.value;
  const H = vb.height || svg.height.baseVal.value;
  const out = {w: W, h: H, oob: [], overlap: [], tri: [], right: [], err: []};

  // 用「根逆 × 元素 CTM」把 bbox 变换到 viewBox 用户坐标系。
  // 直接用 getCTM 会把 Chrome 对独立 SVG 文档的 fit 缩放（如 1.7 倍）算进去，
  // 导致 520x360 这类尺寸的图被误判为整张越界；<g transform> 的平移仍会保留。
  const rm = svg.getCTM();
  const rootInv = rm ? rm.inverse() : null;
  const bb = el => { try {
    const b = el.getBBox(); let m = el.getCTM(); if (!m) return null;
    if (rootInv) m = rootInv.multiply(m);
    const pts = [[b.x, b.y], [b.x + b.width, b.y],
                 [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]);
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    return {x: Math.min(...xs), y: Math.min(...ys),
            w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)};
  } catch (e) { return null; } };

  // 1) 元素越界
  svg.querySelectorAll('text,polygon,path,line,rect,circle,ellipse,polyline').forEach(el => {
    const b = bb(el); if (!b || (b.w === 0 && b.h === 0)) return;
    const over = [];
    if (b.x < -0.6) over.push('left ' + b.x.toFixed(1));
    if (b.y < -0.6) over.push('top ' + b.y.toFixed(1));
    if (b.x + b.w > W + 0.6) over.push('right +' + (b.x + b.w - W).toFixed(1));
    if (b.y + b.h > H + 0.6) over.push('bottom +' + (b.y + b.h - H).toFixed(1));
    if (over.length) out.oob.push({
      tag: el.tagName, txt: (el.textContent || '').slice(0, 12),
      box: [+b.x.toFixed(1), +b.y.toFixed(1), +b.w.toFixed(1), +b.h.toFixed(1)],
      over: over.join(',')});
  });

  // 2) 文字互相压盖
  const ts = [...svg.querySelectorAll('text')].map(el => ({el, b: bb(el),
      txt: el.textContent.trim()})).filter(o => o.b && o.b.w > 0);
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i].b, c = ts[j].b;
    const ox = Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x);
    const oy = Math.min(a.y + a.h, c.y + c.h) - Math.max(a.y, c.y);
    if (ox > 0.5 && oy > 0.5) {
      const ratio = (ox * oy) / Math.min(a.w * a.h, c.w * c.h);
      if (ratio > 0.22) out.overlap.push({
        a: ts[i].txt.slice(0, 14), b: ts[j].txt.slice(0, 14),
        ratio: +ratio.toFixed(2)});
    }
  }

  // 3) 三角形内角
  const ang = (p, q, r) => {  // 顶点 q
    const v1 = [p[0] - q[0], p[1] - q[1]], v2 = [r[0] - q[0], r[1] - q[1]];
    const d = v1[0] * v2[0] + v1[1] * v2[1];
    const n = Math.hypot(...v1) * Math.hypot(...v2);
    return Math.acos(Math.max(-1, Math.min(1, d / n))) * 180 / Math.PI;
  };
  svg.querySelectorAll('polygon').forEach(el => {
    const pts = el.getAttribute('points').trim().split(/[\s,]+/).map(Number);
    const p = []; for (let i = 0; i < pts.length; i += 2) p.push([pts[i], pts[i + 1]]);
    if (p.length !== 3) return;
    out.tri.push({pts: p, angles: [
      +ang(p[1], p[0], p[2]).toFixed(1),
      +ang(p[0], p[1], p[2]).toFixed(1),
      +ang(p[0], p[2], p[1]).toFixed(1)]});
  });

  // 4) 直角符号是否画在真正的直角上
  const verts = [];
  svg.querySelectorAll('polygon').forEach(el => {
    el.getAttribute('points').trim().split(/[\s,]+/).map(Number)
      .forEach((v, i, a) => { if (i % 2 === 0) verts.push([v, a[i + 1]]); });
  });
  svg.querySelectorAll('path').forEach(el => {
    const d = el.getAttribute('d') || '';
    const m = d.match(/^M\s*([\d.]+),([\d.]+)\s*L\s*([\d.]+),([\d.]+)\s*L\s*([\d.]+),([\d.]+)\s*$/);
    if (!m) return;
    const p1 = [+m[1], +m[2]], p2 = [+m[3], +m[4]], p3 = [+m[5], +m[6]];
    const l1 = Math.hypot(p1[0] - p2[0], p1[1] - p2[1]);
    const l2 = Math.hypot(p3[0] - p2[0], p3[1] - p2[1]);
    if (l1 > 30 || l2 > 30) return;
    const dot = (p1[0] - p2[0]) * (p3[0] - p2[0]) + (p1[1] - p2[1]) * (p3[1] - p2[1]);
    if (Math.abs(dot) > 0.5) return;                      // 符号本身不是直角
    // 找最近的真实顶点（直角符号的拐角应离顶点最远，取两端点中点反推）
    const mid = [(p1[0] + p3[0]) / 2, (p1[1] + p3[1]) / 2];
    let best = null, bd = 1e9;
    verts.forEach(v => { const dd = Math.hypot(v[0] - mid[0], v[1] - mid[1]);
      if (dd < bd) { bd = dd; best = v; } });
    if (!best || bd > 26) return;
    // 该顶点在哪个三角形里、内角多少
    let info = null;
    svg.querySelectorAll('polygon').forEach(pl => {
      const a = pl.getAttribute('points').trim().split(/[\s,]+/).map(Number);
      for (let i = 0; i < a.length; i += 2) {
        if (Math.hypot(a[i] - best[0], a[i + 1] - best[1]) > 0.6) continue;
        const q = [a[i], a[i + 1]];
        const o1 = [a[(i + 2) % a.length], a[(i + 3) % a.length]];
        const o2 = [a[(i - 2 + a.length) % a.length], a[(i - 1 + a.length) % a.length]];
        if (a.length === 3) info = +ang(o1, q, o2).toFixed(1);
      }
    });
    out.right.push({corner: p2, vertex: best, dist: +bd.toFixed(1), angle: info});
  });
  return out;
}
"""


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    d = sys.argv[1] if len(sys.argv) > 1 else "content/media"
    files = sorted(glob.glob(str(root / d / "*.svg")))
    report = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 900, "height": 700})
        for f in files:
            pg.goto(pathlib.Path(f).resolve().as_uri(), wait_until="load")
            pg.wait_for_timeout(60)
            report[os.path.basename(f)] = pg.evaluate(JS)
        br.close()

    bad = 0
    for name, r in report.items():
        issues = []
        for o in r["oob"]:
            issues.append(f"越界 [{o['tag']}] '{o['txt']}' {o['box']} -> {o['over']}")
        for o in r["overlap"]:
            issues.append(f"压字 '{o['a']}' x '{o['b']}' 重叠比 {o['ratio']}")
        for t in r["tri"]:
            a = t["angles"]
            if min(a) < 6:
                issues.append(f"退化三角形 角度 {a}")
            if max(a) > 168:
                issues.append(f"近似平角 角度 {a}")
        for rr in r["right"]:
            if rr["angle"] is not None and abs(rr["angle"] - 90) > 3:
                issues.append(
                    f"直角符号处实际 {rr['angle']}° (顶点 {rr['vertex']})")
        if issues:
            bad += 1
            print(f"\n### {name}  ({int(r['w'])}x{int(r['h'])})")
            for i in issues:
                print("   -", i)
    print(f"\n共 {len(files)} 张，疑似问题 {bad} 张")
    json.dump(report, open(root / ".tmp" / "figs_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("详细几何数据 -> .tmp/figs_report.json")


if __name__ == "__main__":
    main()
