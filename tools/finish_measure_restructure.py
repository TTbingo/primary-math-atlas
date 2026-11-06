# -*- coding: utf-8 -*-
"""收尾脚本：前一次迁移被沙箱中断，这里把剩余步骤幂等补齐。

只做没做完的事：补重定向、补改 m2-01-01 旧 id、m1-07 文件改名、modules/guides 登记。
不再对 id 做二次重编号（引用已经改过，重复替换会再挪一格）。
"""
import json
import io
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PTS = os.path.join(ROOT, "content", "points")

DELETED = "m1-07-02-rmb-time-and-date"
REDIRECT = {
    "m1-06-05-multiplication-intro-and-table": "m1-10-04-rmb",
    "m1-07-01-quantity-relations-basic": "m1-10-04-rmb",
    "m1-07-07-optimization-and-find-bad-item": "m1-10-02-time-units-and-24h",
    "m4-02-01-pattern-arith-sequence-cycle": "m1-10-02-time-units-and-24h",
}
RENUM = {"m1-07-%02d" % i: "m1-07-%02d" % (i - 1) for i in range(3, 15)}
OLD_M2 = "m2-01-01-plane-shapes-and-mass"
NEW_M2 = "m2-01-01-plane-shapes"


def load():
    pts = {}
    for fn in sorted(os.listdir(PTS)):
        if fn.endswith(".json"):
            d = json.load(io.open(os.path.join(PTS, fn), encoding="utf-8"))
            pts[d["id"]] = d
    return pts


def save(d):
    p = os.path.join(PTS, d["id"] + ".json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def main():
    pts = load()

    # 1) 残留重定向（只对还没改的篇目生效）
    for pid, target in REDIRECT.items():
        if pid not in pts:
            continue
        p = pts[pid]
        touched = False
        for r in p["sections"].get("related", []):
            if r["id"] == DELETED:
                r["id"] = target
                touched = True
                if pid == "m1-07-07-optimization-and-find-bad-item":
                    r["kind"] = "常一起考"
                    r["note"] = "常一起考：优化问题全靠算「一共多少分钟」，时分秒的进率与经过时间要和方案比较一起用"
        if DELETED in p.get("prerequisites", []):
            p["prerequisites"] = [x for x in p["prerequisites"] if x != DELETED]
            touched = True
        if touched:
            save(p)
            print("重定向", pid, "→", target)

    # 2) m2-01-01 旧 id 改新 id
    for pid, d in list(pts.items()):
        s = json.dumps(d, ensure_ascii=False)
        if OLD_M2 in s:
            d = json.loads(s.replace(OLD_M2, NEW_M2))
            save(d)
            print("旧 id 更新", pid)

    # 3) m1-07 文件改名（03..14 → 02..13），升序逐级腾空
    pts = load()
    for i in range(3, 15):
        old = "m1-07-%02d" % i
        cands = [k for k in pts if k.startswith(old + "-")]
        if not cands:
            continue
        pid = cands[0]
        new_id = RENUM[old] + pid[len(old):]
        d = pts[pid]
        d["id"] = new_id
        src = os.path.join(PTS, pid + ".json")
        data = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
        os.remove(src)
        io.open(os.path.join(PTS, new_id + ".json"), "w", encoding="utf-8").write(data)
        print("改名", pid, "→", new_id)

    # 4) modules.json
    pts = load()
    mp = os.path.join(ROOT, "content", "modules.json")
    mod = json.loads(io.open(mp, encoding="utf-8").read())
    t7 = next(t for t in mod["topics"] if t["id"] == "m1-07")
    t7["points"] = sorted([p for p in t7["points"] if p != DELETED and p in pts],
                          key=lambda x: int(x.split("-")[2]))
    t7["desc"] = ("和差倍、归一、植树、鸡兔同笼、行程、工程、浓度……这些「典型应用题」"
                  "不是靠背公式，是靠认出它属于哪种数量关系。")
    if not any(t["id"] == "m1-10" for t in mod["topics"]):
        i9 = [i for i, t in enumerate(mod["topics"]) if t["id"] == "m1-09"][0]
        mod["topics"].insert(i9 + 1, {
            "id": "m1-10",
            "module": "m1",
            "no": 10,
            "title": "常见的量",
            "desc": ("多长、多重、多久、多热、多快——量出来的数离开单位就没有意义。"
                     "单位分级、进率、名数的化与聚，加上时间、人民币、质量、温度、速度这几套常用单位，单独成一节。"),
            "standard_ids": ["std-s1-cp-2", "std-s1-cp-3", "std-s1-cp-5", "std-s1-na-7",
                             "std-s1-geo-2", "std-s2-cp-1", "std-s2-cp-2", "std-s2-cp-4",
                             "std-s2-na-8", "std-s2-na-10", "std-s2-geo-3"],
            "points": ["m1-10-01-measure-units-and-denominate", "m1-10-02-time-units-and-24h",
                       "m1-10-03-mass-temperature-speed", "m1-10-04-rmb"],
        })
        print("新增节 m1-10")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(mod, ensure_ascii=False, indent=2) + "\n")

    # 5) guides.json
    gp = os.path.join(ROOT, "content", "guides.json")
    g = json.loads(io.open(gp, encoding="utf-8").read())
    rows = g["guides"]["m1"]["rows"]
    for r in rows:
        if r["topic"] == "m1-07" and "人民币" in r["where"]:
            r["where"] = ("这一章把运算变成解决真实问题的能力。[[m1-07-02]] 的三条关系是全站应用题的通用钥匙；"
                          "[[m1-07-06]] 优化问题是把时间与方案一起算计，[[m1-07-07]] 鸡兔同笼是假设法的代表。")
            print("改写 m1-07 导语")
    if not any(r["topic"] == "m1-10" for r in rows):
        rows.append({
            "topic": "m1-10",
            "where": ("常见的量是应用题里的「翻译层」：题目给的是 2 时 30 分、3 吨 50 千克、60 千米/时，"
                      "先得看懂单位、换成同一级，才能算。[[m1-10-01]] 讲单位、进率与名数的化聚，"
                      "[[m1-10-02]] 是时间，[[m1-10-03]] 是质量、温度与速度，[[m1-10-04]] 是人民币。"
                      "单位看错一格，后面的算式全白算。"),
        })
        print("新增 m1-10 导语")
    io.open(gp, "w", encoding="utf-8").write(json.dumps(g, ensure_ascii=False, indent=2) + "\n")

    # 6) 一致性自检：所有引用都要落在现存知识点上
    pts = load()
    bad = []
    for pid, d in pts.items():
        refs = list(d.get("prerequisites", [])) + [r["id"] for r in d["sections"].get("related", [])
                                                   if not r["id"].startswith("ext:")]
        for r in refs:
            if r not in pts:
                bad.append((pid, r))
    print("悬空引用:", bad if bad else "无")
    print("知识点总数:", len(pts))


if __name__ == "__main__":
    main()
