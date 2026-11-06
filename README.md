# 小学数学知识点图谱

按**四大模块**（而不是年级）归纳的小学数学知识点静态站点，每个知识点对应《义务教育数学课程标准（2022 年版）》。

- 线上地址（GitHub Pages）：<https://ttbingo.github.io/primary-math-atlas/>
- 线上地址（workbuddy.host，需分享码）：<https://primary-math-atlas.app.workbuddy.host/?sharecode=BYT4SQX5HE>
- 内容规模：4 模块 / 22 主题 / 90 知识点 / 117 个页面 / 102 张 SVG 配图
- 纯静态，零依赖：断网双击 `dist/index.html` 也能完整浏览（KaTeX 已本地化）

## 四个模块

| ID | 模块 | 主题数 | 知识点数 |
|----|------|--------|----------|
| m1 | 数与代数 | 10 | 58 |
| m2 | 图形与几何 | 4 | 20 |
| m3 | 统计与概率 | 4 | 6 |
| m4 | 数学思考 | 4 | 6 |

主题划分参照《小升初数学知识点汇编（四大模块）》，正文结合课标 2022、人教版教材与《小学学霸笔记·数学》撰写。
每个知识点固定九大板块：说明 · 使用场景 · 注意点 · **为什么是这样** · 按场景的例题 · 常用推论 · 易错点 · 直观理解 · 关联知识点。

## 目录结构

```
content/
  modules.json       模块/主题/知识点清单（唯一定义）
  points/*.json      136 篇知识点正文
  standards.json     课标原文条目
  taxonomy.json      行为动词、核心素养、scope 字典
  media/*.svg        配图
assets/              CSS / JS / 本地化 KaTeX
templates/           HTML 模板
tools/               迁移、配图生成、部署等脚本
build.py             单文件构建脚本（仅用 Python 标准库）
dist/                构建产物（不入库，走 gh-pages 分支）
```

## 本地使用

```bash
python build.py          # 生成 dist/
python build.py --check  # 只做校验：死链、裸公式、禁用词、板块完整性
MATH_NO_CLEAN=1 python build.py   # 原地覆盖，不删 dist（沙箱禁止整树删除时用）
open dist/index.html     # 或直接双击
```

## 内容约定

- `content/points/*.json` 的 `sections` 是**字典**（键为板块 id），不是数组。
- `prerequisites` 存**知识点 id 数组**，必须是真正的先修知识，不能拿 `related[0]` 顶替。
- `related` 每条为 `{id, note}`，**只从一个方向书写**：构建时由 `idx.incoming` 自动生成反向引用并渲染为「指向本知识点」分组。若两个方向都写，同一目标会在两个分组重复出现（`render_related` 已做去重兜底，但数据仍应单向书写）。
- 配图放 `content/media/*.svg`，在知识点的 `media` 字段声明（alt/caption/宽高）；未被正文 slot 引用的图会自动插入「为什么是这样」之前。SVG 是 XML，文本中的 `<`、`>` 必须写成 `&lt;`、`&gt;`。

## 备份与发布

- `main` 分支：源码（本目录内容，`dist/` 已忽略）
- `gh-pages` 分支：`dist/` 成品，GitHub Pages 从该分支根路径发布

更新 GitHub Pages：

```bash
python build.py
python tools/deploy_ghpages.py "site: 更新说明"   # 差异同步，避免整树删除被拦截
```

更新 workbuddy.host：发布目录固定为 `dist/`，appId `wbapp_kHGLrsiTw1074ukrOuud1h`，重新发布后链接不变（`domainPrefix=primary-math-atlas`，`entryHtml=index.html`）。

线上冒烟检查（Playwright）：

```bash
python tools/verify_online.py                                          # GitHub Pages
python tools/verify_online.py https://primary-math-atlas.app.workbuddy.host BYT4SQX5HE
```

> workbuddy.host 对每个请求做门禁，裸访问返回 403「链接不完整」；首次带 `?sharecode=` 后服务端下发 HttpOnly cookie，子资源自动放行，因此 `dist/` 不需要嵌入分享码。
