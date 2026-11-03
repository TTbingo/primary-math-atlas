#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按精确坐标重画 7 张知识点配图。文字位置全部预先算过，避免压线与溢出。"""
import math
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "content" / "media"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#17181c"
SUB = "#555962"
FAINT = "#8a8578"
LINE = "#cfc3ae"
RED = "#c0392b"
BLUE = "#2b6cb0"
GREEN = "#4a7c59"
BROWN = "#8b5e34"
PAPER = "#fffdf8"
FONT = "'Noto Serif SC','Songti SC',serif"


def head(w, h, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">',
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="{PAPER}"/>',
        f'  <text x="{w/2}" y="24" text-anchor="middle" font-family="{FONT}" '
        f'font-size="15" fill="{INK}">{title}</text>',
    ]


def write(name, lines):
    (OUT / name).write_text("\n".join(lines + ["</svg>", ""]), encoding="utf-8")
    print("写入", name)


# ---------------------------------------------------------------- 1. 量角器
def protractor():
    W, H = 480, 300
    cx, cy, R = 240, 196, 158
    L = head(W, H, "量角器：同一刻度上两圈数字相加正好 180")

    L.append(f'  <path d="M {cx-R} {cy} A {R} {R} 0 0 1 {cx+R} {cy} Z" '
             f'fill="#fdf6e8" stroke="{INK}" stroke-width="2"/>')
    L.append(f'  <path d="M {cx-R+22} {cy} A {R-22} {R-22} 0 0 1 {cx+R-22} {cy}" '
             f'fill="none" stroke="{LINE}" stroke-width="1"/>')

    # 刻度：每 5 度短线，每 10 度中线，每 30 度长线
    for deg in range(0, 181, 5):
        a = math.radians(180 - deg)
        ln = 15 if deg % 30 == 0 else (10 if deg % 10 == 0 else 6)
        x1, y1 = cx + R * math.cos(a), cy - R * math.sin(a)
        x2, y2 = cx + (R - ln) * math.cos(a), cy - (R - ln) * math.sin(a)
        col = LINE if deg % 10 else FAINT
        L.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{col}" stroke-width="1"/>')

    # 两圈数字：端点（0 / 180）贴着底线往里收，避免压在轴线上
    for deg in range(0, 181, 30):
        a = math.radians(180 - deg)
        if deg in (0, 180):
            side = -1 if deg == 0 else 1
            ox, oy = cx + side * (R - 12), cy - 8
            ix, iy = cx + side * (R - 38), cy - 8
        else:
            ox, oy = cx + 146 * math.cos(a), cy - 146 * math.sin(a) + 4
            ix, iy = cx + 112 * math.cos(a), cy - 112 * math.sin(a) + 4
        L.append(f'  <text x="{ox:.1f}" y="{oy:.1f}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="11" fill="{RED}">{deg}</text>')
        L.append(f'  <text x="{ix:.1f}" y="{iy:.1f}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="11" fill="{BLUE}">{180-deg}</text>')

    # 一个 60 度的角：水平边贴右侧 0 刻度线，斜边抬到 60 度
    L.append(f'  <line x1="{cx}" y1="{cy}" x2="{cx+R}" y2="{cy}" stroke="{INK}" stroke-width="2.4"/>')
    ra = math.radians(50)
    L.append(f'  <line x1="{cx}" y1="{cy}" x2="{cx+R*math.cos(ra):.1f}" '
             f'y2="{cy-R*math.sin(ra):.1f}" stroke="{INK}" stroke-width="2.4"/>')
    # 角弧
    ar = 86
    L.append(f'  <path d="M {cx+ar} {cy} A {ar} {ar} 0 0 0 '
             f'{cx+ar*math.cos(ra):.1f} {cy-ar*math.sin(ra):.1f}" fill="none" '
             f'stroke="{RED}" stroke-width="1.6"/>')
    # 角内标注（半径 64，避开两圈数字）
    ba = math.radians(25)
    lx, ly = cx + 74 * math.cos(ba), cy - 74 * math.sin(ba) + 4
    L.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
             f'font-family="{FONT}" font-size="12" fill="{RED}">内圈 50°</text>')

    # 中心十字
    L.append(f'  <circle cx="{cx}" cy="{cy}" r="3.5" fill="{RED}"/>')
    L.append(f'  <line x1="{cx-9}" y1="{cy}" x2="{cx+9}" y2="{cy}" stroke="{RED}" stroke-width="1.4"/>')
    L.append(f'  <line x1="{cx}" y1="{cy-9}" x2="{cx}" y2="{cy+9}" stroke="{RED}" stroke-width="1.4"/>')

    L.append(f'  <text x="24" y="278" font-family="{FONT}" font-size="11" fill="{RED}">'
             f'外圈（红）：左端 0 → 右端 180</text>')
    L.append(f'  <text x="24" y="293" font-family="{FONT}" font-size="11" fill="{BLUE}">'
             f'内圈（蓝）：右端 0 → 左端 180　同一处两数相加 = 180</text>')
    write("m2-01-03-angle-protractor.svg", L)


# ------------------------------------------------------------ 2. 长度单位
def length_units():
    W, H = 480, 320
    L = head(W, H, "长度单位：每上一级，数字就要换一套")
    rows = [
        ("千米 km", "走约 15 分钟（约 1 千米）", None),
        ("米 m", "门高约 2 米", "×1000"),
        ("分米 dm", "手掌宽约 1 分米", "×10"),
        ("厘米 cm", "食指宽约 1 厘米", "×10"),
        ("毫米 mm", "硬币厚约 1 毫米", "×10"),
    ]
    ys = [52, 102, 152, 202, 252]
    shades = ["#f3e6d6", "#f6ecdd", "#f9f2e6", "#fbf6ec", "#fdfaf3"]

    for i, (unit, ref, rate) in enumerate(rows):
        y = ys[i]
        L.append(f'  <rect x="20" y="{y-17}" width="130" height="34" rx="3" '
                 f'fill="{shades[i]}" stroke="{INK}" stroke-width="1.4"/>')
        L.append(f'  <text x="85" y="{y+5}" text-anchor="middle" font-family="{FONT}" '
                 f'font-size="15" fill="{INK}">{unit}</text>')
        L.append(f'  <text x="190" y="{y+5}" font-family="{FONT}" font-size="12" '
                 f'fill="{SUB}">{ref}</text>')
        if rate:
            mid = (ys[i - 1] + y) / 2
            L.append(f'  <text x="165" y="{mid+4}" text-anchor="middle" font-family="{FONT}" '
                     f'font-size="11" fill="{RED}">{rate}</text>')
            L.append(f'  <line x1="165" y1="{mid-12}" x2="165" y2="{mid-4}" stroke="{RED}" '
                     f'stroke-width="1.2"/>')
            L.append(f'  <line x1="165" y1="{mid+8}" x2="165" y2="{mid+14}" stroke="{RED}" '
                     f'stroke-width="1.2"/>')
            L.append(f'  <path d="M 161 {mid+10} L 165 {mid+16} L 169 {mid+10}" fill="none" '
                     f'stroke="{RED}" stroke-width="1.2"/>')

    L.append(f'  <text x="20" y="292" font-family="{FONT}" font-size="12" fill="{SUB}">'
             f'1 米 = 10 分米 = 100 厘米 = 1000 毫米　｜　1 千米 = 1000 米</text>')
    L.append(f'  <text x="20" y="310" font-family="{FONT}" font-size="12" fill="{RED}">'
             f'只有千米到米是 1000，其余相邻都是 10</text>')
    write("m2-01-12-length-units.svg", L)


# -------------------------------------------- 3 / 4. 长方体（共用投影）
def cube_parts():
    """返回可见棱、隐藏棱、各面路径。s=单位长，d=进深。"""
    return None


def cuboid(x0, y0, w, h, dx, dy):
    """前表面左上角 (x0,y0)，宽 w 高 h，进深向量 (dx,dy)（向右上）。"""
    A = (x0, y0)
    B = (x0 + w, y0)
    C = (x0 + w, y0 + h)
    D = (x0, y0 + h)
    A2 = (x0 + dx, y0 + dy)
    B2 = (x0 + w + dx, y0 + dy)
    C2 = (x0 + w + dx, y0 + h + dy)
    D2 = (x0 + dx, y0 + h + dy)
    return dict(A=A, B=B, C=C, D=D, A2=A2, B2=B2, C2=C2, D2=D2)


def pt(p):
    return f"{p[0]:.1f} {p[1]:.1f}"


def poly(pts):
    return " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)


def parts():
    W, H = 540, 290
    L = head(W, H, "长方体的面、棱、顶点")
    v = cuboid(64, 108, 120, 72, 36, -24)
    A, B, C, D = v["A"], v["B"], v["C"], v["D"]
    A2, B2, C2, D2 = v["A2"], v["B2"], v["C2"], v["D2"]

    # 三个可见面
    L.append(f'  <polygon points="{poly([A, B, B2, A2])}" fill="#f6ecdd" stroke="none"/>')
    L.append(f'  <polygon points="{poly([B, C, C2, B2])}" fill="#f3e6d6" stroke="none"/>')
    L.append(f'  <polygon points="{poly([A, B, C, D])}" fill="#fdf6e8" stroke="none"/>')

    # 隐藏棱（虚线，画在面之上才看得见）
    L.append(f'  <g fill="none" stroke-width="1.4" stroke-dasharray="5 3">')
    L.append(f'    <line x1="{D[0]}" y1="{D[1]}" x2="{D2[0]}" y2="{D2[1]}" stroke="{GREEN}"/>')
    L.append(f'    <line x1="{D2[0]}" y1="{D2[1]}" x2="{C2[0]}" y2="{C2[1]}" stroke="{BROWN}"/>')
    L.append(f'    <line x1="{D2[0]}" y1="{D2[1]}" x2="{A2[0]}" y2="{A2[1]}" stroke="{BLUE}"/>')
    L.append('  </g>')

    # 可见棱按方向着色：长（横）棕、宽（进深）绿、高（竖）蓝
    L.append('  <g fill="none" stroke-width="2.2">')
    for p, q in [(A, B), (C, D), (A2, B2), (B2, C2)]:
        col = BROWN if (p, q) in [(A, B), (C, D), (A2, B2)] else GREEN
        L.append(f'    <line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{col}"/>')
    for p, q in [(A, A2), (B, B2), (C, C2)]:
        col = GREEN if (p, q) in [(A, A2), (B, B2)] else BLUE
        L.append(f'    <line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{col}"/>')
    for p, q in [(A, D), (B, C), (A2, D2), (B2, C2)]:
        L.append(f'    <line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{BLUE}"/>')
    L.append('  </g>')

    # 顶点
    L.append('  <g fill="#17181c">')
    for p in [A, B, C, D, A2, B2, C2, D2]:
        L.append(f'    <circle cx="{p[0]}" cy="{p[1]}" r="3"/>')
    L.append('  </g>')

    # 标注：长在正下方，高在正左，宽在右面外侧
    L.append(f'  <text x="{(A[0]+B[0])/2}" y="{D[1]+22}" text-anchor="middle" '
             f'font-family="{FONT}" font-size="12" fill="{BROWN}">长 8 厘米</text>')
    L.append(f'  <text x="{A[0]-8}" y="{(A[1]+D[1])/2+4}" text-anchor="end" '
             f'font-family="{FONT}" font-size="12" fill="{BLUE}">高 5 厘米</text>')
    L.append(f'  <text x="{C2[0]+10}" y="{(B2[1]+C2[1])/2+4}" '
             f'font-family="{FONT}" font-size="12" fill="{GREEN}">宽 4 厘米</text>')

    # 右侧说明
    L.append(f'  <rect x="300" y="60" width="222" height="176" fill="#fdf6e8" '
             f'stroke="{LINE}" stroke-width="1"/>')
    items = [
        ("面　6 个", INK, 88),
        ("相对的两个完全相同，共 3 对", SUB, 108),
        ("棱　12 条", INK, 142),
        ("长棕、宽绿、高蓝，各 4 条", SUB, 162),
        ("顶点　8 个", INK, 196),
        ("长宽高相交处就是顶点", SUB, 216),
    ]
    for txt, col, y in items:
        L.append(f'  <text x="316" y="{y}" font-family="{FONT}" font-size="13" '
                 f'fill="{col}">{txt}</text>')
    for y in (120, 176):
        L.append(f'  <line x1="312" y1="{y}" x2="508" y2="{y}" stroke="{LINE}" stroke-width="0.8"/>')

    L.append(f'  <text x="270" y="282" text-anchor="middle" font-family="{FONT}" '
             f'font-size="12" fill="{SUB}">正方形是长、宽、高都相等的长方体，面棱顶点的数量完全一样</text>')
    write("m2-02-01-cuboid-parts.svg", L)


# ------------------------------------------------------ 5. 圆柱圆锥展开
def cyl_cone():
    W, H = 580, 326
    L = head(W, H, "圆柱侧面展开是长方形，圆锥侧面展开是扇形")

    # ---- 上排：圆柱 → 长方形
    L.append(f'  <text x="95" y="46" text-anchor="middle" font-family="{FONT}" '
             f'font-size="14" fill="{INK}">圆柱</text>')
    top_y, bot_y, rx, ry = 74, 158, 52, 15
    L.append(f'  <path d="M {95-rx} {top_y} A {rx} {ry} 0 0 1 {95+rx} {top_y} '
             f'L {95+rx} {bot_y} A {rx} {ry} 0 0 1 {95-rx} {bot_y} Z" fill="#f6ecdd" '
             f'stroke="{INK}" stroke-width="1.8"/>')
    L.append(f'  <ellipse cx="95" cy="{top_y}" rx="{rx}" ry="{ry}" fill="#fdf6e8" '
             f'stroke="{INK}" stroke-width="1.8"/>')
    L.append(f'  <path d="M {95-rx} {bot_y} A {rx} {ry} 0 0 0 {95+rx} {bot_y}" fill="none" '
             f'stroke="{INK}" stroke-width="1.8"/>')
    # 高（右侧引线）
    L.append(f'  <line x1="162" y1="{top_y}" x2="162" y2="{bot_y}" stroke="{RED}" stroke-width="1.3"/>')
    L.append(f'  <line x1="156" y1="{top_y}" x2="168" y2="{top_y}" stroke="{RED}" stroke-width="1.3"/>')
    L.append(f'  <line x1="156" y1="{bot_y}" x2="168" y2="{bot_y}" stroke="{RED}" stroke-width="1.3"/>')
    L.append(f'  <text x="172" y="{(top_y+bot_y)/2+4}" font-family="{FONT}" font-size="12" '
             f'fill="{RED}">高</text>')
    # 箭头
    L.append(f'  <line x1="196" y1="116" x2="238" y2="116" stroke="{FAINT}" stroke-width="1.4"/>')
    L.append(f'  <path d="M 238 116 L 230 112 M 238 116 L 230 120" fill="none" '
             f'stroke="{FAINT}" stroke-width="1.4"/>')
    # 长方形：长 = 底面周长，宽 = 高
    L.append(f'  <rect x="248" y="{top_y}" width="150" height="{bot_y-top_y}" fill="#f3ead6" '
             f'stroke="{INK}" stroke-width="1.8"/>')
    L.append(f'  <text x="323" y="{top_y-8}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="12" fill="{SUB}">长 = 底面周长</text>')
    L.append(f'  <text x="405" y="{(top_y+bot_y)/2+4}" font-family="{FONT}" font-size="12" '
             f'fill="{SUB}">宽 = 高</text>')
    L.append(f'  <text x="323" y="{bot_y+22}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="12" fill="{INK}">侧面展开成长方形</text>')

    # ---- 下排：圆锥 → 扇形
    L.append(f'  <text x="95" y="184" text-anchor="middle" font-family="{FONT}" '
             f'font-size="14" fill="{INK}">圆锥</text>')
    apex = (95, 202)
    base_y = 280
    L.append(f'  <path d="M {apex[0]} {apex[1]} L {95-rx} {base_y} '
             f'A {rx} {ry} 0 0 0 {95+rx} {base_y} Z" fill="#f6ecdd" stroke="{INK}" stroke-width="1.8"/>')
    L.append(f'  <circle cx="{apex[0]}" cy="{apex[1]}" r="3.6" fill="{RED}"/>')
    L.append(f'  <text x="{apex[0]+10}" y="{apex[1]+4}" font-family="{FONT}" font-size="12" '
             f'fill="{RED}">顶点</text>')
    L.append(f'  <line x1="{apex[0]}" y1="{apex[1]+6}" x2="{apex[0]}" y2="{base_y}" '
             f'stroke="{RED}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    L.append(f'  <text x="{apex[0]-8}" y="{(apex[1]+base_y)/2}" text-anchor="end" '
             f'font-family="{FONT}" font-size="12" fill="{RED}">高</text>')
    L.append(f'  <line x1="196" y1="246" x2="238" y2="246" stroke="{FAINT}" stroke-width="1.4"/>')
    L.append(f'  <path d="M 238 246 L 230 242 M 238 246 L 230 250" fill="none" '
             f'stroke="{FAINT}" stroke-width="1.4"/>')
    # 扇形：圆心 (323,286)，半径 80，开口朝上
    cx2, cy2, r2 = 323, base_y, 80
    a1, a2 = math.radians(235), math.radians(305)
    p1 = (cx2 + r2 * math.cos(a1), cy2 + r2 * math.sin(a1))
    p2 = (cx2 + r2 * math.cos(a2), cy2 + r2 * math.sin(a2))
    L.append(f'  <path d="M {cx2} {cy2} L {p1[0]:.1f} {p1[1]:.1f} A {r2} {r2} 0 0 1 '
             f'{p2[0]:.1f} {p2[1]:.1f} Z" fill="#f3ead6" stroke="{INK}" stroke-width="1.8"/>')
    L.append(f'  <circle cx="{cx2}" cy="{cy2}" r="2.6" fill="{INK}"/>')
    L.append(f'  <text x="{cx2}" y="{cy2+26}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="12" fill="{INK}">侧面展开成扇形</text>')
    write("m2-02-02-cylinder-cone-unfold.svg", L)


# ------------------------------------------------------- 6. 观察物体
def observe():
    W, H = 520, 330
    L = head(W, H, "从不同方向看，形状可以不一样")
    s, dx, dy = 40, 16, -12
    x0, y0 = 66, 178

    def cube(X, Y, shade_top, shade_side, shade_front):
        L.append(f'  <polygon points="{poly([(X,Y),(X+dx,Y+dy),(X+s+dx,Y+dy),(X+s,Y)])}" '
                 f'fill="{shade_top}" stroke="{INK}" stroke-width="1.3"/>')
        L.append(f'  <polygon points="{poly([(X+s,Y),(X+s+dx,Y+dy),(X+s+dx,Y+dy+s),(X+s,Y+s)])}" '
                 f'fill="{shade_side}" stroke="{INK}" stroke-width="1.3"/>')
        L.append(f'  <polygon points="{poly([(X,Y),(X+s,Y),(X+s,Y+s),(X,Y+s)])}" '
                 f'fill="{shade_front}" stroke="{INK}" stroke-width="1.3"/>')

    # 后排（中间那个后面）先画，会被前排挡住大半
    cube(x0 + s + dx, y0 + dy, "#efe7d8", "#ded4c2", "#e9e0cf")
    # 前排三个，从左到右
    for i in range(3):
        cube(x0 + i * s, y0, "#f6eee1", "#e6dccb", "#f3ece0")

    # 指向被挡住的那个
    L.append(f'  <line x1="{x0+2*s+dx+58}" y1="{y0+dy-16}" x2="{x0+2*s+dx+10}" '
             f'y2="{y0+dy+2}" stroke="{RED}" stroke-width="1.3"/>')
    L.append(f'  <path d="M {x0+2*s+dx+10} {y0+dy+2} L {x0+2*s+dx+18} {y0+dy} '
             f'M {x0+2*s+dx+10} {y0+dy+2} L {x0+2*s+dx+14} {y0+dy+9}" fill="none" '
             f'stroke="{RED}" stroke-width="1.3"/>')
    L.append(f'  <text x="{x0+2*s+dx+62}" y="{y0+dy-20}" font-family="{FONT}" '
             f'font-size="11" fill="{RED}">后面还藏着 1 个</text>')

    # 三个观察方向标签
    L.append(f'  <text x="{x0+s}" y="{y0+s+24}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="11" fill="{SUB}">从前面看</text>')
    L.append(f'  <text x="{x0-10}" y="{y0+s/2+4}" text-anchor="end" font-family="{FONT}" '
             f'font-size="11" fill="{SUB}">从左看</text>')
    L.append(f'  <line x1="{x0-8}" y1="{y0+s/2}" x2="{x0+8}" y2="{y0+s/2}" '
             f'stroke="{FAINT}" stroke-width="1.2"/>')
    L.append(f'  <text x="{x0+dx+10}" y="{y0+dy-14}" font-family="{FONT}" '
             f'font-size="11" fill="{SUB}">从上看</text>')

    # 三张视图
    u = 30
    vx = 268
    L.append(f'  <text x="{vx}" y="58" font-family="{FONT}" font-size="12" fill="{INK}">从前面看</text>')
    for i in range(3):
        L.append(f'  <rect x="{vx+i*u}" y="66" width="{u}" height="{u}" fill="#e8dfd0" '
                 f'stroke="{INK}" stroke-width="1.3"/>')
    L.append(f'  <text x="{vx}" y="114" font-family="{FONT}" font-size="11" fill="{SUB}">'
             f'横着 3 个，后排那个被挡住了</text>')

    L.append(f'  <text x="{vx}" y="146" font-family="{FONT}" font-size="12" fill="{INK}">从左面看</text>')
    for i in range(2):
        L.append(f'  <rect x="{vx+i*u}" y="154" width="{u}" height="{u}" fill="#e8dfd0" '
                 f'stroke="{INK}" stroke-width="1.3"/>')
    L.append(f'  <text x="{vx}" y="202" font-family="{FONT}" font-size="11" fill="{SUB}">'
             f'横着 2 个，前后各一层</text>')

    L.append(f'  <text x="{vx}" y="234" font-family="{FONT}" font-size="12" fill="{INK}">从上面看</text>')
    for i in range(3):
        L.append(f'  <rect x="{vx+i*u}" y="272" width="{u}" height="{u}" fill="#e8dfd0" '
                 f'stroke="{INK}" stroke-width="1.3"/>')
    L.append(f'  <rect x="{vx+u}" y="242" width="{u}" height="{u}" fill="#e8dfd0" '
             f'stroke="{INK}" stroke-width="1.3"/>')
    L.append(f'  <text x="{vx}" y="320" font-family="{FONT}" font-size="11" fill="{SUB}">'
             f'4 个格子，说明一共 4 个</text>')

    L.append(f'  <text x="260" y="40" text-anchor="middle" font-family="{FONT}" font-size="11" '
             f'fill="{RED}">看到的方块数 ≠ 实际个数</text>')
    write("m2-02-09-observe-object-views.svg", L)


# ------------------------------------------------------ 7. 展开图相对面
def net_pairs():
    W, H = 520, 326
    L = head(W, H, "展开图上，隔着一个面的两个面就是相对面")
    c = 78
    x_s, y_row = 20, 118
    cols = [("左面", "#cfe3d4"), ("前面", "#f3ead6"), ("右面", "#cfe3d4"), ("后面", "#f3ead6")]
    for i, (name, col) in enumerate(cols):
        L.append(f'  <rect x="{x_s+i*c}" y="{y_row}" width="{c}" height="{c}" fill="{col}" '
                 f'stroke="{INK}" stroke-width="1.5"/>')
        L.append(f'  <text x="{x_s+i*c+c/2}" y="{y_row+c/2+5}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="13" fill="{INK}">{name}</text>')
    for name, yy in (("上面", y_row - c), ("下面", y_row + c)):
        L.append(f'  <rect x="{x_s+c}" y="{yy}" width="{c}" height="{c}" fill="#f6d9d2" '
                 f'stroke="{INK}" stroke-width="1.5"/>')
        L.append(f'  <text x="{x_s+c+c/2}" y="{yy+c/2+5}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="13" fill="{INK}">{name}</text>')

    # 右侧图例
    lx = 372
    L.append(f'  <rect x="{lx-12}" y="60" width="150" height="140" fill="#fdf6e8" '
             f'stroke="{LINE}" stroke-width="1"/>')
    for i, (col, txt) in enumerate([("#cfe3d4", "左 ↔ 右"), ("#f3ead6", "前 ↔ 后"), ("#f6d9d2", "上 ↔ 下")]):
        y = 84 + i * 30
        L.append(f'  <rect x="{lx}" y="{y-13}" width="16" height="16" fill="{col}" '
                 f'stroke="{INK}" stroke-width="1"/>')
        L.append(f'  <text x="{lx+24}" y="{y}" font-family="{FONT}" font-size="13" '
                 f'fill="{INK}">{txt}</text>')
    L.append(f'  <line x1="{lx-4}" y1="166" x2="{lx+126}" y2="166" stroke="{LINE}" stroke-width="0.8"/>')
    L.append(f'  <text x="{lx}" y="188" font-family="{FONT}" font-size="12" fill="{RED}">颜色相同 = 相对面</text>')

    L.append(f'  <text x="20" y="310" font-family="{FONT}" font-size="12" fill="{SUB}">'
             f'相对面在展开图上永远不相邻，中间总隔着另一个面</text>')
    write("m2-02-01-cuboid-net-pairs.svg", L)


# ------------------------------------------------------ 8. 分层体积
def volume_layers():
    W, H = 540, 300
    L = head(W, H, "体积公式是数出来的：每层 15 个，摞 2 层")
    u, dx, dy = 26, 42, -30
    x0, y0 = 44, 132
    w, h = 5 * u, 2 * u
    A = (x0, y0)
    B = (x0 + w, y0)
    C = (x0 + w, y0 + h)
    D = (x0, y0 + h)
    A2 = (x0 + dx, y0 + dy)
    B2 = (x0 + w + dx, y0 + dy)
    C2 = (x0 + w + dx, y0 + h + dy)

    L.append(f'  <polygon points="{poly([A, B, B2, A2])}" fill="#f6ecdd" stroke="none"/>')
    L.append(f'  <polygon points="{poly([B, C, C2, B2])}" fill="#f3e6d6" stroke="none"/>')
    L.append(f'  <polygon points="{poly([A, B, C, D])}" fill="#fdf6e8" stroke="none"/>')

    # 前表面网格：5 列 2 行
    L.append(f'  <g stroke="{LINE}" stroke-width="0.9">')
    for i in range(1, 5):
        L.append(f'    <line x1="{x0+i*u}" y1="{y0}" x2="{x0+i*u}" y2="{y0+h}"/>')
    L.append(f'    <line x1="{x0}" y1="{y0+u}" x2="{x0+w}" y2="{y0+u}"/>')
    # 上面网格：沿长 4 条 + 沿进深 2 条
    for i in range(1, 5):
        L.append(f'    <line x1="{x0+i*u}" y1="{y0}" x2="{x0+i*u+dx}" y2="{y0+dy}"/>')
    for j in range(1, 3):
        fx, fy = j * dx / 3, j * dy / 3
        L.append(f'    <line x1="{x0+fx:.1f}" y1="{y0+fy:.1f}" x2="{x0+w+fx:.1f}" y2="{y0+fy:.1f}"/>')
    # 右面网格：进深 2 条 + 竖向 1 条
    for j in range(1, 3):
        fx, fy = j * dx / 3, j * dy / 3
        L.append(f'    <line x1="{x0+w+fx:.1f}" y1="{y0+fy:.1f}" x2="{x0+w+fx:.1f}" y2="{y0+h+fy:.1f}"/>')
    L.append(f'    <line x1="{x0+w}" y1="{y0+u}" x2="{x0+w+dx}" y2="{y0+u+dy}"/>')
    L.append('  </g>')

    # 外框
    L.append(f'  <g fill="none" stroke="{INK}" stroke-width="1.8">')
    L.append(f'    <polygon points="{poly([A, B, C, D])}"/>')
    L.append(f'    <polygon points="{poly([A, B, B2, A2])}"/>')
    L.append(f'    <polygon points="{poly([B, C, C2, B2])}"/>')
    L.append('  </g>')

    L.append(f'  <text x="{x0+w/2}" y="{y0+h+24}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="12" fill="{BROWN}">长 5 厘米</text>')
    L.append(f'  <text x="{x0-8}" y="{y0+h/2+4}" text-anchor="end" font-family="{FONT}" '
             f'font-size="12" fill="{BLUE}">高 2</text>')
    L.append(f'  <text x="{C2[0]+10}" y="{(B2[1]+C2[1])/2+4}" font-family="{FONT}" '
             f'font-size="12" fill="{GREEN}">宽 3</text>')
    L.append(f'  <text x="{x0+w/2+dx/2}" y="{y0+dy-8}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="11" fill="{FAINT}">每小格 = 1 个棱长 1 厘米的小正方体</text>')

    # 右侧算式
    L.append(f'  <rect x="298" y="58" width="220" height="146" fill="#fdf6e8" '
             f'stroke="{LINE}" stroke-width="1"/>')
    rows = [
        ('每层：5 × 3 = 15 个', 88, INK),
        ('共 2 层：15 × 2 = 30 个', 118, INK),
        ('V = 长 × 宽 × 高', 156, INK),
        ('= 5 × 3 × 2 = 30 立方厘米', 182, RED),
    ]
    for txt, y, col in rows:
        L.append(f'  <text x="314" y="{y}" font-family="{FONT}" font-size="13" fill="{col}">{txt}</text>')
    L.append(f'  <line x1="310" y1="134" x2="506" y2="134" stroke="{LINE}" stroke-width="0.8"/>')

    L.append(f'  <text x="270" y="248" text-anchor="middle" font-family="{FONT}" font-size="12" '
             f'fill="{SUB}">体积量的是「装得下多少个 1 立方厘米」，所以单位是 cm³</text>')
    L.append(f'  <text x="270" y="270" text-anchor="middle" font-family="{FONT}" font-size="12" '
             f'fill="{RED}">正方体是长宽高相等的长方体：V = 棱长 × 棱长 × 棱长</text>')
    L.append(f'  <text x="270" y="290" text-anchor="middle" font-family="{FONT}" font-size="12" '
             f'fill="{FAINT}">别把体积和表面积搞混：一个量里面，一个量外面</text>')
    write("m2-02-05-volume-layers.svg", L)


if __name__ == "__main__":
    protractor()
    length_units()
    parts()
    cyl_cone()
    observe()
    net_pairs()
    volume_layers()
