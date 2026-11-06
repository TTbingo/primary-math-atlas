"""按例题实际内容修正「场景」标签。

输入：tools/_scene_fix.tsv（格式：全局序号 \t 新场景 \t 依据）
全局序号 = 按文件名排序后，逐篇按 examples 顺序从 1 起的连号（与 tools/_scene_dump.txt 一致）。

用法：
    python tools/fix_example_scenes.py --dry   # 只打印，不写盘
    python tools/fix_example_scenes.py         # 写盘
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, "tools", "_scene_fix.tsv")
TAX = os.path.join(ROOT, "content", "taxonomy.json")


def load_fix():
    fix = {}
    with open(TSV, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            idx, scene, why = line.split("\t")
            fix[int(idx)] = (scene, why)
    return fix


def main():
    dry = "--dry" in sys.argv
    scenes = set(json.load(open(TAX, encoding="utf-8"))["scenes"])
    fix = load_fix()

    bad = sorted({s for s, _ in fix.values()} - scenes)
    if bad:
        sys.exit(f"新场景不在枚举内：{bad}")

    n = 0
    changed = 0
    touched = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "points", "*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        examples = data["sections"].get("examples", [])
        dirty = False
        for ex in examples:
            n += 1
            if n not in fix:
                continue
            new, why = fix[n]
            old = ex.get("scene")
            if old == new:
                print(f"  跳过 {n}: 已是「{new}」")
                continue
            print(f"{n}\t{data['id']}\t{ex['id']}\t{old} → {new}\t{why}")
            ex["scene"] = new
            changed += 1
            dirty = True
        if dirty:
            touched.append(os.path.basename(path))
            if not dry:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    unused = sorted(set(fix) - set(range(1, n + 1)))
    print(f"\n例题总数 {n}｜本次改动 {changed}｜涉及篇目 {len(touched)}｜TSV 条目 {len(fix)}")
    if unused:
        print(f"⚠ 未命中的序号：{unused}")
    if dry:
        print("（--dry 未写盘）")


if __name__ == "__main__":
    main()
