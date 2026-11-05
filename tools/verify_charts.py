# -*- coding: utf-8 -*-
"""统计图 SVG 数据验证：解析图形几何，与坐标轴刻度、标签数字比对。

覆盖三类图：
- 条形统计图：rect 的高度 ↔ 纵轴刻度值 ↔ 条顶标签
- 折线统计图：polyline 的点 ↔ 纵轴刻度值
- 扇形统计图：path 的弧度占比 ↔ 百分比标签

用法：python tools/verify_charts.py
"""
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEDIA = ROOT / "content" / "media"
P = ROOT / "content" / "points"


def parse_rects(svg):
    """取所有 <rect> 的 x/y/width/height。"""
    out = []
    for m in re.finditer(r"<rect\b([^>]*)>", svg):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        try:
            out.append({k: float(attrs[k]) for k in ("x", "y", "width", "height") if k in attrs})
        except (KeyError, ValueError):
            continue
    return out


def parse_texts(svg):
    """取所有 <text> 的内容与坐标。"""
    out = []
    for m in re.finditer(r"<text\b([^>]*)>([^<]*)</text>", svg):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        x = float(attrs.get("x", 0))
        y = float(attrs.get("y", 0))
        out.append((x, y, m.group(2).strip()))
    return out


def parse_axis_ticks(svg):
    """从纵轴刻度文本里取 (值, y坐标)。刻度文本通常是纯数字，x 在轴线左侧。"""
    ticks = []
    for x, y, t in parse_texts(svg):
        t = t.strip()
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            ticks.append((float(t), y))
    return ticks


def parse_polylines(svg):
    out = []
    for m in re.finditer(r"<polyline\b([^>]*)>", svg):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        pts = attrs.get("points", "")
        coords = []
        for pair in pts.split():
            if "," in pair:
                a, b = pair.split(",")[:2]
                try:
                    coords.append((float(a), float(b)))
                except ValueError:
                    pass
        if coords:
            out.append(coords)
    return out


def build_scale(svg):
    """建立 y 坐标 → 数值的线性映射。

    判据：纵轴刻度标签的 x 坐标相同（同一列），且该 x 是所有数字文本里
    出现次数最多的——条形上方的数据标签 x 各不相同，不会干扰。
    返回 (y0, v0, k)，使 value = v0 + (y - y0) * k
    """
    from collections import Counter
    nums = [(x, y, t) for x, y, t in parse_texts(svg)
            if re.fullmatch(r"\d+(?:\.\d+)?", t.strip())]
    if len(nums) < 2:
        return None
    axis_x = Counter(round(x, 1) for x, _, _ in nums).most_common(1)[0][0]
    axis_ticks = sorted([(float(t), y) for x, y, t in nums
                          if abs(x - axis_x) < 1.0], key=lambda v: v[1])
    if len(axis_ticks) < 2:
        return None
    v_top, y_top = axis_ticks[0]
    v_bot, y_bot = axis_ticks[-1]
    if abs(y_top - y_bot) < 1e-9:
        return None
    k = (v_bot - v_top) / (y_bot - y_top)   # k 为负：y 增大值减小
    return (y_top, v_top, k)


def axis_x_of(texts):
    """轴刻度标签所在的 x（数字文本里出现次数最多的那个 x）。"""
    from collections import Counter
    nums = [x for x, _, t in texts if re.fullmatch(r"\d+(?:\.\d+)?", t.strip())]
    if not nums:
        return -9999
    return Counter(round(x, 1) for x in nums).most_common(1)[0][0]


def value_of(y, scale):
    y0, v0, k = scale
    return v0 + (y - y0) * k


def check_bar_chart(svg, name):
    """条形统计图：条形高度代表的值，应与条顶标签数字一致。

    做法：建立 y→值 的线性映射，条形底端应是 0，条顶 y 对应的值即条形代表的数。
    """
    problems = []
    scale = build_scale(svg)
    if not scale:
        return problems
    rects = parse_rects(svg)
    texts = parse_texts(svg)
    # 竖条：高度明显大于宽度
    bars = [r for r in rects if r.get("height", 0) > r.get("width", 0) * 1.2
            and r.get("height", 0) > 3]
    if not bars:
        return problems
    base = max(r["y"] + r["height"] for r in bars)
    base_val = value_of(base, scale)
    # 条顶标签：在条形水平范围内、y 在条顶附近
    for r in bars:
        top = r["y"]
        cx = r["x"] + r["width"] / 2
        # 标签按 x 位置匹配（在条形的水平范围内），
        # 不依赖 y——故意改错条形高度时标签位置也会动，用 y 会漏检
        lab = None
        for x, y, t in texts:
            if not re.fullmatch(r"\d+(?:\.\d+)?", t.strip()):
                continue
            if r["x"] - 4 <= x <= r["x"] + r["width"] + 4:
                # 排除轴刻度那一列
                if abs(x - axis_x_of(texts)) < 1.0:
                    continue
                lab = float(t)
                break
        if lab is None:
            continue
        # 判据一：条形底端必须落在 0 上（条形统计图的基本要求）
        bottom_val = value_of(r["y"] + r["height"], scale)
        if abs(bottom_val) > 0.6:
            problems.append((name, f"条形底端在 {bottom_val:.2f} 处，不在 0 上"))
        # 判据二：条顶对应的值应等于标签数字
        # （刻度文字基线比网格线低几像素，所以用条形自身的底端作零点更准）
        represented = value_of(top, scale) - bottom_val
        if abs(represented - lab) > max(0.51, abs(lab) * 0.03):
            problems.append((name, f"条形高度代表 {represented:.2f}，标签写 {lab}"))
    return problems


def check_line_chart(svg, name):
    """折线统计图：每个数据点的 y 坐标对应的值，应与标签数字一致。"""
    problems = []
    scale = build_scale(svg)
    if not scale:
        return problems
    polys = parse_polylines(svg)
    if not polys:
        return problems
    texts = parse_texts(svg)
    for coords in polys:
        for (x, y) in coords:
            v = value_of(y, scale)
            # 找附近的标签
            found = None
            for tx, ty, t in texts:
                if re.fullmatch(r"\d+(?:\.\d+)?", t.strip()) and abs(tx - x) < 24 and abs(ty - (y - 6)) < 16:
                    found = float(t)
                    break
            if found is None:
                continue
            if abs(v - found) > max(0.51, abs(found) * 0.05):
                problems.append((name, f"折线点在 y={y} 对应值 {v:.2f}，标签写 {found}"))
    return problems


def check_pie_chart(svg, name):
    """扇形统计图：每个扇形角度占比，应与百分比标签一致。"""
    problems = []
    paths = re.findall(r"<path\b([^>]*)/?>", svg)
    pcts = []
    for x, y, t in parse_texts(svg):
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", t.strip())
        if m:
            pcts.append(float(m.group(1)))
    if not pcts:
        return problems
    # 找扇形：path 的 d 里含 A（弧线）
    arcs = []
    for attrs in paths:
        d = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', attrs))
        dd = d.get("d", "")
        if "A" in dd:
            arcs.append(dd)
    if not arcs:
        return problems
    for dd in arcs:
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", dd)]
        if len(nums) < 5:
            continue
        # 常见格式: M cx cy L x1 y1 A r r 0 largeArc 1 x2 y2
        # 提取半径与端点，算中心角
        rx = nums[-7] if len(nums) >= 7 else None
        try:
            cx, cy = nums[0], nums[1]
            x1, y1 = nums[2], nums[3]
            x2, y2 = nums[-2], nums[-1]
            a1 = math.atan2(y1 - cy, x1 - cx)
            a2 = math.atan2(y2 - cy, x2 - cx)
            ang = math.degrees(a2 - a1)
            # SVG 弧线的 sweep-flag=1 表示顺时针；atan2 在屏幕坐标系（y 向下）里
            # 正好相反，所以顺时针要取负号
            # 解析 A 命令参数：rx ry rot largeArc sweep x y（空格或逗号分隔）
            sweep, large = 1, 0
            am = re.search(r"A\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)[\s,]+([01])[\s,]+([01])[\s,]+([\d.-]+)[\s,]+([\d.-]+)", dd)
            if am:
                large = int(am.group(4))
                sweep = int(am.group(5))
            if sweep == 1:
                ang = -ang
            ang = ang % 360
            # largeArc=0 表示走劣弧；若算出的角大于 180°，那实际走的是优弧
            if large == 0 and ang > 180:
                ang = 360 - ang
            pct = ang / 360 * 100
        except Exception:
            continue
        # 与最接近的百分比标签比对
        if pcts:
            best = min(pcts, key=lambda v: abs(v - pct))
            if abs(best - pct) > 1.2:
                problems.append((name, f"扇形角度 {ang:.1f}° 对应 {pct:.1f}%，标签写 {best}%"))
    return problems


def main():
    # 先自检：解析器在一个已知正确的图上必须自洽
    selfcheck = []
    for f in sorted(MEDIA.glob("*.svg")):
        svg = f.read_text(encoding="utf-8")
        name = f.name
        if "bar" in name or "bars" in name:
            selfcheck += check_bar_chart(svg, name)
        elif "line" in name:
            selfcheck += check_line_chart(svg, name)
        elif "pie" in name:
            selfcheck += check_pie_chart(svg, name)
    print(f"【图表数据验证】检查了 {len(list(MEDIA.glob('*.svg')))} 个 SVG，发现 {len(selfcheck)} 处几何与标注不符")
    for n, msg in selfcheck:
        print(f"  ✗ {n}: {msg}")

    # 图例/标签与篇目 alt 的对应
    print()
    problems = []
    for f in sorted(P.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for m in d.get("media", []):
            sp = MEDIA / m["file"]
            if not sp.exists():
                problems.append((d["id"], "配图缺失", m["file"]))
                continue
            svg = sp.read_text(encoding="utf-8")
            # alt 里说的标题应当出现在 SVG 里
            for t in re.findall(r"「([^」]{2,20})」", m.get("alt", "")):
                if t not in svg and not any(c in svg for c in t.replace(" ", "")):
                    problems.append((d["id"], "alt 里的标题在 SVG 中找不到", t))
    print(f"【图文对应】发现 {len(problems)} 处问题")
    for pid, tag, x in problems[:20]:
        print(f"  ✗ {pid}: {tag} — {x}")


if __name__ == "__main__":
    main()
