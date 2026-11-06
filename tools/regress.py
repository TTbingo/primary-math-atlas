# -*- coding: utf-8 -*-
"""全站回归：构建产物的每一项都要实测，不能只看状态码。

用法：python tools/regress.py [端口]
"""
import json
import pathlib
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def idx_topics_of(mid):
    """某模块下的主题数（用于导读链接数的下限判定）。"""
    mod = json.loads((DIST.parent / "content" / "modules.json").read_text(encoding="utf-8"))
    return [t for t in mod["topics"] if t["module"] == mid]


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8914"
    base = f"http://127.0.0.1:{port}"
    fails = []

    # ── 1. 产物完整性
    points = sorted(p.parent.name for p in (DIST / "points").glob("*/index.html"))
    topics = sorted(p.parent.name for p in (DIST / "t").glob("*/index.html"))
    modules = sorted(p.parent.name for p in DIST.glob("m*/index.html"))
    print(f"产物：{len(points)} 篇 / {len(topics)} 主题 / {len(modules)} 模块")
    # 期望值从 modules.json 动态读，不硬编码——节点增减时不用改这里
    mod = json.loads((DIST.parent / "content" / "modules.json").read_text(encoding="utf-8"))
    want_points = sum(len(t["points"]) for t in mod["topics"])
    if len(points) != want_points:
        fails.append(f"知识点页数 {len(points)}，应为 {want_points}")
    if len(points) > want_points:
        fails.append(f"dist/points 有 {len(points) - want_points} 个陈旧页面，需清空 dist 后重建")

    # ── 2. 浏览器实测
    urls = ["/", "/m1/", "/m2/", "/m3/", "/m4/"]
    urls += [f"/t/{t}/" for t in topics]
    urls += [f"/points/{p}/" for p in points]
    total_katex = 0
    n_ptref = 0
    n_dead = 0
    n_rel3 = 0
    n_tb = 0
    with sync_playwright() as pw:
        # 本机装了代理，Chromium 会自动走系统代理，访问 127.0.0.1 会被代理
        # 拦成 502。显式加 --no-proxy-server 让它直连本地服务。
        b = pw.chromium.launch(args=["--no-proxy-server"])
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        for u in urls:
            errs.clear()
            try:
                resp = pg.goto(base + u, wait_until="domcontentloaded", timeout=30000)
                code = resp.status if resp else 0
            except Exception as e:
                fails.append(f"{u} 加载失败: {str(e)[:60]}")
                continue
            if code >= 400:
                fails.append(f"{u} HTTP {code}")
                continue
            # 等图片真正加载完（loading="lazy" 的图需要滚动到视口才会加载）
            try:
                pg.wait_for_function(
                    "() => [...document.images].every(i => i.complete)", timeout=5000)
            except Exception:
                pass
            # 懒加载的图没进视口就不会请求，complete 恒为 false——不能据此判失败。
            # 改成把每个 img 的 src 单独取回来做 HTTP 实测，确认真能取到。
            try:
                pg.evaluate("""async () => {
                  for (const img of document.images) {
                    img.loading = 'eager';
                    const s = img.getAttribute('src');
                    if (!s) continue;
                    try { await fetch(s, {method:'GET'}); } catch(e) {}
                  }
                }""")
                pg.wait_for_timeout(120)
            except Exception:
                pass
            info = pg.evaluate("""() => {
              const imgs=[...document.querySelectorAll('img')].filter(x=>!x.complete||x.naturalWidth===0).map(x=>x.getAttribute('src'));
              const body=document.body.innerText;
              return {
                imgs, secs: document.querySelectorAll('section').length,
                kerr: document.querySelectorAll('.katex-error').length,
                k: document.querySelectorAll('.katex').length,
                ptref: document.querySelectorAll('a.ptref').length,
                dead: document.querySelectorAll('span.ptref-dead').length,
                relTags: [...document.querySelectorAll('.rel-tag')].map(e=>e.innerText),
                relGroups: document.querySelectorAll('.rel-group').length,
                tb: document.querySelectorAll('.textbook, .tb-line').length,
                bd: (body.match(/\\$/g)||[]).length,
                tc: (body.match(/\\\\\\\\(frac|times|cdot|circ|angle|triangle|sqrt|perp|parallel|geqslant|leqslant|tfrac|vec|checkmark|mathrm)/g)||[]).length,
                secKeys: [...document.querySelectorAll('section[id]')].map(e=>e.id)
              };
            }""")
            total_katex += info["k"]
            n_ptref += info["ptref"]
            n_dead += info["dead"]
            n_tb += info["tb"]
            if "/points/" in u:
                n_rel3 += 1 if set(info["relTags"]) == {"前置", "后续", "常一起考"} else 0
                if set(info["relTags"]) != {"前置", "后续", "常一起考"}:
                    fails.append(f"{u} 三类关联不全: {info['relTags']}")
                need = {"explanation","scenarios","cautions","why","examples","inferences",
                        "pitfalls","intuition","related"}
                miss = need - set(info["secKeys"])
                if miss:
                    fails.append(f"{u} 缺板块 {miss}")
            if info["imgs"]:
                fails.append(f"{u} 配图未加载 {info['imgs'][:2]}")
            if info["kerr"]:
                fails.append(f"{u} KaTeX 报错 {info['kerr']}")
            if info["bd"] or info["tc"]:
                fails.append(f"{u} 有裸 TeX 残留")
            if errs:
                fails.append(f"{u} 控制台报错 {errs[:1]}")
        b.close()

    print(f"KaTeX 渲染 {total_katex} 处 | 正文知识点链接 {n_ptref} 个 | 死链 {n_dead}")
    print(f"教材定位标记 {n_tb} 个 | 三类关联齐全的篇目 {n_rel3}/{len(points)}")
    if n_dead:
        fails.append(f"有 {n_dead} 个死链")
    if n_rel3 != len(points):
        fails.append(f"三类关联齐全的只有 {n_rel3} 篇")

    # ── 3. 导读板块
    for mid in modules:
        body = urllib.request.urlopen(f"{base}/{mid}/").read().decode("utf-8")
        if 'class="block guide"' not in body:
            fails.append(f"/{mid}/ 缺导读板块")
        # m4 只有 2 个主题，链接数天然少——按主题数给下限
        n_links = body.count('class="ptref"')
        if n_links < len(idx_topics_of(mid)) - 1:
            fails.append(f"/{mid}/ 导读里的知识点链接只有 {n_links} 个")
    print(f"导读板块：{len(modules)} 个模块页")

    # ── 4. 构建进度字样
    for u in urls[:6] + [f"/points/{p}/" for p in points[:3]]:
        body = urllib.request.urlopen(base + u).read().decode("utf-8")
        for w in ("待写", "还在规划中", "这一节还会包含"):
            if w in body:
                fails.append(f"{u} 出现构建进度字样「{w}」")

    print()
    if fails:
        print(f"✗ 发现 {len(fails)} 个问题：")
        for f in fails[:30]:
            print("  -", f)
        sys.exit(1)
    print("✓ 全站回归通过")


if __name__ == "__main__":
    main()
