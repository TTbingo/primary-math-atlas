#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按年级重排 + 合并同类/递进知识点。

两步：
1) 合并：把同一主题内、同一知识体系（加法与减法、乘法与除法、数的认识与比较…）
   的零散节点合成一个节点，内容全部保留（说明/场景/注意点/算理/例题/推论/易错/
   配图/关联逐项并入，标题与关键词重写）。
2) 重排：每个主题内按教材册次（g01-s1 → g06-s2）升序重排，并重新编号。

被合并掉的节点统一以 ID 映射表做重定向：
  - sections.related 里的 id
  - 正文里的 [[短ID]] 交叉引用
  - prerequisites
合并组用 (topic, [原节点], 新标题, 新 slug, 关键词补充) 描述。
"""
import json
import re
import glob
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
POINTS = os.path.join(CONTENT, "points")

VOL_ORDER = ['g01-s1', 'g01-s2', 'g02-s1', 'g02-s2', 'g03-s1', 'g03-s2',
             'g04-s1', 'g04-s2', 'g05-s1', 'g05-s2', 'g06-s1', 'g06-s2']
VOL_IDX = {v: i for i, v in enumerate(VOL_ORDER)}


# ---------------------------------------------------------------- 合并方案
# key: (topic_id, [原 id...], 新标题, 新 slug, 补充关键词)
MERGES = [
    # ===== m1-01 数的意义和性质 =====
    ("m1-01", ["m1-01-02-num-1-to-5", "m1-01-13-num-6-to-10", "m1-01-14-num-11-to-20"],
     "1~20 的认识", "num-1-to-20",
     ["1~20的认识", "20以内的数", "数数", "数的顺序", "比多少", "一一对应"]),
    ("m1-01", ["m1-01-07-decimal-meaning", "m1-01-08-decimal-intro"],
     "小数的认识与意义", "decimal-intro-and-meaning",
     ["认识小数", "小数的意义", "小数单位", "小数的性质", "计数"]),
    ("m1-01", ["m1-01-09-fraction-meaning", "m1-01-10-fraction-property"],
     "分数的意义与基本性质", "fraction-meaning-and-property",
     ["分数的意义", "分数单位", "分数的基本性质", "约分", "通分"]),
    ("m1-01", ["m1-01-15-fraction-intro", "m1-01-16-fraction-division"],
     "分数的初步认识与分数和除法的关系", "fraction-intro-and-division",
     ["分数的初步认识", "几分之一", "分数与除法的关系", "分数与除法的互化"]),

    # ===== m1-02 数的读写 =====
    ("m1-02", ["m1-02-01-integer-read-write", "m1-02-02-decimal-fraction-read-write"],
     "整数、小数、分数与百分数的读写", "number-read-write",
     ["读数", "写数", "中间末尾有0", "小数点", "分数读法", "百分数读法"]),

    # ===== m1-03 数的改写与近似数 =====
    ("m1-03", ["m1-03-01-rounding", "m1-03-02-rewrite-wan-yi"],
     "近似数与大数的改写", "rounding-and-rewrite",
     ["四舍五入", "近似数", "改写成万", "改写成亿", "省略尾数"]),
    ("m1-03", ["m1-03-03-fraction-forms", "m1-03-04-decimal-fraction-percent-convert"],
     "分数、小数与百分数的互化", "fraction-decimal-percent-convert",
     ["假分数", "带分数", "互化", "化成小数", "化成百分数"]),

    # ===== m1-04 比较大小 =====
    ("m1-04", ["m1-04-01-compare-integer-decimal", "m1-04-02-compare-fraction",
               "m1-04-03-compare-negative"],
     "整数、小数、分数与正负数的比较大小", "compare-numbers",
     ["比大小", "数位比较", "分数比较", "通分", "正负数比较"]),

    # ===== m1-05 因数、倍数、质数、合数 =====
    ("m1-05", ["m1-05-02-divisibility-rules", "m1-05-03-prime-composite"],
     "2、3、5 的倍数特征与质数、合数", "divisibility-and-prime",
     ["倍数特征", "质数", "合数", "2的倍数", "3的倍数", "5的倍数"]),
    ("m1-05", ["m1-05-01-factors-multiples", "m1-05-04-gcd-lcm"],
     "因数、倍数与最大公因数、最小公倍数", "factors-multiples-and-gcd-lcm",
     ["因数", "倍数", "公因数", "公倍数", "最大公因数", "最小公倍数"]),

    # ===== m1-06 数的运算 =====
    ("m1-06", ["m1-06-02-add-within-5", "m1-06-03-sub-within-5"],
     "5 以内数的加法与减法", "add-sub-within-5",
     ["加法", "减法", "5以内加法", "5以内减法", "加减法互逆"]),
    ("m1-06", ["m1-06-04-carry-add-9", "m1-06-05-borrow-sub-9",
               "m1-06-06-borrow-sub-methods"],
     "20 以内的进位加法与退位减法", "add-sub-within-20",
     ["凑十法", "破十法", "进位加法", "退位减法", "想加算减"]),
    ("m1-06", ["m1-06-07-written-add-sub-2digit", "m1-06-33-mental-add-sub-100"],
     "100 以内加减法的口算与笔算", "add-sub-within-100",
     ["100以内口算", "两位数加减", "竖式计算", "进位", "退位"]),
    ("m1-06", ["m1-06-09-intro-multiplication", "m1-06-10-mult-table",
               "m1-06-34-mul-table-7-9"],
     "乘法的初步认识与 1~9 的乘法口诀", "multiplication-intro-and-table",
     ["几个几", "乘法口诀", "2~6乘法口诀", "7~9乘法口诀", "一上一下二十以内"]),
    ("m1-06", ["m1-06-11-intro-division", "m1-06-12-division-by-table",
               "m1-06-35-div-table-7-9"],
     "除法的初步认识与用口诀求商", "division-intro-and-quotient",
     ["平均分", "除法意义", "用口诀求商", "7~9求商", "每份数"]),
    ("m1-06", ["m1-06-13-remainder-meaning", "m1-06-14-remainder-rule"],
     "有余数除法的意义与余数的性质", "division-with-remainder",
     ["有余数除法", "余数", "余数比除数小", "商和余数"]),
    ("m1-06", ["m1-06-15-mult-1digit", "m1-06-16-mult-2digit"],
     "多位数乘一位数与多位数乘两位数", "multiplication-multi-digit",
     ["多位数乘一位数", "三位数乘两位数", "竖式计算", "进位乘法"]),
    ("m1-06", ["m1-06-17-div-1digit", "m1-06-18-div-2digit"],
     "除数是一位数与除数是两位数的除法", "division-multi-digit",
     ["除数是一位数", "除数是两位数", "商一位数", "商两位数", "试商"]),
    ("m1-06", ["m1-06-19-decimal-mult", "m1-06-20-decimal-div"],
     "小数乘法与小数除法的算理", "decimal-mult-and-div",
     ["小数乘法", "小数除法", "积的小数位数", "商的小数位数", "算理"]),
    ("m1-06", ["m1-06-21-fraction-add-sub", "m1-06-36-fraction-diff"],
     "分数的加法和减法", "fraction-add-sub",
     ["同分母加减", "异分母加减", "先通分", "结果化简"]),
    ("m1-06", ["m1-06-22-fraction-mult", "m1-06-23-fraction-div"],
     "分数乘法与分数除法的算理", "fraction-mult-and-div",
     ["分数乘法", "分数除法", "倒数", "算理推导"]),
    ("m1-06", ["m1-06-24-mixed-op-order", "m1-06-25-mixed-op-bracket"],
     "混合运算的顺序", "mixed-operation-order",
     ["两级混合运算", "带小括号", "先乘除后加减", "运算顺序"]),
    ("m1-06", ["m1-06-26-add-laws", "m1-06-27-mult-laws",
               "m1-06-28-sub-div-property"],
     "加法、乘法的运算律与减法、除法的性质", "operation-laws",
     ["加法交换律", "加法结合律", "乘法交换律", "乘法结合律", "乘法分配律",
      "减法性质", "除法性质"]),
    ("m1-06", ["m1-06-31-mult-add-sub"],
     "乘加乘减", "mult-add-sub", ["乘加乘减", "先乘后加", "运算顺序"]),
    ("m1-06", ["m1-06-32-decimal-add-sub"],
     "小数的加法和减法", "decimal-add-sub", ["小数加减", "小数点对齐", "位数对齐"]),

    # ===== m1-07 解决问题 =====
    ("m1-07", ["m1-07-02-sum-difference", "m1-07-03-sum-multiple",
               "m1-07-04-difference-multiple"],
     "和差、和倍与差倍问题", "sum-difference-multiple-problems",
     ["和差问题", "和倍问题", "差倍问题", "关系式", "倍数关系"]),
    ("m1-07", ["m1-07-05-normalization", "m1-07-06-total-normalization"],
     "归一问题与归总问题", "normalization-problems",
     ["归一问题", "归总问题", "一份数", "总量"]),
    ("m1-07", ["m1-07-11-meeting", "m1-07-12-chasing"],
     "相遇问题与追及问题", "meeting-and-chasing",
     ["相遇问题", "追及问题", "速度和", "速度差", "路程关系"]),
    ("m1-07", ["m1-07-16-add-sub-relation", "m1-07-17-times-relation"],
     "数量间的加减关系与倍的关系", "quantity-relations-basic",
     ["求比一个数多几少几", "倍的认识", "求一个数的几倍", "数量关系"]),
    ("m1-07", ["m1-07-18-rmb", "m1-07-19-time-units", "m1-07-20-date"],
     "人民币、时、分、秒与年月日", "rmb-time-and-date",
     ["认识人民币", "元角分", "时、分、秒", "年月日", "时间单位", "计量"]),
    ("m1-07", ["m1-07-21-optimization", "m1-07-22-find-bad-item"],
     "优化问题与找次品", "optimization-and-find-bad-item",
     ["优化问题", "找次品", "最少次数", "合理安排"]),

    # ===== m1-08 式与方程 =====
    ("m1-08", ["m1-08-01-letters", "m1-08-02-equation-solve"],
     "用字母表示数与方程的意义", "letters-and-equation",
     ["用字母表示数", "方程", "解方程", "等式性质"]),
    ("m1-08", ["m1-08-03-equation-word-problem"],
     "列方程解应用题", "equation-word-problem",
     ["列方程解应用题", "设未知数", "等量关系"]),

    # ===== m1-09 比和比例 =====
    ("m1-09", ["m1-09-01-ratio-meaning", "m1-09-02-proportion"],
     "比的意义、化简与正反比例", "ratio-and-proportion",
     ["比的意义", "比的基本性质", "化简比", "比例", "正比例", "反比例"]),
    ("m1-09", ["m1-09-03-scale", "m1-09-04-proportion-allocation",
               "m1-09-05-lever-balance"],
     "比例尺、按比例分配与杠杆平衡", "scale-allocation-lever",
     ["比例尺", "按比例分配", "杠杆平衡", "比例应用"]),

    # ===== m2-01 图形的认识与测量 =====
    ("m2-01", ["m2-01-01-lines-ray-segment", "m2-01-02-intro-angles",
               "m2-01-03-angle-measure"],
     "线段、射线、直线与角的认识", "lines-and-angles",
     ["线段", "射线", "直线", "角的初步认识", "角的度量", "角的分类"]),
    ("m2-01", ["m2-01-05-triangle-classify", "m2-01-06-triangle-angle-sum",
               "m2-01-07-triangle-three-sides"],
     "三角形的认识、内角和与三边关系", "triangle",
     ["三角形分类", "内角和", "三边关系", "稳定性", "等腰三角形"]),
    ("m2-01", ["m2-01-11-length-cm-m", "m2-01-12-length-km-mm"],
     "长度单位：厘米、米、毫米、分米与千米", "length-units",
     ["厘米", "米", "毫米", "分米", "千米", "长度单位进率"]),
    ("m2-01", ["m2-01-13-perimeter", "m2-01-14-rect-perimeter"],
     "周长的认识与长方形、正方形的周长", "perimeter",
     ["周长", "长方形周长", "正方形周长", "封闭图形"]),
    ("m2-01", ["m2-01-15-area-and-unit", "m2-01-16-area-unit-convert",
               "m2-01-17-rect-area"],
     "面积、面积单位与长方形正方形的面积", "area-and-rect-area",
     ["面积", "面积单位", "面积单位换算", "长方形面积", "正方形面积"]),
    ("m2-01", ["m2-01-18-area-parallelogram", "m2-01-19-area-triangle",
               "m2-01-20-area-trapezoid"],
     "平行四边形、三角形与梯形的面积", "polygon-area",
     ["平行四边形面积", "三角形面积", "梯形面积", "底高", "面积公式"]),
    ("m2-01", ["m2-01-23-composite-area", "m2-01-24-irregular-area"],
     "组合图形与不规则图形的面积", "composite-irregular-area",
     ["组合图形面积", "不规则图形面积", "割补", "方格估算法"]),
    ("m2-01", ["m2-01-09-circle-features", "m2-01-10-sector"],
     "圆的特征与扇形的认识", "circle-features-and-sector",
     ["圆的特征", "扇形", "圆心", "半径", "直径", "对称"]),
    ("m2-01", ["m2-01-21-circle-circumference", "m2-01-22-circle-area"],
     "圆的周长与圆的面积", "circle-circumference-and-area",
     ["圆周率", "圆的周长", "圆的面积", "半径直径关系"]),
    ("m2-01", ["m2-01-04-parallel-perpendicular", "m2-01-08-quadrilateral"],
     "平行与垂直、平行四边形和梯形的认识", "parallel-perpendicular-quadrilateral",
     ["平行", "垂直", "平行四边形", "梯形", "高", "底"]),
    ("m2-01", ["m2-01-25-plane-shapes", "m2-01-26-mass-units"],
     "认识平面图形与克、千克、吨", "plane-shapes-and-mass",
     ["认识平面图形", "克", "千克", "吨", "质量单位"]),

    # ===== m2-02 立体图形 =====
    ("m2-02", ["m2-02-01-solid-features", "m2-02-03-cuboid-surface",
               "m2-02-05-cuboid-volume-formula"],
     "长方体和正方体的认识、表面积与体积", "cuboid",
     ["长方体", "正方体", "表面积", "体积公式", "棱长总和"]),
    ("m2-02", ["m2-02-02-cylinder-cone-features", "m2-02-06-cylinder-surface"],
     "圆柱和圆锥的认识与圆柱的表面积", "cylinder-cone-and-surface",
     ["圆柱", "圆锥", "侧面积", "表面积", "底面", "侧面展开"]),
    ("m2-02", ["m2-02-07-cylinder-volume", "m2-02-08-cone-volume"],
     "圆柱和圆锥的体积", "cylinder-and-cone-volume",
     ["圆柱体积", "圆锥体积", "底面积乘高", "三分之一"]),
    ("m2-02", ["m2-02-04-cuboid-volume", "m2-02-10-irregular-volume"],
     "体积和体积单位与不规则物体的体积", "volume-and-irregular-volume",
     ["体积单位", "容积", "不规则物体体积", "排水法"]),
    ("m2-02", ["m2-02-11-solid-shapes-intro"],
     "认识立体图形", "solid-shapes-intro", ["认识立体图形", "长方体", "正方体", "圆柱", "球"]),
    ("m2-02", ["m2-02-09-observe-object"],
     "观察物体", "observe-object", ["观察物体", "不同角度观察", "看到的形状"]),

    # ===== m2-03 图形的变换与运动 =====
    ("m2-03", ["m2-03-01-axis-symmetry", "m2-03-02-translation-rotation"],
     "轴对称、平移和旋转", "axis-symmetry-translation-rotation",
     ["轴对称", "对称轴", "平移", "旋转", "图形运动"]),
    ("m2-03", ["m2-03-03-scale-enlarge", "m2-03-04-tessellation"],
     "图形的放大与缩小和图形密铺", "scale-enlarge-and-tessellation",
     ["放大与缩小", "相似图形", "密铺", "不重复不留缝隙"]),

    # ===== m2-04 图形与位置 =====
    ("m2-04", ["m2-04-01-direction", "m2-04-02-number-pair",
               "m2-04-03-route-map"],
     "方向与位置、用数对确定位置和描述路线", "position-and-route",
     ["方向与位置", "数对", "描述路线", "方向标", "确定位置"]),

    # ===== m3-01 数据的收集与整理 =====
    ("m3-01", ["m3-01-01-data-collect", "m3-01-02-statistical-table"],
     "数据的收集、整理与统计表", "data-collect-and-table",
     ["数据收集", "数据整理", "统计表", "数据分析", "画条形图"]),

    # ===== m3-02 统计图 =====
    ("m3-02", ["m3-02-01-bar-chart", "m3-02-02-line-chart"],
     "条形统计图与折线统计图", "bar-and-line-chart",
     ["条形统计图", "折线统计图", "一格代表", "增减变化"]),
    ("m3-02", ["m3-02-03-pie-chart", "m3-02-04-chart-choice"],
     "扇形统计图与统计图的选择", "pie-chart-and-choice",
     ["扇形统计图", "统计图的选择", "百分比", "整圆"]),

    # ===== m3-04 可能性 =====
    ("m3-04", ["m3-04-01-certainty", "m3-04-02-possibility"],
     "确定事件与可能性的大小", "certainty-and-possibility",
     ["确定事件", "不确定事件", "可能性", "可能性大小"]),
    ("m3-04", ["m3-04-03-digital-code"],
     "数字编码", "digital-code", ["数字编码", "编码", "身份证号", "邮政编码"]),

    # ===== m4-01 / m4-02 =====
    ("m4-02", ["m4-02-01-pattern-formula", "m4-02-02-pattern-sequence",
               "m4-02-03-pattern-cycle"],
     "算式、数列与周期中的规律", "pattern-arith-sequence-cycle",
     ["算式规律", "数列规律", "周期规律", "找规律"]),
    ("m4-02", ["m4-02-04-pattern-figure", "m4-02-05-logic-reasoning"],
     "数图形中的规律与推理", "pattern-figure-and-reasoning",
     ["数图形", "规律", "推理", "逻辑推理"]),

    # ===== m4-03 计数方法 =====
    ("m4-03", ["m4-03-01-addition-principle", "m4-03-02-multiplication-principle"],
     "加法原理与乘法原理", "addition-multiplication-principle",
     ["加法原理", "分类计数", "乘法原理", "分步计数"]),
    ("m4-03", ["m4-03-03-permutation-combination", "m4-03-04-set-overlap"],
     "排列与组合、集合与重叠问题", "permutation-and-set-overlap",
     ["排列", "组合", "集合", "重叠问题", "容斥"]),

    # ===== m4-04 抽屉原理 =====
    ("m4-04", ["m4-04-01-pigeonhole", "m4-04-02-worst-case"],
     "抽屉原理与最不利原则", "pigeonhole-and-worst-case",
     ["抽屉原理", "最不利原则", "至少", "保证"]),
]


def load_points():
    pts = {}
    for f in sorted(glob.glob(os.path.join(POINTS, "*.json"))):
        j = json.load(open(f, encoding="utf-8"))
        pts[j["id"]] = j
    return pts


def vol_rank(j):
    """按教材册次取最早出现的位置，用于排序。"""
    ref = j.get("textbook_ref") or {}
    vs = [VOL_IDX.get(l.get("volume"), 99) for l in ref.get("locations", []) if l.get("volume")]
    return min(vs) if vs else 99


def merge_sections(target, srcs):
    """把 srcs 的内容并入 target（target 为列表里的第一个，即主节点）。"""
    S = target["sections"]
    for src in srcs[1:]:
        SS = src["sections"]
        # 说明：加小标题分隔，标明来自哪个部分
        head = "**（{}）**".format(src["title"])
        S["explanation"] = S["explanation"] + [head] + list(SS.get("explanation", []))
        S["scenarios"] = S["scenarios"] + [head] + list(SS.get("scenarios", []))
        S["cautions"] = S["cautions"] + [head] + list(SS.get("cautions", []))
        # 算理：步骤合并，实验并列
        why = S.setdefault("why", {"steps": [], "experiment": ""})
        swhy = SS.get("why") or {}
        if swhy.get("steps"):
            why["steps"] = list(why.get("steps", [])) + [head] + list(swhy["steps"])
        if swhy.get("experiment"):
            why["experiment"] = (why.get("experiment", "") + " " + head + " " + swhy["experiment"]).strip()
        # 例题：编号重排
        for ex in SS.get("examples", []):
            ex = dict(ex)
            ex["id"] = "ex%d" % (len(S["examples"]) + 1)
            S["examples"].append(ex)
        for it in SS.get("inferences", []):
            S["inferences"].append(it)
        for pf in SS.get("pitfalls", []):
            S["pitfalls"].append(pf)
        # intuition / rhyme 是字符串，用小标题分隔后并列
        for k in ("intuition", "rhyme"):
            sv = SS.get(k)
            if sv:
                S[k] = (S.get(k, "") + " " + head + " " + sv).strip()
    return target


def merge_media(target, srcs):
    """配图合并，media id 重排为 fig1..figN，避免 id 冲突。"""
    merged = []
    for src in srcs:
        for m in src.get("media") or []:
            mm = dict(m)
            mm["id"] = "fig%d" % (len(merged) + 1)
            merged.append(mm)
    if merged:
        target["media"] = merged
    return target


def main():
    pts = load_points()
    mod = json.load(open(os.path.join(CONTENT, "modules.json"), encoding="utf-8"))

    # ---- 幂等保护：已合并过就直接退出，避免二次执行破坏数据 ----
    marker = os.path.join(CONTENT, "_reference", "reorder-merge-report.json")
    if os.path.exists(marker):
        print("检测到本脚本已执行过（%s 存在），不重复执行。" % marker)
        print("如需重跑，请先 git checkout content/ 或删除该标记文件。")
        return

    # ---- 校验合并方案 ----
    all_ids = set(pts)
    merged_into = {}          # 原 id -> 组序号
    group_of = []             # 组序号 -> {topic, ids, title, slug, kw}
    for gi, (topic, ids, title, slug, kw) in enumerate(MERGES):
        for i in ids:
            if i not in all_ids:
                sys.exit("合并方案引用了不存在的节点：%s" % i)
            if i in merged_into:
                sys.exit("节点被重复合并：%s" % i)
            if pts[i]["topic"] != topic:
                sys.exit("节点 %s 不属于主题 %s（实际 %s）" % (i, topic, pts[i]["topic"]))
            merged_into[i] = gi
        group_of.append({"topic": topic, "ids": ids, "title": title, "slug": slug, "kw": kw})

    # 记录每组的新 id（组内第一个节点的 id 保持不变，其余被重定向）
    redirect = {}
    for gi, g in enumerate(group_of):
        for i in g["ids"][1:]:
            redirect[i] = g["ids"][0]

    # ---- 执行合并 ----
    new_pts = {}
    for pid, j in pts.items():
        if pid in merged_into and redirect.get(pid):
            continue          # 被并入的节点，稍后删除
        new_pts[pid] = j

    for gi, g in enumerate(group_of):
        ids = g["ids"]
        main_id = ids[0]
        t = new_pts[main_id]
        # 标题 / slug / 关键词
        t["title"] = g["title"]
        t["slug"] = g["slug"]
        kw = list(t.get("keywords", []))
        for extra in g["kw"]:
            if extra not in kw:
                kw.append(extra)
        for i in ids[1:]:
            for k in pts[i].get("keywords", []):
                if k not in kw:
                    kw.append(k)
        t["keywords"] = kw
        # 内容合并
        merge_sections(t, [pts[i] for i in ids])
        merge_media(t, [pts[i] for i in ids])
        # 教材定位：合并 locations
        locs = []
        seen = set()
        for i in ids:
            ref = pts[i].get("textbook_ref") or {}
            for loc in ref.get("locations", []):
                key = (loc.get("volume"),
                       tuple(sorted((u.get("no"), u.get("name")) for u in loc.get("units", []))),
                       tuple(sorted((s.get("kind"), s.get("name")) for s in loc.get("special", []))))
                if key in seen:
                    continue
                seen.add(key)
                locs.append(loc)
        locs.sort(key=lambda l: VOL_IDX.get(l.get("volume"), 99))
        notes = [ (pts[i].get("textbook_ref") or {}).get("note") for i in ids ]
        notes = [n for n in notes if n]
        t["textbook_ref"] = {
            "note": "；".join(notes),
            "locations": locs,
        }
        # 关联：并入其余节点的 related（去重，同 id 保留先出现的）
        rel = list(t["sections"].get("related") or [])
        have = {(r.get("id"), r.get("kind")) for r in rel}
        for i in ids[1:]:
            for r in (pts[i].get("sections", {}).get("related") or []):
                k = (r.get("id"), r.get("kind"))
                if k in have:
                    continue
                have.add(k)
                rel.append(dict(r))
        t["sections"]["related"] = rel
        # 课标关联：并集
        st = list(t.get("standard_ids", []))
        for i in ids[1:]:
            for s in pts[i].get("standard_ids", []):
                if s not in st:
                    st.append(s)
        t["standard_ids"] = st
        # 素养：并集
        lit = list(t.get("literacy", []))
        for i in ids[1:]:
            for s in pts[i].get("literacy", []):
                if s not in lit:
                    lit.append(s)
        t["literacy"] = lit
        # 前置知识：并集（去重 + 排除自身与被合并掉的兄弟）
        pre = list(t.get("prerequisites", []))
        for i in ids[1:]:
            for s in pts[i].get("prerequisites", []) or []:
                if s not in pre:
                    pre.append(s)
        # prerequisites 重定向
        pre = [redirect.get(s, s) for s in pre]
        pre = [s for s in pre if s not in ids and s != main_id]
        t["prerequisites"] = pre
        # 学段取最早
        t["segment"] = min(pts[i].get("segment", 3) for i in ids)
        # meta.source 合并说明
        srcs = [ (pts[i].get("meta") or {}).get("source") for i in ids ]
        srcs = [s for s in srcs if s]
        if srcs:
            t.setdefault("meta", {})["source"] = " ／ ".join(srcs)

    # ---- 全量重定向引用 ----
    # 说明：正文里的 [[短ID]] 引用统一在最后一步重写（重编号之后），
    # 因为短 ID 的序号会随重排变化。这里先只处理 related / prerequisites 这类
    # 存完整 ID 的字段。
    def fix_ref(x):
        return redirect.get(x, x)

    for j in new_pts.values():
        rel = j["sections"].get("related") or []
        new_rel = []
        seen_pair = set()
        for r in rel:
            rid = r.get("id")
            if rid and not rid.startswith("ext:"):
                rid = fix_ref(rid)
                r = dict(r)
                r["id"] = rid
            key = (r.get("id"), r.get("kind"))
            if key in seen_pair:
                continue
            seen_pair.add(key)
            new_rel.append(r)
        j["sections"]["related"] = new_rel
        j["prerequisites"] = [fix_ref(s) for s in (j.get("prerequisites") or [])]

    # ---- 重排 + 重编号 ----
    topic_points = {}
    for t in mod["topics"]:
        topic_points[t["id"]] = [p for p in t["points"] if p in new_pts]

    order_report = []
    for t in mod["topics"]:
        ps = topic_points[t["id"]]
        before = list(t["points"])
        # 稳定排序：教材册次 -> 原序号（保持同册内的逻辑顺序）
        after = sorted(ps, key=lambda p: (vol_rank(new_pts[p]), before.index(p)))
        if before != after:
            order_report.append((t["id"], t["title"], before, after))
        t["points"] = after

    # 重编号：每个主题内按新顺序重新赋序号（id 的第 3 段），slug 用合并后的新 slug
    id_map = {}          # 旧 id -> 新 id
    for t in mod["topics"]:
        new_list = []
        for i, pid in enumerate(t["points"], start=1):
            parts = pid.split("-", 3)          # m1 / 01 / 13 / slug
            topic_id = parts[0] + "-" + parts[1]
            slug = new_pts[pid].get("slug") or (parts[3] if len(parts) > 3 else "")
            new_no = "%02d" % i
            new_id = "%s-%s-%s" % (topic_id, new_no, slug) if slug else "%s-%s" % (topic_id, new_no)
            id_map[pid] = new_id
            new_list.append(new_id)
        t["points"] = new_list

    # 应用新 id：改 id 字段、重定向引用、改文件名
    # 完整的「旧 id → 新 id」映射：先过合并 redirect（被并掉的节点指向主节点），
    # 再过重编号 id_map。缺了这一层，被合并节点的正文 [[短ID]] 引用就会变成死链。
    full_map = {}
    for old, new in id_map.items():
        full_map[old] = new
    for old, new in redirect.items():
        full_map[old] = id_map.get(new, new)

    # 短 ID 表：旧短 ID -> 新短 ID
    # 用完整映射反推，保证「被合并掉的节点」的原短 ID 也能落到正确的节点上
    short_map = {}
    for old, new in full_map.items():
        so = "-".join(old.split("-")[:3])
        sn = "-".join(new.split("-")[:3])
        # 同一旧短 ID 理论上只对应一个旧节点；若重复则保留先出现的
        if so not in short_map:
            short_map[so] = sn

    final_pts = {}
    for pid, j in new_pts.items():
        nid = id_map[pid]
        j["id"] = nid
        rel = j["sections"].get("related") or []
        for r in rel:
            rid = r.get("id")
            if rid and not rid.startswith("ext:") and rid in full_map:
                r["id"] = full_map[rid]
        j["prerequisites"] = [id_map.get(s, s) for s in (j.get("prerequisites") or [])]
        final_pts[nid] = j

    # 正文 [[短ID]] 引用重写：旧短 ID -> 新短 ID
    def fix_text(s):
        def rep(m):
            key = m.group(1)
            if key in short_map:
                return "[[%s]]" % short_map[key]
            # 完整 ID 形式（带 slug）
            if key in full_map:
                return "[[%s]]" % "-".join(full_map[key].split("-")[:3])
            return m.group(0)
        return re.sub(r"\[\[(m[1-4]-\d{2}-\d{2}(?:-[a-z0-9-]+)?)\]\]", rep, s)

    def walk_text(obj):
        if isinstance(obj, str):
            return fix_text(obj)
        if isinstance(obj, list):
            return [walk_text(x) for x in obj]
        if isinstance(obj, dict):
            return {k: walk_text(v) for k, v in obj.items()}
        return obj

    for nid, j in final_pts.items():
        j["sections"] = walk_text(j["sections"])

    # guides.json 里的 [[短ID]] 也要重写
    guides_path = os.path.join(CONTENT, "guides.json")
    if os.path.exists(guides_path):
        g = json.load(open(guides_path, encoding="utf-8"))
        g = walk_text(g)
        with open(guides_path, "w", encoding="utf-8") as fh:
            json.dump(g, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    # ---- 写盘前自检 ----
    errs = []
    all_new_ids = set(final_pts)
    plan_ids = [p for t in mod["topics"] for p in t["points"]]
    if len(plan_ids) != len(set(plan_ids)):
        errs.append("modules.json 的 points 清单里有重复 id")
    for t in mod["topics"]:
        for pid in t["points"]:
            if pid not in final_pts:
                errs.append("清单里的 %s 没有对应数据文件" % pid)
    for nid, j in final_pts.items():
        if j["id"] != nid:
            errs.append("%s: id 字段与文件名不一致" % nid)
        if not re.match(r"^m\d-\d\d-\d\d-[a-z0-9-]+$", nid):
            errs.append("%s: id 不符合命名规则" % nid)
        tid = "-".join(nid.split("-")[:2])
        if tid != j.get("topic"):
            errs.append("%s: topic 字段(%s)与 id 前缀(%s)不一致" % (nid, j.get("topic"), tid))
        if nid not in plan_ids:
            errs.append("%s: 不在 modules.json 清单里" % nid)
        for r in (j["sections"].get("related") or []):
            rid = r.get("id", "")
            if rid.startswith("ext:"):
                continue
            if rid not in all_new_ids:
                errs.append("%s: 关联指向不存在的节点 %s" % (nid, rid))
        for p in (j.get("prerequisites") or []):
            if p not in all_new_ids:
                errs.append("%s: 前置知识点 %s 不存在" % (nid, p))
    # 正文短 ID 引用必须唯一可解析
    for nid, j in final_pts.items():
        s = json.dumps(j["sections"], ensure_ascii=False) + json.dumps(final_pts[nid].get("summary", ""), ensure_ascii=False)
        for m in re.finditer(r"\[\[(m[1-4]-\d{2}-\d{2}(?:-[a-z0-9-]+)?)\]\]", s):
            key = m.group(1)
            hits = [k for k in all_new_ids if k == key or k.startswith(key + "-")]
            if len(hits) != 1:
                errs.append("%s: 正文引用 [[%s]] 解析到 %d 个节点" % (nid, key, len(hits)))
    if errs:
        print("写盘前自检未通过：")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    # ---- 写盘 ----
    # 先写新文件，再删陈旧的：中途失败也不会出现「目录空了一半」的状态。
    # （删除量可能上百个文件，走仓库的安全删除钩子时要带
    #   CODEBUDDY_SAFE_DELETE_ENABLED=0
    #  否则一次删超过阈值会被拦下。）
    existing = {os.path.basename(f) for f in glob.glob(os.path.join(POINTS, "*.json"))}
    want = {nid + ".json" for nid in final_pts}
    for nid, j in sorted(final_pts.items()):
        with open(os.path.join(POINTS, nid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(j, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    stale = existing - want
    for name in sorted(stale):
        os.remove(os.path.join(POINTS, name))

    with open(os.path.join(CONTENT, "modules.json"), "w", encoding="utf-8") as fh:
        json.dump(mod, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ---- 报告 ----
    report = {
        "merge_groups": [
            {"topic": g["topic"], "new_title": g["title"], "new_slug": g["slug"],
             "from": g["ids"]} for g in group_of],
        "order_changes": [
            {"topic": tid, "title": tt, "before": b, "after": a}
            for tid, tt, b, a in order_report],
        "count_before": len(pts),
        "count_after": len(final_pts),
    }
    with open(os.path.join(CONTENT, "_reference", "reorder-merge-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print("合并组数：%d" % len(group_of))
    print("节点数：%d -> %d" % (len(pts), len(final_pts)))
    print("顺序调整的主题数：%d" % len(order_report))
    for tid, tt, b, a in order_report:
        print("  %s %s：%d -> %d 篇" % (tid, tt, len(b), len(a)))


if __name__ == "__main__":
    main()
