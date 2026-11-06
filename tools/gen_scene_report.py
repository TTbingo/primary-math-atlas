# -*- coding: utf-8 -*-
"""生成「例题场景修正」审核报告（markdown + 独立 HTML）。

数据来源：tools/_scene_dump.txt（改动前的快照）、tools/_scene_fix.tsv（改动清单）、content/points/*.json（改动后）。

用法：python tools/gen_scene_report.py
"""
import collections
import glob
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, "content", "_reference", "scene-fix-report.md")
OUT_HTML = os.path.join(ROOT, "content", "_reference", "scene-fix-report.html")


def read_dump():
    """改动前：全局序号 → (篇id, 例id, 场景, context, question)"""
    rows, point = {}, None
    n = 0
    with open(os.path.join(ROOT, "tools", "_scene_dump.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("###"):
                point = line[4:].split("|")[0].strip()
                continue
            if not line.strip():
                continue
            n += 1
            idx, ex, scene, ctx, q = line.split("\t")
            rows[n] = dict(point=point, ex=ex, old=scene, ctx=ctx, q=q)
    return rows


def read_fix():
    fix = {}
    with open(os.path.join(ROOT, "tools", "_scene_fix.tsv"), encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            idx, scene, why = line.rstrip("\n").split("\t")
            fix[int(idx)] = (scene, why)
    return fix


def main():
    rows = read_dump()
    fix = read_fix()

    # 篇名 + 最终场景
    meta = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "points", "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        meta[d["id"]] = d["title"]

    items = []
    for idx in sorted(fix):
        r = rows[idx]
        new, why = fix[idx]
        if new == r["old"]:
            continue
        items.append(dict(point=r["point"], title=meta.get(r["point"], ""), ex=r["ex"],
                          old=r["old"], new=new, why=why, q=r["q"]))

    # 统计
    by_point = collections.OrderedDict()
    for it in items:
        by_point.setdefault((it["point"], it["title"]), []).append(it)
    pair = collections.Counter((it["old"], it["new"]) for it in items)
    before = collections.Counter(r["old"] for r in rows.values())
    after = collections.Counter()
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "points", "*.json"))):
        for e in json.load(open(path, encoding="utf-8"))["sections"]["examples"]:
            after[e["scene"]] += 1
    total = sum(len(v) for v in by_point.values())

    # ── markdown
    lines = [
        "# 例题场景修正报告",
        "",
        f"- 全站例题：648 道；本次修正场景标签：**{total} 道**，涉及 **{len(by_point)} 篇**",
        "- 只改 `examples[].scene` 一个字段，题干、解法、答案、配图一律未动（`git diff` 非 scene 行 = 0）",
        "- 场景枚举仍为 13 个（`content/taxonomy.json.scenes`），未新增词条",
        "",
        "## 一、修正后的场景分布",
        "",
        "| 场景 | 修正前 | 修正后 | 增减 |",
        "|---|---:|---:|---:|",
    ]
    for k in [x for x, _ in after.most_common()]:
        d = after[k] - before.get(k, 0)
        lines.append(f"| {k} | {before.get(k, 0)} | {after[k]} | {d:+d} |")
    lines.append(f"| **合计** | **{sum(before.values())}** | **{sum(after.values())}** | — |")

    lines += ["", "## 二、主要错配类型（原场景 → 新场景）", "", "| 原 → 新 | 道数 |", "|---|---:|"]
    for (o, n), c in pair.most_common(12):
        lines.append(f"| {o} → {n} | {c} |")

    lines += ["", "## 三、逐篇明细", ""]
    for (pid, title), its in by_point.items():
        lines.append(f"### {title}（`{pid}`）— {len(its)} 处")
        lines.append("")
        lines.append("| 例 | 场景修正 | 依据 | 题目 |")
        lines.append("|---|---|---|---|")
        for it in its:
            q = it["q"].replace("|", "\\|")
            if len(q) > 46:
                q = q[:46] + "…"
            lines.append(f"| {it['ex']} | {it['old']} → **{it['new']}** | {it['why']} | {q} |")
        lines.append("")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines))

    # ── HTML
    def esc(s):
        return html.escape(s)

    css = """
:root{--ink:#1b2430;--muted:#5d6b7a;--line:#e3e8ee;--bg:#f6f8fa;--card:#fff;
--accent:#2f6fd0;--old:#b23b3b;--new:#1e7a52}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 8px}
.lead{color:var(--muted);margin:0 0 22px;font-size:14px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 26px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;flex:1 1 150px}
.card b{display:block;font-size:22px;line-height:1.2}
.card span{color:var(--muted);font-size:13px}
h2{font-size:18px;margin:34px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:15px;margin:26px 0 8px;color:var(--accent)}
h3 em{color:var(--muted);font-style:normal;font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:13.5px;
border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#eef2f7;font-weight:600;color:#33414f}
tr:last-child td{border-bottom:none}
td.n{white-space:nowrap;color:var(--muted)}
.o{color:var(--old);text-decoration:line-through;text-decoration-thickness:1px}
.nw{color:var(--new);font-weight:600}
.tag{display:inline-block;background:#eef2f7;border-radius:5px;padding:1px 6px;font-size:12px;color:#42536a}
.note{background:#fff8e6;border:1px solid #f0e0b0;border-radius:8px;padding:12px 16px;font-size:13.5px;margin:18px 0}
"""

    parts = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>例题场景修正报告</title><style>", css, "</style></head><body><div class=\"wrap\">",
        "<h1>例题场景修正报告</h1>",
        f"<p class=\"lead\">只改 <code>examples[].scene</code>；题干/解法/答案/配图零改动。共 {total} 处，涉及 {len(by_point)} 篇。</p>",
        "<div class=\"cards\">",
        f"<div class=\"card\"><b>648</b><span>全站例题</span></div>",
        f"<div class=\"card\"><b>{total}</b><span>修正场景</span></div>",
        f"<div class=\"card\"><b>{len(by_point)}</b><span>涉及篇目</span></div>",
        "<div class=\"card\"><b>13</b><span>场景枚举（未增减）</span></div>",
        "</div>",
        "<div class=\"note\"><strong>规则变更：</strong>原先要求「同一篇内场景不得重复」，是机械分配留下的约束——为凑不重复，"
        "出现了「金融理财：一年有多少天」这类错标签。现改为按题目实际内容判定，允许同篇重复（两道题都在超市很正常）。"
        "构建器仍校验「场景必须在 13 个枚举内」。</div>",
        "<h2>主要错配类型</h2><table><tr><th>原场景 → 新场景</th><th class=\"n\">道数</th></tr>",
    ]
    for (o, n), c in pair.most_common(12):
        parts.append(f"<tr><td><span class=\"o\">{esc(o)}</span> → <span class=\"nw\">{esc(n)}</span></td><td class=\"n\">{c}</td></tr>")
    parts.append("</table>")

    parts.append("<h2>逐篇明细</h2>")
    for (pid, title), its in by_point.items():
        parts.append(f"<h3>{esc(title)} <em>{esc(pid)} · {len(its)} 处</em></h3>")
        parts.append("<table><tr><th style=\"width:52px\">例</th><th style=\"width:190px\">场景修正</th>"
                     "<th style=\"width:150px\">依据</th><th>题目</th></tr>")
        for it in its:
            parts.append(
                f"<tr><td class=\"n\">{esc(it['ex'])}</td>"
                f"<td><span class=\"o\">{esc(it['old'])}</span> → <span class=\"nw\">{esc(it['new'])}</span></td>"
                f"<td><span class=\"tag\">{esc(it['why'])}</span></td>"
                f"<td>{esc(it['q'])}</td></tr>"
            )
        parts.append("</table>")
    parts.append("</div></body></html>")
    open(OUT_HTML, "w", encoding="utf-8").write("\n".join(parts))

    print(f"markdown → {os.path.relpath(OUT_MD, ROOT)}")
    print(f"html     → {os.path.relpath(OUT_HTML, ROOT)}")
    print(f"修正 {total} 处 / {len(by_point)} 篇")


if __name__ == "__main__":
    main()
