# 知识点写作规范（所有写作 Agent 必读）

项目根：`D:\workbuddy的工作空间\2026-11-03-11-08-31\math-site`

## 0. 开工前必须读的三个文件

1. `content/points/m2-01-17-rect-area.json` —— **样板篇**，照着它的语感、深度、字段结构写
2. `content/modules.json` —— 四大模块与 21 个节的定义，你的每篇都必须挂在其中一个节下面
3. `content/taxonomy.json` —— 所有枚举值（scenes / scopes / literacy / verb_level）
4. `content/_reference/formula-audit.md` —— **公式唯一合法来源**，不得使用表外公式
5. `content/_reference/point-plan.md` —— 全部知识点清单，写 `related` / `prerequisites` 时只能引用这里出现过的 id

## 1. 产出物

每篇一个 JSON：`content/points/{id}.json`，文件名必须与 `id` 完全一致。

**不要再改任何其它文件** —— 目录、清单、索引都由构建脚本自动生成。

## 2. 完整字段

```json
{
  "schema": 1,
  "id": "<与文件名同名>",
  "type": "point",
  "title": "<中文标题，6~14 字>",
  "slug": "<英文短名>",
  "summary": "<一句话，30~60 字，说清这个知识点在讲什么>",
  "keywords": ["3~7 个检索词"],
  "module": "<m1|m2|m3|m4，来自清单>",
  "topic": "<如 m1-07，你的 id 前两段>",
  "domain": "<四领域之一：数与代数|图形与几何|统计与概率|综合与实践>",
  "strand": "<课标主题，如 数与运算 / 图形的认识与测量>",
  "segment": "<1|2|3，按年级：1-2年级=1，3-4年级=2，5-6年级=3>",
  "standard_ids": ["<从 content/standards.json 里选 1~3 个真实存在的 id>"],
  "verb_level": "<课标行为动词：了解|理解|掌握|运用|经历|体验|感悟|探索>",
  "literacy": ["<从 taxonomy.literacy 选 1~3 个>"],
  "scope": "core",
  "prerequisites": ["<可选，必须是 manifest 里存在的 id>"],
  "media": [ { "id":"fig1","file":"xxx.svg","alt":"...","width":480,"height":240,"caption":"图 1：..." } ],
  "sections": { ...九板块... },
  "meta": { "source": "课标2022 第X学段·领域·主题(N) ／ 参考《小学学霸笔记·数学》《小升初数学知识点汇编》", "reviewed": true, "updated": "2026-11-03" }
}
```

`media` 可选。**只有几何图形、线段图、方格图这类「看图才明白」的知识点才配 SVG**；纯计算类知识点可以不配，`why` 里不要写 `diagram` 字段。

配 SVG 时：文件放 `content/media/`，命名与 id 对应，如 `m2-01-17-rect-formula.svg`，宽高写在 JSON 里，`alt` 必须**详细描述图里画了什么**（这是本站的亮点，参考样板篇）。

## 3. 九板块写法（硬性要求）

| 板块 | 类型 | 要求 |
|---|---|---|
| `explanation` | string[] | ≥80 字。用小学生听得懂的话讲「是什么」，**不出现初中术语** |
| `scenarios` | string[] | ≥80 字。「什么时候会用到」，每条以场景名开头 |
| `cautions` | string[] | ≥60 字。注意点，每条「**要点**+解释」 |
| `why` | object | `{ "diagram":"fig1"(可选), "steps":[...≥2条], "experiment":"动手实验" }`。**不许出现「证明/求证/证毕/∵/∴」**。steps 要真做算理拆解，不能把公式换个说法重述一遍 |
| `examples` | array ≥3 | 每题 `{id, scene, context, question, solution, answer, media(可选), tags}`。`scene` 必须来自 taxonomy.scenes 且**同一篇内不重复**；`context` 写现代真实情境 |
| `inferences` | string[] ≥2 | 常用推论，**只能用 formula-audit.md 里收录的公式** |
| `pitfalls` | array ≥2 | `{wrong, why, right}` 三字段齐全。资料里没有易错点，靠你归纳典型错因 |
| `intuition` | string | ≥60 字。一个生活类比，不能重复 explanation 的内容。有顺口溜填在 `rhyme`（没有就空字符串） |
| `related` | array 2~4 | `{id, note}`，id 必须来自 manifest，**note 写清为什么关联**（如「前置：先认识面积单位」） |

## 4. 情境改造（必须做）

例题的 `context` 要用**现代、孩子有体感**的情境，禁止沿用旧资料的原型：

| 旧资料原型 | 改成 |
|---|---|
| 甲乙两地、两港轮船 | 两个地铁站 / 两地的高铁站 |
| 好马劣马、解放军追敌 | 删除，改地铁快慢车 / 两人骑车 |
| 服装厂用布、某工厂调度 | 给教室做窗帘 / 手工课分材料 / 图书馆换座位 |
| 拖拉机耕地、油菜籽榨油 | 现代农业口吻，或换成共享单车调度 |
| 存款利率 + 利息税 20% | 删除利息税，改用「零花钱存入储蓄罐」 |
| 某班学生、某校 | 保留，但尽量写成具体可感的校园场景 |

## 5. 公式与符号

- 行内公式：`$6 \times 4 = 24$`
- 块级公式：单独一行写 `$$S = a \times b$$`
- **JSON 里反斜杠必须写成 `\\`**，例如 `"$6 \\times 4$"`
- 人民币写「元」或 `¥`，**绝不能写 `$5`**
- 面积写 `$\text{cm}^2$`，不要写 `cm2`

## 6. 禁止事项

- 禁用词：`证明`、`求证`、`证毕`、`∵`、`∴`、`Q.E.D.`（小学不讲证明）
- 不得使用 formula-audit.md 之外的公式
- 不得修改 `build.py`、`templates/`、`assets/`、其他册的 JSON
- 不得编造 `standard_ids`，必须是 `content/standards.json` 里真实存在的 id
- 不得运行 `python build.py`（有并发冲突），改用下面第 7 条自检

## 7. 自检（每写完一篇就跑）

```bash
cd "D:/workbuddy的工作空间/2026-11-03-11-08-31/math-site"
python -c "
import json,pathlib
for p in sorted(pathlib.Path('content/points').glob('*.json')):
    try: json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception as e: print('BAD', p.name, e)
print('json syntax ok')
"
```

再逐篇自查：九板块齐全、`scene` 不重复、`why.steps` ≥2 且真做了算理拆解、`pitfalls` 三字段齐、`related` 的 id 都在 manifest 里、字数达标。

## 8. 语感

参考样板篇：直接、具体、像一位有经验的老师在讲。
- 用「你」「我们」，不要「学生应」
- 先给具体例子，再抽象出结论
- 「为什么是这样」要让人读完觉得「哦，原来是这样」，而不是「背下来吧」
- 易错点要先摆出**具体的错误答案**（如「算成 $4 \times 2 = 8$」），再说错在哪
