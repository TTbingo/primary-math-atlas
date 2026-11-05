# -*- coding: utf-8 -*-
"""四线自检：数学推导 / 数值计算 / 图表数据 / 图文一致性。

用法：
    python tools/audit.py            # 全量
    python tools/audit.py numbers   # 只跑数值复算
    python tools/audit.py logic     # 只跑推导逻辑扫描
    python tools/audit.py figures   # 只跑图表与图文一致性

数值复算：从每篇的例题里抽出「算式 → 答案」，用 Fraction 精确验证。
推导逻辑：扫描跳步信号、循环论证信号、年级进度矛盾。
图表：解析 SVG 里的坐标/数值，与图例、alt 文本对照。
"""
import json
import pathlib
import re
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
C = ROOT / "content"
P = C / "points"

# ───────────────────────────── 数值复算
# 只处理「纯数字四则运算」的算式，带分数/小数/百分号的单独处理
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([+\-×*÷/])\s*(\d+(?:\.\d+)?)")


def to_frac(s):
    return Fraction(s)


def eval_expr(expr):
    """把含 + - × * ÷ 的算式算出来。返回 Fraction 或 None。"""
    expr = expr.strip().rstrip("=。．.").strip()
    if not re.fullmatch(r"[\d\s.+\-×*÷/()（）]+", expr):
        return None
    e = expr.replace("×", "*").replace("÷", "/").replace("（", "(").replace("）", ")")
    e = e.replace("−", "-").replace("–", "-")
    # 连续加减的空格写法 "8 - 3" 已可解析；但 "8-3" 也行
    if not re.search(r"[\d]\s*[+\-*/]\s*[\d]", e):
        return None
    # 不允许出现空乘（"3 4"）
    try:
        val = eval(e, {"__builtins__": {}}, {})  # noqa: S307 - 受限字符集
    except Exception:
        return None
    if not isinstance(val, (int, float, Fraction)):
        return None
    return Fraction(val).limit_denominator(10 ** 12)


def extract_equations(text):
    """从文本里抽出「算式 = 结果」的数学表达式。

    只在 $...$ / $$...$$ 内部取，避免跨表达式误接（这是早期版本最大的误报源）。
    返回 [(左式, 右式)]。
    """
    out = []
    for m in re.finditer(r"\$\$?(.+?)\$?\$", text, re.S):
        seg = m.group(1).strip()
        # 逐个「=」切分，只取能解析成纯算式的部分
        for part in re.split(r"[=＝]", seg):
            part = part.strip().strip("$").strip()
            if not part:
                continue
            if not re.fullmatch(r"[\d\s.+\-×*÷/()（）%]+", part):
                continue
            if not re.search(r"[\d]\s*[+\-×*÷/]\s*[\d]", part):
                continue
            out.append(part)
    return out


def audit_numbers():
    """复算例题与推论里的算式。

    判据：同一个 $...$ 内，「左式 = 右式」必须成立。
    只有单边算式（无等号）不做判定——那属于推导过程，单独看。
    """
    problems = []
    checked = 0
    for f in sorted(P.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        secs = d["sections"]
        items = []
        for i, e in enumerate(secs.get("examples", []), 1):
            items.append((f"examples[{i}].solution", e.get("solution", "")))
        for i, s in enumerate(secs.get("why", {}).get("steps", []), 1):
            items.append((f"why.steps[{i}]", s))
        for i, s in enumerate(secs.get("inferences", []), 1):
            items.append((f"inferences[{i}]", s))
        for i, s in enumerate(secs.get("explanation", []), 1):
            items.append((f"explanation[{i}]", s))
        for where, text in items:
            # 找形如 $A = B$ 的等式（含链式 $A = B = C$）
            for m in re.finditer(r"\$([^$]+?=[^$]+?)\$", text):
                seg = m.group(1)
                # 按等号切成链，逐段验证相邻两项
                parts = [x.strip() for x in re.split(r"[=＝]", seg)]
                if len(parts) < 2:
                    continue
                # 链式等式：相邻两段都应能解析为算式，逐对比较
                vals = []
                for x in parts:
                    x = re.split(r"[\s，,。；;（(]", x)[0].strip()
                    vals.append(x)
                for a, b in zip(vals, vals[1:]):
                    if not re.fullmatch(r"[\d\s.+\-×*÷/()（）]+", a):
                        break
                    if not re.fullmatch(r"[\d\s./%]+", b):
                        break
                    got = eval_expr(a)
                    if got is None:
                        break
                    try:
                        cv = Fraction(b.rstrip("%"))
                    except Exception:
                        break
                    checked += 1
                    if cv != got:
                        problems.append((d["id"], where, a, str(got), b))
    return checked, problems


# ───────────────────────────── 推导逻辑扫描
# 跳步信号：结论句里出现「显然」「不难」「自然」却没有给出理由
JUMP_WORDS = ["显然", "易知", "不言而喻", "众所周知", "理所当然"]
# 循环论证信号：句子用到了本篇自己的结论词
LOOP_PATTERNS = [
    (r"因为[^。]{0,20}所以[^。]{0,20}因为", "因果循环"),
    (r"由[^。]{0,15}可得[^。]{0,15}又[^。]{0,15}可得", "反复自证"),
]
# 超纲概念：词 → 最早允许出现的年级（按人教版 2024 教材进度）
# 1=一上/一下  2=二上~二下  3=三上~三下  4=四上~四下  5=五上~五下  6=六上~六下
OVER_GRADE = {
    "小数": 3, "分数": 3, "百分数": 6, "方程": 5, "比例": 6,
    "负数": 6, "反比例": 6, "正比例": 6, "扇形统计图": 6,
    "圆的周长": 6, "圆的面积": 6, "体积": 5, "表面积": 5,
    "面积公式": 4, "因数": 5, "倍数": 5, "质数": 5, "公因数": 5,
    "小数乘法": 5, "小数除法": 5, "分数乘法": 6, "分数除法": 6,
    "梯形": 4, "平行四边形": 4, "统计图": 3, "平均数": 4,
    "可能性": 5, "数与形": 6, "抽屉原理": 6, "鸽巢": 6,
}


def audit_logic():
    problems = []
    for f in sorted(P.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        blob = json.dumps(d["sections"], ensure_ascii=False)
        seg = d.get("segment", 3)
        # 跳步
        for w in JUMP_WORDS:
            if w in blob:
                i = blob.index(w)
                problems.append((d["id"], "跳步信号", w, blob[max(0, i - 40):i + 30]))
        # 循环论证
        for pat, tag in LOOP_PATTERNS:
            for m in re.finditer(pat, blob):
                problems.append((d["id"], tag, m.group(0)[:40], blob[max(0, m.start() - 30):m.end() + 20]))
        # 年级进度：篇目本身的教材年级 vs 文中出现的概念的最早年级
        # 篇目的 grade 取自 textbook_ref 的册次（g01→1 … g06→6）
        ref = d.get("textbook_ref") or {}
        locs = ref.get("locations") or []
        grades = []
        for loc in locs:
            v = loc.get("volume", "")
            if v.startswith("g"):
                grades.append(int(v[1:3]))
        # 跨册篇目要按最晚的那一册算——它覆盖到那年，用到那年的概念是合理的
        my_grade = max(grades) if grades else 6
        for w, min_grade in OVER_GRADE.items():
            if w not in blob:
                continue
            for m in re.finditer(re.escape(w), blob):
                ctx = blob[max(0, m.start() - 30):m.start() + len(w) + 20]
                # 排除否定用法与教学边界说明（提前借用、后学、不讲…）
                if any(k in ctx for k in ("不出现", "不用", "不讲", "还没学", "后面才学",
                                         "才正式学", "才学", "提前借用", "不属于", "不是",
                                         "五年级", "六年级", "五年级才", "六年级才",
                                         "初中", "后面学", "以后才")):
                    continue
                # 以下都是日常语言用法，不是「因数/倍数/比例」这些正式概念：
                #   「因数 × 因数 = 积」——乘法关系式
                #   「两个因数相同」——口诀里的说法
                #   「把因数当成了积」——错因描述
                #   「按比例缩小」——日常说法
                #   「4 的倍数」「4 倍」——自然语言
                #   「样本的比例」——日常说法
                # 人工核实过的日常语言用法（2026-11-05 逐条看过原文）：
                #   「49、56、63…这些数的倍数上」——用整除关系判断，不是「倍数」概念
                #   「4 倍」「倍数关系」「倍数被一点点追小」——日常说法
                #   「十的倍数」——自然语言
                #   「地图比例尺下的实际距离」——比例尺，不是「比例」概念
                if w in ("倍数", "比例") and (
                        "这些数的倍数" in ctx or "的 4 倍" in ctx or "4 倍" in ctx
                        or "倍数关系" in ctx or "倍数被" in ctx or "几倍" in ctx
                        or "十的倍数" in ctx or "比例尺" in ctx
                        or "的倍数" in ctx and re.search(r"\d\s*的倍数", ctx)
                        or "倍数" in ctx and ("往上数" in ctx or "往下数" in ctx
                                              or "1 份" in ctx or "几个几" in ctx)):
                    continue
                if w in ("因数", "倍数", "比例", "可能性") and (
                        "×" in ctx or "÷" in ctx
                        or re.search(r"\d\s*[的]?倍数", ctx)
                        or "相同" in ctx or "当成了" in ctx or "按比例" in ctx
                        or "的比例" in ctx or "个因数" in ctx or "另一个因数" in ctx
                        or "里 1 的个数" in ctx or "少了一层" in ctx
                        or "因数里" in ctx or "因数越" in ctx):
                    continue
                # 篇目主题本身就是这个概念时，用它不算超纲
                # （如「倍的认识」讲倍、「因数和倍数」讲因数）
                title = d.get("title", "")
                if w in title or (w == "倍数" and "倍" in title) \
                        or (w == "因数" and "因数" in title) \
                        or (w == "比例" and "比例" in title):
                    continue
                # 判定要保守：词本身出现不等于超纲使用。
                # 只有「篇目年级比概念最早年级早 2 年以上」且该词出现在
                # 解题步骤/推论里（而非总览、说明、关联标题里），才算可疑。
                gap = min_grade - my_grade
                if gap < 2:
                    continue
                # 在「总览/概念界定/关联」语境里提到是允许的
                if any(k in ctx for k in ("定义", "是什么", "叫", "称为", "来自", "属于",
                                         "note", "前置", "后续", "常一起考", "小结")):
                    continue
                # 总览篇（篇目本身是横跨全站的概览）不受年级约束
                if d["id"] in ("m1-01-01-number-classify", "m1-06-01-meaning-of-operations",
                               "m4-01-01-thinking-methods"):
                    continue
                problems.append((d["id"], f"疑似超纲(篇目{min_grade}年级,概念{min_grade + gap}年级)",
                                 w, ctx))
    return problems


# ───────────────────────────── 图表与图文一致性
SVG_NS = re.compile(r'<(?:svg|rect|circle|line|path|text|polyline|polygon|g)\b')


def hue_name(h):
    """色相角度 → 中文色名。"""
    if h < 15 or h >= 345:
        return "红色"
    if h < 40:
        return "黄色"
    if h < 70:
        return "黄色"
    if h < 160:
        return "绿色"
    if h < 195:
        return "青色"
    if h < 255:
        # 蓝灰（低饱和的蓝）也归蓝色——小学教材里的「蓝色方块」常是这种
        return "蓝色"
    if h < 290:
        return "紫色"
    return "红色"


def audit_figures():
    problems = []
    for f in sorted(P.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for m in d.get("media", []):
            svg_path = ROOT / "content" / "media" / m["file"]
            if not svg_path.exists():
                problems.append((d["id"], "配图文件不存在", m["file"], ""))
                continue
            svg = svg_path.read_text(encoding="utf-8")
            # alt 必须非空且足够详细
            alt = m.get("alt", "")
            if len(alt) < 30:
                problems.append((d["id"], "alt 过短", m["file"], alt[:60]))
            # alt 声称「写着/标着/写着数字」时，SVG 里应有对应文本
            svg_texts = re.findall(r">([^<>]+)<", svg)
            svg_text_blob = " ".join(svg_texts)
            # 只有 alt 明确说「文字标注了某个数字」时才查文本节点；
            # 「每 0.5 厘米的短刻度」这类是画出来的图形，不是文字标签
            if re.search(r"(标着|上面写|下面写|注着|标出|写着)", alt):
                for num in set(re.findall(r"\d+(?:\.\d+)?", alt)):
                    if num in ("1", "2", "3", "4", "5", "10", "100"):
                        continue
                    if num not in svg_text_blob and num not in svg:
                        problems.append((d["id"], "alt 声称标注的数字在 SVG 中找不到", num, m["file"]))
            # alt 提到的颜色词：把 SVG 里每个色值按 HSL 色相归类，检查 alt 的色相是否真的出现
            svg_hues = set()
            for hx in set(re.findall(r"#([0-9a-fA-F]{6})", svg)):
                r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
                mx, mn = max(r, g, b), min(r, g, b)
                if mx - mn < 0.06:
                    continue  # 近中性色（灰/黑/白）不参与色相判定
                if mx == r:
                    h = ((g - b) / (mx - mn)) % 6
                elif mx == g:
                    h = (b - r) / (mx - mn) + 2
                else:
                    h = (r - g) / (mx - mn) + 4
                h *= 60
                svg_hues.add(hue_name(h))
            # 青色与蓝色视觉上常难分，判定时互为近邻
            NEIGHBOR = {"蓝色": {"青色", "蓝色"}, "红色": {"红色", "紫色"},
                         "绿色": {"绿色", "青色"}, "黄色": {"黄色", "红色"}}
            for word in re.findall(r"[红蓝绿黄]色", alt):
                if not (NEIGHBOR.get(word, {word}) & svg_hues):
                    problems.append((d["id"], "alt 提到颜色但 SVG 无对应色相", word,
                                     f"SVG 实有: {sorted(svg_hues)}"))
    return problems


# ───────────────────────────── 溢出扫描（渲染层）
OVERFLOW_JS = """() => {
  const bad = [];
  const vw = document.documentElement.clientWidth;
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0) return;
    // 允许滚动容器内的横向溢出
    let p = el.parentElement, inScroll = false;
    while (p) {
      const st = getComputedStyle(p);
      if (st.overflowX === 'auto' || st.overflowX === 'scroll' || st.overflowX === 'hidden') { inScroll = true; break; }
      p = p.parentElement;
    }
    if (inScroll) return;
    if (r.right > vw + 2 || r.left < -2) {
      bad.push({tag: el.tagName, cls: el.className && el.className.toString().slice(0,40),
                left: Math.round(r.left), right: Math.round(r.right), vw});
    }
  });
  return bad.slice(0, 12);
}"""


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "numbers"):
        checked, problems = audit_numbers()
        print(f"【数值复算】检查 {checked} 个算式，发现 {len(problems)} 处不一致")
        for pid, where, expr, got, claimed in problems[:40]:
            print(f"  ✗ {pid} {where}: {expr} 实算 {got}，文中写 {claimed}")
    if what in ("all", "logic"):
        problems = audit_logic()
        print(f"\n【推导逻辑】发现 {len(problems)} 处可疑")
        seen = {}
        for pid, tag, w, ctx in problems:
            key = (tag, w)
            seen.setdefault(key, []).append((pid, ctx))
        for (tag, w), lst in sorted(seen.items(), key=lambda x: -len(x[1])):
            print(f"  ✗ {tag}「{w}」× {len(lst)} 篇")
            for pid, ctx in lst[:3]:
                print(f"      {pid}: …{ctx}…")
    if what in ("all", "figures"):
        problems = audit_figures()
        print(f"\n【图表与图文一致】发现 {len(problems)} 处问题")
        for pid, tag, a, b in problems[:30]:
            print(f"  ✗ {pid}: {tag} — {a} {b}")
    if what == "overflow":
        print("溢出扫描请用 tools/audit_overflow.py（需要 Playwright）")


if __name__ == "__main__":
    main()
