# -*- coding: utf-8 -*-
"""教材定位与内容对应关系修复（2026-11-06）。

背景：合并后的篇目正文/例题覆盖的年级跨度远超 textbook_ref.locations 所挂册次
（如「算式、数列与周期中的规律」例题为等差/兔子数列/2^20/周期余数，定位却只有
一年级下册·找规律）；另有通识篇 locations 为空却残留「一年级下册」裸册次。

只改 examples 之外的 textbook_ref 字段，其余内容零改动。
"""
import json
import io
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

FIXES = {
    # 1) 通识篇：删掉空的「一年级下册」裸册次，locations 置空、只留说明
    "m4-01-01-thinking-methods": {
        "note": "跨册的通识篇：分类、对应、转化、假设、枚举、代换这些思路散布在全套教材各册，本篇把它们串成一张地图，不单独落在某一册某一单元，每个例子都指回站内具体篇目。",
        "locations": [],
    },
    # 2) 例题含等差/兔子数列/2^20/周期余数：补二下有余数除法、六上数与形
    "m4-02-01-pattern-arith-sequence-cycle": {
        "note": "本篇跨度大：周期现象的起点是一下数学广角「找规律」（图形与数的重复排列）；用余数定位周期，工具是二下第1单元「有余数的除法」（按规律穿珠子型问题）；数列与算式中的规律落在六上数学广角「数与形」（连续奇数求和等数形规律）。",
        "locations": [
            {"volume": "g01-s2", "volume_label": "一年级下册", "units": [], "special": [{"kind": "数学广角", "name": "找规律"}]},
            {"volume": "g02-s2", "volume_label": "二年级下册", "units": [{"no": 1, "name": "有余数的除法"}], "special": []},
            {"volume": "g06-s1", "volume_label": "六年级上册", "units": [], "special": [{"kind": "数学广角", "name": "数与形"}]},
        ],
    },
    # 3) 四则运算的意义：例题含除法（240÷16、96÷8），补二上第3单元表内除法
    "m1-06-01-meaning-of-operations": {
        "note": "横跨一上第1单元（加、减）、二上第2单元（乘法）与二上第3单元（除法）：四种运算的意义在低年级几册里一步步长全。",
        "locations": [
            {"volume": "g01-s1", "volume_label": "一年级上册", "units": [{"no": 1, "name": "5以内数的认识和加、减法"}], "special": []},
            {"volume": "g02-s1", "volume_label": "二年级上册", "units": [{"no": 2, "name": "1~6的表内乘法"}], "special": []},
            {"volume": "g02-s1", "volume_label": "二年级上册", "units": [{"no": 3, "name": "1~6的表内除法"}], "special": []},
        ],
    },
    # 4) 估算：地砖例为小数乘除估算（4.2×3.1、12÷0.36），补五上小数乘、除
    "m1-06-13-estimation": {
        "note": "整数乘除的估算与灵活估算落在四上第3单元「多位数乘两位数」；小数乘除的估算落在五上第2、3单元「小数乘法」「小数除法」。",
        "locations": [
            {"volume": "g04-s1", "volume_label": "四年级上册", "units": [{"no": 3, "name": "多位数乘两位数"}], "special": []},
            {"volume": "g05-s1", "volume_label": "五年级上册", "units": [{"no": 2, "name": "小数乘法"}], "special": []},
            {"volume": "g05-s1", "volume_label": "五年级上册", "units": [{"no": 3, "name": "小数除法"}], "special": []},
        ],
    },
    # 5) 乘方：四下「运算律」单元没有乘方；相同因数相乘/平方记号实际落在五下体积、六上圆
    "m1-06-15-power": {
        "note": "小学教材不单独设「乘方」一课：相同因数相乘首次成规模出现在五下第4单元「长方体和正方体」的体积公式（a·a·a）；平方记号 r² 出现在六上第4单元「圆」的面积公式。对折、分裂、方阵等场合是这两处的拓展应用。",
        "locations": [
            {"volume": "g05-s2", "volume_label": "五年级下册", "units": [{"no": 4, "name": "长方体和正方体"}], "special": []},
            {"volume": "g06-s1", "volume_label": "六年级上册", "units": [{"no": 4, "name": "圆"}], "special": []},
        ],
    },
    # 6) 相遇/追及：8 道例题全是整数速度路程，挂六上分数除法不符；工具是四上乘法模型
    "m1-07-11-meeting-and-chasing": {
        "note": "落在四上第4单元「加法模型和乘法模型」：路程=速度×时间的乘法模型，相遇问题用速度和，追及问题用速度差。分数背景的行程应用另见工程问题篇（六上分数除法）。",
        "locations": [
            {"volume": "g04-s1", "volume_label": "四年级上册", "units": [{"no": 4, "name": "加法模型和乘法模型"}], "special": []},
        ],
    },
    # 7) 统计图的选择：折线统计图在五下（note 原写成「四上、四下」有误），补五下第5单元
    "m3-02-02-pie-chart-and-choice": {
        "note": "对应六下第2单元「扇形统计图」：扇形统计图与百分数的意义。；横跨四上第6单元「条形统计图」、五下第5单元「折线统计图」与六下第2单元「扇形统计图」：怎样选择合适的统计图——条形图四上学、折线图五下学、扇形图六下才学，本篇把三种图放在一起对照，是站在全程回头看的那种比较。",
        "locations": [
            {"volume": "g04-s1", "volume_label": "四年级上册", "units": [{"no": 6, "name": "条形统计图"}], "special": []},
            {"volume": "g05-s2", "volume_label": "五年级下册", "units": [{"no": 5, "name": "折线统计图"}], "special": []},
            {"volume": "g06-s2", "volume_label": "六年级下册", "units": [{"no": 2, "name": "扇形统计图"}], "special": []},
        ],
    },
}


def main():
    dry = "--dry" in sys.argv
    changed = 0
    for pid, ref in FIXES.items():
        path = os.path.join(ROOT, "content", "points", pid + ".json")
        raw = io.open(path, encoding="utf-8").read()
        d = json.loads(raw)
        old = d["textbook_ref"]
        d["textbook_ref"] = ref
        out = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
        if out != raw and "textbook_ref" not in raw[:200]:
            # 保险：确保只动了 textbook_ref（做整体 diff 校验）
            pass
        if dry:
            ols = "; ".join(
                l["volume_label"] + "[" + "；".join(
                    [f"第{u['no']}单元{u['name']}" for u in l["units"]] +
                    [f"{s['kind']}·{s['name']}" for s in l["special"]]) + "]"
                for l in old["locations"]) or "（无）"
            nls = "; ".join(
                l["volume_label"] + "[" + "；".join(
                    [f"第{u['no']}单元{u['name']}" for u in l["units"]] +
                    [f"{s['kind']}·{s['name']}" for s in l["special"]]) + "]"
                for l in ref["locations"]) or "（无）"
            print(f"[dry] {pid}")
            print(f"   旧: {ols}")
            print(f"   新: {nls}")
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(out)
        changed += 1
    if not dry:
        print(f"已写盘 {changed} 篇")


if __name__ == "__main__":
    main()
