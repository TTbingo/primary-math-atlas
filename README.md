# 小学数学知识点图谱

按**四大模块**（而不是年级）归纳的小学数学知识点静态站点，每个知识点对应《义务教育数学课程标准（2022 年版）》。

- 线上地址：<https://ttbingo.github.io/primary-math-atlas/>
- 内容规模：4 模块 / 21 主题 / 136 知识点 / 163 个页面
- 纯静态，零依赖：断网双击 `dist/index.html` 也能完整浏览（KaTeX 已本地化）

## 四个模块

| ID | 模块 | 主题数 | 知识点数 |
|----|------|--------|----------|
| m1 | 数与代数 | 9 | 77 |
| m2 | 图形与几何 | 4 | 40 |
| m3 | 统计与概率 | 4 | 9 |
| m4 | 数学思考 | 4 | 10 |

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
open dist/index.html     # 或直接双击
```

## 备份与发布

- `main` 分支：源码（本目录内容，`dist/` 已忽略）
- `gh-pages` 分支：`dist/` 成品，GitHub Pages 从该分支根路径发布

更新站点：

```bash
python build.py
python tools/deploy_ghpages.py "site: 更新说明"
```

线上冒烟检查（Playwright）：

```bash
python tools/verify_online.py
```
