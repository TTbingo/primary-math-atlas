#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并后例题场景的语义化重分配。

合并把多个原节点的例题并到一个节点，同一节点内场景不允许重复
（build.py 校验规则）。原站点每个节点只有 3~5 道题、场景天然不重复；
合并后最多 20 道题，13 个场景不够用，且机械轮换会把「数花生」改成
「物流运输」这种不贴切的场景。

做法：按例题正文（question + context）里的语义线索判定最贴切的生活场景，
再在该节点内做贪心分配——先给每道题算一个「首选场景」，冲突时让位给
次优候选；全都占位冲突的，退到同语义族内的其他场景。
"""
import json
import glob
import os
import re
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
POINTS = os.path.join(CONTENT, "points")

tax = json.load(open(os.path.join(CONTENT, "taxonomy.json"), encoding="utf-8"))
SCENES = tax["scenes"]

# 场景语义族：同族之间可以互换而不太失真
FAMILY = {
    "购物消费": "钱货", "金融理财": "钱货", "饮食与配比": "量配",
    "农业生产": "田地", "工程建造": "建造", "绿化照明": "建造",
    "物流运输": "交通", "行程出行": "交通", "上学日常": "校园",
    "校园生活": "校园", "家庭与年龄": "家居", "自然现象": "自然",
    "计量与估算": "量配",
}

# 场景 → 触发关键词（命中即加分）
KEYWORDS = {
    "购物消费": ["买", "卖", "花", "元", "角", "分", "钱", "付", "找零", "价钱", "超市", "商店", "文具店", "购物", "购买", "售"],
    "金融理财": ["利息", "本金", "利润", "银行", "存钱", "利率", "税", "保险"],
    "饮食与配比": ["吃", "食物", "米", "面", "菜", "肉", "果汁", "牛奶", "配", "食谱", "餐", "水果", "草莓", "糖", "蛋糕", "食堂", "份"],
    "农业生产": ["田", "地", "亩", "庄稼", "水稻", "麦", "玉米", "大棚", "菜地", "农场", "植树", "庄稼地", "果园", "养殖"],
    "工程建造": ["建", "造", "房", "桥", "墙", "楼", "工", "铺", "修", "盖", "工程", "装饰", "管道", "通风管", "承重"],
    "绿化照明": ["花坛", "绿化", "草坪", "树", "草", "灯", "绿植", "花圃", "植树", "扫", "街道", "公园"],
    "物流运输": ["运", "送", "搬", "载", "车", "货", "快递", "批发", "仓库", "物流", "卡车", "运输"],
    "行程出行": ["车", "路", "走", "行", "旅", "坐", "骑", "开", "公里", "速度", "站", "机场", "距离"],
    "上学日常": ["上", "课", "作业", "本子", "铅笔", "书包", "文具", "班", "学校", "早", "晚", "课间", "粉笔", "讲台"],
    "校园生活": ["班", "同学", "小朋友", "游戏", "活动", "操场", "排队", "报数", "运动会", "社团", "值日", "课桌"],
    "家庭与年龄": ["家", "爸爸", "妈妈", "爷", "奶", "哥", "弟", "姐", "妹", "岁", "年龄", "家人", "碗", "房间", "弟妹"],
    "自然现象": ["气温", "下雨", "雪", "风", "雷", "彩虹", "树叶", "影子", "日出", "潮", "太阳", "月", "白天", "黑夜"],
    "计量与估算": ["大约", "估算", "估计", "约", "厘米", "米", "分米", "毫米", "千克", "克", "吨", "升", "毫升", "量", "测"],
}


def score(scene, text):
    """某场景与例题文本的贴合度。"""
    s = 0
    for kw in KEYWORDS.get(scene, []):
        if kw in text:
            s += 1
    return s


def candidates(text):
    """按贴合度排出的候选场景（分数降序）。"""
    sc = [(score(s, text), s) for s in SCENES]
    sc.sort(key=lambda x: (-x[0], SCENES.index(x[1])))
    return [s for _, s in sc]


def main():
    files = sorted(glob.glob(os.path.join(POINTS, "*.json")))
    total = 0
    for f in files:
        j = json.load(open(f, encoding="utf-8"))
        exs = j["sections"].get("examples") or []
        if not exs:
            continue
        cur = [e.get("scene") for e in exs]
        dup_scenes = {s for s, c in collections.Counter(cur).items() if c > 1}
        if not dup_scenes:
            continue

        # 第一遍：算出每道题的首选场景
        want = []
        for e in exs:
            text = "%s %s" % (e.get("question", ""), e.get("context", ""))
            want.append(candidates(text))

        # 第二遍：贪心分配——先处理原场景不冲突的题，再处理冲突的
        used = set()
        assign = [None] * len(exs)
        # 2a. 原场景不冲突的直接保留
        for i, e in enumerate(exs):
            s = e.get("scene")
            if s not in dup_scenes and s not in used:
                assign[i] = s
                used.add(s)
        # 2b. 冲突题：按候选顺序找空位
        for i, e in enumerate(exs):
            if assign[i]:
                continue
            for c in want[i]:
                if c not in used:
                    assign[i] = c
                    used.add(c)
                    break
            else:
                # 全站场景都占满（同族兜底）
                fam = FAMILY.get(e.get("scene"), e.get("scene"))
                for c in SCENES:
                    if FAMILY.get(c, c) == fam and c not in used:
                        assign[i] = c
                        used.add(c)
                        break

        for i, e in enumerate(exs):
            if assign[i] and assign[i] != e.get("scene"):
                total += 1
                e["scene"] = assign[i]

        with open(f, "w", encoding="utf-8") as fh:
            json.dump(j, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print("场景重分配完成：%d 处" % total)


if __name__ == "__main__":
    main()
