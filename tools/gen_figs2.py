"""为缺少配图的知识点生成 SVG 配图（坐标全部由计算得出，保证数学正确）。

用法: python tools/gen_figs2.py [批次名...]   # 不传则生成全部
"""
import math
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "content", "media")
FONT = "'Noto Serif SC','Songti SC',serif"


def P(cx, cy, r, deg):
    """数学角（0=右，逆时针为正）-> 屏幕坐标（y 向下）"""
    a = math.radians(deg)
    return (cx + r * math.cos(a), cy - r * math.sin(a))


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img">\n'
            f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#fffdf8"/>\n'
            + body + "</svg>\n")


def title(w, t, y=26, size=14):
    return (f'  <text x="{w//2}" y="{y}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="{size}" fill="#17181c">{t}</text>\n')


def note(x, y, t, size=11.5, color="#7a7266", anchor="middle"):
    return (f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" '
            f'font-size="{size}" fill="{color}">{t}</text>\n')


def txt(x, y, t, size=12, color="#17181c", anchor="middle", weight=""):
    wt = f' font-weight="{weight}"' if weight else ""
    return (f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" '
            f'font-size="{size}" fill="{color}"{wt}>{t}</text>\n')


def write(name, content):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
    print("  gen", name)


# ───────────────────────────────────────────── 1. 扇形统计图
def pie_chart():
    W, H = 520, 320
    cx, cy, r = 168, 158, 108
    data = [("阅读", 25, "#e8dcc4"), ("运动", 30, "#cfe0d0"),
            ("绘画", 20, "#d8e2ef"), ("音乐", 15, "#eed8d2"),
            ("其他", 10, "#e5dcef")]
    b = title(W, "六(1)班 40 人最喜欢的社团统计图")
    deg = 90.0  # 从正上方开始顺时针
    for name, pct, color in data:
        sweep = pct * 3.6
        a1, a2 = deg, deg - sweep
        x1, y1 = P(cx, cy, r, a1)
        x2, y2 = P(cx, cy, r, a2)
        large = 1 if sweep > 180 else 0
        b += (f'  <path d="M {cx},{cy} L {f(x1)},{f(y1)} '
              f'A {r},{r} 0 {large} 1 {f(x2)},{f(y2)} Z" '
              f'fill="{color}" stroke="#fffdf8" stroke-width="2"/>\n')
        mid = (a1 + a2) / 2
        rr = 0.72 * r if sweep <= 60 else 0.6 * r
        tx, ty = P(cx, cy, rr, mid)
        b += txt(f(tx), f(ty + 4), f"{pct}%", size=12, color="#17181c")
        deg = a2
    # 图例
    y = 86
    for name, pct, color in data:
        b += (f'  <rect x="312" y="{y-11}" width="16" height="14" fill="{color}" '
              f'stroke="#b9a888" stroke-width="1"/>\n')
        b += txt(340, y, name, size=12.5, anchor="start")
        b += txt(470, y, f"{pct}%  {40*pct//100}人", size=12, anchor="end")
        y += 30
    b += note(390, 250, "整个圆 = 总人数 40 人", size=11.5, color="#17181c")
    b += note(390, 268, "扇形大小 = 占百分之几", size=11.5, color="#17181c")
    b += note(260, 296, "整个圆表示总数量，每个扇形表示其中一部分占总数的百分之几",
              size=11.5)
    b += note(260, 314,
              "25% + 30% + 20% + 15% + 10% = 100%：所有扇形拼起来正好是一个整圆",
              size=11.5, color="#8f2419")
    write("m3-02-03-pie-chart-example.svg", svg(W, H, b))


# ───────────────────────────────────────────── 2. 确定事件与不确定事件
def certainty():
    W, H = 520, 320
    b = title(W, "从盒子里任意摸出 1 个球，会摸到什么颜色？")
    boxes = [(30, ["#c0392b"] * 4, "一定摸到红球", "确定事件", "#8f2419"),
             (190, ["#c0392b", "#c0392b", "#c0392b", "#f2ecdc"],
              "可能摸到红球", "不确定事件", "#17181c"),
             (350, ["#f2ecdc"] * 4, "不可能摸到红球", "确定事件", "#8f2419")]
    for x, balls, lab, kind, color in boxes:
        b += (f'  <rect x="{x}" y="90" width="140" height="84" fill="#faf6ee" '
              f'stroke="#b9a888" stroke-width="1.4"/>\n')
        for i, c in enumerate(balls):
            bx = x + 25 + i * 30
            b += (f'  <circle cx="{bx}" cy="132" r="13" fill="{c}" '
                  f'stroke="#17181c" stroke-width="1.1"/>\n')
            if c == "#f2ecdc":
                b += (f'  <circle cx="{bx}" cy="132" r="13" fill="none" '
                      f'stroke="#17181c" stroke-width="1.1"/>\n')
        b += txt(x + 70, 194, lab, size=12.5, color=color)
        b += txt(x + 70, 214, kind, size=12, color="#7a7266")
    b += note(260, 258, "一定能发生、一定不会发生，这两种都是确定事件；"
              "可能发生也可能不发生的，是不确定事件", size=11.5)
    b += note(260, 278, "中间那盒里红球有 3 个、白球只有 1 个，"
              "所以摸到红球的可能性大，摸到白球的可能性小", size=11.5, color="#8f2419")
    b += note(260, 302, "「可能性大」不等于「一定」：白球只有 1 个，也还是有可能摸到",
              size=11.5)
    write("m3-04-01-certainty-boxes.svg", svg(W, H, b))


# ───────────────────────────────────────────── 3. 三角形三边关系
def triangle_three_sides():
    W, H = 520, 360
    b = title(W, "三根小棒，能不能围成一个三角形？")
    # 上组：3、4、5 能围成（1 厘米 = 30 像素）
    ax, ay, bx = 120, 154, 270
    b += (f'  <line x1="{ax}" y1="{ay}" x2="{bx}" y2="{ay}" stroke="#17181c" '
          f'stroke-width="2"/>\n')
    for cx, rr in ((ax, 120), (bx, 90)):
        x1, y1 = P(cx, ay, rr, 8)
        x2, y2 = P(cx, ay, rr, 172)
        b += (f'  <path d="M {f(x1)},{f(y1)} A {rr},{rr} 0 0 0 {f(x2)},{f(y2)}" '
              f'fill="none" stroke="#c0392b" stroke-width="1.2" '
              f'stroke-dasharray="5 4"/>\n')
    b += (f'  <polygon points="{ax},{ay} {bx},{ay} 216,82" fill="#f2ecdc" '
          f'stroke="#17181c" stroke-width="1.8"/>\n')
    b += txt(195, 172, "5 厘米", size=12)
    b += txt(158, 126, "4 厘米", size=12)
    b += txt(248, 126, "3 厘米", size=12)
    b += txt(195, 208, "较短两根 3 + 4 = 7，比 5 长，围得起来",
             size=12.5, color="#8f2419")
    b += txt(195, 228, "3 + 4 &gt; 5，能围成三角形", size=13, color="#17181c")
    # 下组：2、3、6 不能围成
    ax2, ay2, bx2 = 150, 290, 330
    b += (f'  <line x1="{ax2}" y1="{ay2}" x2="{bx2}" y2="{ay2}" stroke="#17181c" '
          f'stroke-width="2"/>\n')
    for cx, rr in ((ax2, 90), (bx2, 60)):
        x1, y1 = P(cx, ay2, rr, 5)
        x2, y2 = P(cx, ay2, rr, 175)
        b += (f'  <path d="M {f(x1)},{f(y1)} A {rr},{rr} 0 0 0 {f(x2)},{f(y2)}" '
              f'fill="none" stroke="#c0392b" stroke-width="1.2" '
              f'stroke-dasharray="5 4"/>\n')
    gx1, _ = P(ax2, ay2, 90, 0)
    gx2, _ = P(bx2, ay2, 60, 180)
    b += (f'  <line x1="{f(gx1)}" y1="290" x2="{f(gx2)}" y2="290" '
          f'stroke="#8f2419" stroke-width="2"/>\n')
    b += txt(255, 278, "还差 1 厘米", size=12, color="#8f2419")
    b += txt(240, 310, "2 + 3 = 5，还不到 6，两根短的加起来都不够长",
             size=12.5, color="#8f2419")
    b += txt(240, 330, "2 + 3 &lt; 6，围不成三角形", size=13, color="#17181c")
    b += note(260, 352, "只要最短的两边加起来比第三边长，就能围成三角形",
              size=11.5)
    write("m2-01-07-triangle-three-sides.svg", svg(W, H, b))


# ───────────────────────────────────────────── 4. 圆的特征
def circle_features():
    W, H = 480, 320
    cx, cy, r = 148, 148, 96
    b = title(W, "圆的各个部分")
    b += (f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#f7f2e6" '
          f'stroke="#17181c" stroke-width="1.8"/>\n')
    for deg, lab in ((35, "r"), (140, "r"), (255, "r")):
        px, py = P(cx, cy, r, deg)
        b += (f'  <line x1="{cx}" y1="{cy}" x2="{f(px)}" y2="{f(py)}" '
              f'stroke="#c0392b" stroke-width="1.8"/>\n')
        mx, my = P(cx, cy, r * 0.58, deg)
        b += txt(f(mx), f(my), lab, size=13, color="#8f2419")
    dx1, dy1 = P(cx, cy, r, 180)
    dx2, dy2 = P(cx, cy, r, 0)
    b += (f'  <line x1="{f(dx1)}" y1="{f(dy1)}" x2="{f(dx2)}" y2="{f(dy2)}" '
          f'stroke="#2b6cb0" stroke-width="2.2"/>\n')
    b += txt(cx, cy - 12, "d", size=14, color="#2b6cb0")
    b += (f'  <circle cx="{cx}" cy="{cy}" r="3.4" fill="#17181c"/>\n')
    b += txt(cx + 10, cy + 16, "O", size=13)
    b += txt(cx + 10, cy + 32, "圆心", size=12, color="#7a7266")
    # 右侧要点
    pts = ["圆心 O：圆的中心", "半径 r：圆心到圆上一点",
           "直径 d：过圆心、两端在圆上", "同圆里，半径都相等"]
    y = 96
    for t in pts:
        b += (f'  <circle cx="280" cy="{y-4}" r="3" fill="#bfa578"/>\n')
        b += txt(290, y, t, size=11.5, anchor="start")
        y += 26
    b += txt(280, 214, "d = 2r，r = d ÷ 2", size=14, color="#8f2419", anchor="start")
    b += note(240, 262, "圆心决定圆画在哪儿，半径决定圆画得多大", size=12)
    b += note(240, 284, "一个圆里有无数条半径、无数条直径，它们都分别相等",
              size=12, color="#8f2419")
    b += note(240, 306, "用圆规画圆：针尖扎的那点就是圆心，两脚张开的距离就是半径",
              size=11.5)
    write("m2-01-09-circle-features.svg", svg(W, H, b))


# ───────────────────────────────────────────── 5. 扇形的认识
def sector():
    W, H = 480, 300
    b = title(W, "弧和扇形")
    for (cx, cy, r, a1, a2, lab, ang) in (
            (120, 160, 96, 30, 100, "圆心角小", 70),
            (350, 160, 96, 25, 175, "圆心角大", 150)):
        x1, y1 = P(cx, cy, r, a1)
        x2, y2 = P(cx, cy, r, a2)
        b += (f'  <path d="M {cx},{cy} L {f(x1)},{f(y1)} '
              f'A {r},{r} 0 0 0 {f(x2)},{f(y2)} Z" fill="#f2ecdc" '
              f'stroke="#17181c" stroke-width="1.6"/>\n')
        b += (f'  <line x1="{cx}" y1="{cy}" x2="{f(x1)}" y2="{f(y1)}" '
              f'stroke="#17181c" stroke-width="1.8"/>\n')
        b += (f'  <line x1="{cx}" y1="{cy}" x2="{f(x2)}" y2="{f(y2)}" '
              f'stroke="#17181c" stroke-width="1.8"/>\n')
        b += (f'  <circle cx="{cx}" cy="{cy}" r="3.4" fill="#17181c"/>\n')
        am = (a1 + a2) / 2
        ax_, ay_ = P(cx, cy, 58, am)
        b += (f'  <path d="M {f(P(cx, cy, 40, a2)[0])},{f(P(cx, cy, 40, a2)[1])} '
              f'A 40,40 0 0 1 {f(P(cx, cy, 40, a1)[0])},{f(P(cx, cy, 40, a1)[1])}" '
              f'fill="none" stroke="#c0392b" stroke-width="1.4"/>\n')
        b += txt(f(ax_), f(ay_ + 4), "圆心角", size=11.5, color="#8f2419")
        mx, my = P(cx, cy, r + 14, am)
        b += txt(f(mx), f(my + 4), "弧", size=12, color="#2b6cb0")
        b += txt(cx, 262, f"{lab}（{ang}°）", size=12.5, color="#17181c")
    b += note(240, 288, "圆上两点之间的部分叫弧；两条半径和一段弧围成的图形叫扇形",
              size=11.5)
    write("m2-01-10-sector.svg", svg(W, H, b))


# ───────────────────────────────────────────── 6. 周长的认识
def perimeter():
    W, H = 520, 300
    b = title(W, "封闭图形一周的长度，是它的周长")
    # 三角形
    b += ('  <polygon points="60,180 150,90 240,180" fill="#f7f2e6" '
          'stroke="#c0392b" stroke-width="3"/>\n')
    b += txt(150, 208, "三角形", size=12)
    # 长方形
    b += ('  <rect x="300" y="100" width="160" height="80" fill="#f7f2e6" '
          'stroke="#c0392b" stroke-width="3"/>\n')
    b += txt(380, 208, "长方形", size=12)
    # 不封闭的开口图形
    b += ('  <path d="M 60,262 L 120,222 L 180,262 L 240,222" fill="none" '
          'stroke="#b9a888" stroke-width="3"/>\n')
    b += txt(150, 288, "没有围起来，就没有周长", size=12, color="#7a7266")
    b += ('  <circle cx="380" cy="240" r="38" fill="#f7f2e6" stroke="#c0392b" '
          'stroke-width="3"/>\n')
    b += txt(380, 294, "圆", size=12)
    b += note(260, 62, "红色的一圈就是「一周」：从边上一点出发，沿着边走回原点",
              size=11.5)
    write("m2-01-13-perimeter.svg", svg(W, H, b))


# ───────────────────────────────────────────── 7. 长方形、正方形周长
def rect_perimeter():
    W, H = 520, 300
    b = title(W, "长方形和正方形的周长")
    # 长方形 8×5，每格 20px
    x, y, a, bb = 40, 80, 160, 100
    b += (f'  <rect x="{x}" y="{y}" width="{a}" height="{bb}" fill="#f7f2e6" '
          f'stroke="#17181c" stroke-width="1.8"/>\n')
    b += txt(x + a / 2, y - 10, "8 厘米", size=13)
    b += txt(x + a / 2, y + bb + 22, "8 厘米", size=13)
    b += txt(x - 12, y + bb / 2 + 4, "5", size=13)
    b += txt(x + a + 12, y + bb / 2 + 4, "5", size=13)
    b += (f'  <path d="M {x+4},{y+bb-1} L {x+a-4},{y+bb-1}" stroke="#c0392b" '
          f'stroke-width="1.6"/>\n')
    b += txt(x + a / 2, y + bb + 46, "(8 + 5) × 2 = 26 厘米", size=14,
             color="#8f2419")
    b += txt(x + a / 2, y + bb + 68, "周长 = (长 + 宽) × 2", size=12.5)
    # 正方形 6×6
    x2, y2, s = 340, 70, 120
    b += (f'  <rect x="{x2}" y="{y2}" width="{s}" height="{s}" fill="#f7f2e6" '
          f'stroke="#17181c" stroke-width="1.8"/>\n')
    b += txt(x2 + s / 2, y2 - 10, "6 厘米", size=13)
    b += txt(x2 + s / 2, y2 + s + 22, "6 厘米", size=13)
    b += txt(x2 - 12, y2 + s / 2 + 4, "6", size=13)
    b += txt(x2 + s + 12, y2 + s / 2 + 4, "6", size=13)
    b += txt(x2 + s / 2, y2 + s + 46, "6 × 4 = 24 厘米", size=14, color="#8f2419")
    b += txt(x2 + s / 2, y2 + s + 68, "周长 = 边长 × 4", size=12.5)
    b += note(260, 288, "四条边一条不落地加起来，就是周长；正方形四边一样长，"
              "所以直接乘 4", size=11.5)
    write("m2-01-14-rect-perimeter.svg", svg(W, H, b))


def box(x, y, w, h, label, fill="#f7f2e6", stroke="#b9a888", size=12,
        color="#17181c"):
    return (f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.2"/>\n'
            + txt(x + w / 2, y + h / 2 + 4, label, size=size, color=color))


def line(x1, y1, x2, y2, color="#bfa578", width=1.2, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'  <line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'stroke="{color}" stroke-width="{width}"{d}/>\n')


# ───────────────────────────────────────────── 8. 数的分类
def number_classify():
    W, H = 520, 320
    b = title(W, "小学阶段认识的数")
    b += box(210, 44, 100, 32, "数", fill="#e8dcc4")
    b += line(260, 76, 150, 100)
    b += line(260, 76, 390, 100)
    b += box(90, 100, 120, 32, "整数", fill="#e8dcc4")
    b += box(310, 100, 160, 32, "分数、小数、百分数", fill="#e8dcc4", size=11.5)
    for x, lab in ((30, "正整数"), (116, "0"), (202, "负整数")):
        b += line(150, 132, x + 38, 180)
        b += box(x, 180, 76, 32, lab)
    for x, lab in ((304, "分数"), (378, "小数"), (452, "百分数")):
        b += line(390, 132, x + 32, 180)
        b += box(x, 180, 64, 32, lab, size=11.5)
    b += note(260, 246, "正整数、0、负整数都是整数；0 也是整数，但它既不是正数也不是负数",
              size=11.5)
    b += note(260, 268, "分数、小数、百分数是同一个数量的不同写法，可以互相改写",
              size=11.5)
    b += note(260, 296, "分类的标准不一样，分出来的名字也不一样；先想清楚「按什么分」",
              size=11.5, color="#8f2419")
    write("m1-01-01-number-classify.svg", svg(W, H, b))


# ───────────────────────────────────────────── 9. 数位顺序表
def decimal_position():
    W, H = 520, 300
    b = title(W, "数位顺序表（以 352.48 为例）")
    cols = ["千位", "百位", "十位", "个位", "小数点", "十分位", "百分位", "千分位"]
    units = ["千", "百", "十", "一（个）", "·", "十分之一", "百分之一", "千分之一"]
    digits = ["", "3", "5", "2", "·", "4", "8", ""]
    x0, cw, y0, rh = 20, 60, 54, 34
    for i in range(9):
        b += line(x0 + i * cw, y0, x0 + i * cw, y0 + 3 * rh, "#cfc3ae", 1)
    for j in range(4):
        b += line(x0, y0 + j * rh, x0 + 8 * cw, y0 + j * rh, "#cfc3ae", 1)
    b += line(x0 + 4 * cw, y0, x0 + 4 * cw, y0 + 3 * rh, "#c0392b", 1.8)
    for i in range(8):
        cx = x0 + i * cw + cw / 2
        col = "#8f2419" if i == 4 else "#7a7266"
        b += txt(cx, y0 + 22, cols[i], size=11.5, color=col)
        b += txt(cx, y0 + rh + 22, units[i], size=10.5, color="#7a7266")
        b += txt(cx, y0 + 2 * rh + 24, digits[i], size=16,
                 color="#c0392b" if i == 4 else "#17181c")
    b += txt(30, y0 - 12, "整数部分", size=11.5, color="#7a7266", anchor="start")
    b += txt(500, y0 - 12, "小数部分", size=11.5, color="#7a7266", anchor="end")
    b += note(260, 190, "每相邻两个计数单位之间的进率都是 10", size=12.5)
    b += note(260, 214, "10 个一是十，10 个十分之一是 1；小数点右边第一位是十分位",
              size=11.5)
    b += note(260, 242, "352.48 里，4 在十分位上表示 4 个 0.1，8 在百分位上表示 8 个 0.01",
              size=11.5)
    b += note(260, 272, "数位说的是「位置」，计数单位说的是「这一位上的 1 表示多少」",
              size=11.5, color="#8f2419")
    write("m1-01-06-decimal-position.svg", svg(W, H, b))


# ───────────────────────────────────────────── 10. 分数的意义
def fraction_meaning():
    W, H = 520, 300
    b = title(W, "把单位「1」平均分")
    cx, cy, r = 140, 148, 82
    for k in range(4):
        a1, a2 = 90 - k * 90, 90 - (k + 1) * 90
        x1, y1 = P(cx, cy, r, a1)
        x2, y2 = P(cx, cy, r, a2)
        fill = "#e8dcc4" if k < 3 else "#fffdf8"
        b += (f'  <path d="M {cx},{cy} L {f(x1)},{f(y1)} '
              f'A {r},{r} 0 0 1 {f(x2)},{f(y2)} Z" fill="{fill}" '
              f'stroke="#17181c" stroke-width="1.4"/>\n')
    b += txt(140, 248, "平均分成 4 份，取 3 份 → 3/4", size=12.5)
    b += txt(140, 268, "分数单位是 1/4", size=12, color="#8f2419")
    # 线段模型
    x0, y, total, seg = 300, 148, 180, 36
    for k in range(5):
        fill = "#e8dcc4" if k < 3 else "#fffdf8"
        b += (f'  <rect x="{x0+k*seg}" y="{y-18}" width="{seg}" height="36" '
              f'fill="{fill}" stroke="#17181c" stroke-width="1.4"/>\n')
    b += txt(390, 248, "平均分成 5 份，取 3 份 → 3/5", size=12.5)
    b += txt(390, 268, "分数单位是 1/5", size=12, color="#8f2419")
    b += note(260, 290, "分母表示平均分成几份，分子表示取了几份；表示其中一份的数叫分数单位",
              size=11.5)
    write("m1-01-09-fraction-meaning.svg", svg(W, H, b))


# ───────────────────────────────────────────── 11. 分数的基本性质
def fraction_property():
    W, H = 520, 300
    b = title(W, "同样的长条，分的份数不同，涂色部分一样长")
    x0, w, h = 30, 380, 42
    for row, (n, k, lab) in enumerate(((2, 1, "1/2"), (4, 2, "2/4"),
                                       (8, 4, "4/8"))):
        y = 62 + row * 68
        for j in range(n):
            fill = "#e8dcc4" if j < k else "#fffdf8"
            b += (f'  <rect x="{f(x0+j*w/n)}" y="{y}" width="{f(w/n)}" '
                  f'height="{h}" fill="{fill}" stroke="#17181c" '
                  f'stroke-width="1.2"/>\n')
        b += txt(440, y + 27, lab, size=16, color="#17181c")
        b += txt(30, y - 8, f"平均分成 {n} 份，涂 {k} 份", size=11.5,
                 color="#7a7266", anchor="start")
    b += txt(260, 272, "1/2 = 2/4 = 4/8", size=17, color="#8f2419")
    b += note(260, 294, "分子、分母同时乘或除以同一个不为 0 的数，分数的大小不变",
              size=11.5)
    write("m1-01-10-fraction-property.svg", svg(W, H, b))


# ───────────────────────────────────────────── 12. 百分数的意义
def percentage_meaning():
    W, H = 520, 320
    b = title(W, "百格图：一眼看出百分之几")
    x0, y0, g = 36, 52, 20
    for row in range(10):
        for col in range(10):
            k = row * 10 + col
            fill = "#e8dcc4" if k < 45 else "#fffdf8"
            b += (f'  <rect x="{x0+col*g}" y="{y0+row*g}" width="{g}" '
                  f'height="{g}" fill="{fill}" stroke="#cfc3ae" '
                  f'stroke-width="0.7"/>\n')
    b += (f'  <rect x="{x0}" y="{y0}" width="{g*10}" height="{g*10}" '
          f'fill="none" stroke="#17181c" stroke-width="1.6"/>\n')
    b += txt(270, 84, "全班 40 人，女生 18 人", size=12.5, anchor="start")
    b += txt(270, 120, "18 ÷ 40 = 0.45 = 45%", size=16, color="#8f2419",
             anchor="start")
    b += txt(270, 152, "100 格里涂 45 格，就是 45%", size=12, anchor="start")
    b += txt(270, 182, "百分数表示两个数的比", size=11.5, anchor="start")
    b += txt(270, 208, "也叫百分率、百分比", size=11.5, anchor="start")
    b += txt(270, 240, "45% 只表示关系，不能带单位", size=12,
             color="#8f2419", anchor="start")
    b += note(260, 286, "百分数是分母固定为 100 的另一种写法，便于比较大小",
              size=11.5)
    b += note(260, 308, "写作 45%，不能写成「45% 人」；「谁占谁的百分之几」要先说清单位「1」",
              size=11.5, color="#8f2419")
    write("m1-01-11-percentage-meaning.svg", svg(W, H, b))


# ───────────────────────────────────────────── 13. 正数和负数
def positive_negative():
    W, H = 520, 320
    b = title(W, "用正数和负数表示相反意义的量")
    x0, x1, y = 40, 480, 130
    b += ('  <defs><marker id="pnArr" markerWidth="8" markerHeight="8" '
          'refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" '
          'fill="#17181c"/></marker></defs>\n')
    b += (f'  <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#17181c" '
          f'stroke-width="1.6" marker-end="url(#pnArr)"/>\n')
    for k in range(-5, 6):
        x = 260 + k * 44
        b += line(x, y - 7, x, y + 7, "#17181c", 1.2)
        col = "#8f2419" if k > 0 else ("#2b6cb0" if k < 0 else "#17181c")
        b += txt(x, y - 14, str(k), size=12, color=col)
    b += (f'  <circle cx="260" cy="{y}" r="4.5" fill="#17181c"/>\n')
    b += line(260, 58, 260, 176, "#bfa578", 1.2, "5 4")
    b += txt(260, 50, "分界", size=11, color="#7a7266")
    b += txt(140, 182, "负数（比 0 小）", size=12, color="#2b6cb0")
    b += txt(390, 182, "正数（比 0 大）", size=12, color="#8f2419")
    b += txt(145, 220, "零下 5℃ → -5℃", size=12.5)
    b += txt(145, 246, "支出 200 元 → -200", size=12.5)
    b += txt(385, 220, "零上 5℃ → +5℃", size=12.5)
    b += txt(385, 246, "收入 200 元 → +200", size=12.5)
    b += note(260, 282, "0 既不是正数，也不是负数，它是正与负的分界", size=12)
    b += note(260, 306, "数轴上从左往右越来越大，所以 正数 &gt; 0 &gt; 负数",
              size=11.5, color="#8f2419")
    write("m1-01-12-positive-negative.svg", svg(W, H, b))


# ───────────────────────────────────────────── 14. 乘法的初步认识
def intro_multiplication():
    W, H = 520, 300
    b = title(W, "每盘 3 个，有 4 盘，一共几个？")
    for i in range(4):
        x = 30 + i * 122
        b += (f'  <rect x="{x}" y="76" width="104" height="76" rx="8" '
              f'fill="#faf6ee" stroke="#b9a888" stroke-width="1.4"/>\n')
        for j in range(3):
            b += (f'  <circle cx="{x+22+j*30}" cy="114" r="11" fill="#e8dcc4" '
                  f'stroke="#b9a888" stroke-width="1.2"/>\n')
    b += txt(260, 184, "3 + 3 + 3 + 3 = 12", size=15)
    b += txt(260, 216, "4 个 3 相加  →  3 × 4 = 12", size=16, color="#8f2419")
    b += txt(260, 244, "3 是每盘的个数，4 是盘数", size=12)
    b += note(260, 274, "求几个相同加数的和，用乘法算更简便", size=12)
    b += note(260, 296, "3 × 4 读作「3 乘 4」，3 和 4 都叫因数，12 叫积",
              size=11.5, color="#8f2419")
    write("m1-06-09-intro-multiplication.svg", svg(W, H, b))


# ───────────────────────────────────────────── 15. 除法的初步认识
def intro_division():
    W, H = 520, 320
    b = title(W, "把 12 个圆片平均分，有两种分法")
    for i in range(3):
        x = 26 + i * 158
        b += (f'  <rect x="{x}" y="62" width="146" height="62" rx="6" '
              f'fill="#f7f2e6" stroke="#b9a888" stroke-width="1.3"/>\n')
        for j in range(4):
            b += (f'  <circle cx="{x+22+j*34}" cy="93" r="10" fill="#e8dcc4" '
                  f'stroke="#b9a888" stroke-width="1.1"/>\n')
    b += txt(260, 148, "平均分成 3 份，每份 4 个：12 ÷ 3 = 4", size=13,
             color="#8f2419")
    x0, y, g = 34, 190, 38
    for j in range(12):
        fill = "#cfe0d0" if (j // 4) % 2 == 0 else "#e8dcc4"
        b += (f'  <rect x="{x0+j*g}" y="{y}" width="{g}" height="34" '
              f'fill="{fill}" stroke="#b9a888" stroke-width="1"/>\n')
        b += txt(x0 + j * g + g / 2, y + 23, str(j + 1), size=11)
    for k in range(4):
        b += line(x0 + k * 4 * g, y - 8, x0 + k * 4 * g, y + 42,
                  "#8f2419", 1.6)
    b += txt(260, 254, "每 4 个一份，能分成 3 份：12 ÷ 4 = 3", size=13,
             color="#8f2419")
    b += note(260, 284, "两种分法都是「平均分」，都用除法计算", size=12)
    b += note(260, 308, "总数 ÷ 份数 = 每份数；总数 ÷ 每份数 = 份数",
              size=11.5, color="#8f2419")
    write("m1-06-11-intro-division.svg", svg(W, H, b))


# ───────────────────────────────────────────── 16. 余数一定比除数小
def remainder_rule():
    W, H = 520, 320
    b = title(W, "17 个圆片，每 5 个分一组")
    for i in range(3):
        x = 20 + i * 150
        b += (f'  <rect x="{x}" y="60" width="136" height="58" rx="6" '
              f'fill="#f7f2e6" stroke="#b9a888" stroke-width="1.3"/>\n')
        for j in range(5):
            b += (f'  <circle cx="{x+18+j*25}" cy="89" r="9" fill="#e8dcc4" '
                  f'stroke="#b9a888" stroke-width="1"/>\n')
    for j in range(2):
        b += (f'  <circle cx="{478+j*24}" cy="89" r="9" fill="#eed8d2" '
              f'stroke="#8f2419" stroke-width="1.3"/>\n')
    b += txt(478, 136, "余 2 个", size=11, color="#8f2419")
    b += txt(260, 158, "17 ÷ 5 = 3 … 2，余数 2 &lt; 除数 5", size=14,
             color="#17181c")
    b += line(30, 176, 490, 176, "#cfc3ae", 1)
    b += txt(260, 202, "如果写成 17 ÷ 5 = 2 … 7 呢？", size=13)
    b += txt(260, 228, "余下的 7 个里还能再拿出 5 个凑成一组，其实没分完",
             size=11.5)
    b += txt(260, 252, "余数 7 比除数 5 大，说明商还能再添 1", size=12,
             color="#8f2419")
    b += note(260, 282, "余数一定要比除数小：余下的不够再分一组，才叫余数",
              size=12)
    b += note(260, 306, "验算：除数 × 商 + 余数 = 被除数，5 × 3 + 2 = 17",
              size=11.5, color="#8f2419")
    write("m1-06-14-remainder-rule.svg", svg(W, H, b))


# ───────────────────────────────────────────── 17. 小数乘法的算理
def decimal_mult():
    W, H = 520, 320
    b = title(W, "0.3 × 0.2 为什么是 0.06？")
    x0, y0, g = 40, 50, 20
    for row in range(10):
        for col in range(10):
            if col < 3 and row < 2:
                fill = "#e2a99c"
            elif col < 3:
                fill = "#d8e2ef"
            elif row < 2:
                fill = "#eed8d2"
            else:
                fill = "#fffdf8"
            b += (f'  <rect x="{x0+col*g}" y="{y0+row*g}" width="{g}" '
                  f'height="{g}" fill="{fill}" stroke="#cfc3ae" '
                  f'stroke-width="0.7"/>\n')
    b += (f'  <rect x="{x0}" y="{y0}" width="{g*10}" height="{g*10}" '
          f'fill="none" stroke="#17181c" stroke-width="1.5"/>\n')
    b += txt(70, 268, "0.3", size=12, color="#2b6cb0")
    b += txt(26, 70, "0.2", size=12, color="#8f2419")
    b += txt(270, 76, "把 1 × 1 的正方形平均分成 100 格", size=12,
             anchor="start")
    b += txt(270, 104, "每一小格是 0.01", size=12, anchor="start")
    b += txt(270, 132, "横着取 0.3，竖着取 0.2", size=12, anchor="start")
    b += txt(270, 160, "重叠部分是 3 × 2 = 6 格", size=12, anchor="start")
    b += txt(270, 196, "6 个 0.01 就是 0.06", size=14, color="#8f2419",
             anchor="start")
    b += txt(270, 228, "0.3 × 0.2 = 0.06", size=16, color="#8f2419",
             anchor="start")
    b += note(260, 280, "先按整数算 3 × 2 = 6，再看两个因数一共有 2 位小数，"
              "积就点 2 位小数", size=11.5)
    b += note(260, 304, "积的小数位数 = 两个因数的小数位数之和",
              size=11.5, color="#8f2419")
    write("m1-06-19-decimal-mult.svg", svg(W, H, b))


# ───────────────────────────────────────────── 18. 同分母分数加减
def fraction_add_sub():
    W, H = 520, 300
    b = title(W, "3/8 + 2/8，为什么分母不变？")
    for idx, (cx, k, color) in enumerate(((100, 3, "#e8dcc4"),
                                          (260, 2, "#cfe0d0"),
                                          (420, 5, "#e8dcc4"))):
        r = 64
        cy = 138
        for j in range(8):
            a1, a2 = 90 - j * 45, 90 - (j + 1) * 45
            x1, y1 = P(cx, cy, r, a1)
            x2, y2 = P(cx, cy, r, a2)
            fill = color if j < k else "#fffdf8"
            b += (f'  <path d="M {cx},{cy} L {f(x1)},{f(y1)} '
                  f'A {r},{r} 0 0 1 {f(x2)},{f(y2)} Z" fill="{fill}" '
                  f'stroke="#17181c" stroke-width="1.2"/>\n')
        b += txt(cx, 226, ["3/8", "2/8", "5/8"][idx], size=15,
                 color="#8f2419")
    b += txt(180, 144, "+", size=26, color="#7a7266")
    b += txt(340, 144, "=", size=26, color="#7a7266")
    b += txt(260, 258, "分母相同，每份就一样大：3 份 + 2 份 = 5 份",
             size=12.5)
    b += note(260, 286, "同分母分数相加减，分母不变，只把分子相加减；"
              "结果能约分的要约成最简分数", size=11.5)
    write("m1-06-21-fraction-add-sub.svg", svg(W, H, b))


# ───────────────────────────────────────────── 19. 乘法运算律
def mult_laws():
    W, H = 520, 320
    b = title(W, "分配律：把 6 拆成 4 + 2，结果不变")
    x0, y0, g = 40, 62, 30
    for col in range(6):
        for row in range(3):
            fill = "#e8dcc4" if col < 4 else "#cfe0d0"
            b += (f'  <rect x="{x0+col*g}" y="{y0+row*g}" width="{g}" '
                  f'height="{g}" fill="{fill}" stroke="#b9a888" '
                  f'stroke-width="1"/>\n')
    b += txt(100, 125, "4 × 3", size=13)
    b += txt(190, 125, "2 × 3", size=13)
    b += txt(130, 52, "4 + 2 = 6", size=12, color="#7a7266")
    b += txt(26, 107, "3", size=13, color="#7a7266")
    b += txt(260, 82, "(4 + 2) × 3 = 6 × 3 = 18", size=12.5, anchor="start")
    b += txt(260, 112, "4 × 3 + 2 × 3 = 12 + 6 = 18", size=12.5,
             anchor="start")
    b += txt(260, 146, "两边相等，这就是乘法分配律", size=12.5,
             color="#8f2419", anchor="start")
    b += txt(260, 182, "交换律：a × b = b × a", size=12, anchor="start")
    b += txt(260, 208, "结合律：(a×b)×c = a×(b×c)", size=12, anchor="start")
    b += note(260, 250, "用字母写更清楚：(a + b) × c = a × c + b × c", size=12)
    b += note(260, 278, "运算律能让计算变简单：25 × 13 × 4 = (25 × 4) × 13",
              size=11.5)
    b += note(260, 304, "先看清数之间的关系，再决定用哪条定律，别硬套",
              size=11.5, color="#8f2419")
    write("m1-06-27-mult-laws.svg", svg(W, H, b))


# ───────────────────────────────────────────── 20. 分数除法的算理
def fraction_div():
    W, H = 520, 320
    b = title(W, "分数除法：换个问法就懂了")
    # 上：4/5 ÷ 2
    x0, y, g = 40, 70, 40
    for j in range(5):
        fill = "#e8dcc4" if j < 4 else "#fffdf8"
        b += (f'  <rect x="{x0+j*g}" y="{y}" width="{g}" height="40" '
              f'fill="{fill}" stroke="#17181c" stroke-width="1.2"/>\n')
    b += line(x0 + 2 * g, y - 8, x0 + 2 * g, y + 48, "#8f2419", 2)
    b += txt(40, 60, "4/5 平均分成 2 份", size=11.5, color="#7a7266",
             anchor="start")
    b += txt(280, 96, "4/5 ÷ 2 = 2/5", size=15, color="#8f2419", anchor="start")
    b += txt(280, 122, "4 个 1/5 平分，每份 2 个 1/5", size=11.5, anchor="start")
    # 下：2/3 ÷ 1/6
    y2, g2 = 190, 34
    for j in range(6):
        fill = "#cfe0d0" if j < 4 else "#fffdf8"
        b += (f'  <rect x="{x0+j*g2}" y="{y2}" width="{g2}" height="40" '
              f'fill="{fill}" stroke="#17181c" stroke-width="1.2"/>\n')
        b += line(x0 + j * g2, y2, x0 + j * g2, y2 + 40, "#b9a888", 1)
    b += txt(40, 180, "2/3 里有几个 1/6？", size=11.5, color="#7a7266",
             anchor="start")
    b += txt(280, 216, "2/3 ÷ 1/6 = 4", size=15, color="#8f2419", anchor="start")
    b += txt(280, 242, "4 个 1/6 正好是 4/6，也就是 2/3", size=11.5,
             anchor="start")
    b += note(260, 276, "除以一个不为 0 的数，等于乘这个数的倒数", size=12.5)
    b += note(260, 300, "4/5 ÷ 2 = 4/5 × 1/2 = 2/5；"
              "2/3 ÷ 1/6 = 2/3 × 6 = 4", size=11.5, color="#8f2419")
    write("m1-06-23-fraction-div.svg", svg(W, H, b))


# ───────────────────────────────────────────── 21. 方程与等式性质
def equation_solve():
    W, H = 520, 320
    b = title(W, "天平平衡，就是等式成立")
    def balance(cx, left, right):
        s = ""
        s += (f'  <line x1="{cx-92}" y1="110" x2="{cx+92}" y2="110" '
              f'stroke="#17181c" stroke-width="2.4"/>\n')
        s += (f'  <polygon points="{cx},112 {cx-12},146 {cx+12},146" '
              f'fill="#e8dcc4" stroke="#b9a888" stroke-width="1.2"/>\n')
        for dx, lab in ((-60, left), (60, right)):
            s += line(cx + dx, 110, cx + dx, 140, "#b9a888", 1.2)
            s += (f'  <rect x="{cx+dx-32}" y="140" width="64" height="26" '
                  f'rx="3" fill="#f7f2e6" stroke="#b9a888" stroke-width="1.2"/>\n')
            s += txt(cx + dx, 158, lab, size=13, color="#17181c")
        return s
    b += balance(150, "x + 3", "8")
    b += balance(390, "x", "5")
    b += txt(270, 136, "两边同时减 3", size=11.5, color="#8f2419")
    b += txt(260, 198, "等式两边同时加上或减去同一个数，等式仍然成立",
             size=12)
    b += txt(260, 230, "x + 3 = 8  →  x = 8 - 3 = 5", size=15,
             color="#8f2419")
    b += txt(260, 262, "检验：5 + 3 = 8，左右相等，x = 5 就是方程的解",
             size=12)
    b += note(260, 292, "含有未知数的等式叫方程；求方程的解的过程叫解方程",
              size=11.5)
    write("m1-08-02-equation-solve.svg", svg(W, H, b))


# ───────────────────────────────────────────── 22. 正比例与反比例
def proportion():
    W, H = 520, 320
    b = title(W, "正比例看「比值」，反比例看「乘积」")
    ox, oy = 50, 240
    b += line(ox, oy, 240, oy, "#17181c", 1.3)
    b += line(ox, oy, ox, 56, "#17181c", 1.3)
    b += line(ox, oy, 230, 60, "#c0392b", 2.2)
    for k in (1, 2, 3, 4, 5):
        px, py = ox + k * 30, oy - 2 * k * 15
        b += (f'  <circle cx="{px}" cy="{py}" r="3.4" fill="#c0392b"/>\n')
        b += txt(px, py - 10, f"({k},{2*k})", size=9.5, color="#7a7266")
    b += txt(44, 256, "0", size=9.5, color="#7a7266", anchor="end")
    for k in range(1, 6):
        b += txt(ox + k * 30, 256, str(k), size=9.5, color="#7a7266")
        b += txt(44, oy - 2 * k * 15 + 4, str(2 * k), size=9.5,
                 color="#7a7266", anchor="end")
    b += txt(244, 244, "x", size=11, color="#7a7266", anchor="start")
    b += txt(42, 54, "y", size=11, color="#7a7266", anchor="end")
    b += txt(150, 44, "y / x = 2（一定）", size=11.5, color="#8f2419")
    # 反比例表格
    tx, ty, cw, rh = 290, 70, 90, 30
    for j in range(6):
        b += line(tx, ty + j * rh, tx + 2 * cw, ty + j * rh, "#cfc3ae", 1)
    for i in range(3):
        b += line(tx + i * cw, ty, tx + i * cw, ty + 5 * rh, "#cfc3ae", 1)
    b += txt(tx + cw / 2, ty + 20, "x", size=11.5, color="#7a7266")
    b += txt(tx + cw * 1.5, ty + 20, "y", size=11.5, color="#7a7266")
    for j, (xv, yv) in enumerate(((1, 12), (2, 6), (3, 4), (6, 2)), start=1):
        b += txt(tx + cw / 2, ty + j * rh + 20, str(xv), size=12)
        b += txt(tx + cw * 1.5, ty + j * rh + 20, str(yv), size=12)
    b += txt(380, 238, "x × y = 12（一定）", size=11.5, color="#8f2419")
    b += note(260, 274, "正比例：比值一定，图像是一条过原点的直线", size=11.5)
    b += note(260, 294, "反比例：乘积一定，一个量变大，另一个反而变小", size=11.5)
    b += note(260, 314, "判断前先找「什么一定」：比值一定 → 正；乘积一定 → 反",
              size=11.5, color="#8f2419")
    write("m1-09-02-proportion.svg", svg(W, H, b))


# ───────────────────────────────────────────── 23. 比例尺
def scale():
    W, H = 520, 320
    b = title(W, "图上 5 厘米，实际有多远？")
    b += line(60, 110, 310, 110, "#c0392b", 3)
    b += line(60, 100, 60, 120, "#c0392b", 2)
    b += line(310, 100, 310, 120, "#c0392b", 2)
    b += txt(185, 94, "图上 5 厘米", size=12.5, color="#8f2419")
    b += txt(185, 146, "× 20000", size=13, color="#7a7266")
    b += line(60, 196, 460, 196, "#2b6cb0", 3)
    b += line(60, 186, 60, 206, "#2b6cb0", 2)
    b += line(460, 186, 460, 206, "#2b6cb0", 2)
    b += txt(260, 222, "实际 100000 厘米 = 1 千米", size=12.5,
             color="#2b6cb0")
    b += box(350, 54, 150, 34, "比例尺 1 : 20000", fill="#e8dcc4", size=12)
    b += note(260, 252, "比例尺 = 图上距离 : 实际距离", size=12.5)
    b += note(260, 276, "图上 1 厘米代表实际 20000 厘米，也就是 200 米", size=11.5)
    b += note(260, 290, "算之前先统一单位：1 千米 = 100000 厘米", size=11.5,
              color="#8f2419")
    b += note(260, 312, "示意图：两条线段不按同一比例画，真实长度相差 20000 倍",
              size=11)
    write("m1-09-03-scale.svg", svg(W, H, b))


# ───────────────────────────────────────────── 24. 周期中的规律
def pattern_cycle():
    W, H = 520, 300
    b = title(W, "彩旗按「红 黄 蓝 绿」重复排列")
    colors = ["#c0392b", "#d9a441", "#2b6cb0", "#4a7c59"]
    for i in range(12):
        x = 34 + i * 40
        c = colors[i % 4]
        b += line(x + 4, 66, x + 4, 118, "#7a7266", 1.2)
        b += (f'  <path d="M {x+4},70 L {x+32},70 L {x+24},82 L {x+32},94 '
              f'L {x+4},94 Z" fill="{c}" stroke="#17181c" '
              f'stroke-width="0.8"/>\n')
        b += txt(x + 4, 132, str(i + 1), size=10.5, color="#7a7266")
    b += (f'  <rect x="28" y="58" width="160" height="82" rx="4" fill="none" '
          f'stroke="#8f2419" stroke-width="1.4" stroke-dasharray="5 4"/>\n')
    b += txt(108, 156, "一组 4 面", size=11.5, color="#8f2419")
    b += txt(260, 190, "第 14 面是什么颜色？14 ÷ 4 = 3 … 2", size=13,
             color="#8f2419")
    b += txt(260, 218, "余 2 → 是一组里的第 2 面 → 黄色", size=12.5)
    b += txt(260, 246, "余 0 就是一组里的最后一面", size=12)
    b += note(260, 276, "先找出重复的一组有几个，再用除法看余数", size=11.5)
    write("m4-02-03-pattern-cycle.svg", svg(W, H, b))


# ───────────────────────────────────────────── 25. 乘法原理（分步计数）
def multiplication_principle():
    W, H = 520, 300
    b = title(W, "2 件上衣、3 条裤子，有几种搭配？")
    left = [(110, 100, "上衣 A"), (110, 190, "上衣 B")]
    right = [(410, 72, "裤子 1"), (410, 145, "裤子 2"), (410, 218, "裤子 3")]
    for lx, ly, _ in left:
        for rx, ry, _ in right:
            b += line(lx + 42, ly, rx - 42, ry, "#cfc3ae", 1)
    for lx, ly, lab in left:
        b += (f'  <circle cx="{lx}" cy="{ly}" r="24" fill="#e8dcc4" '
              f'stroke="#b9a888" stroke-width="1.3"/>\n')
        b += txt(lx, ly + 4, lab, size=11)
    for rx, ry, lab in right:
        b += (f'  <circle cx="{rx}" cy="{ry}" r="24" fill="#cfe0d0" '
              f'stroke="#b9a888" stroke-width="1.3"/>\n')
        b += txt(rx, ry + 4, lab, size=11)
    b += txt(260, 258, "2 × 3 = 6（种）", size=16, color="#8f2419")
    b += note(260, 284, "先选上衣 2 种，再选裤子 3 种；每一步的选法数相乘",
              size=11.5)
    write("m4-03-02-multiplication-principle.svg", svg(W, H, b))


# ───────────────────────────────────────────── 26. 抽屉原理
def pigeonhole():
    W, H = 520, 320
    b = title(W, "4 个苹果放进 3 个抽屉")
    b += txt(260, 56, "想一想：不管怎么放，总有一个抽屉里至少有几个？",
             size=11.5, color="#7a7266")
    for i in range(3):
        x = 50 + i * 150
        b += (f'  <rect x="{x}" y="80" width="140" height="120" rx="4" '
              f'fill="#f7f2e6" stroke="#b9a888" stroke-width="1.5"/>\n')
        b += line(x, 104, x + 140, 104, "#b9a888", 1)
        b += (f'  <rect x="{x+58}" y="96" width="24" height="8" rx="3" '
              f'fill="#e8dcc4" stroke="#b9a888" stroke-width="1"/>\n')
        b += txt(x + 70, 220, f"第 {i+1} 个抽屉", size=11.5, color="#7a7266")
    apples = [(90, 150), (145, 150), (270, 150), (420, 150)]
    for ax, ay in apples:
        b += (f'  <circle cx="{ax}" cy="{ay}" r="17" fill="#e2a99c" '
              f'stroke="#8f2419" stroke-width="1.3"/>\n')
        b += line(ax, ay - 17, ax + 3, ay - 25, "#4a7c59", 2)
    b += note(260, 248, "先尽量平均分：每个抽屉放 1 个，用掉 3 个，还剩 1 个",
              size=11.5)
    b += note(260, 274, "剩下的那个不管放进哪个抽屉，那个抽屉就有 2 个",
              size=11.5)
    b += note(260, 300, "所以总有一个抽屉里不少于 2 个：物体比抽屉多就行",
              size=11.5, color="#8f2419")
    write("m4-04-01-pigeonhole.svg", svg(W, H, b))


BATCH1 = [pie_chart, certainty, triangle_three_sides, circle_features,
          sector, perimeter, rect_perimeter]
BATCH2 = [number_classify, decimal_position, fraction_meaning,
          fraction_property, percentage_meaning, positive_negative,
          intro_multiplication, intro_division, remainder_rule, decimal_mult,
          fraction_add_sub, mult_laws]
BATCH3 = [fraction_div, equation_solve, proportion, scale, pattern_cycle,
          multiplication_principle, pigeonhole]
ALL = BATCH1 + BATCH2 + BATCH3

if __name__ == "__main__":
    args = sys.argv[1:]
    for fn in ALL:
        if not args or fn.__name__ in args:
            fn()
    print("done")
