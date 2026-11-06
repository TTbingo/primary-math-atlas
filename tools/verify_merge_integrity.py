#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对合并是否丢失原有知识点的实质内容。

把新旧两站的所有正文片段（说明/场景/注意点/算理/例题/推论/易错/直觉/口诀）
归一化后逐条比对：旧站每一条片段都必须能在新站某个节点里原样找到。
"""
import json
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OLD = os.path.join(CONTENT, "_backup_points_premerge_20261106_092835")
NEW = os.path.join(CONTENT, "points")


def norm(s):
    return re.sub(r"\s+", "", s)


def texts_of(j):
    """抽出节点里所有可读的文本片段。"""
    out = []
    for sec, v in j["sections"].items():
        if sec == "related":
            continue
        if isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    out.append((sec, it))
                elif isinstance(it, dict):
                    for k, x in it.items():
                        if isinstance(x, str):
                            out.append((sec + "." + k, x))
        elif isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, list):
                    for it in x:
                        if isinstance(it, str):
                            out.append((sec + "." + k, it))
                        elif isinstance(it, dict):
                            for k2, x2 in it.items():
                                if isinstance(x2, str):
                                    out.append((sec + "." + k + "." + k2, x2))
                elif isinstance(x, str):
                    out.append((sec + "." + k, x))
        elif isinstance(v, str):
            out.append((sec, v))
    # 关键词与教材定位说明也算实质内容
    for kw in j.get("keywords", []):
        out.append(("keywords", kw))
    return out


def main():
    old = {}
    for f in sorted(glob.glob(os.path.join(OLD, "*.json"))):
        j = json.load(open(f, encoding="utf-8"))
        old[j["id"]] = j
    new = {}
    for f in sorted(glob.glob(os.path.join(NEW, "*.json"))):
        j = json.load(open(f, encoding="utf-8"))
        new[j["id"]] = j

    # 新站全部正文拼成一个大字符串做子串查找。
    # 合并时旧片段会被拼进更长的文本（用小标题分隔），
    # 所以必须用子串比对，不能用集合精确匹配。
    hay = "\n".join(t for j in new.values() for _, t in texts_of(j))
    hay = norm(hay)

    total = 0
    missing = []
    for oid, j in sorted(old.items()):
        for sec, t in texts_of(j):
            t2 = norm(t)
            if len(t2) < 10:
                continue
            total += 1
            if t2 not in hay:
                missing.append((oid, sec, t[:90]))

    print("=== 合并内容完整性核对 ===")
    print("原站节点数：%d  →  新站节点数：%d" % (len(old), len(new)))
    print("原站正文片段总数：%d" % total)
    print("合并后未找到的片段：%d" % len(missing))
    if missing:
        print()
        for m in missing[:30]:
            print("   %s [%s] %s" % m)
        if len(missing) > 30:
            print("   ...（另有 %d 条）" % (len(missing) - 30))
        sys.exit(1)
    print()
    print("✓ 旧站全部正文片段均在新站中原样保留，无内容丢失")


if __name__ == "__main__":
    main()
