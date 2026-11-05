# -*- coding: utf-8 -*-
"""小学数学知识点图谱 — 静态站构建脚本。
仅依赖 Python 3 标准库。用法：
    python build.py          全量构建
    python build.py --check  只做校验，不产出
"""
import json
import os
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

# 关联知识点的三类：学之前要先会的 / 学完之后接着用的 / 常与本文同题出现的
REL_KINDS = ("前置", "后续", "常一起考")
# 反向补链时类别的翻转：A 的「后续」= B 的「前置」
REL_FLIP = {"前置": "后续", "后续": "前置", "常一起考": "常一起考"}


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
    mod = read_json(C / "modules.json")
    points = {p.stem: read_json(p) for p in sorted((C / "points").glob("*.json"))}
    tb = read_json(C / "textbook.json")
    guides = read_json(C / "guides.json").get("guides", {})
    return tax, site, std, mod, points, tb, guides

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


# 渲染期上下文：当前页面的 depth 与知识点索引，供 [[id]] 生成站内链接
RENDER_CTX = {"depth": 2, "idx": None}


def set_render_ctx(idx, depth):
    RENDER_CTX["idx"] = idx
    RENDER_CTX["depth"] = depth


def _point_link(m):
    """把 [[m2-01-17]] 转成指向该知识点页的链接，链接文字是知识点名称。

    正文里用短 ID 更易读，而 idx.points 的键是完整 slug（含英文后缀），
    这里做一次短 ID → slug 的映射。匹配不到或不唯一时退回纯文本，不生成错链接。
    """
    short = m.group(1)
    idx = RENDER_CTX.get("idx")
    if idx is None:
        return f'<span class="ptref-dead">{esc(short)}</span>'
    hits = [k for k in idx.points if k == short or k.startswith(short + "-")]
    if len(hits) != 1:
        return f'<span class="ptref-dead">{esc(short)}</span>'
    pid = hits[0]
    title = idx.points[pid]["title"]
    href = idx.rel(pid, RENDER_CTX["depth"])
    return f'<a class="ptref" href="{href}">{esc(title)}</a>'


def md_inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`\n]+)`", r'<code class="inline">\1</code>', s)
    s = re.sub(r"@@([A-Za-z0-9_-]+)", r'<span class="figref" data-fig="\1"></span>', s)
    s = re.sub(r"@point:([a-z0-9-]+)", r'<span class="ptref" data-point="\1"></span>', s)
    # [[知识点短 ID]] → 站点内链接（文字是知识点名称，不是 id）
    s = re.sub(r"\[\[(m[1-4]-\d{2}-\d{2})\]\]", _point_link, s)
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
def validate(tax, std, mod, points, tb):
    sec_keys = [s["key"] for s in tax["sections"]]
    domains = set(tax["domains"])
    scenes = set(tax["scenes"])
    modules_ = {m["id"]: m for m in mod["modules"]}
    topics_ = {t["id"]: t for t in mod["topics"]}
    plan = {p for t in mod["topics"] for p in t["points"]}
    # 清单展开后的顺序（判定「前置/后续」先后用）：先 topics 顺序，再节内 points 顺序
    plan_order = [p for t in mod["topics"] for p in t["points"]]
    scopes = set(tax["scopes"])
    literacy = set(tax["literacy"])

    for pid, p in points.items():
        ctx = f"points/{pid}.json"
        if p.get("id") != pid:
            err(f"{ctx}: 文件名字与 id 不一致（{p.get('id')}）")
        if not ID_RE.match(pid):
            err(f"{ctx}: id 不满足 [a-z0-9-] 命名规则")
        # 归属：id 前两段必须是一个已定义的节，第三段是节内序号
        m = re.match(r"^(m\d-\d\d)-(\d\d)-", pid)
        if not m:
            err(f"{ctx}: id 不符合 m{{模块}}-{{节}}-{{序号}}-{{slug}}")
        else:
            tid = m.group(1)
            if tid not in topics_:
                err(f"{ctx}: 节 {tid} 未在 modules.json 中定义")
            elif pid not in topics_[tid]["points"]:
                err(f"{ctx}: 节 {tid} 的 points 清单里没有这个 id")
            if p.get("topic") and p["topic"] != tid:
                err(f"{ctx}: topic 字段与 id 前缀不一致（{p.get('topic')} ≠ {tid}）")
            if p.get("module") and p["module"] != topics_.get(tid, {}).get("module"):
                err(f"{ctx}: module 字段与所属节不一致")
        for f in ("title", "summary", "domain", "module", "topic", "scope", "verb_level"):
            if not p.get(f):
                err(f"{ctx}: 缺字段 {f}")
        if p.get("domain") and p["domain"] not in domains:
            err(f"{ctx}: domain「{p['domain']}」不在枚举内")
        if p.get("scope") and p["scope"] not in scopes:
            err(f"{ctx}: scope「{p['scope']}」不在枚举内")
        for x in p.get("literacy", []):
            if x not in literacy:
                err(f"{ctx}: 核心素养「{x}」不在枚举内")
        for sid in p.get("standard_ids", []):
            if sid not in std:
                err(f"{ctx}: 课标条目 {sid} 不存在")
        for rid in p.get("prerequisites", []):
            if rid not in plan:
                err(f"{ctx}: 前置知识点 {rid} 不在知识点清单内")

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
                has_kind = any(r.get("kind") for r in v)
                for r in v:
                    rid = r.get("id")
                    if rid.startswith("ext:"):
                        # ext: = 站外的知识方向（如高中衔接），只作文字提示，不生成链接
                        continue
                    if rid not in plan:
                        err(f"{ctx}.{k}: 关联 {rid} 不在知识点清单内")
                        continue
                    if not has_kind:
                        continue
                    rk = r.get("kind")
                    if rk not in REL_KINDS:
                        err(f"{ctx}.{k}: 关联 {rid} 的 kind「{rk}」不合法（只能是 {REL_KINDS}）")
                        continue
                    # 顺序校验：前置必须排在本文之前，后续必须排在本文之后
                    if rk == "前置" and plan_order.index(rid) > plan_order.index(pid):
                        err(f"{ctx}.{k}: 「前置」{rid} 排在本文之后（前置必须先学）")
                    if rk == "后续" and plan_order.index(rid) < plan_order.index(pid):
                        err(f"{ctx}.{k}: 「后续」{rid} 排在本文之前（后续必须后学）")
                if has_kind:
                    kinds = {r.get("kind") for r in v}
                    for rk in REL_KINDS:
                        if rk not in kinds:
                            err(f"{ctx}.{k}: 关联知识点缺「{rk}」类")

        # 教材定位：必须有，且册次/单元能对得上 content/textbook.json
        ref = p.get("textbook_ref")
        if not ref:
            err(f"{ctx}: 缺 textbook_ref（教材定位）")
        else:
            for loc in ref.get("locations", []):
                vol = tb["volumes"].get(loc.get("volume"))
                if not vol:
                    err(f"{ctx}: 教材册次 {loc.get('volume')} 不在 textbook.json 内")
                    continue
                for u in loc.get("units", []):
                    if vol["units"].get(str(u.get("no"))) != u.get("name"):
                        err(f"{ctx}: 教材单元 {loc['volume']} 第{u.get('no')}单元 标成「{u.get('name')}」与教材表不符")
                for sp in loc.get("special", []):
                    pool = vol["practical"] if sp.get("kind") == "综合与实践" else vol["corner"]
                    if sp.get("name") not in pool:
                        err(f"{ctx}: 教材栏目 {sp.get('kind')}·{sp.get('name')} 不在 {loc['volume']} 内")
            if not ref.get("note"):
                err(f"{ctx}: textbook_ref 缺 note（要说明与教材的对应关系）")

        # LaTeX 禁用「反斜杠 + 空格」写法（KaTeX 会解析失败）
        blob_s = json.dumps(p.get("sections", {}), ensure_ascii=False)
        for mm in re.finditer(r"\\\\\s", blob_s):
            err(f"{ctx}: LaTeX 出现「反斜杠+空格」写法（KaTeX 会报错）→ {blob_s[max(0,mm.start()-30):mm.start()+12]}")

        # 禁用词
        blob = blob_s
        for w in tax["forbidden_words"]:
            if w in blob:
                err(f"{ctx}: 命中禁用词「{w}」（小学阶段不使用「证明」类表述）")
        for w in ("综上所述", "值得注意", "不难发现", "众所周知", "由此可见", "总而言之", "不难看出"):
            if w in blob:
                err(f"{ctx}: 命中模板腔词「{w}」（要写小学生能听懂的大白话）")
        # 人民币 $ 误用（先剥离数学公式，避免误伤 $1\,\text{cm}^2$ 这类写法）
        blob_nomath = re.sub(r"\$[^$\n]+\$", "\x00", blob)
        for m2 in re.finditer(r"(?<!\\)\$\d", blob_nomath):
            err(f"{ctx}: 疑似用 $ 表示人民币（应写「元」或 ¥）→ {blob_nomath[max(0,m2.start()-15):m2.start()+8]}")
        # 圆锥体积漏 1/3
        if "圆锥" in p.get("title", "") and re.search(r"(?<![\d/])V\s*=\s*Sh(?!\s*/)", blob):
            err(f"{ctx}: 圆锥体积疑似漏 1/3，请查 _reference/formula-audit.md A1")

    # 模块体系自身的完整性：节必须有模块、模块必须有节、节内序号必须从 01 连续
    for t in mod["topics"]:
        if t["module"] not in modules_:
            err(f"modules.json: 节 {t['id']} 属于不存在的模块 {t['module']}")
        nums = [int(p.split("-")[2]) for p in t["points"]]
        if sorted(nums) != list(range(1, len(nums) + 1)):
            err(f"节 {t['id']}: 知识点序号不连续 → {sorted(nums)}")
        for sid in t.get("standard_ids", []):
            if sid not in std:
                err(f"modules.json: 节 {t['id']} 引用了不存在的课标条目 {sid}")
    for mid in modules_:
        if not any(t["module"] == mid for t in mod["topics"]):
            err(f"modules.json: 模块 {mid} 下面没有节")

    # 每篇已写内容都要能在清单里找到归属（反向检查）
    missing = set(points) - plan
    if missing:
        err(f"以下篇目未登记进知识点清单: {sorted(missing)}")


# --------------------------------------------------------------- index
class Index:
    """按「模块 → 节 → 知识点」组织。清单里已写和待写都在，只是待写的不出现在页面链接里。"""

    def __init__(self, tax, std, mod, points, guides=None, tb=None):
        self.tax, self.std, self.mod, self.points = tax, std, mod, points
        self.guides = guides or {}
        self.tb = tb or {}
        self.modules = {m["id"]: m for m in mod["modules"]}
        self.module_order = [m["id"] for m in mod["modules"]]
        self.topics = {t["id"]: t for t in mod["topics"]}
        self.topic_order = [t["id"] for t in mod["topics"]]
        # 清单全量（含待写）；已写篇目按清单顺序排，字典序不等于清单顺序时以清单为准
        self.plan = [p for t in mod["topics"] for p in t["points"]]
        self.point_order = [p for p in self.plan if p in points]
        self.module_of, self.topic_of = {}, {}
        for tid in self.topic_order:
            for pid in self.topics[tid]["points"]:
                self.topic_of[pid] = tid
                self.module_of[pid] = self.topics[tid]["module"]
        self.incoming = {pid: [] for pid in self.point_order}
        for pid, p in points.items():
            for r in p.get("sections", {}).get("related", []):
                if r.get("id") in self.incoming:
                    # 带 kind 的条目反向补链时翻转类别（A 的「后续」= B 的「前置」）
                    kind = r.get("kind")
                    flipped = REL_FLIP.get(kind) if kind else None
                    self.incoming[r["id"]].append((pid, r.get("note", ""), flipped))

    def topic_points(self, tid):
        return [p for p in self.topics[tid]["points"] if p in self.points]

    def topic_pending(self, tid):
        return [p for p in self.topics[tid]["points"] if p not in self.points]

    def module_topics(self, mid):
        return [t for t in self.topic_order if self.topics[t]["module"] == mid]

    def module_count(self, mid):
        return sum(len(self.topic_points(t)) for t in self.module_topics(mid))

    def prev_next(self, pid):
        i = self.point_order.index(pid)
        return (self.point_order[i - 1] if i > 0 else None,
                self.point_order[i + 1] if i < len(self.point_order) - 1 else None)

    def root_for(self, depth):
        return "." if depth == 0 else "/".join([".."] * depth)

    def rel(self, pid, depth):
        return f"{self.root_for(depth)}/points/{pid}/index.html"

    def rel_topic(self, tid, depth):
        return f"{self.root_for(depth)}/t/{tid}/index.html"

    def rel_module(self, mid, depth):
        return f"{self.root_for(depth)}/{mid}/index.html"

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


def render_textbook(p, depth, idx):
    """教材定位区块：册次 · 第X章 章名 · X.Y 节名 + 与教材的对应说明。

    定位精确到人教版教材的节，读者据此能直接翻到课本的那一节。
    """
    ref = p.get("textbook_ref")
    if not ref:
        return ""
    tb = idx.tb
    parts = ['<section class="block textbook"><h2>教材定位</h2>']
    segs = []
    for loc in ref.get("locations", []):
        vol = tb["volumes"].get(loc.get("volume"))
        if not vol:
            continue
        seg = [f'<span class="tb-vol">{esc(vol["label"])}</span>']
        for u in loc.get("units", []):
            seg.append(f'<span class="tb-ch">第{esc(str(u["no"]))}单元 {esc(u["name"])}</span>')
        for sp in loc.get("special", []):
            seg.append(f'<span class="tb-ch">{esc(sp.get("kind",""))}·{esc(sp.get("name",""))}</span>')
        segs.append('<span class="tb-line">' + "".join(seg) + "</span>")
    if not segs:
        return ""
    parts.append(f'<p class="tb-edition">{esc(tb["publisher"])}《{esc(tb["edition"])}》</p>')
    parts.append('<div class="tb-lines">' + "".join(segs) + "</div>")
    if ref.get("note"):
        parts.append(f'<p class="tb-note">{render_inline(ref["note"])}</p>')
    parts.append("</section>")
    return "".join(parts)


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
    """关联知识点。

    新格式：每条带 kind（前置/后续/常一起考），按三类分组渲染。
    反向补链（别的篇目指向本文）按 REL_FLIP 翻转类别后并入对应分组：
    A 的「后续」= B 的「前置」。
    旧格式：只有 {id, note}，渲染成单组「本知识点指向」——向后兼容历史篇目。
    """
    out_parts = []
    outs = p.get("sections", {}).get("related", [])
    has_kind = any(r.get("kind") for r in outs)
    out_ids = {r["id"] for r in outs}

    # 反向补链：(来源 id, 说明, 翻转后的类别)；来源已在本页 outgoing 里则不重复展示
    inc = [(pid, note, fl) for pid, note, fl in idx.incoming.get(p["id"], [])
           if pid not in out_ids]

    def rel_items(pairs):
        lis = []
        for rid, note in pairs:
            if rid.startswith("ext:"):
                # ext: = 站外的知识方向（如高中衔接），只作文字提示，不生成链接
                lis.append(f'<li><span class="rel-ext">{esc(rid[4:])}</span>'
                           f'<span class="rel-note">{render_inline(note)}</span></li>')
                continue
            t = idx.points[rid]["title"]
            lis.append(f'<li><a href="{idx.rel(rid, depth)}">{esc(t)}</a>'
                       f'<span class="rel-note">{render_inline(note)}</span></li>')
        return lis

    legacy_out = []
    if has_kind:
        groups = {k: [] for k in REL_KINDS}
        for r in outs:
            # kind 非法时校验器会报错，但构建不能崩——归到 legacy 组
            k = r.get("kind")
            if k in groups:
                groups[k].append((r["id"], r.get("note", "")))
            else:
                legacy_out.append((r["id"], r.get("note", "")))
        # 旧格式篇目指过来的链接没有类别，单列一组，不丢
        legacy = [(pid, note) for pid, note, fl in inc if fl not in groups]
        for pid, note, fl in inc:
            if fl in groups:
                groups[fl].append((pid, note))
        for kind in REL_KINDS:
            lis = rel_items(groups[kind])
            if not lis:
                continue
            out_parts.append(
                f'<div class="rel-group rel-{esc(kind)}"><p class="rel-label">'
                f'<span class="rel-tag">{esc(kind)}</span></p><ul>' + "".join(lis) + "</ul></div>")
        legacy = legacy + legacy_out
        if legacy:
            out_parts.append('<div class="rel-group"><p class="rel-label">指向本知识点</p><ul>'
                             + "".join(rel_items(legacy)) + "</ul></div>")
    else:
        if outs:
            out_parts.append('<div class="rel-group"><p class="rel-label">本知识点指向</p><ul>'
                             + "".join(rel_items((r["id"], r.get("note", "")) for r in outs))
                             + "</ul></div>")
        # 旧格式页面：所有反向补链都放进「指向本知识点」
        if inc:
            out_parts.append('<div class="rel-group"><p class="rel-label">指向本知识点</p><ul>'
                             + "".join(rel_items((pid, note) for pid, note, _ in inc))
                             + "</ul></div>")
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
        # 同一张图可能被「为什么是这样」和「例题」同时引用，只保留第一个位置
        slot = (r'<div class="(?:why-fig|ex-fig)" data-fig-slot="'
                + re.escape(fid) + r'"></div>')
        html = re.sub(slot, lambda _m: fig, html, count=1)
        html = re.sub(slot, "", html)
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
    """四模块折叠树。当前模块展开；当前主题再展开它下面的知识点。"""
    cur_topic = idx.topic_of.get(current) or (current if current in idx.topics else None)
    cur_mod = idx.module_of.get(current) or (current if current in idx.modules else None)
    # 主题页 / 节 id 也要能定位到所属模块，否则侧栏不展开
    if cur_mod is None and cur_topic:
        cur_mod = cur_topic.split("-")[0]
    parts = ['<nav class="side-nav" aria-label="模块目录">']
    for mid in idx.module_order:
        m = idx.modules[mid]
        open_ = "open" if cur_mod == mid else ""
        n = idx.module_count(mid)
        parts.append(f'<details class="side-group" {open_}>')
        parts.append(f'<summary><a href="{idx.rel_module(mid, depth)}">{esc(m["title"])}</a>'
                     f'<span class="side-n">{n}</span></summary>')
        parts.append("<ul>")
        for tid in idx.module_topics(mid):
            t = idx.topics[tid]
            is_cur = (tid == cur_topic)
            curc = ' aria-current="page"' if is_cur else ""
            dry = "" if idx.topic_points(tid) else ' data-empty="1"'
            parts.append(f'<li class="side-term"{dry}><a href="{idx.rel_topic(tid, depth)}"'
                         f'{curc}>{esc(t["title"])}</a></li>')
            if is_cur:
                parts.append('<li><ul class="side-sub">')
                for pid in idx.topic_points(tid):
                    c = ' aria-current="page"' if pid == current else ""
                    parts.append(f'<li class="side-item"><a href="{idx.rel(pid, depth)}"{c}>'
                                 f'{esc(idx.points[pid]["title"])}</a></li>')
                parts.append("</ul></li>")
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
    set_render_ctx(idx, depth)
    p = idx.points[pid]
    tax = idx.tax
    scope_label = tax["scopes"].get(p.get("scope", "core"), "")
    tid = idx.topic_of.get(pid)
    tname = idx.topics[tid]["title"] if tid else ""
    meta_bits = [badge(p.get("domain", "")), badge(tname),
                 badge(f'课标：{p.get("verb_level","")}'), badge(scope_label, "badge badge-scope")]
    head = (f'<div class="point-meta">{"".join(meta_bits)}</div>'
            f'<p class="point-summary">{render_inline(p.get("summary",""))}</p>')
    overview = '<table class="kv"><tbody>'
    if tid:
        mid = idx.topics[tid]["module"]
        overview += (f'<tr><th>所属主题</th><td><a href="{idx.rel_topic(tid, depth)}">'
                     f'{esc(idx.topics[tid]["title"])}</a></td></tr>'
                     f'<tr><th>所属模块</th><td><a href="{idx.rel_module(mid, depth)}">'
                     f'{esc(idx.modules[mid]["title"])}</a></td></tr>')
    if p.get("segment"):
        overview += (f'<tr><th>课标学段</th><td>'
                     f'{esc(idx.tax["segments"][str(p["segment"])])}</td></tr>')
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
    body.append(render_textbook(p, depth, idx))
    body.append(render_standards(p, depth, idx))
    secs = render_sections(p, depth, idx, 2)
    if p.get("media"):
        # 图若未被正文 slot 引用，统一放在「为什么是这样」之前
        unused = []
        for m in p["media"]:
            if f'data-fig-slot="{m["id"]}"' in secs:
                continue
            src = f"{idx.root_for(depth)}/assets/svg/{m['file']}"
            unused.append(
                f'<figure class="fig"><img src="{src}" '
                f'width="{m.get("width",480)}" height="{m.get("height",260)}" '
                f'alt="{attr(fig_alt(m.get("alt","")))}" loading="lazy">'
                f'<figcaption>{render_text(m.get("caption",""))}</figcaption></figure>')
        if unused:
            figs = "".join(unused)
            marker = '<section class="block sec-why"'
            secs = secs.replace(marker, figs + marker, 1) if marker in secs else secs + figs
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
        "SIDEBAR": build_sidebar(idx, pid, depth),
        "TOC": build_toc(extra + entries),
        "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-point",
    }))


def render_related_block_tail(p, depth, idx):
    return ""


def emit_topic(idx, tid, depth=2):
    set_render_ctx(idx, depth)
    """主题页：这一节讲什么、对应课标哪几条、下面有哪些知识点。"""
    t = idx.topics[tid]
    mid = t["module"]
    m = idx.modules[mid]
    written = idx.topic_points(tid)

    overview = '<table class="kv"><tbody>'
    overview += (f'<tr><th>所属模块</th><td><a href="{idx.rel_module(mid, depth)}">'
                 f'{esc(m["title"])}</a></td></tr>')
    segs = sorted({idx.points[p].get("segment") for p in written if idx.points[p].get("segment")})
    if segs:
        overview += (f'<tr><th>课标学段</th><td>'
                     f'{"、".join(esc(idx.tax["segments"][str(x)]) for x in segs)}</td></tr>')
    overview += f'<tr><th>知识点</th><td>{len(written)} 篇</td></tr>'
    if t.get("standard_ids"):
        txt = "；".join(esc(idx.std[x]["text"]) for x in t["standard_ids"] if x in idx.std)
        overview += (f'<tr><th>课标要求</th><td class="std-text">'
                     f'<details class="std-fold"><summary>共 {len(t["standard_ids"])} 条，点开查看</summary>'
                     f'{txt}</details></td></tr>')
    overview += "</tbody></table>"

    body = [f'<div class="panel panel-h1"><h1 id="_top">{esc(t["title"])}</h1>'
            f'<p class="grade-sub">{esc(t["desc"])}</p></div>',
            '<div class="panel panel-body">',
            f'<section class="block overview">{overview}</section>']

    if written:
        body.append('<section class="block"><h2 id="list">知识点</h2><ul class="topic-list">')
        for pid in written:
            p = idx.points[pid]
            body.append(
                f'<li><a href="{idx.rel(pid, depth)}">'
                f'<span class="tl-t">{esc(p["title"])}</span>'
                f'<span class="tl-s">{render_inline(p.get("summary",""))}</span>'
                f'<span class="tl-m">{badge(p.get("verb_level",""))}'
                f'{badge(idx.tax["scopes"].get(p.get("scope","core"),""))}</span></a></li>')
        body.append("</ul></section>")
    body.append("</div>")

    entries = [(2, "知识点", "list")] if written else []
    return tmpl("base.html", page_vars(idx, {
        "TITLE": t["title"], "DESC": plain(t["desc"]),
        "MAIN": "".join(body), "SIDEBAR": build_sidebar(idx, tid, depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-topic",
    }))



def render_guide(idx, mid, depth):
    """领域导读板块。

    结构参照参考站「部分导读」：引言定位 → 「主题/内容/在后面哪里用」表格
    → 「考试里怎么考」→ 「怎么读这一部分」。

    表格的「内容」列由各主题的知识点标题自动汇总（不手写，避免与正文脱节）；
    「在后面哪里用」列里的 [[知识点短ID]] 渲染成站内链接。
    """
    g = idx.guides.get(mid)
    if not g:
        return ""
    rows = []
    for r in g.get("rows", []):
        tid = r.get("topic")
        t = idx.topics.get(tid)
        if not t:
            continue
        # 「内容」列：自动汇总该主题下所有知识点的标题
        titles = [idx.points[p]["title"] for p in idx.topic_points(tid)]
        content = "、".join(titles) if titles else "—"
        where = render_inline(r.get("where", ""))
        rows.append(
            f'<tr><th scope="row"><a href="{idx.rel_topic(tid, depth)}">{esc(t["title"])}</a></th>'
            f'<td class="gd-content">{esc(content)}</td>'
            f'<td class="gd-where">{where}</td></tr>')
    if not rows:
        return ""
    parts = ['<section class="block guide" id="guide"><h2>导读</h2>']
    if g.get("intro"):
        parts.append(f'<p class="gd-intro">{render_inline(g["intro"])}</p>')
    parts.append('<div class="gd-table-wrap"><table class="gd-table">'
                 '<thead><tr><th>主题</th><th>内容</th><th>在后面哪里用</th></tr></thead>'
                 '<tbody>' + "".join(rows) + '</tbody></table></div>')
    if g.get("exam_hint"):
        parts.append(f'<h3>考试里怎么考</h3><p class="gd-hint">{render_inline(g["exam_hint"])}</p>')
    if g.get("read_hint"):
        parts.append(f'<h3>怎么读这一部分</h3><p class="gd-hint">{render_inline(g["read_hint"])}</p>')
    parts.append("</section>")
    return "".join(parts)


def emit_module(idx, mid, depth=1):
    set_render_ctx(idx, depth)
    """模块页：这个模块由哪些主题组成。"""
    m = idx.modules[mid]
    tids = idx.module_topics(mid)
    total = idx.module_count(mid)
    head = ('<div class="panel panel-h1">'
            f'<p class="mod-kicker">模块 {m["no"]}</p>'
            f'<h1 id="_top">{esc(m["title"])}</h1>'
            f'<p class="grade-sub">{esc(m["desc"])}</p></div>')
    body = [head]
    guide = render_guide(idx, mid, depth)
    if guide:
        body.append('<div class="panel panel-body">')
        body.append(guide)
        body.append("</div>")
    body.append('<div class="panel panel-body">')
    body.append('<section class="block overview"><table class="kv"><tbody>'
                f'<tr><th>课标主题</th><td>{esc(m.get("strand",""))}</td></tr>'
                f'<tr><th>主题数</th><td>{len(tids)} 个</td></tr>'
                f'<tr><th>知识点</th><td>{total} 篇</td></tr>'
                '</tbody></table></section>')
    entries = []
    if guide:
        entries.append((2, "导读", "guide"))
    for tid in tids:
        t = idx.topics[tid]
        written = idx.topic_points(tid)
        body.append(f'<section class="block" id="{tid}">'
                    f'<h2><a href="{idx.rel_topic(tid, depth)}">{esc(t["title"])}</a>'
                    f'<span class="tg-n">{len(written)}</span></h2>'
                    f'<p class="mod-desc">{esc(t["desc"])}</p>')
        if written:
            body.append('<ul class="items">')
            for pid in written:
                body.append(f'<li><a href="{idx.rel(pid, depth)}">'
                            f'{esc(idx.points[pid]["title"])}</a></li>')
            body.append("</ul>")
        body.append("</section>")
        entries.append((2, t["title"], tid))
    body.append("</div>")
    return tmpl("base.html", page_vars(idx, {
        "TITLE": m["title"], "DESC": plain(m["desc"]),
        "MAIN": "".join(body), "SIDEBAR": build_sidebar(idx, mid, depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-module",
    }))

def emit_home(idx, depth=0):
    set_render_ctx(idx, depth)
    tax = idx.tax
    n_written = len(idx.point_order)
    n_topics = len(idx.topic_order)
    stats = (f'<div class="stats">'
             f'<span><b>{len(idx.module_order)}</b> 大模块</span>'
             f'<span><b>{n_topics}</b> 个主题</span>'
             f'<span><b>{n_written}</b> 篇知识点</span>'
             f'<span class="stat-done">已学 <b class="done-count">0</b> 篇</span></div>')

    cards = []
    for mid in idx.module_order:
        m = idx.modules[mid]
        tids = idx.module_topics(mid)
        cards.append(f'<a class="card mod-card" href="{idx.rel_module(mid, depth)}">'
                     f'<span class="mod-no">模块 {m["no"]}</span>'
                     f'<span class="card-t">{esc(m["title"])}</span>'
                     f'<span class="card-d">{esc(m["desc"])}</span>'
                     f'<span class="card-m">{len(tids)} 个主题&#12288;{idx.module_count(mid)} 篇</span></a>')

    blocks = []
    for mid in idx.module_order:
        m = idx.modules[mid]
        inner = []
        for tid in idx.module_topics(mid):
            t = idx.topics[tid]
            pids = idx.topic_points(tid)
            items = "".join(
                f'<li data-id="{pid}"><a href="{idx.rel(pid, depth)}">'
                f'{esc(idx.points[pid]["title"])}'
                f'<span class="li-sum">{render_inline(idx.points[pid].get("summary",""))}</span>'
                f'</a></li>' for pid in pids)
            inner.append(f'<div class="topic-group">'
                         f'<h3><a href="{idx.rel_topic(tid, depth)}">{esc(t["title"])}</a>'
                         f'<span class="tg-n">{len(pids)}</span></h3>'
                         f'<ul class="items point-items">{items}</ul></div>')
        blocks.append(f'<section class="block mod-block" id="{mid}">'
                      f'<h2><a href="{idx.rel_module(mid, depth)}">{esc(m["title"])}</a></h2>'
                      f'{"".join(inner)}</section>')

    main = (f'<div class="panel panel-h1"><h1 id="_top">{esc(tax["site_title"])}</h1>'
            f'<p class="home-sub">{esc(idx.site_title_sub)}</p>{stats}</div>'
            '<div class="panel panel-body">'
            f'<section class="block"><h2>四大模块</h2>'
            f'<div class="card-grid mod-grid">{"".join(cards)}</div></section>'
            + "".join(blocks) + "</div>")
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
    for mid in idx.module_order:
        m = idx.modules[mid]
        arr.append({"id": mid, "ty": "m", "t": m["title"], "s": m.get("desc", ""),
                    "k": [m["title"], "模块"], "d": "", "c": "", "b": m.get("desc", "")})
    for tid in idx.topic_order:
        t = idx.topics[tid]
        arr.append({"id": tid, "ty": "t", "t": t["title"], "s": t.get("desc", ""),
                    "k": [t["title"]], "d": idx.modules[t["module"]]["title"], "c": "",
                    "b": t.get("desc", "")})
    for pid in idx.point_order:
        p = idx.points[pid]
        body = json.dumps(p.get("sections", {}), ensure_ascii=False)
        body = re.sub(r'[\"]', " ", body)
        arr.append({
            "id": pid, "ty": "p", "t": p["title"], "s": p.get("summary", ""),
            "k": p.get("keywords", []), "d": p.get("domain", ""),
            "c": idx.topics[idx.topic_of[pid]]["title"],
            "b": body[:1200],
        })
    js = "window.__SEARCH_INDEX__=" + json.dumps(arr, ensure_ascii=False) + ";"
    return js.replace("</", "<\\/")

# --------------------------------------------------------------- build
def safe_rebuild():
    # MATH_NO_CLEAN=1：原地覆盖，不删整个目录（页面集合不变时更安全）
    if os.environ.get("MATH_NO_CLEAN") == "1":
        D.mkdir(parents=True, exist_ok=True)
        return
    if D.exists():
        if not D.resolve().is_relative_to(ROOT.resolve()):
            raise SystemExit("dist 不在项目内，拒绝删除")
        shutil.rmtree(D)
    D.mkdir(parents=True)


def copy_assets():
    dst = D / "assets"
    if os.environ.get("MATH_NO_CLEAN") == "1":
        shutil.copytree(A, dst, dirs_exist_ok=True)
    else:
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
    tax, site, std, mod, points, tb, guides = load_all()
    validate(tax, std, mod, points, tb)
    if errors:
        print(f"校验失败：{len(errors)} 个错误")
        for e in errors[:60]:
            print("  ✗", e)
        if len(errors) > 60:
            print(f"  … 另有 {len(errors)-60} 条")
        return 1
    idx = Index(tax, std, mod, points, guides, tb)
    idx.site_title_sub = site.get("subtitle", "")

    safe_rebuild()
    copy_assets()

    write(D / "index.html", emit_home(idx, 0))
    write(D / "404.html", emit_404(idx, 0))
    for mid in idx.module_order:
        write(D / mid / "index.html", emit_module(idx, mid, 1))
    for tid in idx.topic_order:
        write(D / "t" / tid / "index.html", emit_topic(idx, tid, 2))
    for pid in idx.point_order:
        write(D / "points" / pid / "index.html", emit_point(idx, pid, 2))
    write(D / "assets" / "js" / "search-index.js", build_search_index(idx))

    if warnings:
        print(f"警告 {len(warnings)} 条：")
        for w in warnings[:20]:
            print("  !", w)
    print(f"构建完成：{len(idx.point_order)} 篇知识点 / {len(idx.topic_order)} 个主题"
          f" / {len(idx.module_order)} 个模块 → dist/")
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
    tax, site, std, mod, points, tb, guides = load_all()
    validate(tax, std, mod, points, tb)
    if errors:
        print(f"✗ {len(errors)} 个错误")
        for e in errors[:80]:
            print("  ✗", e)
        if len(errors) > 80:
            print(f"  … 另有 {len(errors)-80} 条")
        return 1
    print(f"✓ 校验通过：{len(points)} 篇知识点 / {len(mod['topics'])} 个主题"
          f" / {len(mod['modules'])} 个模块 / {len(std)} 条课标条目")
    if warnings:
        for w in warnings[:20]:
            print("  !", w)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(check() if "--check" in sys.argv else build())
