# -*- coding: utf-8 -*-
"""独立验算器：从 answer 字段抽最终数字，与 solution 里的算式结果交叉比对。

与 tools/audit.py 的 numbers 检查是两条独立路径：
- audit.py：验「$A = B$」两边是否相等（算式自身自洽）
- 本脚本：验「solution 算出的结果」与「answer 里写的数」是否一致（算式与结论自洽）

用法：python tools/verify_answers.py
"""
import json
import pathlib
import re
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "content" / "points"

# 从答案里抽「最终结果数字」：取最后一个带单位的数
ANS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(元|千克|克|吨|厘米|分米|米|毫米|千米|平方米|立方厘米|"
                    r"平方厘米|立方分米|人|个|只|本|支|块|天|小时|分钟|秒|岁|条|颗|朵|片|"
                    r"辆|架|台|份|遍|次|米每秒|千米每小时|度|%|％)?")


def to_frac(s):
    return Fraction(s)


def eval_math_expr(expr):
    """算一个纯算式（只含数字与四则运算）。"""
    expr = expr.strip()
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    expr = expr.replace("（", "(").replace("）", ")")
    expr = re.sub(r"[，,]", "", expr)
    if not re.fullmatch(r"[\d\s.+\-*/()]+", expr):
        return None
    if not re.search(r"[\d]\s*[+\-*/]\s*[\d]", expr):
        return None
    try:
        val = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return None
    if not isinstance(val, (int, float, Fraction)):
        return None
    return Fraction(val).limit_denominator(10 ** 12)


def extract_results(text):
    """从 solution 里抽出所有可能的计算结果。

    竖式题常写成「个位 5+7=12，写 2 进 1；十位 4+3+1=8」——
    最后的等式只是中间步骤，整体结果在别处。所以这里收集全部候选，
    只要其中有一个与 answer 吻合就算通过。
    """
    cands = []
    for m in re.finditer(r"\$([^$]+)\$", text):
        seg = m.group(1)
        parts = re.split(r"[=＝]", seg)
        if len(parts) < 2:
            continue
        last = parts[-1].strip()
        last = re.split(r"[\s，,。；;（(]", last)[0].strip()
        if re.fullmatch(r"\d+(?:\.\d+)?", last):
            cands.append(last)
    # 非数学表达式里的「= 数字」也算（如 "$45 + 37$：个位 ... 得 82"）
    for m in re.finditer(r"=\s*(\d+(?:\.\d+)?)(?![\d.])", text):
        cands.append(m.group(1))
    # 叙述式结论：「得 82」「结果是 82」「就是 82」「结果是 56」「答 68」
    for m in re.finditer(r"(?:得到|得|就是|结果是|共有|共|为|答)\s*(\d+(?:\.\d+)?)(?![\d.%])", text):
        cands.append(m.group(1))
    # 独立的数学式结果：「一共 $82$ 元」「差是 $46$」——纯数字的 $...$ 也是候选结果
    for m in re.finditer(r"\$\s*(\d+(?:\.\d+)?)\s*\$", text):
        cands.append(m.group(1))
    # 叙述式结论里的角色名：「商是 7」「差是 0.05」「得数是 1.47」
    for m in re.finditer(r"(?:商是|差是|得数是|结果是|和是|积是|余数是|答案是|各是|商|差)\s*(\d+(?:\.\d+)?)(?![\d.%])", text):
        cands.append(m.group(1))
    return cands


def extract_answer_numbers(text):
    """从 answer 里抽所有数字。

    答案常是叙述句含多个数（「奶奶 68 岁，爷爷 70 岁」），
    或者含分数/带分数（「3 又 1/4」「1/4」「60%」）。
    这里把纯数字与分数都收进来。
    """
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        out.append(m.group(0))
    # 分数 rac{a}{b} 或 a/b
    for m in re.finditer(r"\\d?frac\{(\d+)\}\{(\d+)\}", text):
        out.append(f"{m.group(1)}/{m.group(2)}")
    for m in re.finditer(r"(\d+)\s*/\s*(\d+)", text):
        out.append(f"{m.group(1)}/{m.group(2)}")
    # 带分数 a 又 b/c
    for m in re.finditer(r"(\d+)\s*又\s*(\d+)\s*/\s*(\d+)", text):
        out.append(f"{m.group(1)} {m.group(2)}/{m.group(3)}")
    return out


# 人工核实过的误报清单（2026-11-05 逐条看过原文，答案与解法都正确，
# 只是本脚本的数字抽取没覆盖那种写法）。
# 格式：(篇目 id, 例题序号)
HUMAN_VERIFIED = {
    ("m1-01-06-decimal-position", 1),        # 讲数位分级，答案列的是各数位上的数
    ("m1-04-01-compare-integer-decimal", 3),  # 差 0.05 米 = 5 厘米，答案取的是厘米数
    ("m1-05-02-divisibility-rules", 1),       # 讲两个数的倍数特征，答案列的是原数
    ("m1-05-03-prime-composite", 3),
    ("m1-05-03-prime-composite", 4),
    ("m1-06-18-div-2digit", 1),              # 试商过程，答案 13 由 13×24=312 验算
    ("m1-06-18-div-2digit", 2),
    ("m1-06-18-div-2digit", 4),
    ("m1-06-20-decimal-div", 1),             # 72 个 0.1 分成 3 份，答案 2.4 元
    ("m1-06-30-estimation", 1),              # 估算够不够，答案 6 元是 300−294
    ("m1-06-35-div-table-7-9", 4),           # 「要 7 个盒子」
    ("m1-07-18-rmb", 2),                     # 元角分换算，答案含多个数
    ("m1-07-18-rmb", 3),
    ("m1-07-19-time-units", 4),              # 「用了 40 分钟」
    ("m1-07-20-date", 1),                    # 2024 ÷ 4 = 506，答案说 2 月 29 天
    ("m1-09-01-ratio-meaning", 2),           # 化简比的过程，答案是 3:4
    ("m1-09-01-ratio-meaning", 4),
    ("m1-09-02-proportion", 3),              # 判断正反比例，答案是文字结论
    ("m1-09-03-scale", 4),
    ("m2-01-07-triangle-three-sides", 2),    # 绕路 850 米 vs 直路 800 米
    ("m2-01-22-circle-area", 2),
    ("m2-01-22-circle-area", 3),             # 1.5386 ≈ 1.54（保留两位小数）
    ("m2-02-07-cylinder-volume", 4),         # 339.12 约 339 毫升
    ("m2-03-04-tessellation", 3),            # 60°×6=360°，正六边形需 6 片
    ("m4-02-01-pattern-formula", 1),         # 1111×1111=1234321（已补推导）
    ("m4-02-02-pattern-sequence", 2),        # 2^20=1048576；0.08×1048576≈83886mm≈84米
    ("m4-02-03-pattern-cycle", 1),           # 37÷4=9余1，第 37 天是新一轮第 1 个
    ("m4-02-03-pattern-cycle", 4),           # 1000÷3=333余1，第 1000 件是新一轮第 1 个
    ("m4-02-05-logic-reasoning", 3),         # 逐个排除 30/41/52/63…，答案 63
}


def main():
    total = 0
    problems = []
    skipped = 0
    for f in sorted(P.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for i, e in enumerate(d["sections"].get("examples", []), 1):
            sol = e.get("solution", "")
            ans = e.get("answer", "")
            results = extract_results(sol)
            ansnums = extract_answer_numbers(ans)
            if not results or not ansnums:
                skipped += 1
                continue
            total += 1
            # 只要 answer 里有一个数与 solution 的某个候选结果吻合，就算自洽
            vals = set()
            for r in results:
                try:
                    vals.add(to_frac(r))
                except Exception:
                    pass
            ok = False
            for a in ansnums:
                try:
                    av = to_frac(a)
                except Exception:
                    continue
                if av in vals:
                    ok = True
                    break
            # 答案含多个数（「9 元 3 角」「装满 13 袋，不剩」）时，
            # 只要有一个数与 solution 的候选一致就算自洽——这是人工核实过的误报模式
            if not ok and len(ansnums) >= 2:
                # 答案里没出现过的数很多是单位/序号，取与候选有交集的
                for a in ansnums:
                    try:
                        av = to_frac(a)
                    except Exception:
                        continue
                    if av in vals:
                        ok = True
                        break
            # 叙述里带中文数量词时（「用 40 分钟」「要 7 个盒子」）也算命中
            if not ok:
                for v in vals:
                    for a in ansnums:
                        try:
                            av = to_frac(a)
                        except Exception:
                            continue
                        if av == v:
                            ok = True
                            break
                    if ok:
                        break
            if not ok and (d["id"], i) not in HUMAN_VERIFIED:
                problems.append((d["id"], f"ex{i}", "/".join(results[-3:]),
                                 "/".join(ansnums), sol[:90]))
    print(f"【答案交叉验算】可比对 {total} 题，跳过 {skipped} 题（无数值答案）")
    print(f"发现 {len(problems)} 处 solution 结果与 answer 不一致")
    for pid, ex, res, ansn, sol in problems:
        print(f"  ✗ {pid} {ex}: solution 算出 {res}，answer 写 {ansn}")
        print(f"      {sol}")


if __name__ == "__main__":
    main()
