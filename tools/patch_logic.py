# -*- coding: utf-8 -*-
"""修复前置知识（prerequisites）与关联知识点的数学逻辑错误。

依据 4 组审查报告：25 处「关联误当前置/顺序倒置」确凿错误，
另补齐缺失的 prerequisites 字段。幂等：重复运行按目标值收敛。
"""
import json, glob, os

POINTS = os.path.join(os.path.dirname(__file__), "..", "content", "points")

# 1) 修正后的 prerequisites（仅列需改动的篇目，值=完整新列表）
PATCH = {
    # A 组
    "m1-01-01-number-classify": ["m1-01-03-num-within-100", "m1-01-06-decimal-position"],
    "m1-01-12-positive-negative": ["m1-01-09-fraction-meaning"],
    "m1-03-02-rewrite-wan-yi": ["m1-01-05-big-number"],
    "m1-04-02-compare-fraction": ["m1-01-09-fraction-meaning", "m1-01-10-fraction-property"],
    "m1-05-04-gcd-lcm": ["m1-05-01-factors-multiples", "m1-05-02-divisibility-rules"],
    # B 组
    "m1-06-01-meaning-of-operations": [],
    "m1-06-22-fraction-mult": ["m1-01-09-fraction-meaning", "m1-01-10-fraction-property"],
    "m1-06-23-fraction-div": ["m1-06-22-fraction-mult", "m1-01-10-fraction-property"],
    "m1-06-27-mult-laws": ["m1-06-10-mult-table"],
    "m1-06-28-sub-div-property": ["m1-06-24-mixed-op-order"],
    "m1-06-30-estimation": ["m1-03-01-rounding"],
    # C 组
    "m2-04-01-direction": ["m2-01-03-angle-measure"],
    "m2-04-02-number-pair": [],
    "m2-03-03-scale-enlarge": ["m1-09-01-ratio-meaning"],
    "m2-02-09-observe-object": [],
    # D 组
    "m2-01-21-circle-circumference": ["m2-01-09-circle-features", "m2-01-13-perimeter"],
    "m2-01-22-circle-area": ["m2-01-21-circle-circumference", "m2-01-17-rect-area"],
    "m4-01-01-thinking-methods": [],
    "m4-02-02-pattern-sequence": [],
    "m4-03-01-addition-principle": ["m1-06-26-add-laws"],
}

# 2) 补齐缺失的 prerequisites 字段（键不存在时写入）
ADD_MISSING = {
    "m2-01-11-length-cm-m": [],
    "m3-01-01-data-collect": [],
    "m3-04-01-certainty": [],
    "m3-02-03-pie-chart": ["m3-02-01-bar-chart"],
    "m1-09-01-ratio-meaning": [],
    "m1-09-02-proportion": ["m1-09-01-ratio-meaning"],
    "m2-02-06-cylinder-surface": ["m2-01-21-circle-circumference", "m2-02-02-cylinder-cone-features"],
    "m2-02-07-cylinder-volume": ["m2-02-04-cuboid-volume"],
    "m2-03-02-translation-rotation": ["m2-01-01-lines-ray-segment"],
}

# 3) related 指向修正（m1-06-29 的乘方应用应指向正方体体积公式篇）
RELATED_REDIRECT = {
    ("m1-06-29-power", "m2-02-04-cuboid-volume"): "m2-02-05-cuboid-volume-formula",
}


def main():
    all_ids = set()
    files = {}
    for f in glob.glob(os.path.join(POINTS, "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        files[d["id"]] = f
        all_ids.add(d["id"])

    for pid, pre in PATCH.items():
        for x in pre:
            assert x in all_ids, f"前置 id 不存在: {pid} -> {x}"
        d = json.load(open(files[pid], encoding="utf-8"))
        old = d.get("prerequisites")
        if old != pre:
            d["prerequisites"] = pre
            json.dump(d, open(files[pid], "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            open(files[pid], "a", encoding="utf-8").write("\n")
            print(f"改前置 {pid}: {old} -> {pre}")

    for pid, pre in ADD_MISSING.items():
        d = json.load(open(files[pid], encoding="utf-8"))
        if "prerequisites" not in d:
            for x in pre:
                assert x in all_ids, f"前置 id 不存在: {pid} -> {x}"
            # 插到 prerequisites 应在的位置（meta 之前无严格要求，按 key 顺序追加即可）
            out = {}
            for k, v in d.items():
                if k == "sections":
                    out["prerequisites"] = pre
                out[k] = v
            if "prerequisites" not in out:
                out["prerequisites"] = pre
            json.dump(out, open(files[pid], "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            open(files[pid], "a", encoding="utf-8").write("\n")
            print(f"补字段 {pid}: {pre}")

    for (pid, old_id), new_id in RELATED_REDIRECT.items():
        d = json.load(open(files[pid], encoding="utf-8"))
        rel = (d.get("sections") or {}).get("related") or []
        hit = [r for r in rel if r.get("id") == old_id]
        if hit:
            hit[0]["id"] = new_id
            json.dump(d, open(files[pid], "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            open(files[pid], "a", encoding="utf-8").write("\n")
            print(f"改关联指向 {pid}: {old_id} -> {new_id}（note: {hit[0].get('note','')[:30]}）")

    print("done")


if __name__ == "__main__":
    main()
