# CLAUDE.md — 小学数学知识点图谱

纯静态站：`content/*.json` → `build.py`（Python 3 标准库，零第三方依赖）→ `dist/`。
双发布：GitHub Pages（`ttbingo/primary-math-atlas`）与 workbuddy.host（appId `wbapp_kHGLrsiTw1074ukrOuud1h`，需 `?sharecode=`）。
对外说明见 `README.md`；本文只写「下次改代码必须知道」的规则。

## 命令速查

```bash
python build.py                    # 构建到 dist/
python build.py --check            # 只校验：死链/裸公式/禁用词/九板块/模板残留
MATH_NO_CLEAN=1 python build.py    # 原地覆盖（沙箱禁止整树删 dist 时用）
python tools/deploy_ghpages.py "msg"          # 推 gh-pages（差异同步）
python tools/verify_online.py [BASE] [CODE]   # Playwright 线上冒烟（含配图加载）
```

## 硬规则

1. **改内容只改 `content/`，不手改 `dist/`**——`dist/` 是产物，已 gitignore，重跑 build 即覆盖。
2. **`sections` 是字典**（键 = `explanation/scenarios/cautions/why/examples/inferences/pitfalls/intuition/related`），不是数组；九板块缺一即校验失败。
3. **`prerequisites` 必须是真先修**（知识点 id 数组）。历史上曾把 `related[0]` 批量抄成前置，产生 87 条错误前置，已由 `tools/patch_logic.py` 修正。新增知识点时逐条判断，禁止机械复制。
4. **`related` 单向书写**：每条 `{id, note}` 只从本页视角写一次。`build.py` 用 `idx.incoming` 自动补「指向本知识点」分组；两向都写会让同一目标重复出现（`render_related` 有去重兜底，但不要依赖）。
5. **禁用词**（`taxonomy.json.forbidden_words`）：`证明` `求证` `证毕` `∵` `∴` `Q.E.D.`——小学阶段不出现。`build.py --check` 会拦。
6. **SVG 是 XML**：文本里的 `<` `>` 必须写成 `&lt;` `&gt;`，否则整张图解析失败（曾导致三边关系、余数图白屏）。
7. **公式**：正文用 `$...$` / `$$...$$`；块级 `render_text` 不要塞进 `<p>`（用 `render_inline` 剥外层）。渲染后不应残留裸 `$`。
8. **术语不得超纲**：不出现绝对值、平方根、√、相反数、极限、`n-m` 字母公式等初中表述，改成小学说法（"负号后面的数""试到两数相乘超过它"）。

## 环境陷阱（已踩过，别重犯）

- **git push**：SSH 被沙箱禁读 `~/.ssh` → 远端用 HTTPS，走 `credential.helper`（gh）通道。
- **批量删除**：`shutil.rmtree` 删 `gh-pages` 整树被 bulk-delete 拦截 → `deploy_ghpages.py` 用集合差 + 逐个 `os.remove`。
- **CDN 缓存**：GitHub Pages HTML 有缓存，校验线上改动要带 `Cache-Control: no-cache` 或加 `?r=时间戳`。
- **workbuddy.host 门禁**：裸请求 403；首次 `/?sharecode=BYT4SQX5HE` 种 HttpOnly cookie 后子资源自动 200。curl 验证必须带 cookie jar（`-b`），否则误判"图片全 403"。
- **lazy 加载假阳性**：未进视口时 `naturalWidth=0`，检查配图前先 `loading='eager'` + `scrollIntoView` + `networkidle`。

## 目录职责

| 路径 | 作用 |
|---|---|
| `content/modules.json` | 模块/主题/知识点清单，ID 唯一定义（`m{模块}-{节}-{序}-{slug}`，字典序即学习顺序） |
| `content/points/*.json` | 136 篇正文 |
| `content/media/*.svg` | 102 张配图 |
| `build.py` | 单文件构建 + `verify_output()` 自检 |
| `tools/gen_figs*.py` `patch_media.py` | 配图生成 / media 字段批量写入 |
| `tools/patch_logic*.py` | 前置与正文逻辑批量修复（历史修复留档，可参照写法） |
| `templates/` `assets/` | HTML 模板、CSS/JS、本地化 KaTeX 0.16.22 |
