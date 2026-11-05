# -*- coding: utf-8 -*-
"""把新增篇目登记进 content/modules.json 的 topics[].points。

新篇按「节内已有序号之后顺延」插入，并保持每个主题内 points 数组的原有顺序
（只在末尾追加，避免打乱既有篇目的呈现顺序）。
写入时保持原文件的 1 空格缩进风格，避免无意义的整文件 diff。
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
C = ROOT / "content"
MOD = C / "modules.json"


def load_with_style(raw):
    """探测原文件的缩进宽度。"""
    for line in raw.split("\n")[1:6]:
        stripped = line.lstrip(" ")
        if stripped and line != stripped:
            return len(line) - len(stripped)
    return 1


def main():
    raw = subprocess.run(["git", "show", "HEAD:content/modules.json"],
                         capture_output=True, text=True).stdout
    indent = load_with_style(raw)
    mod = json.loads(raw)

    # 新增篇目：id -> 所属节
    NEW = {
        "m1-01": ["m1-01-13-num-6-to-10", "m1-01-14-num-11-to-20",
                  "m1-01-15-fraction-intro", "m1-01-16-fraction-division"],
        "m1-03": ["m1-03-05-hundred-thousand"],
        "m1-06": ["m1-06-31-mult-add-sub", "m1-06-32-decimal-add-sub",
                  "m1-06-33-mental-add-sub-100", "m1-06-34-mul-table-7-9",
                  "m1-06-35-div-table-7-9", "m1-06-36-fraction-diff"],
        "m1-07": ["m1-07-16-add-sub-relation", "m1-07-17-times-relation",
                  "m1-07-18-rmb", "m1-07-19-time-units", "m1-07-20-date",
                  "m1-07-21-optimization", "m1-07-22-find-bad-item"],
        "m1-09": ["m1-09-05-lever-balance"],
        "m2-01": ["m2-01-25-plane-shapes", "m2-01-26-mass-units"],
        "m2-02": ["m2-02-11-solid-shapes-intro"],
        "m2-03": ["m2-03-04-tessellation"],
        "m3-04": ["m3-04-03-digital-code"],
        "m4-02": ["m4-02-05-logic-reasoning"],
        "m4-03": ["m4-03-04-set-overlap"],
    }

    added = 0
    for t in mod["topics"]:
        new_ids = NEW.get(t["id"], [])
        if not new_ids:
            continue
        for pid in new_ids:
            if pid not in t["points"]:
                t["points"].append(pid)
                added += 1
    # 未被任何主题认领的新 id → 报错
    claimed = {p for t in mod["topics"] for p in t["points"]}
    orphan = [p for lst in NEW.values() for p in lst if p not in claimed]
    if orphan:
        raise SystemExit(f"这些新 id 没能归入任何主题：{orphan}")

    MOD.write_text(json.dumps(mod, ensure_ascii=False, indent=indent) + "\n",
                   encoding="utf-8")
    print(f"已登记 {added} 个新 id 进 modules.json（indent={indent}）")


if __name__ == "__main__":
    main()
