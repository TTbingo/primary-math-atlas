# -*- coding: utf-8 -*-
"""正文数学逻辑修复（依据 4 组审查报告的 48 处确凿错误）。

每条: (pid, json_path, mode, old, new)
mode = 'SUB': 在该字段值内做子串替换（要求恰好出现一次）
mode = 'FULL': 整值替换
执行后做 JSON 可解析校验。
"""
import json, os, sys

POINTS = os.path.join(os.path.dirname(__file__), "..", "content", "points")

E = [
    # ---------- A 组：数与代数（认识） ----------
    ("m1-01-04-num-within-10000", "/sections/why/steps[1]", "SUB",
     "没写 0，5 就会从千位滑到十位", "没写 0，3 就会从千位滑到十位、5 从百位滑到个位"),
    ("m1-01-04-num-within-10000", "/sections/pitfalls[2]/why", "SUB",
     "写成 205，5 从个位跑到了十位、2 从千位跑到了百位",
     "写成 205，2 从千位降到了百位，5 仍在个位——丢掉的是百位和十位上的 0"),
    ("m1-01-05-big-number", "/sections/pitfalls[0]/right", "SUB",
     "如果读成「十万零六千」，写回去会变成 1006000，多了一位",
     "若读成「十万零六千」，就是凭空多读了一个「零」——按规范读法十万六千写回去，正是 106000"),
    ("m1-01-06-decimal-position", "/sections/why/experiment", "SUB",
     "把百位的 2 颗珠子挪到十位", "把千位的 2 颗珠子挪到十位"),
    ("m1-01-06-decimal-position", "/sections/examples[2]/solution", "SUB",
     "挪到百位后是 2600，扩大到原来的 10 倍",
     "挪到百位后，6 表示的数由 60 变成 600，扩大到原来的 10 倍；整个数由 2060 变成 2600"),
    ("m1-01-06-decimal-position", "/sections/examples[2]/answer", "SUB",
     "变成 2600，是原来的 10 倍", "6 表示的数变成 600，是原来的 10 倍；整个数变成 2600"),
    ("m1-01-06-decimal-position", "/sections/examples[3]/solution", "SUB",
     "4 在十位，是 4 个十千米即 40 千米", "4 在十位，是 4 个十千米即 40 千米（40000 米）"),
    ("m1-01-06-decimal-position", "/sections/examples[3]/answer", "SUB",
     "4 表示 40 千米，8 表示 800 米", "4 表示 40 千米（40000 米），8 表示 800 米"),
    ("m1-01-06-decimal-position", "/sections/why/steps[2]", "FULL", None,
     "**位置就这样被捆了出来**。从右往左，第一格放单根，第二格放捆，第三格放包，第四格放箱。第 1 格代表 1，第 2 格代表 10，第 3 格代表 100，第 4 格代表 1000——每往左挪一格，代表的东西就扩大到 10 倍。"),
    ("m1-01-06-decimal-position", "/sections/related[0]/note", "SUB",
     "应用：亿以上的数靠分级才读得清", "应用：亿以内数的分级读写，用的就是这张表"),
    ("m1-01-07-decimal-meaning", "/sections/pitfalls[0]/why", "SUB",
     "3 就从十分位「挤」到了百分位，数值变大", "5 就从千分位「挤」到了百分位，数值变大"),
    ("m1-01-07-decimal-meaning", "/sections/why/experiment", "SUB",
     "先把 1 小段涂色表示 0.1，再数出 30 个小格涂色，看看是不是和 0.3 涂得一样多——这就是 0.3 = 0.30",
     "先涂 3 个小段（每个小段 10 个小格，共 30 个小格）表示 0.3，再单独数出 30 个小格涂色表示 0.30——两次涂色的范围完全重合，这就是 0.3 = 0.30"),
    ("m1-01-08-decimal-intro", "/sections/related[0]/note", "FULL", None,
     "算理：0.1 来自「把 1 平均分成 10 份」，这一步用的正是除法"),
    ("m1-01-08-decimal-intro", "/sections/related[2]/note", "FULL", None,
     "延伸：长度单位进率是 10，1 分米写成 0.1 米；面积单位进率是 100，1 平方分米 = 0.01 平方米——两套进率不同，别混"),
    ("m1-01-10-fraction-property", "/sections/related[2]/note", "FULL", None,
     "后续：同分母分数相加减，正是分数单位相同才能直接数"),
    ("m1-01-11-percentage-meaning", "/sections/examples[3]/solution", "SUB",
     "剩下的占 $1 - 30\\% = 70\\%$，至少 350 毫升", "剩下的至多占 $1 - 30\\% = 70\\%$，至多 350 毫升"),
    ("m1-01-11-percentage-meaning", "/sections/examples[3]/answer", "SUB",
     "果汁至少 150 毫升，其余至少占 70%", "果汁至少 150 毫升，其余至多占 70%"),
    ("m1-01-11-percentage-meaning", "/sections/related[1]/note", "SUB",
     "用的是分数除法", "用的是除法（化成小数再改写成百分数）"),
    ("m1-02-01-integer-read-write", "/sections/cautions[1]", "SUB",
     "满了四位就要往上一级进", "写满四位，下一位就要落到更高级去"),
    ("m1-02-01-integer-read-write", "/sections/cautions[2]", "FULL", None,
     "**只有最左边那一级（最高级）可以不满四位**，其余每一级都必须写满四位、不足补 0；分级线永远从右往左每四位一道。"),
    ("m1-02-02-decimal-fraction-read-write", "/sections/why/steps[2]", "SUB",
     "后者的 0 占住了十分位", "后者的 0 占住了百分位"),
    ("m1-02-02-decimal-fraction-read-write", "/sections/pitfalls[1]/why", "SUB",
     "中间的 0 占着十分位", "中间的 0 占着百分位"),
    ("m1-03-02-rewrite-wan-yi", "/sections/intuition", "SUB",
     "每 4 颗装一小盒，每 4 个小盒再装一大盒", "每 10000 颗装一小盒，每 10000 个小盒再装一大盒"),
    ("m1-03-03-fraction-forms", "/sections/scenarios[2]", "SUB",
     "说成「两圈又四分之一」", "说成「两圈又四分之三」"),
    ("m1-03-03-fraction-forms", "/sections/examples[1]/solution", "SUB",
     "$400 \\times 2 + 100 = 1100$ 米", "$400 \\times 2 + 400 \\times \\frac{3}{4} = 800 + 300 = 1100$ 米"),
    ("m1-03-03-fraction-forms", "/sections/why/experiment", "SUB",
     "剪 7 个同样大的圆，每个用十字线分成 4 份，全部剪开，得到 7 个四分之一圆片",
     "剪 2 个同样大的圆，每个用十字线分成 4 份，全部剪开得到 8 个四分之一圆片，取其中 7 个"),
    ("m1-03-03-fraction-forms", "/sections/related[2]/note", "FULL", None,
     "后续：同分母分数相加减，分母不变、分子相加减"),
    ("m1-03-04-decimal-fraction-percent-convert", "/sections/related[2]/note", "FULL", None,
     "算理：分数化小数是分子除以分母，用的是整数除法"),
    ("m1-05-02-divisibility-rules", "/sections/why/experiment", "SUB",
     "再把没被涂掉的数圈出来，它们就是 100 以内的质数，一共 25 个",
     "再把没被涂掉的数圈出来——里面还混着 1 和 49、77、91 这些数，得再用 7 去试除一遍，最后剩下的才是 100 以内的质数，一共 25 个"),
    ("m1-05-04-gcd-lcm", "/sections/related[1]/note", "SUB",
     "短除要除到商互质，得先知道什么是质数", "短除要除到两个商互质，得先知道什么是互质"),
    ("m1-05-03-prime-composite", "/sections/related[2]/note", "FULL", None,
     "递进：找公因数、公倍数时，先会成对找因数更快"),

    # ---------- B 组：数的运算 ----------
    ("m1-06-30-estimation", "/sections/cautions[2]", "SUB",
     "两个两位数相乘一定是四位数，这条先记住",
     "两个两位数相乘，积是三位数或四位数（$10 \\times 10 = 100$、$99 \\times 99 = 9801$），这条先记住"),
    ("m1-06-30-estimation", "/sections/pitfalls[2]/why", "SUB",
     "两个两位数相乘，结果一定是四位数",
     "两个两位数相乘，积可能是三位数（$10 \\times 10 = 100$）也可能是四位数（$99 \\times 99 = 9801$）"),
    ("m1-06-30-estimation", "/sections/inferences[4]", "SUB",
     "往不利方向估都不够，实际就一定不够",
     "往有利方向估都不够，实际才一定不够；往不利方向估不够，是不能下结论的，得精确计算"),
    ("m1-06-27-mult-laws", "/sections/why/experiment", "FULL", None,
     "在方格纸上画 4 行点阵，每行前 25 个点涂红、后 23 个点涂蓝。数总数有两种办法：先数每行 $25 + 23$ 个、共 4 行，是 $4 \\times (25 + 23) = 192$；或者分开数，红点 $4 \\times 25 = 100$ 个、蓝点 $4 \\times 23 = 92$ 个，合起来 $100 + 92 = 192$。两种数法结果一样，这就是你亲手「数」出来的分配律。"),
    ("m1-06-16-mult-2digit", "/sections/examples[1]/question", "SUB",
     "竖式第二层的 5 为什么写在十位下面", "竖式第二层的 6 为什么写在十位下面"),
    ("m1-06-16-mult-2digit", "/sections/examples[1]/solution", "SUB",
     "第二层的 5 代表「256 个十」", "第二层的 256 代表「256 个十」"),
    ("m1-06-22-fraction-mult", "/sections/scenarios[1]", "FULL", None,
     "**分披萨、分蛋糕**：一个披萨，小明吃了整个的 $\\frac{2}{3}$，小红吃的又是小明那份的 $\\frac{3}{4}$——小红吃了整个披萨的几分之几？这就是分数乘法。"),
    ("m1-06-12-division-by-table", "/sections/related[2]/note", "FULL", None,
     "后续：除数是一位数的除法竖式，每一步仍靠口诀试商"),

    # ---------- C 组：应用题 / 式与方程 / 比 ----------
    ("m1-09-01-ratio-meaning", "/sections/cautions[1]", "SUB",
     "求比值得 $\\frac{2}{3}$ 或 1.5", "求比值得 $\\frac{2}{3}$（约 0.67）"),
    ("m1-07-14-profit-interest", "/sections/why/experiment", "SUB",
     "第二轮进价 10 元、卖 15 元", "第二轮进价 10 元、卖 14 元"),
    ("m1-07-13-engineering", "/sections/why/experiment", "SUB",
     "再把纸换成 60 格，速度不变，会发现还是要 6 分钟。**格子总数变了，时间没变**——这就是可以设总量为 1 的原因",
     "再把纸换成 60 格、同时把效率也翻倍（甲每分 6 格、乙每分 4 格），计时仍是 6 分钟——**总量和效率按同一倍数变化，时间就不变**；若只把格子换成 60 格而速度不变，就要 12 分钟了。这就是可以把总量设为 1 的原因：真正决定时间的，是效率之间的比"),
    ("m1-07-10-age-problem", "/sections/why/experiment", "SUB",
     "第四列从 3.8 一路往下掉，慢慢靠近 2", "第四列从 3.8 一路往下掉，越来越接近 1"),

    # ---------- D 组：平面图形 / 统计 / 思考 ----------
    ("m2-04-01-direction", "/sections/cautions[0]", "SUB",
     "后者从东向北偏 30 度（离东更近），两者相差 60 度", "后者从东向北偏 30 度（离东更近），两者相差 30 度"),
    ("m2-04-01-direction", "/sections/why/experiment", "SUB",
     "两人相距约 60 度", "两人相距约 30 度"),
    ("m2-04-01-direction", "/sections/pitfalls[0]/why", "SUB",
     "后者从东向北偏 30 度，两者相差 60 度", "后者从东向北偏 30 度，两者相差 30 度"),
    ("m2-01-05-triangle-classify", "/sections/examples[2]/solution", "SUB",
     "不用管另一个锐角是 35° 还是 65°", "不用管另一个锐角是多少度——它一定是 90° − 35° = 55°"),
    ("m2-01-06-triangle-angle-sum", "/sections/related[2]/note", "SUB",
     "内角和帮你判断图形能不能拼成", "能不能拼成三角形，要看三边关系"),
    ("m2-01-07-triangle-three-sides", "/sections/inferences[2]", "FULL", None,
     "**三角形最稳固**：三条边一旦确定，形状和大小就完全定死，推不动、拉不变形——这也是木架、自行车架爱用三角形的原因。"),
    ("m2-01-14-rect-perimeter", "/sections/cautions[3]", "SUB",
     "（那样也对，但容易漏一步）", "（那样得到的是 8，等于两条宽的和，还要再除以 2）"),
    ("m2-01-21-circle-circumference", "/sections/related[2]/note", "FULL", None,
     "递进：有了 S = ab 这个根基，把圆剪拼成长方形时，才拼得出长 πr、宽 r"),
    ("m2-01-22-circle-area", "/sections/why/steps[5]", "SUB",
     "极限的想法是——分成非常非常多的份，拼出来就是一个长方形",
     "分得非常非常多时，拼出的图形就非常非常接近长方形——份数越多越像，而且没有尽头"),
    ("m3-02-04-chart-choice", "/media[0]/alt", "SUB",
     "连线一路向上，图下写着「读出：一路上升，增长明显」",
     "连线忽升忽降，图下写着「读出：忽上忽下像大涨大跌，其实只差 3 本」"),
    ("m3-02-04-chart-choice", "/sections/explanation[3]", "SUB",
     "右边用折线图、纵轴只画 95 到 100，四个点被拉开，读者会说「一路上升、增长明显」",
     "右边用折线图、纵轴只画 95 到 100，四个点被拉开，读者会说「忽上忽下、像大涨大跌」"),
]


def get_path(obj, path):
    """按 /sections/why/steps[1] 形式取值"""
    cur = obj
    for part in path.strip("/").split("/"):
        if "[" in part:
            key, idx = part[:-1].split("[")
            cur = cur[key][int(idx)]
        else:
            cur = cur[part]
    return cur


def set_path(obj, path, val):
    parts = path.strip("/").split("/")
    parent = obj
    for part in parts[:-1]:
        if "[" in part:
            key, idx = part[:-1].split("[")
            parent = parent[key][int(idx)]
        else:
            parent = parent[part]
    last = parts[-1]
    if "[" in last:
        key, idx = last[:-1].split("[")
        parent[key][int(idx)] = val
    else:
        parent[last] = val


def main():
    ok = fail = 0
    for pid, path, mode, old, new in E:
        fp = os.path.join(POINTS, pid + ".json")
        d = json.load(open(fp, encoding="utf-8"))
        cur = get_path(d, path)
        if mode == "FULL":
            if cur == new:
                ok += 1
                continue
            set_path(d, path, new)
        else:
            n = cur.count(old)
            if n != 1:
                print(f"[MISS] {pid} {path} 命中 {n} 次: {old[:40]}")
                fail += 1
                continue
            set_path(d, path, cur.replace(old, new))
        json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(fp, "a", encoding="utf-8").write("\n")
        ok += 1
    print(f"完成 {ok} / {len(E)}，失败 {fail}")
    # JSON 可解析校验
    import glob
    for f in glob.glob(os.path.join(POINTS, "*.json")):
        json.load(open(f, encoding="utf-8"))
    print("全部 JSON 可解析")


if __name__ == "__main__":
    main()
