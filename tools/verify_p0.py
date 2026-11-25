"""P0 三项改造实测：折叠交互、进度三态与导入导出、语义色与 SVG 暗色抽检。
运行前先在 dist/ 启动 http.server 8914。
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8914"
OUT = Path(__file__).resolve().parents[2] / "design-review" / "p0-verify"
OUT.mkdir(parents=True, exist_ok=True)
POINT = BASE + "/points/m1-01-01-number-classify/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    result = {}

    # ---------- P0-1 折叠 ----------
    page = browser.new_page(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    page.goto(POINT, wait_until="networkidle")
    result["fold_initial_open"] = page.evaluate(
        "() => Array.from(document.querySelectorAll('details.ex-answer,details.pitfall')).filter(d=>d.open).length")
    result["fold_total"] = page.evaluate(
        "() => document.querySelectorAll('details.ex-answer,details.pitfall').length")
    result["question_visible"] = page.locator(".ex-q").first.is_visible()
    page.locator(".fold-all").click()
    result["fold_after_click"] = page.evaluate(
        "() => Array.from(document.querySelectorAll('details.ex-answer,details.pitfall')).filter(d=>d.open).length")
    result["fold_btn_text"] = page.locator(".fold-all").inner_text()
    result["answer_visible"] = page.locator(".ex-s").first.is_visible()
    page.screenshot(path=str(OUT / "point-expanded.png"), full_page=False)

    # ---------- P0-2 旧数据迁移 ----------
    page.goto(BASE + "/", wait_until="networkidle")
    page.evaluate("""() => {
      localStorage.removeItem('mathsite:state');
      localStorage.setItem('mathsite:done', JSON.stringify([
        'm1-01-01-number-classify','m1-01-02-number-classify'
      ]));
    }""")
    page.reload(wait_until="networkidle")
    result["migrated_mastered"] = page.locator(".done-count").inner_text()
    result["old_key_kept"] = page.evaluate("() => localStorage.getItem('mathsite:done') !== null")

    # 三态切换
    page.goto(POINT, wait_until="networkidle")
    page.locator('.state-btn[data-state="review"]').click()
    result["state_after_review"] = page.evaluate("() => localStorage.getItem('mathsite:state')")
    result["heading_mark"] = page.evaluate("() => getComputedStyle(document.querySelector('.panel-h1 h1'),'::after').content")
    page.locator('.state-btn[data-state=""]').click()
    result["state_after_reset"] = page.evaluate("() => localStorage.getItem('mathsite:state')")

    # 导出 / 导入
    page.goto(BASE + "/", wait_until="networkidle")
    page.evaluate("""() => localStorage.setItem('mathsite:state', JSON.stringify({
      'm1-01-01-number-classify':'mastered','m2-01-01-plane-shapes':'review'
    }))""")
    page.reload(wait_until="networkidle")
    with page.expect_download() as dl:
        page.locator("[data-progress-export]").click()
    download = dl.value
    exported = OUT / "progress-export.json"
    download.save_as(str(exported))
    result["export_json"] = json.loads(exported.read_text(encoding="utf-8"))["state"]
    page.evaluate("() => localStorage.removeItem('mathsite:state')")
    page.reload(wait_until="networkidle")
    page.locator(".progress-file").set_input_files(str(exported))
    page.wait_for_timeout(300)
    result["import_mastered"] = page.locator(".done-count").inner_text()
    result["import_review"] = page.locator(".review-count").inner_text()
    page.screenshot(path=str(OUT / "home-desktop.png"), full_page=False)

    # ---------- P0-3 语义色 ----------
    page.goto(POINT, wait_until="networkidle")
    result["rel_pre_light"] = page.evaluate("""() => {
      const e=document.querySelector('.rel-前置 .rel-tag');
      return e ? getComputedStyle(e).color : null;
    }""")
    page.evaluate("() => document.documentElement.setAttribute('data-theme','dark')")
    result["rel_pre_dark"] = page.evaluate("""() => {
      const e=document.querySelector('.rel-前置 .rel-tag');
      return e ? getComputedStyle(e).color : null;
    }""")
    page.screenshot(path=str(OUT / "point-dark.png"), full_page=False)

    # ---------- 手机视图 ----------
    mob = browser.new_page(viewport={"width": 390, "height": 844}, accept_downloads=True)
    mob.goto(POINT, wait_until="networkidle")
    result["mobile_overflow"] = mob.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    result["mobile_fold_visible"] = mob.locator(".fold-all").is_visible()
    mob.screenshot(path=str(OUT / "point-mobile.png"), full_page=False)
    mob.goto(BASE + "/", wait_until="networkidle")
    result["mobile_home_overflow"] = mob.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    result["mobile_import_visible"] = mob.locator("[data-progress-import]").is_visible()
    mob.screenshot(path=str(OUT / "home-mobile.png"), full_page=False)

    browser.close()

print(json.dumps(result, ensure_ascii=False, indent=2))
(OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
