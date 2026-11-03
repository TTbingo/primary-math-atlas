# -*- coding: utf-8 -*-
"""把现有 64 篇从「年级-册-单元」迁到「模块-节-知识点」。

只改组织字段（id / module / topic / domain / strand），正文一字不动。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
C = ROOT / "content"

# 每节对应的课标主题（strand），用于校正旧数据的 strand 字段
TOPIC_STRAND = {
    "m1-01": "数与运算", "m1-02": "数与运算", "m1-03": "数与运算",
    "m1-04": "数与运算", "m1-05": "数与运算", "m1-06": "数与运算",
    "m1-07": "数量关系", "m1-08": "数量关系", "m1-09": "数量关系",
    "m2-01": "图形的认识与测量", "m2-02": "图形的认识与测量",
    "m2-03": "图形的位置与运动", "m2-04": "图形的位置与运动",
    "m3-01": "数据的收集、整理与表达", "m3-02": "数据的收集、整理与表达",
    "m3-03": "数据的收集、整理与表达", "m3-04": "随机现象发生的可能性",
    "m4-01": "综合与实践", "m4-02": "综合与实践",
    "m4-03": "综合与实践", "m4-04": "综合与实践",
}
MODULE_DOMAIN = {"m1": "数与代数", "m2": "图形与几何",
                 "m3": "统计与概率", "m4": "综合与实践"}


def main(dry=False):
    mod = json.loads((C / "modules.json").read_text(encoding="utf-8"))
    points = [p for t in mod["topics"] for p in t["points"]]
    # 新 id -> (module, topic)
    where = {}
    for t in mod["topics"]:
        for pid in t["points"]:
            where[pid] = (t["module"], t["id"])

    plan = json.loads((C / "_reference" / "plan-map.json").read_text(encoding="utf-8"))
    old2new = plan["old2new"]

    files = {f.stem: f for f in (C / "points").glob("*.json")}
    unmapped = {k for k in files if not re.match(r"^m\d-\d\d-", k)} - set(old2new)
    if unmapped:
        raise SystemExit(f"未安排归位的旧篇目: {sorted(unmapped)}")

    changed_ids = done = 0
    for old, new in old2new.items():
        if old not in files:
            # 已经迁过（脚本可能被重复执行），跳过
            done += 1
            continue
        src = files[old]
        d = json.loads(src.read_text(encoding="utf-8"))
        module, topic = where[new]

        d["id"] = new
        d["module"] = module
        d["topic"] = topic
        d["domain"] = MODULE_DOMAIN[module]
        d["strand"] = TOPIC_STRAND[topic]
        d.pop("chapter", None)
        # lesson 记的是「第几课时」，按模块重组后无意义；学段信息仍在 segment 里
        d.pop("lesson", None)

        # 交叉引用改映射
        if d.get("prerequisites"):
            d["prerequisites"] = [old2new.get(x, x) for x in d["prerequisites"]]
        for r in d.get("sections", {}).get("related", []):
            r["id"] = old2new.get(r["id"], r["id"])

        # 字段顺序：schema, id, type, module, topic, title ...
        order = ["schema", "id", "type", "module", "topic", "title", "slug", "summary",
                 "keywords", "domain", "strand", "segment", "standard_ids", "verb_level",
                 "literacy", "scope", "prerequisites", "media", "sections", "meta"]
        out = {k: d[k] for k in order if k in d}
        out.update({k: v for k, v in d.items() if k not in out})

        if not dry:
            dst = C / "points" / f"{new}.json"
            dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
            if dst != src:
                src.unlink()
        changed_ids += 1

    # 检查所有引用都能落地
    ids = {f.stem for f in (C / "points").glob("*.json")} if not dry else set(old2new.values())
    bad = []
    for f in (C / "points").glob("*.json") if not dry else []:
        d = json.loads(f.read_text(encoding="utf-8"))
        for x in d.get("prerequisites") or []:
            if x not in ids:
                bad.append((d["id"], "prereq", x))
        for r in d.get("sections", {}).get("related", []):
            if r["id"] not in ids:
                bad.append((d["id"], "related", r["id"]))
    print(f"{'[预演] ' if dry else ''}迁移 {changed_ids} 篇；断引用 {len(bad)}")
    for b in bad[:10]:
        print("  ", b)


if __name__ == "__main__":
    import sys
    main(dry="--dry" in sys.argv)
