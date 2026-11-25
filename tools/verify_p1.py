"""P1 改造实测：精简视图默认与切换、伴读句覆盖、问句搜索、打印完整性。
运行前先启动 dist/ 的 http.server 8914。
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8914"
OUT = Path(__file__).resolve().parents[2] / "design-review" / "p1-verify"
OUT.mkdir(parents=True, exist_ok=True)
LOW = BASE + "/points/m1-01-02-num-1-to-20/"       # segment 1，应默认精简
LOW2 = BASE + "/points/m1-01-06-fraction-intro-and-division/"  # segment 2
HIGH = BASE + "/points/m1-01-01-number-classify/"  # segment 3，应默认完整

with sync_playwright() as p:
    b = p.chromium.launch()
    result = {}

    def vis(page, sel):
        loc = page.locator(sel).first
        return loc.is_visible() if loc.count() else False

    # 学段默认
    for name, url in [("low", LOW), ("low2", LOW2), ("high", HIGH)]:
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(url, wait_until="networkidle")
        result[f"view_default_{name}"] = pg.evaluate("() => document.documentElement.getAttribute('data-view')")
        result[f"plain_{name}"] = (pg.locator(".plain-talk p").inner_text()[:40]
                                   if pg.locator(".plain-talk").count() else None)
        pg.close()

    # 手动切换与跨页记忆
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(LOW, wait_until="networkidle")
    result["low_initial_examples"] = vis(pg, ".sec-examples")
    result["low_initial_cautions"] = vis(pg, ".sec-cautions")
    pg.locator('[data-view-set="full"]').click()
    result["low_after_full"] = pg.evaluate("() => document.documentElement.getAttribute('data-view')")
    result["low_full_cautions"] = vis(pg, ".sec-cautions")
    pg.goto(HIGH, wait_until="networkidle")
    result["cross_page_full"] = pg.evaluate("() => document.documentElement.getAttribute('data-view')")
    pg.locator('[data-view-set="auto"]').click()
    pg.goto(LOW, wait_until="networkidle")
    result["auto_back_low"] = pg.evaluate("() => document.documentElement.getAttribute('data-view')")
    pg.screenshot(path=str(OUT / "view-simple.png"), full_page=False)
    pg.locator('[data-view-set="full"]').click()
    pg.screenshot(path=str(OUT / "view-full.png"), full_page=False)

    # 打印始终完整
    pg.locator('[data-view-set="simple"]').click()
    pg.emulate_media(media="print")
    result["print_all_blocks_visible"] = pg.evaluate("""() => {
      var blocks = Array.from(document.querySelectorAll('.page-point .block'));
      return blocks.every(function(b){ return getComputedStyle(b).display !== 'none'; });
    }""")
    pg.emulate_media(media="screen")
    pg.close()

    # 问句搜索
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="networkidle")
    def search(q):
        pg.evaluate("() => document.getElementById('search-modal').hidden = false")
        pg.locator("#search-input").fill(q)
        pg.wait_for_timeout(120)
        n = pg.locator("#search-results li").count()
        first = pg.locator("#search-results li .sr-t").first.inner_text() if n else None
        return n, first
    result["search_plain"] = search("通分")
    result["search_question"] = search("通分怎么算")
    result["search_howto"] = search("怎么列方程")
    result["search_whatis"] = search("什么是平均数")
    result["search_short"] = search("鸡兔")
    pg.close()

    # 手机视图与伴读句
    mob = b.new_page(viewport={"width": 390, "height": 844})
    mob.goto(LOW, wait_until="networkidle")
    result["mobile_overflow"] = mob.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    result["mobile_plain_visible"] = vis(mob, ".plain-talk")
    result["mobile_switch_visible"] = vis(mob, ".view-switch")
    mob.screenshot(path=str(OUT / "view-mobile.png"), full_page=False)
    mob.close()
    b.close()

print(json.dumps(result, ensure_ascii=False, indent=2))
(OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
