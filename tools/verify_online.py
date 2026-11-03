"""线上站点冒烟验证：检查渲染、公式、搜索索引、站内跳转、控制台报错。

用法: python tools/verify_online.py [BASE_URL] [SHARECODE]
默认 BASE_URL = https://ttbingo.github.io/primary-math-atlas
带门禁的域名（app.workbuddy.host）需传 SHARECODE，首次访问会种 cookie。
"""
import sys
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        "https://ttbingo.github.io/primary-math-atlas").rstrip("/")
CODE = sys.argv[2] if len(sys.argv) > 2 else ""
ENTRY = BASE + (f"/?sharecode={CODE}" if CODE else "/")
SHOTS = ".shots"


def main():
    errs, fails = [], []
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1360, "height": 900})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(ENTRY, wait_until="networkidle", timeout=60000)
        cards = pg.locator(".mod-card").count()
        idx = pg.evaluate("(window.__SEARCH_INDEX__||[]).length")
        links = pg.locator("a[href]").count()
        print(f"首页: 模块卡片={cards} 搜索索引={idx} 链接数={links}")
        if cards != 4:
            fails.append(f"模块卡片数异常: {cards}")
        if idx < 160:
            fails.append(f"搜索索引条数异常: {idx}")

        # 站内跳转（子路径相对链接）
        pg.locator(".mod-card").first.click()
        pg.wait_for_load_state("networkidle")
        print(f"点模块卡片 -> {pg.url}")
        if not pg.url.startswith(BASE + "/m"):
            fails.append(f"模块跳转 URL 异常: {pg.url}")
        topics = pg.locator('a[href*="/t/"]').count()
        print(f"模块页: 主题链接={topics}")
        if topics == 0:
            fails.append("模块页无主题链接")

        pg.goto(BASE + "/points/m2-01-17-rect-area/", wait_until="networkidle",
                timeout=60000)
        katex = pg.locator(".katex").count()
        bare = pg.evaluate(
            r"document.body.innerText.match(/(^|[^\\])\$[^$\n]{1,40}\$/g)||[]"
        )
        h2 = pg.locator(".point-body h2, .p-sec h2, h2").count()
        print(f"知识点页: KaTeX={katex} 裸$= {len(bare)} 板块标题={h2}")
        if katex == 0:
            fails.append("知识点页未渲染公式")
        if bare:
            fails.append(f"残留裸 $ 公式: {bare[:3]}")
        pg.screenshot(path=f"{SHOTS}/gh-point.png", full_page=False)

        # 配图是否真的加载（门禁域名子资源易 403）
        pg.goto(BASE + "/points/m2-01-05-triangle-classify/", wait_until="networkidle",
                timeout=60000)
        bad_img = pg.evaluate(
            "[...document.images].filter(i=>!i.complete||i.naturalWidth===0)"
            ".map(i=>i.currentSrc||i.src)")
        n_img = pg.evaluate("document.images.length")
        print(f"三角形分类页: 图片={n_img} 加载失败={len(bad_img)}")
        if n_img == 0:
            fails.append("配图未出现在页面")
        if bad_img:
            fails.append(f"配图加载失败: {bad_img[:2]}")

        # 搜索
        pg.keyboard.press("Control+k")
        pg.wait_for_timeout(400)
        if pg.locator("#search-input, .search-input, input[type=search]").count():
            pg.locator("#search-input, .search-input, input[type=search]").first.fill("面积")
            pg.wait_for_timeout(600)
            hits = pg.locator("#search-results a").count()
            print(f"搜索「面积」命中={hits}")
            if hits == 0:
                fails.append("搜索无结果")
        pg.screenshot(path=f"{SHOTS}/gh-search.png")

        pg.goto(ENTRY, wait_until="networkidle")
        pg.screenshot(path=f"{SHOTS}/gh-home.png", full_page=False)
        br.close()

    print(f"\n控制台错误: {len(errs)}")
    for e in errs[:5]:
        print("  !", e[:120])
    print(f"失败项: {len(fails)}")
    for f in fails:
        print("  X", f)
    sys.exit(1 if (fails or errs) else 0)


if __name__ == "__main__":
    main()
