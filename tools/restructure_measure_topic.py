# -*- coding: utf-8 -*-
"""把「常见的量」从各处抽出来，单独成一节 m1-10（数与代数模块）。

做四件事：
1. 新建 m1-10-01..04 四篇（已在 content/points/ 里写好），登记进 modules.json；
2. 删除原 m1-07-02（人民币+时分秒+年月日），内容已搬进 m1-10-02 / m1-10-04；
3. m1-07 其余篇目重编号（03..14 → 02..13），节内序号必须从 01 连续；
4. m2-01-01 剥掉「克、千克、吨」，只留平面图形，标题改为「认识平面图形」。
所有跨篇引用（related / prerequisites / guides 短引用）同步重定向。
"""
import json
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PTS = os.path.join(ROOT, "content", "points")

DELETED = "m1-07-02-rmb-time-and-date"
# 该篇拆成时间篇与人民币篇，按引用语义重定向
REDIRECT = {
    "m1-06-05-multiplication-intro-and-table": "m1-10-04-rmb",       # 常一起考：买东西算总价
    "m1-07-01-quantity-relations-basic": "m1-10-04-rmb",             # 后续：逛超市比价
    "m1-07-07-optimization-and-find-bad-item": "m1-10-02-time-units-and-24h",  # 前置：时分秒进率
    "m4-02-01-pattern-arith-sequence-cycle": "m1-10-02-time-units-and-24h",    # 常一起考：周期
}
# m1-07 重编号：03..14 → 02..13
RENUM = {"m1-07-%02d" % i: "m1-07-%02d" % (i - 1) for i in range(3, 15)}
# m2-01-01 改名（不再讲质量）
OLD_M2 = "m2-01-01-plane-shapes-and-mass"
NEW_M2 = "m2-01-01-plane-shapes"

MARK = "**（克、千克和吨）**"


def load_points():
    pts = {}
    for fn in sorted(os.listdir(PTS)):
        if not fn.endswith(".json"):
            continue
        d = json.load(io.open(os.path.join(PTS, fn), encoding="utf-8"))
        pts[d["id"]] = d
    return pts


def split_mass(d):
    """从 m2-01-01 里剥掉质量内容，返回只讲平面图形的版本。"""
    s = d["sections"]
    # 段落型板块：marker 之后都是质量
    for k in ("explanation", "scenarios", "cautions"):
        v = s[k]
        if MARK in v:
            s[k] = v[: v.index(MARK)]
    steps = s["why"]["steps"]
    if MARK in steps:
        s["why"]["steps"] = steps[: steps.index(MARK)]
    s["why"]["experiment"] = s["why"]["experiment"].split(MARK)[0].strip()
    s["intuition"] = s["intuition"].split(MARK)[0].strip()
    s["rhyme"] = s["rhyme"].split(MARK)[0].strip()
    s["examples"] = [e for e in s["examples"] if e["id"] in ("ex1", "ex2", "ex3", "ex4")]
    # inferences / pitfalls：图形在前、质量在后，按关键词截断
    mass_kw = ("千克", "吨", "克", "天平", "曹冲", "秤", "等量")
    s["inferences"] = [x for x in s["inferences"] if not any(w in x for w in mass_kw)]
    s["pitfalls"] = [x for x in s["pitfalls"] if not any(w in x["wrong"] + x["right"] for w in mass_kw)]

    d["id"] = NEW_M2
    d["slug"] = "plane-shapes"
    d["title"] = "认识平面图形"
    d["keywords"] = ["平面图形", "立体图形", "长方形", "正方形", "三角形", "圆", "拼组", "七巧板", "认识平面图形"]
    d["textbook_ref"] = {
        "note": "对应一下第 1 单元「认识平面图形」：长方形、正方形、三角形、圆的辨认与拼组。质量单位（克、千克、吨）已独立成「常见的量」一节，见《质量、温度与速度》。",
        "locations": [
            {"volume": "g01-s2", "volume_label": "一年级下册",
             "units": [{"no": 1, "name": "认识平面图形"}], "special": []}
        ],
    }
    d["meta"]["source"] = "课标2022 第一学段·图形与几何·图形的认识与测量(1)(3) ／ 人教版2024 一年级下册、第1单元 认识平面图形"
    d["sections"]["related"] = [
        {"id": "m1-01-02-num-1-to-20", "kind": "前置",
         "note": "前置：数图形有几条边、几个角，靠的是一个一个数得准"},
        {"id": "m2-01-02-length-units", "kind": "后续",
         "note": "后续：认准面以后就要量边，长度单位是下一步"},
        {"id": "m2-03-02-scale-enlarge-and-tessellation", "kind": "后续",
         "note": "后续：五年级「有趣的密铺」把平面图形铺满整片，靠的还是先认清形状"},
        {"id": "m2-02-01-solid-shapes-intro", "kind": "常一起考",
         "note": "常一起考：一上第3单元认识立体图形、一下第1单元认识平面图形，两课前后照应，一道题里常对照着问"},
        {"id": "m3-01-01-data-collect-and-table", "kind": "常一起考",
         "note": "常一起考：二上「分类与整理」按图形分堆，用的正是这四种形状的名字"},
    ]
    return d


def try_redirect(pid, target):
    """指定文件里对已删篇目的引用改成 target；m1-07-07 的「前置」改「常一起考」。"""
    p = pts[pid]
    s = p["sections"]
    for r in s.get("related", []):
        if r["id"] == DELETED:
            r["id"] = target
            if pid == "m1-07-07-optimization-and-find-bad-item":
                r["kind"] = "常一起考"
                r["note"] = "常一起考：优化问题全靠算「一共多少分钟」，时分秒的进率与经过时间要和方案比较一起用"
    if DELETED in p.get("prerequisites", []):
        p["prerequisites"] = [x for x in p["prerequisites"] if x != DELETED]
    if DELETED in json.dumps(p, ensure_ascii=False):
        raise SystemExit(f"{pid} 里仍有 {DELETED} 残留")


def main():
    global pts
    pts = load_points()
    if DELETED not in pts:
        raise SystemExit("找不到待删除的 m1-07-02，脚本可能已跑过")

    # 1) 逐文件重定向
    for pid, target in REDIRECT.items():
        try_redirect(pid, target)

    # 2) m2-01-01 剥离质量
    pts[OLD_M2] = split_mass(pts[OLD_M2])

    # 3) 全站 id 重编号（含新篇里对 m1-07 的引用）
    pat = re.compile(r"m1-07-(\d\d)(?=-|\b)")

    def sub_ids(text):
        def rep(m):
            key = "m1-07-" + m.group(1)
            return RENUM.get(key, key)
        return pat.sub(rep, text)

    # 4) 删除旧篇；m1-07 按升序改名（03→02 时 02 已删，逐级腾空）
    os.remove(os.path.join(PTS, DELETED + ".json"))
    del pts[DELETED]

    plan = []  # (old_id, new_id, dict)
    for pid in list(pts):
        new_id = pid
        if pid.startswith("m1-07-") and pid[:8] in RENUM:
            new_id = RENUM[pid[:8]] + pid[8:]
        elif pid == OLD_M2:
            new_id = NEW_M2
        plan.append((pid, new_id, pts[pid]))

    for old_id, new_id, d in sorted(plan, key=lambda x: (x[0].startswith("m1-07"), x[0])):
        src = os.path.join(PTS, old_id + ".json")
        d["id"] = new_id
        blob = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
        blob = sub_ids(blob).replace(OLD_M2, NEW_M2)
        os.remove(src)
        io.open(os.path.join(PTS, new_id + ".json"), "w", encoding="utf-8").write(blob)

    # 5) modules.json：m1-07 清单重排 + 新增 m1-10
    mp = os.path.join(ROOT, "content", "modules.json")
    mod = json.loads(io.open(mp, encoding="utf-8").read())
    t7 = next(t for t in mod["topics"] if t["id"] == "m1-07")
    t7["points"] = sorted(
        [p for p in (sub_ids(x) for x in t7["points"]) if p != DELETED],
        key=lambda x: int(x.split("-")[2]),
    )
    t7["desc"] = "和差倍、归一、植树、鸡兔同笼、行程、工程、浓度……这些「典型应用题」不是靠背公式，是靠认出它属于哪种数量关系。"
    if not any(t["id"] == "m1-10" for t in mod["topics"]):
        idx = [i for i, t in enumerate(mod["topics"]) if t["id"] == "m1-09"][0]
        mod["topics"].insert(idx + 1, {
            "id": "m1-10",
            "module": "m1",
            "no": 10,
            "title": "常见的量",
            "desc": "多长、多重、多久、多热、多快——量出来的数离开单位就没有意义。单位分级、进率、名数的化与聚，加上时间、人民币、质量、温度、速度这几套常用单位，单独成一节。",
            "standard_ids": [
                "std-s1-cp-2", "std-s1-cp-3", "std-s1-cp-5", "std-s1-na-7",
                "std-s1-geo-2", "std-s2-cp-1", "std-s2-cp-2", "std-s2-cp-4",
                "std-s2-na-8", "std-s2-na-10", "std-s2-geo-3",
            ],
            "points": [
                "m1-10-01-measure-units-and-denominate",
                "m1-10-02-time-units-and-24h",
                "m1-10-03-mass-temperature-speed",
                "m1-10-04-rmb",
            ],
        })
    io.open(mp, "w", encoding="utf-8").write(json.dumps(mod, ensure_ascii=False, indent=2) + "\n")

    # 6) guides.json：m1-07 的导语改写 + 新增 m1-10 行
    gp = os.path.join(ROOT, "content", "guides.json")
    guides = json.loads(io.open(gp, encoding="utf-8").read())
    rows = guides["guides"]["m1"]["rows"]
    for r in rows:
        if r["topic"] == "m1-07":
            r["where"] = ("这一章把运算变成解决真实问题的能力。[[m1-07-03]] 的三条关系是全站应用题的通用钥匙；"
                          "[[m1-07-07]] 优化问题是把时间与方案一起算计，[[m1-07-08]] 鸡兔同笼是假设法的代表。")
    if not any(r["topic"] == "m1-10" for r in rows):
        rows.append({
            "topic": "m1-10",
            "where": "常见的量是应用题里的「翻译层」：题目给的是 2 时 30 分、3 吨 50 千克、60 千米/时，先得看懂单位、换成同一级，才能算。"
                     "[[m1-10-01]] 讲单位、进率与名数的化聚，[[m1-10-02]] 是时间，[[m1-10-03]] 是质量、温度与速度，[[m1-10-04]] 是人民币。"
                     "单位看错一格，后面的算式全白算。"
        })
    io.open(gp, "w", encoding="utf-8").write(sub_ids(json.dumps(guides, ensure_ascii=False, indent=2)) + "\n")

    print("迁移完成：新节 m1-10 四篇 + m1-07 重编号 + m2-01-01 剥离质量")


if __name__ == "__main__":
    main()
