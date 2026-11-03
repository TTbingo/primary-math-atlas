# -*- coding: utf-8 -*-
"""把 build.py 从「年级-册-单元」体系切到「模块-节-知识点」体系。

思路：渲染层（markdown、九板块、KaTeX、模板）一行不动，
只替换体系层（数据加载、索引、侧栏、三种页面、搜索索引、主流程、校验）。
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
F = ROOT / "build.py"
s = F.read_text(encoding="utf-8")


def fn(src, name, new):
    pat = re.compile(rf"\ndef {name}\(.*?(?=\ndef |\nclass |\n# -{{10,}})", re.S)
    assert pat.search(src), f"找不到函数 {name}"
    return pat.sub("\n" + new.strip("\n") + "\n", src, count=1)


def cls(src, name, new):
    pat = re.compile(rf"\nclass {name}\b.*?(?=\ndef |\n# -{{10,}})", re.S)
    assert pat.search(src), f"找不到类 {name}"
    return pat.sub("\n" + new.strip("\n") + "\n", src, count=1)


# ------------------------------------------------------------------ 数据加载
s = fn(s, "load_all", '''
def load_all():
    tax = read_json(C / "taxonomy.json")
    site = read_json(C / "site.json")
    std = {s["id"]: s for s in read_json(C / "standards.json")["items"]}
    mod = read_json(C / "modules.json")
    points = {p.stem: read_json(p) for p in sorted((C / "points").glob("*.json"))}
    return tax, site, std, mod, points
''')

# ------------------------------------------------------------------ Index
s = cls(s, "Index", '''
class Index:
    """按「模块 → 节 → 知识点」组织。清单里已写和待写都在，只是待写的不出现在页面链接里。"""

    def __init__(self, tax, std, mod, points):
        self.tax, self.std, self.mod, self.points = tax, std, mod, points
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
                    self.incoming[r["id"]].append((pid, r.get("note", "")))

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
''')

# ------------------------------------------------------------------ 侧边栏
s = fn(s, "build_sidebar", '''
def build_sidebar(idx, current=None, depth=0):
    """四模块折叠树。当前模块展开；当前主题再展开它下面的知识点。"""
    cur_topic = idx.topic_of.get(current)
    cur_mod = idx.module_of.get(current) or (current if current in idx.modules else None)
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
''')

# ------------------------------------------------------------------ emit_point 里的小改
s = s.replace('''    meta_bits = [badge(p.get("domain", "")), badge(p.get("chapter", "")),
                 badge(f'课标：{p.get("verb_level","")}'), badge(scope_label, "badge badge-scope")]''',
'''    tid = idx.topic_of.get(pid)
    tname = idx.topics[tid]["title"] if tid else ""
    meta_bits = [badge(p.get("domain", "")), badge(tname),
                 badge(f'课标：{p.get("verb_level","")}'), badge(scope_label, "badge badge-scope")]''')

s = s.replace('''    overview = '<table class="kv"><tbody>'
    uid = idx.unit_of.get(pid)
    if uid:
        u = idx.units[uid]
        overview += (f'<tr><th>所在单元</th><td><a href="{idx.rel_unit(uid, depth)}">'
                     f'{esc(u["title"])}</a></td></tr>')
    overview += f'<tr><th>教材位置</th><td>{esc(p.get("lesson","")) or "—"}</td></tr>'
''',
'''    overview = '<table class="kv"><tbody>'
    if tid:
        mid = idx.topics[tid]["module"]
        overview += (f'<tr><th>所属主题</th><td><a href="{idx.rel_topic(tid, depth)}">'
                     f'{esc(idx.topics[tid]["title"])}</a></td></tr>'
                     f'<tr><th>所属模块</th><td><a href="{idx.rel_module(mid, depth)}">'
                     f'{esc(idx.modules[mid]["title"])}</a></td></tr>')
    if p.get("segment"):
        overview += (f'<tr><th>课标学段</th><td>'
                     f'{esc(idx.tax["segments"][str(p["segment"])])}</td></tr>')
''')

s = s.replace('''        "SIDEBAR": build_sidebar(idx, uid, depth),
        "TOC": build_toc(extra + entries),''',
'''        "SIDEBAR": build_sidebar(idx, pid, depth),
        "TOC": build_toc(extra + entries),''')

# ------------------------------------------------------------------ 节页（替换 emit_unit + term_label）
s = fn(s, "emit_unit", '''
def emit_topic(idx, tid, depth=2):
    """主题页：这一节讲什么、对应课标哪几条、下面有哪些知识点。"""
    t = idx.topics[tid]
    mid = t["module"]
    m = idx.modules[mid]
    written = idx.topic_points(tid)
    pending = idx.topic_pending(tid)

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
        overview += f'<tr><th>课标要求</th><td class="std-text">{txt}</td></tr>'
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
    if pending:
        body.append('<section class="block"><h2>这一节还会包含</h2><ul class="items pending">')
        for pid in pending:
            title = pid.split("-", 3)[-1].replace("-", " ")
            body.append(f'<li>{esc(title)}<span class="tag-soon">待写</span></li>')
        body.append('</ul><p class="note">这些知识点已列入规划，正文尚未撰写。</p></section>')
    body.append("</div>")

    entries = [(2, "知识点", "list")] if written else []
    return tmpl("base.html", page_vars(idx, {
        "TITLE": t["title"], "DESC": plain(t["desc"]),
        "MAIN": "".join(body), "SIDEBAR": build_sidebar(idx, tid, depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-topic",
    }))
''')

s = fn(s, "term_label", '''
''')

# ------------------------------------------------------------------ 模块页（替换 emit_grade）
s = fn(s, "emit_grade", '''
def emit_module(idx, mid, depth=1):
    """模块页：这个模块由哪些主题组成。"""
    m = idx.modules[mid]
    tids = idx.module_topics(mid)
    total = idx.module_count(mid)
    head = ('<div class="panel panel-h1">'
            f'<p class="mod-kicker">模块 {m["no"]}</p>'
            f'<h1 id="_top">{esc(m["title"])}</h1>'
            f'<p class="grade-sub">{esc(m["desc"])}</p></div>')
    body = [head, '<div class="panel panel-body">']
    body.append('<section class="block overview"><table class="kv"><tbody>'
                f'<tr><th>课标主题</th><td>{esc(m.get("strand",""))}</td></tr>'
                f'<tr><th>主题数</th><td>{len(tids)} 个</td></tr>'
                f'<tr><th>知识点</th><td>{total} 篇</td></tr>'
                '</tbody></table></section>')
    entries = []
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
        else:
            body.append('<p class="note">这一节的内容还在规划中。</p>')
        body.append("</section>")
        entries.append((2, t["title"], tid))
    body.append("</div>")
    return tmpl("base.html", page_vars(idx, {
        "TITLE": m["title"], "DESC": plain(m["desc"]),
        "MAIN": "".join(body), "SIDEBAR": build_sidebar(idx, mid, depth),
        "TOC": build_toc(entries), "ROOT": idx.root_for(depth), "DEPTH": str(depth),
        "BODY_CLASS": "page-module",
    }))
''')

# ------------------------------------------------------------------ 首页
s = fn(s, "emit_home", '''
def emit_home(idx, depth=0):
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
                      f'<h2>{esc(m["title"])}</h2>'
                      f'<p class="mod-desc">{esc(m["desc"])}</p>{"".join(inner)}</section>')

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
''')

# ------------------------------------------------------------------ 搜索索引
s = fn(s, "build_search_index", '''
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
        body = re.sub(r'[\\\\"]', " ", body)
        arr.append({
            "id": pid, "ty": "p", "t": p["title"], "s": p.get("summary", ""),
            "k": p.get("keywords", []), "d": p.get("domain", ""),
            "c": idx.topics[idx.topic_of[pid]]["title"],
            "b": body[:1200],
        })
    js = "window.__SEARCH_INDEX__=" + json.dumps(arr, ensure_ascii=False) + ";"
    return js.replace("</", "<\\\\/")
''')

# ------------------------------------------------------------------ 主流程
s = fn(s, "build", '''
def build():
    tax, site, std, mod, points = load_all()
    validate(tax, std, mod, points)
    if errors:
        print(f"校验失败：{len(errors)} 个错误")
        for e in errors[:60]:
            print("  ✗", e)
        if len(errors) > 60:
            print(f"  … 另有 {len(errors)-60} 条")
        return 1
    idx = Index(tax, std, mod, points)
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
        write(D / "points" / pid / "index.html", emit_point(idx, pid, 3))
    write(D / "assets" / "js" / "search-index.js", build_search_index(idx))

    if warnings:
        print(f"警告 {len(warnings)} 条：")
        for w in warnings[:20]:
            print("  !", w)
    print(f"构建完成：{len(idx.point_order)} 篇知识点 / {len(idx.topic_order)} 个主题"
          f" / {len(idx.module_order)} 个模块 → dist/")
    return verify_output()
''')

# ------------------------------------------------------------------ check
s = s.replace('''def check():
    tax, site, std, grades, units, points = load_all()
    validate(tax, std, grades, units, points)''',
'''def check():
    tax, site, std, mod, points = load_all()
    validate(tax, std, mod, points)''')

# ------------------------------------------------------------------ validate 签名与体系校验
s = s.replace("def validate(tax, std, grades, units, points):\n    sec_keys",
              "def validate(tax, std, mod, points):\n    sec_keys")

s = s.replace('''    domains = set(tax["domains"])
    chapters = set(tax["chapters"])
    scenes = set(tax["scenes"])''',
'''    domains = set(tax["domains"])
    scenes = set(tax["scenes"])
    modules_ = {m["id"]: m for m in mod["modules"]}
    topics_ = {t["id"]: t for t in mod["topics"]}
    plan = {p for t in mod["topics"] for p in t["points"]}''')

s = s.replace('''        # 前缀归属
        m = re.match(r"^(g\\d\\d-s\\d-u\\d\\d)-p\\d\\d-", pid)
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
            err(f"{ctx}: chapter「{p['chapter']}」不在枚举内")''',
'''        # 归属：id 前两段必须是一个已定义的节，第三段是节内序号
        m = re.match(r"^(m\\d-\\d\\d)-(\\d\\d)-", pid)
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
            err(f"{ctx}: domain「{p['domain']}」不在枚举内")''')

# 前置/关联：允许指向清单内的待写篇目
s = s.replace('''        for rid in p.get("prerequisites", []):
            if rid not in points:
                err(f"{ctx}: 前置知识点 {rid} 不存在")''',
'''        for rid in p.get("prerequisites", []):
            if rid not in plan:
                err(f"{ctx}: 前置知识点 {rid} 不在知识点清单内")''')
s = s.replace('''                for r in v:
                    if r.get("id") not in points:
                        err(f"{ctx}.{k}: 关联 {r.get('id')} 不存在")''',
'''                for r in v:
                    if r.get("id") not in plan:
                        err(f"{ctx}.{k}: 关联 {r.get('id')} 不在知识点清单内")''')

# 删掉单元/年级校验，换成模块体系自身的完整性校验
s = s.replace('''    for uid, u in units.items():
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
        m = re.match(r"^(g\\d\\d-s\\d-u\\d\\d)-p(\\d\\d)-", pid)
        if m:
            byunit.setdefault(m.group(1), []).append(int(m.group(2)))
    for uid, nums in byunit.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            err(f"单元 {uid}: 知识点编号不连续 → {sorted(nums)}")''',
'''    # 模块体系自身的完整性：节必须有模块、模块必须有节、节内序号必须从 01 连续
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
        err(f"以下篇目未登记进知识点清单: {sorted(missing)}")''')

# 语法自检
import ast
ast.parse(s)
F.write_text(s, encoding="utf-8")
print("build.py 已改造，语法通过")
print("剩余旧体系残留:")
for kw in ("unit_of", "rel_unit", "grade_order", "unit_order", "idx.grades", "idx.units",
           "emit_unit", "emit_grade", "term_label", "chapter"):
    n = len(re.findall(kw, s))
    if n:
        print(f"  {kw}: {n}")
