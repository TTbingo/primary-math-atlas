# -*- coding: utf-8 -*-
"""小学数学知识点图谱 — 静态站构建脚本。
仅依赖 Python 3 标准库。用法：
    python build.py          全量构建
    python build.py --check  只做校验，不产出
"""
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
C = ROOT / "content"
T = ROOT / "templates"
A = ROOT / "assets"
D = ROOT / "dist"

VAR_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORBIDDEN = ["证明", "求证", "证毕", "∵", "∴", "Q.E.D."]

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------- io helpers
def read_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def load_all():
    tax = read_json(C / "taxonomy.json")
    site = read_json(C / "site.json")
    std = {s["id"]: s for s in read_json(C / "standards.json")["items"]}
    grades = {p.stem: read_json(p) for p in sorted((C / "grades").glob("*.json"))}
    units = {p.stem: read_json(p) for p in sorted((C / "units").glob("*.json"))}
    points = {p.stem: read_json(p) for p in sorted((C / "points").glob("*.json"))}
    return tax, site, std, grades, units, points


# --------------------------------------------------------------- markdown
MATH_FALLBACK = [
    (r"\\times", "×"), (r"\\div", "÷"), (r"\\pm", "±"), (r"\\le", "≤"),
    (r"\\ge", "≥"), (r"\\ne", "≠"), (r"\\pi", "π"), (r"\\%", "%"),
    (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2"), (r"\\dfrac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2"),
    (r"\^\{([^{}]*)\}", r"^\1"), (r"\\left|\\right|\\!", ""), (r"\\,|\\;|\\quad", " "),
]


def tex_fallback(tex):
    out = tex
    for a, b in MATH_FALLBACK:
        out = re.sub(a, b, out)
    return out.replace("{", "").replace("}", "")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def md_inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`\n]+)`", r'<code class="inline">\1</code>', s)
    s = re.sub(r"@@([A-Za-z0-9_-]+)", r'<span class="figref" data-fig="\1"></span>', s)
    s = re.sub(r"@point:([a-z0-9-]+)", r'<span class="ptref" data-point="\1"></span>', s)
    return s


def md_block(text, math_store):
    """受限 Markdown → HTML。math_store 用于收集公式。"""
    lines = text.split("\n")
    out = []
    i = 0

    def grab(t):
        """抽出公式换成哨兵，其余保持原文（尚未 escape）。"""
        def rep(m):
            n = len(math_store)
            math_store.append(m.group(1))
            return f"\x00M{n}\x00"
        # 段落中间出现的 $$...$$ 按行内公式收掉，否则会被单 $ 正则拆成两个空配对，
        # 留下 "$C = \pi d$" 这样的裸 TeX 残渣。
        t = re.sub(r"\$\$(.+?)\$\$", rep, t)
        return re.sub(r"\$([^$\n]+)\$", rep, t)

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        # 块级公式
        m = re.fullmatch(r"\$\$(.+)\$\$", line.strip())
        if m:
            math_store.append(m.group(1))
            out.append(f'<div class="math-display" data-tex="{attr(m.group(1))}">{esc(tex_fallback(m.group(1)))}</div>')
            i += 1
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li>" + md_inline(grab(lines[i][2:])) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                items.append("<li>" + md_inline(grab(re.sub(r"^\d+\.\s", "", lines[i]))) + "</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        if line.startswith("> "):
            paras = []
            while i < len(lines) and lines[i].startswith("> "):
                paras.append(lines[i][2:])
                i += 1
            out.append("<blockquote>" + md_inline(grab("\n".join(paras))) + "</blockquote>")
            continue
        buf = []
        while i < len(lines):
            cur = lines[i].rstrip()
            if (not cur.strip() or cur.startswith("- ") or cur.startswith("> ")
                    or re.match(r"^\d+\.\s", cur) or re.fullmatch(r"\$\$(.+)\$\$", cur.strip())):
                break
            buf.append(cur)
            i += 1
        out.append("<p>" + md_inline(grab("\n".join(buf))) + "</p>")
    return "".join(out)


def render_text(text, math_store=None):
    """渲染一段受限 Markdown，并把行内公式哨兵还原成 span。"""
    if math_store is None:
        math_store = []
    html = md_block(text, math_store)
    for n, tex in enumerate(math_store):
        html = html.replace(
            f"\x00M{n}\x00",
            f'<span class="math" data-tex="{attr(tex)}">{esc(tex_fallback(tex))}</span>')
    return html


def render_inline(text):
    """内联渲染：剥掉 md_block 产出的最外层 <p>，用于已包在 <p class=...> 里的场合。"""
    h = render_text(text)
    m = re.fullmatch(r"<p>(.*)</p>", h, re.S)
    return m.group(1) if m else h


def render_paragraphs(items, math_store=None):
    # render_text 走 md_block，本身已输出 <p>（或 <ul>），不能再包一层
    return "".join(render_text(x, math_store) for x in items)


# --------------------------------------------------------------- template
def tmpl(name, vars_):
    raw = (T / name).read_text(encoding="utf-8")

    def rep(m):
        k = m.group(1)
        if k not in vars_:
            raise KeyError(f"模板 {name} 缺少变量 {k}")
        return vars_[k]

    out = VAR_RE.sub(rep, raw)
    if VAR_RE.search(out):
        raise RuntimeError(f"模板 {name} 渲染后仍残留变量")
    return out


# --------------------------------------------------------------- validate
def validate(tax, std, grades, units, points):
    sec_keys = [s["key"] for s in tax["sections"]]
    domains = set(tax["domains"])
    chapters = set(tax["chapters"])
    scenes = set(tax["scenes"])
    scopes = set(tax["scopes"])
    literacy = set(tax["literacy"])

    for pid, p in points.items():
        ctx = f"points/{pid}.json"
        if p.get("id") != pid:
            err(f"{ctx}: 文件名字与 id 不一致（{p.get('id')}）")
        if not ID_RE.match(pid):
            err(f"{ctx}: id 不满足 [a-z0-9-] 命名规则")
        # 前缀归属
        m = re.match(r"^(g\d\d-s\d-u\d\d)-p\d\d-", pid)
        if not m:
            err(f"{ctx}: id 前缀不符合 g{{gg}}-s{{s}}-u{{uu}}-p{{nn}}-{{slug}}")
        else:
            uid = m.group(1)
            owner = next((u for u in units.values() if u["id"].startswith(uid + "-")), None)
            if owner is None:
                err(f"{ctx}: 找不到所属单元 {uid}")
            elif pid not in owner.get("point_ids", []):
                err(f"{ctx}: 单元 {owner['id']} 的 point_ids 未登记本知识点")
        for f in ("title", "summary", "domain", "chapter", "scope", "verb_level"):
            if not p.get(f):
                err(f"{ctx}: 缺字段 {f}")
        if p.get("domain") and p["domain"] not in domains:
            err(f"{ctx}: domain「{p['domain']}」不在枚举内")
        if p.get("chapter") and p["chapter"] not in chapters:
            err(f"{ctx}: chapter「{p['chapter']}」不在枚举内")
        if p.get("scope") and p["scope"] not in scopes:
            err(f"{ctx}: scope「{p['scope']}」不在枚举内")
        for x in p.get("literacy", []):
            if x not in literacy:
                err(f"{ctx}: 核心素养「{x}」不在枚举内")
        for sid in p.get("standard_ids", []):
            if sid not in std:
                err(f"{ctx}: 课标条目 {sid} 不存在")
        for rid in p.get("prerequisites", []):
            if rid not in points:
                err(f"{ctx}: 前置知识点 {rid} 不存在")

        secs = p.get("sections", {})
        for k in sec_keys:
            if k not in secs:
                err(f"{ctx}: 缺板块 {k}")
        for spec in tax["sections"]:
            k, kind, mn = spec["key"], spec["kind"], spec["min_len"]
            v = secs.get(k)
            if v is None:
                continue
            if kind == "paragraphs":
                if len(v) < 1:
                    err(f"{ctx}.{k}: 至少 1 段")
                if sum(len(x) for x in v) < mn:
                    err(f"{ctx}.{k}: 字数 {sum(len(x) for x in v)} < 要求 {mn}")
            elif kind == "text":
                if len(v) < mn:
                    err(f"{ctx}.{k}: 字数 {len(v)} < 要求 {mn}")
            elif kind == "items":
                if len(v) < mn:
                    err(f"{ctx}.{k}: 条数 {len(v)} < 要求 {mn}")
            elif kind == "why":
                media_ids = {x["id"] for x in p.get("media", [])}
                if v.get("diagram") and v["diagram"] not in media_ids:
                    err(f"{ctx}.why.diagram: {v['diagram']} 未在 media 中定义")
                if len(v.get("steps", [])) < 2:
                    err(f"{ctx}.why.steps: 至少 2 步算理")
                if not v.get("experiment"):
                    err(f"{ctx}.why.experiment: 缺动手实验")
            elif kind == "examples":
                if len(v) < mn:
                    err(f"{ctx}.{k}: 例题数 {len(v)} < 要求 {mn}")
                seen = []
                for e in v:
                    if e.get("scene") not in scenes:
                        err(f"{ctx}.{k}: 场景「{e.get('scene')}」不在枚举内")
                    if e.get("scene") in seen:
                        err(f"{ctx}.{k}: 场景「{e.get('scene')}」重复")
                    seen.append(e.get("scene"))
                    for f in ("question", "solution", "answer"):
                        if not e.get(f):
                            err(f"{ctx}.{k}.{e.get('id')}: 缺 {f}")
                    em = e.get("media")
                    if em is not None:
                        slots = em if isinstance(em, list) else [em]
                        media_ids = {x["id"] for x in p.get("media", [])}
                        for slot in slots:
                            if slot not in media_ids:
                                err(f"{ctx}.{k}.{e.get('id')}: media「{slot}」未在 media 中定义")
            elif kind == "pitfalls":
                if len(v) < mn:
                    err(f"{ctx}.{k}: 条数 {len(v)} < 要求 {mn}")
                for x in v:
                    for f in ("wrong", "why", "right"):
                        if not x.get(f):
                            err(f"{ctx}.{k}: 缺 {f}")
            elif kind == "related":
                if len(v) < mn:
                    err(f"{ctx}.{k}: 条数 {len(v)} < 要求 {mn}")
                for r in v:
                    if r.get("id") not in points:
                        err(f"{ctx}.{k}: 关联 {r.get('id')} 不存在")

        # 禁用词
        blob = json.dumps(p.get("sections", {}), ensure_ascii=False)
        for w in tax["forbidden_words"]:
            if w in blob:
                err(f"{ctx}: 命中禁用词「{w}」（小学阶段不使用「证明」类表述）")
        # 人民币 $ 误用（先剥离数学公式，避免误伤 $1\,\text{cm}^2$ 这类写法）
        blob_nomath = re.sub(r"\$[^$\n]+\$", "\x00", blob)
        for m2 in re.finditer(r"(?<!\\)\$\d", blob_nomath):
            err(f"{ctx}: 疑似用 $ 表示人民币（应写「元」或 ¥）→ {blob_nomath[max(0,m2.start()-15):m2.start()+8]}")
        # 圆锥体积漏 1/3
        if "圆锥" in p.get("title", "") and re.search(r"(?<![\d/])V\s*=\s*Sh(?!\s*/)", blob):
            err(f"{ctx}: 圆锥体积疑似漏 1/3，请查 _reference/formula-audit.md A1")

    for uid, u in units.items():
        if u.get("id") != uid:
            err(f"units/{uid}.json: 名字与 id 不一致")
        for pid in u.get("point_ids", []):
            if pid not in points:
                err(f"units/{uid}.json: point_ids 中的 {pid} 不存在")
        for sid in u.get("standard_ids", []):
            if sid not in std:
                err(f"units/{uid}.json: 课标条目 {sid} 不存在")

    for gid, g in grades.items():
        for t in g.get("terms", []):
            for uid in t.get("units", []) + t.get("activities", []):
                if uid not in units:
                    err(f"grades/{gid}.json: 引用了不存在的 {uid}")

    # 单元内知识点编号连续性
    byunit = {}
    for pid in points:
        m = re.match(r"^(g\d\d-s\d-u\d\d)-p(\d\d)-", pid)
        if m:
            byunit.setdefault(m.group(1), []).append(int(m.group(2)))
    for uid, nums in byunit.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            err(f"单元 {uid}: 知识点编号不连续 → {sorted(nums)}")


# --------------------------------------------------------------- index
class Index:
    def __init__(self, tax, std, grades, units, points):
        self.tax, self.std, self.grades, self.units, self.points = tax, std, grades, units, points
        self.point_order = sorted(points)
        self.unit_order = sorted(units)
        self.grade_order = sorted(grades)
        self.unit_of = {}
        for pid in self.point_order:
            m = re.match(r"^(g\d\d-s\d-u\d\d)-p\d\d-", pid)
            self.unit_of[pid] = next((u for u in self.unit_order if u.startswith(m.group(1) + "-")), None)
        self.incoming = {pid: [] for pid in self.point_order}
        for pid, p in points.items():
            for r in p.get("sections", {}).get("related", []):
                if r.get("id") in self.incoming:
                    self.incoming[r["id"]].append((pid, r.get("note", "")))
        # 全局序号
        self.no = {pid: i + 1 for i, pid in enumerate(self.point_order)}

    def prev_next(self, pid):
        i = self.point_order.index(pid)
        return (self.point_order[i - 1] if i > 0 else None,
                self.point_order[i + 1] if i < len(self.point_order) - 1 else None)

    def root_for(self, depth):
        return "." if depth == 0 else "/".join([".."] * depth)

    def rel(self, pid, depth):
        return f"{self.root_for(depth)}/points/{pid}/index.html"

    def rel_unit(self, uid, depth):
        return f"{self.root_for(depth)}/units/{uid}/index.html"

    def rel_grade(self, gid, depth):
        return f"{self.root_for(depth)}/grades/{gid}/index.html"


# --------------------------------------------------------------- render bits
def plain(s):
    """属性值/纯文本场景：去掉公式的 $ 定界符，不留原始 TeX 标记。"""
    return re.sub(r"\$([^$]*)\$", r"\1", s or "")


def badge(text, cls="badge"):
    return f'<span class="{cls}">{esc(text)}</span>'


def render_media(p, depth, idx):
    out = []
    for m in p.get("media", []):
        src = f"{idx.root_for(depth)}/assets/svg/{m['file']}"
        out.append(
            f'<figure class="fig" data-fig="{m["id"]}">'
            f'<img src="{src}" width="{m.get("width",480)}" height="{m.get("height",260)}" '
            f'alt="{attr(m.get("alt",""))}" loading="lazy">'
            f'<figcaption>{esc(m.get("caption",""))}</figcaption></figure>')
    return "".join(out)


def render_standards(p, depth, idx):
    ids = p.get("standard_ids", [])
    if not ids:
        return ""
    rows = []
    for sid in ids:
        s = idx.std.get(sid)
        if not s:
            continue
        loc = f"印刷第 {s['print_page']} 页" if s.get("print_page") else "小学部分"
        rows.append(f"<tr><th>{esc(s['domain'])}·{esc(s['strand'])}</th>"
                    f"<td>{render_text(s['text'])}<div class=\"std-loc\">{esc(loc)}&#12288;行为动词：{badge(s.get('verb',''))}</div></td></tr>")
    if not rows:
        return ""
    return ('<section class="block std"><h2>课标要求</h2>'
            '<table class="kv"><tbody>' + "".join(rows) + "</tbody></table></section>")


def render_why(why, p, depth, idx):
    if not why:
        return ""
    parts = ['<div class="why">']
    if why.get("diagram"):
        parts.append(f'<div class="why-fig" data-fig-slot="{esc(why["diagram"])}"></div>')
    steps = "".join(f"<li>{render_text(s)}</li>" for s in why.get("steps", []))
    parts.append(f'<div class="why-steps"><p class="why-label">算理推导</p><ol>{steps}</ol></div>')
    parts.append(f'<div class="why-exp"><p class="why-label">动手实验</p>{render_text(why.get("experiment",""))}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_examples(items, depth, idx):
    if not items:
        return ""
    out = []
    for i, e in enumerate(items, 1):
        out.append('<div class="example">')
        out.append(f'<p class="ex-head"><strong>例 {i}（场景：{esc(e.get("scene",""))}）</strong>'
                   + (f'&#12288;<span class="ex-ctx">{render_inline(e.get("context",""))}</span>' if e.get("context") else "") + "</p>")
        out.append(f'<p class="ex-q">{render_inline(e.get("question",""))}</p>')
        out.append(f'<p class="ex-s"><strong>解：</strong>{render_inline(e.get("solution",""))}</p>')
        out.append(f'<p class="ex-a"><strong>答：</strong>{render_inline(e.get("answer",""))}</p>')
        m = e.get("media")
        if m:
            for slot in (m if isinstance(m, list) else [m]):
                out.append(f'<div class="ex-fig" data-fig-slot="{esc(slot)}"></div>')
        out.append("</div>")
    return "".join(out)


def render_pitfalls(items):
    if not items:
        return ""
    out = []
    for x in items:
        out.append('<div class="pitfall">')
        out.append(f'<p class="pf-w"><span class="pf-tag">错</span>{render_inline(x.get("wrong",""))}</p>')
        out.append(f'<p class="pf-y"><span class="pf-tag">为什么错</span>{render_inline(x.get("why",""))}</p>')
        out.append(f'<p class="pf-r"><span class="pf-tag">正确</span>{render_inline(x.get("right",""))}</p>')
        out.append("</div>")
    return "".join(out)


def render_related(p, depth, idx):
    out_parts = []
    outs = p.get("sections", {}).get("related", [])
    if outs:
        lis = []
        for r in outs:
            t = idx.points[r["id"]]["title"]
            lis.append(f'<li><a href="{idx.rel(r["id"], depth)}">{esc(t)}</a>'
                       f'<span class="rel-note">{render_inline(r.get("note",""))}</span></li>')
        out_parts.append('<div class="rel-group"><p class="rel-label">本知识点指向</p><ul>' + "".join(lis) + "</ul></div>")
    inc = idx.incoming.get(p["id"], [])
    if inc:
        lis = []
        for pid, note in inc:
            t = idx.points[pid]["title"]
            lis.append(f'<li><a href="{idx.rel(pid, depth)}">{esc(t)}</a>'
                       f'<span class="rel-note">{render_inline(note)}</span></li>')
        out_parts.append('<div class="rel-group"><p class="rel-label">指向本知识点</p><ul>' + "".join(lis) + "</ul></div>")
    return "".join(out_parts)


def render_sections(p, depth, idx, base_level):
    """base_level=2 → 板块用 H2（point 页）；=3 → 板块用 H3（unit 页）"""
    tax = idx.tax
    secs = p.get("sections", {})
    figs = {m["id"]: m for m in p.get("media", [])}
    out = []
    for spec in tax["sections"]:
        k, title, kind = spec["key"], spec["title"], spec["kind"]
        v = secs.get(k)
        if v is None:
            continue
        h = f"h{base_level}"
        out.append(f'<section class="block sec-{k}" id="{k}">')
        out.append(f'<{h} class="sec-h">{esc(title)}</{h}>')
        if kind == "paragraphs":
            out.append(render_paragraphs(v))
        elif kind == "text":
            out.append(render_text(v))
            # 直观理解配的顺口溜；render_text 自身已带 <p>，所以外层用 div
            if k == "intuition" and secs.get("rhyme"):
                out.append('<div class="rhyme">' + render_text(secs["rhyme"]) + "</div>")
        elif kind == "items":
            out.append("<ul class=" + '"items">' + "".join("<li>" + render_text(x) + "</li>" for x in v) + "</ul>")
        elif kind == "why":
            out.append(render_why(v, p, depth, idx))
        elif kind == "examples":
            out.append(render_examples(v, depth, idx))
        elif kind == "pitfalls":
            out.append(render_pitfalls(v))
        elif kind == "related":
            out.append(render_related(p, depth, idx))
        out.append("</section>")
    return "".join(out)


def fig_alt(s):
    """alt 只留纯文本：去掉公式的 $ 定界符，避免屏幕阅读器念出美元符号。"""
    return re.sub(r"\$([^$]*)\$", r"\1", s or "")


def resolve_fig_slots(html, p, depth, idx):
    """把 data-fig-slot 换成真实 figure；把 @@fig / @point 引用解析。"""
    figs = {m["id"]: m for m in p.get("media", [])}
    for fid, m in figs.items():
        src = f"{idx.root_for(depth)}/assets/svg/{m['file']}"
        fig = (f'<figure class="fig"><img src="{src}" width="{m.get("width",480)}" '
               f'height="{m.get("height",260)}" alt="{attr(fig_alt(m.get("alt","")))}" loading="lazy">'
               f'<figcaption>{render_text(m.get("caption",""))}</figcaption></figure>')
        html = html.replace(f'<div class="why-fig" data-fig-slot="{fid}"></div>', fig)
        html = html.replace(f'<div class="ex-fig" data-fig-slot="{fid}"></div>', fig)
    html = re.sub(r'<span class="figref" data-fig="([A-Za-z0-9_-]+)"></span>', "", html)
    html = re.sub(r'<div class="why-fig" data-fig-slot="[^"]*"></div>', "", html)
    html = re.sub(r'<div class="ex-fig" data-fig-slot="[^"]*"></div>', "", html)
    return html


def resolve_point_refs(html, depth, idx):
    def rep(m):
        pid = m.group(1)
        if pid in idx.points:
            t = idx.points[pid]["title"]
            return f'<a class="pt-link" href="{idx.rel(pid, depth)}">{esc(t)}</a>'
        return f'<span class="pt-link pt-broken">{esc(pid)}</span>'
    return re.sub(r'<span class="ptref" data-point="([a-z0-9-]+)"></span>', rep, html)


# --------------------------------------------------------------- sidebar / toc
def build_sidebar(idx, current=None, depth=0):
    parts = ['<nav class="side-nav" aria-label="年级目录">']
    for gid in idx.grade_order:
        g = idx.grades[gid]
        gkey = gid.split("-")[-1]          # grade-g03 → g03，侧边栏靠它判断当前年级
        open_ = "open" if (current and current.startswith(gkey)) else ""
        parts.append(f'<details class="side-group" {open_}>')
        parts.append(f'<summary><a href="{idx.rel_grade(gid, depth)}">{esc(g["title"])}</a></summary>')
        parts.append("<ul>")
        for t in g["terms"]:
            parts.append(f'<li class="side-term">{esc(t["label"])}</li>')
            for uid in t["units"] + t["activities"]:
                u = idx.units[uid]
                cur = ' aria-current="page"' if uid == current else ""
                # 还没有详细讲解的单元（纯目录 / 活动单元）淡化，读者一眼能看出哪些点得进去
                dry = "" if u.get("point_ids") else " data-empty=\"1\""
                parts.append(f'<li class="side-item"{dry}><a href="{idx.rel_unit(uid, depth)}"{cur}>'
                             f'{esc(u["title"])}</a></li>')
        parts.append("</ul></details>")
    parts.append("</nav>")
    return "".join(parts)


def build_toc(entries):
    if not entries:
        return ""
    lis = []
    for lvl, text, anchor in entries:
        lis.append(f'<li class="toc-l{lvl}"><a href="#{anchor}">{esc(text)}</a></li>')
    return '<nav class="toc" aria-label="本页内容"><h2 class="toc-h">本页内容</h2><ul>' + "".join(lis) + "</ul></nav>"


# --------------------------------------------------------------- pages
def emit_point(idx, pid, depth=2):
    p = idx.points[pid]
    tax = idx.tax
    scope_label = tax["scopes"].get(p.get("scope", "core"), "")
    meta_bits = [badge(p.get("domain", "")), badge(p.get("chapter", "")),
                 badge(f'课标：{p.get("verb_level","")}'), badge(scope_label, "badge badge-scope")]
    head = (f'<div class="point-meta">{"".join(meta_bits)}</div>'
            f'<p class="point-summary">{render_inline(p.get("summary",""))}</p>')
    overview = '<table class="kv"><tbody>'
    uid = idx.unit_of.get(pid)
    if uid:
        u = idx.units[uid]
        overview += (f'<tr><th>所在单元</th><td><a href="{idx.rel_unit(uid, depth)}">'
                     f'{esc(u["title"])}</a></td></tr>')
    overview += f'<tr><th>教材位置</th><td>{esc(p.get("lesson","")) or "—"}</td></tr>'
    if p.get("prerequisites"):
        lis = "、".join(f'<a href="{idx.rel(x, depth)}">{esc(idx.points[x]["title"])}</a>'
                       for x in p["prerequisites"])
        overview += f'<tr><th>前置知识</th><td>{lis}</td></tr>'
    if p.get("literacy"):
        overview += f'<tr><th>核心素养</th><td>{"".join(badge(x) for x in p["literacy"])}</td></tr>'
    overview += "</tbody></table>"

    body = [f'<div class="panel panel-h1"><h1 id="_top">{esc(p["title"])}'
            '</h1>' + head + '</div>',
            '<div class="panel panel-body">',
            f'<section class="block overview">{overview}</section>']
    body.append(render_standards(p, depth, idx))
    secs = render_sections(p, depth, idx, 2)
    if p.get("media"):
        # 图若未被 slot 引用，统一放在「为什么是这样」之前
        pass
    body.append(secs)
    body.append(render_related_block_tail(p, depth, idx))
    # 上下页
    prev, nxt = idx.prev_next(pid)
    if prev or nxt:
        body.append('<nav class="pager"><div>')
        if prev:
            body.append(f'<a class="pager-link" href="{idx.rel(prev, depth)}">'
                        f'<span class="pager-dir">上一页</span><span class="pager-t">{esc(idx.points[prev]["title"])}</span></a>')
        body.append("</div><div>")
        if nxt:
            body.append(f'<a class="pager-link pager-next" href="{idx.rel(nxt, depth)}">'
                        f'<span class="pager-dir">下一页</span><span class="pager-t">{esc(idx.points[nxt]["title"])}</span></a>')
        body.append("</div></nav>")
    body.append(f'<div class="done-bar"><label class="done-toggle">'
                f'<input type="checkbox" class="done-cb" data-id="{pid}"> 标记为已学</label></div>')
    body.append("</div>")

    main = "".join(body)
    main = resolve_fig_slots(main, p, depth, idx)
    main = resolve_point_refs(main, depth, idx)

    entries = [(2, s["title"], s["key"]) for s in tax["sections"] if s["key"] in p.get("sections", {})]
    extra = [(2, "课标要求", "std")] if p.get("standard_ids") else []
    return tmpl("base.html", page_vars(idx, {
        "TITLE": p["title"], "DESC": plain(p.get("summary", "")), "MAIN": main,
        "SIDEBAR": build_sidebar(idx, uid, depth),
        "TOC": build_toc(extra + entries),
        "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-point",
    }))


def render_related_block_tail(p, depth, idx):
    return ""


def emit_unit(idx, uid, depth=2):
    u = idx.units[uid]
    pids = [x for x in u.get("point_ids", []) if x in idx.points]
    rows = []
    for pid in sorted(pids):
        p = idx.points[pid]
        rows.append(f'<tr><th><a href="{idx.rel(pid, depth)}">{esc(p["title"])}</a></th>'
                    f'<td>{render_text(p.get("summary",""))}</td>'
                    f'<td>{badge(p.get("scope","core") and idx.tax["scopes"][p.get("scope","core")])}</td></tr>')
    overview = '<table class="kv"><tbody>'
    overview += f'<tr><th>课标领域</th><td>{esc(u.get("domain",""))}·{esc(u.get("chapter",""))}</td></tr>'
    overview += f'<tr><th>教材位置</th><td>{esc(term_label(u["term"]))}</td></tr>'
    if u.get("standard_ids"):
        txt = "；".join(esc(idx.std[s]["text"]) for s in u["standard_ids"] if s in idx.std)
        overview += f'<tr><th>课标要求</th><td class="std-text">{txt}</td></tr>'
    overview += "</tbody></table>"

    body = [f'<div class="panel panel-h1"><h1 id="_top">{esc(u["title"])}</h1></div>',
            '<div class="panel panel-body">',
            f'<section class="block overview">{overview}</section>']
    if rows:
        body.append('<section class="block"><h2>知识点一览</h2>'
                    '<table class="kv list"><tbody>' + "".join(rows) + "</tbody></table></section>")
    if pids:
        for pid in sorted(pids):
            p = idx.points[pid]
            body.append(f'<section class="point-embed" id="p-{pid}">')
            body.append(f'<h2 class="pe-h"><a href="{idx.rel(pid, depth)}">{esc(p["title"])}</a></h2>')
            body.append(f'<p class="pe-sum">{render_inline(p.get("summary",""))}</p>')
            body.append(render_sections(p, depth, idx, 3))
            body.append("</section>")
    else:
        body.append('<section class="block empty"><p class="note">'
                    '本单元为骨架条目，深度内容待补充。</p></section>')
    body.append("</div>")
    main = "".join(body)
    # 单元页内嵌多个知识点，逐个解析其图与引用
    for pid in sorted(pids):
        main = resolve_fig_slots(main, idx.points[pid], depth, idx)
    main = resolve_point_refs(main, depth, idx)

    entries = [(2, "知识点一览", "list")] if rows else []
    for pid in sorted(pids):
        p = idx.points[pid]
        entries.append((2, p["title"], f"p-{pid}"))
    return tmpl("base.html", page_vars(idx, {
        "TITLE": u["title"], "DESC": term_label(u["term"]) + "·" + u["title"],
        "MAIN": main, "SIDEBAR": build_sidebar(idx, uid, depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-unit",
    }))


def term_label(term):
    g = int(term[1:3])
    s = int(term[5])
    names = {1: "一年级", 2: "二年级", 3: "三年级", 4: "四年级", 5: "五年级", 6: "六年级"}
    return f"{names[g]}{'上' if s == 1 else '下'}册"


def emit_grade(idx, gid, depth=2):
    g = idx.grades[gid]
    seg_text = idx.tax["segments"][str(g["segment"])]
    n_units = sum(len(t["units"]) for t in g["terms"])
    head = ('<div class="panel panel-h1">'
            '<h1 id="_top">' + esc(g["title"]) + '</h1>'
            '<p class="grade-sub">' + esc(seg_text) + '&#12288;共 '
            + str(n_units) + ' 个教学单元</p></div>')
    body = [head, '<div class="panel panel-body">']
    entries = []
    for t in g["terms"]:
        body.append(f'<section class="block" id="{t["term"]}"><h2>{esc(t["label"])}</h2>')
        body.append('<table class="kv list"><tbody>')
        for uid in t["units"]:
            u = idx.units[uid]
            cnt = len(u.get("point_ids", []))
            body.append(f'<tr><th><a href="{idx.rel_unit(uid, depth)}">{esc(u["title"])}</a></th>'
                        f'<td>{esc(u.get("domain",""))}</td><td>{"已写 " + str(cnt) + " 篇" if cnt else "—"}</td></tr>')
        body.append("</tbody></table>")
        if t["activities"]:
            body.append('<h3>综合与实践</h3><ul class="items">')
            for uid in t["activities"]:
                u = idx.units[uid]
                body.append(f'<li><a href="{idx.rel_unit(uid, depth)}">{esc(u["title"])}</a></li>')
            body.append("</ul>")
        body.append("</section>")
        entries.append((2, t["label"], t["term"]))
    body.append("</div>")
    return tmpl("base.html", page_vars(idx, {
        "TITLE": g["title"], "DESC": f'{g["title"]}数学知识点',
        "MAIN": "".join(body), "SIDEBAR": build_sidebar(idx, gid.split("-")[-1], depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-grade",
    }))


def emit_home(idx, depth=0):
    tax = idx.tax
    n_points = len(idx.points)
    n_units = len([u for u in idx.units.values() if u.get("kind") == "unit"])
    stats = (f'<div class="stats">'
             f'<span><b>6</b> 年级</span><span><b>12</b> 册</span>'
             f'<span><b>{n_units}</b> 单元</span><span><b>{n_points}</b> 篇知识点</span>'
             f'<span class="stat-done">已学 <b class="done-count">0</b> 篇</span></div>')
    cards = []
    for gid in idx.grade_order:
        g = idx.grades[gid]
        cnt = 0
        for t in g["terms"]:
            for uid in t["units"] + t["activities"]:
                cnt += len(idx.units[uid].get("point_ids", []))
        cards.append(f'<a class="card grade-card" href="{idx.rel_grade(gid, depth)}">'
                     f'<span class="card-t">{esc(g["title"])}</span>'
                     f'<span class="card-d">{esc(tax["segments"][str(g["segment"])])}</span>'
                     f'<span class="card-m">{cnt} 篇知识点</span></a>')
    chips = "".join(f'<button class="chip" data-filter="domain:{esc(d)}">{esc(d)}</button>' for d in tax["domains"])
    items = []
    for pid in idx.point_order:
        p = idx.points[pid]
        uid = idx.unit_of.get(pid)
        uname = idx.units[uid]["title"] if uid else ""
        items.append(
            f'<a class="card point-card" href="{idx.rel(pid, depth)}" '
            f'data-domain="{esc(p.get("domain",""))}" data-chapter="{esc(p.get("chapter",""))}" '
            f'data-scope="{esc(p.get("scope","core"))}" data-id="{pid}">'
            f'<span class="card-t">{esc(p["title"])}</span>'
            f'<span class="card-d">{render_inline(p.get("summary",""))}</span>'
            f'<span class="card-m">{esc(uname)}&#12288;{badge(p.get("chapter",""))}</span></a>')
    main = (f'<div class="panel panel-h1"><h1 id="_top">{esc(tax["site_title"])}</h1>'
            f'<p class="home-sub">{esc(idx.site_title_sub)}</p>{stats}</div>'
            '<div class="panel panel-body">'
            f'<section class="block"><h2>按年级浏览</h2><div class="card-grid">{"".join(cards)}</div></section>'
            f'<section class="block"><h2>全部知识点</h2>'
            f'<div class="chips">{chips}<button class="chip chip-on" data-filter="all">全部</button></div>'
            f'<div class="card-grid" id="point-list">{"".join(items)}</div>'
            '<p class="note" id="empty-note" hidden>没有匹配的知识点</p></section>'
            "</div>")
    return tmpl("base.html", page_vars(idx, {
        "TITLE": tax["site_title"], "TITLE_SUFFIX": "",
        "DESC": idx.site_title_sub, "MAIN": main,
        "SIDEBAR": build_sidebar(idx, None, depth), "TOC": "",
        "ROOT": ".", "DEPTH": "0", "BODY_CLASS": "page-home",
    }))


def emit_404(idx, depth=0):
    main = ('<div class="panel panel-h1"><h1 id="_top">页面不存在</h1></div>'
            '<div class="panel panel-body"><section class="block">'
            '<p>这个地址下还没有内容。<a href="index.html">回到首页</a>。</p>'
            "</section></div>")
    return tmpl("base.html", page_vars(idx, {
        "TITLE": "页面不存在", "DESC": "", "MAIN": main,
        "SIDEBAR": build_sidebar(idx, None, depth), "TOC": "",
        "ROOT": ".", "DEPTH": "0", "BODY_CLASS": "page-404",
    }))


def page_vars(idx, v):
    v.setdefault("SITE_TITLE", idx.tax["site_title"])
    v.setdefault("TITLE_SUFFIX", " · " + idx.tax["site_title"])
    v.setdefault("TITLE_SUFFIX", " · " + idx.tax["site_title"])
    v.setdefault("THEME_BOOT", (A / "js" / "theme-boot.js").read_text(encoding="utf-8"))
    v.setdefault("HEAD_EXTRA", "")
    v.setdefault("SCRIPTS", (f'<script src="{v["ROOT"]}/assets/js/search-index.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/katex/katex.min.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/katex-render.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/theme.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/drawer.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/toc.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/search.js"></script>\n'
                             f'<script src="{v["ROOT"]}/assets/js/progress.js"></script>'))
    v.setdefault("SEARCH_MODAL", (T / "partials" / "search-modal.html").read_text(encoding="utf-8"))
    return v


# --------------------------------------------------------------- search index
def build_search_index(idx):
    arr = []
    for pid in idx.point_order:
        p = idx.points[pid]
        body = json.dumps(p.get("sections", {}), ensure_ascii=False)
        body = re.sub(r"[\\\"]", " ", body)
        arr.append({
            "ty": "p", "id": pid, "t": p["title"], "s": p.get("summary", ""),
            "k": p.get("keywords", []), "d": p.get("domain", ""), "c": p.get("chapter", ""),
            "b": body[:1200],
        })
    # 单元页与年级页也进索引：它们是站内的两级导航主干，搜不到会让人以为没写
    for uid in idx.unit_order:
        u = idx.units[uid]
        kids = [idx.points[x]["title"] for x in u.get("point_ids", []) if x in idx.points]
        arr.append({
            "ty": "u", "id": uid, "t": u["title"],
            "s": f'{u.get("domain","")}·{u.get("chapter","")}',
            "k": [], "d": u.get("domain", ""), "c": u.get("chapter", ""),
            "b": " ".join(kids) if kids else u.get("title", ""),
        })
    for gid in idx.grade_order:
        g = idx.grades[gid]
        names = [idx.units[u]["title"] for t in g["terms"] for u in t["units"] + t["activities"]]
        arr.append({
            "ty": "g", "id": gid, "t": g["title"],
            "s": idx.tax["segments"][str(g["segment"])], "k": [],
            "d": "", "c": "", "b": " ".join(names),
        })
    js = "window.__SEARCH_INDEX__=" + json.dumps(arr, ensure_ascii=False) + ";"
    return js.replace("</", "<\\/")


# --------------------------------------------------------------- build
def safe_rebuild():
    if D.exists():
        if not D.resolve().is_relative_to(ROOT.resolve()):
            raise SystemExit("dist 不在项目内，拒绝删除")
        shutil.rmtree(D)
    D.mkdir(parents=True)


def copy_assets():
    dst = D / "assets"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(A, dst)
    # 拷贝 SVG
    svgs = list((C / "media").glob("*.svg"))
    sdir = dst / "svg"
    sdir.mkdir(parents=True, exist_ok=True)
    for s in svgs:
        shutil.copy2(s, sdir / s.name)


def build():
    tax, site, std, grades, units, points = load_all()
    validate(tax, std, grades, units, points)
    if errors:
        print(f"校验失败：{len(errors)} 个错误")
        for e in errors[:60]:
            print("  ✗", e)
        if len(errors) > 60:
            print(f"  … 另有 {len(errors)-60} 条")
        return 1
    idx = Index(tax, std, grades, units, points)
    idx.site_title_sub = site.get("subtitle", "")

    safe_rebuild()
    copy_assets()

    write(D / "index.html", emit_home(idx, 0))
    write(D / "404.html", emit_404(idx, 0))
    for gid in idx.grade_order:
        write(D / "grades" / gid / "index.html", emit_grade(idx, gid, 2))
    for uid in idx.unit_order:
        write(D / "units" / uid / "index.html", emit_unit(idx, uid, 2))
    for pid in idx.point_order:
        write(D / "points" / pid / "index.html", emit_point(idx, pid, 2))
    write(D / "assets" / "js" / "search-index.js", build_search_index(idx))

    if warnings:
        print(f"警告 {len(warnings)} 条：")
        for w in warnings[:20]:
            print("  !", w)
    print(f"构建完成：{len(idx.point_order)} 篇知识点 / {len(idx.unit_order)} 个单元"
          f" / {len(idx.grade_order)} 个年级 → dist/")
    return verify_output()


def verify_output():
    """产物自检：断网双击能开、公式不漏、板块不残。任一不过就返回非零，让 CI/人工都能立刻发现。"""
    bad = []
    sec_want = [s["title"] for s in read_json(C / "taxonomy.json")["sections"]]
    for fp in sorted(D.rglob("*.html")):
        base = str(fp.parent)
        html = fp.read_text(encoding="utf-8")
        rel = str(fp.relative_to(D)).replace("\\", "/")
        for u in re.findall(r'(?:href|src)="([^"]+)"', html):
            if u.startswith(("http", "#", "mailto:", "data:", "javascript:")):
                continue
            p = u.split("#")[0]
            if p and not (pathlib.Path(base) / p).exists():
                bad.append(f"{rel}: 死链 {u}")
        if "{{" in html and re.search(r"\{\{[A-Z0-9_]+\}\}", html):
            bad.append(f"{rel}: 模板变量未替换")
        txt = re.sub(r"<[^>]+>", "", html)
        for w in FORBIDDEN:
            if w in txt:
                bad.append(f"{rel}: 出现禁用词「{w}」")
        for m in re.findall(r"\$[^$\n]{1,80}\$", txt):
            bad.append(f"{rel}: 公式未渲染 {m[:30]}")
        if "/points/" in rel:
            hs = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)]
            for t in sec_want:
                if t not in hs:
                    bad.append(f"{rel}: 缺板块「{t}」")
    if bad:
        print(f"✗ 产物自检 {len(bad)} 条不通过：")
        for b in bad[:30]:
            print("  !", b)
        return 1
    print("✓ 产物自检通过：链接全通、公式全渲染、九板块齐全、无禁用词")
    return 0


def check():
    tax, site, std, grades, units, points = load_all()
    validate(tax, std, grades, units, points)
    if errors:
        print(f"✗ {len(errors)} 个错误")
        for e in errors[:80]:
            print("  ✗", e)
        if len(errors) > 80:
            print(f"  … 另有 {len(errors)-80} 条")
        return 1
    print(f"✓ 校验通过：{len(points)} 篇知识点 / {len(units)} 个单元 / {len(std)} 条课标条目")
    if warnings:
        for w in warnings[:20]:
            print("  !", w)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(check() if "--check" in sys.argv else build())
