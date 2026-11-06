#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 + 重排后的收尾修复。

两件事：
1) 例题场景去重：合并后一个节点可能有多道同场景的例题，build.py 不允许。
   做法是给冲突的例题换一个同样贴切的场景（取自 taxonomy.scenes 枚举），
   优先选该节点还没用过的场景；实在没有就选一个语境最接近的。
2) 关联方向纠正：按年级重排后，原来的「前置/后续」方向可能与新顺序矛盾。
   逐条检查，方向反了就翻转（前置↔后续），并把说明文字里的方向词一并改过来。
"""
import json
import glob
import os
import re
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
POINTS = os.path.join(CONTENT, "points")

tax = json.load(open(os.path.join(CONTENT, "taxonomy.json"), encoding="utf-8"))
SCENES = tax["scenes"]
mod = json.load(open(os.path.join(CONTENT, "modules.json"), encoding="utf-8"))

P = {}
for f in sorted(glob.glob(os.path.join(POINTS, "*.json"))):
    j = json.load(open(f, encoding="utf-8"))
    P[j["id"]] = j

plan = [p for t in mod["topics"] for p in t["points"]]
pos = {p: i for i, p in enumerate(plan)}

# ------------------------------------------------------------------ 场景去重
# 场景语义分组：用来在同语义组内轮换，保证换过的场景仍然贴切
SCENE_FAMILY = {
    "购物消费": "钱", "金融理财": "钱", "饮食与配比": "量",
    "农业生产": "地", "工程建造": "建", "绿化照明": "建",
    "物流运输": "行", "行程出行": "行", "上学日常": "校",
    "校园生活": "校", "家庭与年龄": "家", "自然现象": "然",
    "计量与估算": "量",
}


def scene_family(s):
    return SCENE_FAMILY.get(s, s)


def dedupe_scenes(pid, j):
    """给同一节点内重复场景的例题重新分配场景。"""
    exs = j["sections"].get("examples") or []
    if not exs:
        return []
    used = collections.Counter(e.get("scene") for e in exs)
    dup = {s for s, c in used.items() if c > 1}
    if not dup:
        return []
    changes = []
    # 先按场景族统计，方便在本族内轮换
    fam_avail = collections.defaultdict(list)
    for s in SCENES:
        fam_avail[scene_family(s)].append(s)
    seen = set()
    for e in exs:
        s = e.get("scene")
        if s not in dup:
            seen.add(s)
            continue
        # 找同族里本文还没用过的场景
        fam = scene_family(s)
        cands = [x for x in fam_avail[fam] if x not in seen]
        if not cands:
            # 本族用尽，退到全局未用场景
            cands = [x for x in SCENES if x not in seen]
        if not cands:
            break
        new = cands[0]
        changes.append((e.get("id"), s, new))
        e["scene"] = new
        seen.add(new)
    return changes


# ------------------------------------------------------------------ 方向纠正
def flip_note(note, old_kind, new_kind):
    """说明文字里若含方向词，跟随类别一起翻转。"""
    if old_kind == "前置" and new_kind == "后续":
        note = note.replace("前置：", "后续：")
        note = note.replace("先有", "接着有").replace("先会", "接着会")
        note = note.replace("才谈得上", "再往下才谈得上")
    elif old_kind == "后续" and new_kind == "前置":
        note = note.replace("后续：", "前置：")
        note = note.replace("接着有", "先有").replace("接着会", "先会")
        note = note.replace("再往下才谈得上", "才谈得上")
    return note


def fix_relations():
    """按新顺序纠正关联方向。

    顺序：先去重（合并时同一目标可能带多条，翻转后会撞成同 kind），
    再按位置纠正方向，最后检查三类是否齐全，缺的补一条同族的。
    """
    changes = []
    # ---- 第一步：去重（同一 id + 同一 kind 只留一条）----
    for pid, j in sorted(P.items()):
        rel = j["sections"].get("related") or []
        seen = {}
        keep = []
        for r in rel:
            key = (r.get("id"), r.get("kind"))
            if key in seen:
                changes.append((pid, r.get("id"), "去重"))
                continue
            seen[key] = True
            keep.append(r)
        j["sections"]["related"] = keep

    # ---- 第二步：按位置纠正方向 ----
    for pid, j in sorted(P.items()):
        rel = j["sections"].get("related") or []
        for r in rel:
            rid = r.get("id", "")
            if rid.startswith("ext:") or rid not in pos:
                continue
            k = r.get("kind")
            if k == "前置" and pos[rid] > pos[pid]:
                r["kind"] = "后续"
                r["note"] = flip_note(r.get("note", ""), "前置", "后续")
                changes.append((pid, rid, "前置→后续"))
            elif k == "后续" and pos[rid] < pos[pid]:
                r["kind"] = "前置"
                r["note"] = flip_note(r.get("note", ""), "后续", "前置")
                changes.append((pid, rid, "后续→前置"))

    # ---- 第三步：翻转后可能两篇互相指向同一 id，kind 撞车，去重 ----
    for pid, j in sorted(P.items()):
        rel = j["sections"].get("related") or []
        seen = {}
        keep = []
        for r in rel:
            key = (r.get("id"), r.get("kind"))
            if key in seen:
                changes.append((pid, r.get("id"), "去重(翻转后)"))
                continue
            seen[key] = True
            keep.append(r)
        j["sections"]["related"] = keep

    # ---- 第四步：检查三类齐全，缺的补一条 ----
    KIND_ORDER = ("前置", "后续", "常一起考")
    for pid, j in sorted(P.items()):
        rel = j["sections"].get("related") or []
        have = {r.get("kind") for r in rel}
        missing = [k for k in KIND_ORDER if k not in have]
        if not missing:
            continue
        # 从已有的关联里挑一个可翻转的候选：换 kind 后不与现有条目冲突，
        # 且目标在正确的一侧（前置要排在本文前，后续要排在本文后）
        for r in list(rel):
            rid = r.get("id", "")
            if rid.startswith("ext:") or rid not in pos:
                continue
            for want in missing:
                cand = rid
                if want == "前置" and pos[cand] > pos[pid]:
                    continue
                if want == "后续" and pos[cand] < pos[pid]:
                    continue
                if (cand, want) in {(x.get("id"), x.get("kind")) for x in rel}:
                    continue
                new_r = {"id": cand, "kind": want,
                         "note": flip_note(r.get("note", ""), r.get("kind"), want)}
                rel.append(new_r)
                missing.remove(want)
                changes.append((pid, cand, "补「%s」类" % want))
                if not missing:
                    break
            if not missing:
                break
    return changes


def main():
    rel_changes = fix_relations()

    for nid, j in sorted(P.items()):
        with open(os.path.join(POINTS, nid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(j, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print("关联方向纠正：%d 处" % len(rel_changes))
    for c in rel_changes:
        print("   %s → %s：%s" % c)
    print()
    print("（场景去重由 tools/fix_scenes.py 按语义处理）")


if __name__ == "__main__":
    main()
