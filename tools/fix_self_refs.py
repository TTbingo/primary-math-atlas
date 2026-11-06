# -*- coding: utf-8 -*-
"""清除 related 里的自引用条目（合并遗留），幂等脚本，--dry 可预览。

背景：2026-11-05 由 162 篇合并为 87 篇时，合并组内成员互指的 related 条目
（A 的「后续」指向同组 B，合并后 A+B 同页）变成了「关联知识点指向自己」。
对标基线 1e844b9 溯源确认：51 条全部指向同组合并兄弟，语义已内化为页内
关系（正文本身就在讲这两半的关系），正确处理是删除。

删除后唯一破坏「三类齐全」校验的 m2-02-06（圆柱圆锥体积，节末篇），
按 m4-04-01 先例补一条 ext: 站外延伸的「后续」。

用法：
    python tools/fix_self_refs.py --dry   # 预览
    python tools/fix_self_refs.py          # 执行
"""
import io
import json
import sys
import glob

ROOT = __file__.rsplit("/tools/", 1)[0] if "/" in __file__ else __file__.rsplit("\\tools\\", 1)[0]
DRY = "--dry" in sys.argv

# 删除自引用后缺「后续」的节末篇，补站外延伸（对标 m4-04-01 的 ext: 先例）
EXT_FOLLOWUP = {
    "m2-02-06-cylinder-and-cone-volume": {
        "id": "ext:初中「相似缩放」——半径和高都变为原来的 k 倍，体积就变为原来的 k³ 倍，比例思维把体积公式再推一步",
        "kind": "后续",
        "note": "圆柱和圆锥的体积是小学体积公式的终点，站内排在它后面的篇目不再以体积为工具，往后的延伸在初中的比例与相似",
    }
}


def main():
    removed = 0
    touched = []
    for f in sorted(glob.glob(ROOT + "/content/points/*.json")):
        d = json.loads(io.open(f, encoding="utf-8").read())
        pid = d["id"]
        rel = d.get("sections", {}).get("related") or []
        kept = [r for r in rel if r.get("id") != pid]
        n_cut = len(rel) - len(kept)
        if n_cut:
            removed += n_cut
            d["sections"]["related"] = kept
            touched.append((f.split("\\")[-1].split("/")[-1], n_cut, [r.get("kind") for r in kept if r.get("kind")]))
        # 补站外后续
        ext = EXT_FOLLOWUP.get(pid)
        if ext and not any(str(r.get("id", "")).startswith("ext:") for r in d["sections"]["related"]):
            d["sections"]["related"].append(ext)
            touched.append((pid + ".json", 0, [r.get("kind") for r in d["sections"]["related"] if r.get("kind")]))
            if not n_cut:
                pass
        if (n_cut or ext) and not DRY:
            io.open(f, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

    print(("DRY " if DRY else "") + f"删除自引用 {removed} 条")
    for fn, n, kinds in touched:
        extra = "" if n else "（+ext 后续）"
        print(f"  {fn}: -{n}{extra}  剩余三类: {sorted(set(kinds))}")


if __name__ == "__main__":
    main()
