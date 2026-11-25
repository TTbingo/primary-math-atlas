"""抽检 SVG 在深色模式下的表现：选取跨模块代表图，截图并输出硬编码颜色清单。
本脚本只抽检、不修改 SVG。运行前先启动 http.server 8914。
"""
import json
import re
from collections import Counter
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "design-review" / "p0-verify"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8914"

# 跨模块取样：数与代数 / 图形与几何 / 统计与概率 / 数学思考
SAMPLES = [
    "m1-01-01-number-classify.svg",
    "m1-07-02-sum-difference-line.svg",
    "m2-01-03-angle-protractor.svg",
    "m3-02-01-bar-chart-example.svg",
    "m4-04-01-pigeonhole.svg",
]

files = sorted((ROOT / "dist" / "assets" / "svg").glob("*.svg"))
issues = []
for f in files:
    s = f.read_text(encoding="utf-8")
    bg = bool(re.search(r'fill="#fffdf8"', s))
    ink = bool(re.search(r'fill="#17181c"', s))
    cur = "currentColor" in s
    if bg or (ink and not cur):
        issues.append({"file": f.name, "light_bg": bg, "dark_ink": ink, "currentColor": cur})

summary = {
    "total_svg": len(files),
    "with_light_bg": sum(1 for x in issues if x["light_bg"]),
    "with_dark_ink": sum(1 for x in issues if x["dark_ink"]),
    "with_currentColor": sum(1 for f in files if "currentColor" in f.read_text(encoding="utf-8")),
}
existing = [n for n in SAMPLES if (ROOT / "dist" / "assets" / "svg" / n).exists()]

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1100, "height": 900})
    shots = []
    for name in existing:
        stem = name[:-4]
        page.goto(f"{BASE}/points/{stem}/", wait_until="networkidle")
        page.evaluate("() => document.documentElement.setAttribute('data-theme','dark')")
        img = page.locator(f'img[src$="{name}"]').first
        if img.count():
            img.scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            shot = OUT / f"svg-dark-{stem}.png"
            img.screenshot(path=str(shot))
            shots.append(shot.name)
    b.close()

result = {"summary": summary, "samples_shot": shots, "issue_count": len(issues),
          "issues_first_20": issues[:20]}
(OUT / "svg-dark-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
