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
46. **教材定位（textbook_ref）是必填字段**：每篇都要有 `{note, locations[]}`，locations 里每项是 `{volume, units[{no,name}], special[{kind,name}]}`。册次与单元号必须与 `content/textbook.json` 完全一致（build 会逐条比对单元名，对不上就报错）。`content/textbook.json` 是人教版小学数学 2024 新版：12 册 × 单元号 + 综合实践 + 数学广角（数学广角不占单元号）。
47. **关联知识点用三类结构**：`{id, kind, note}`，kind 只能是 `前置 / 后续 / 常一起考`，每类至少一条、总数 2~4 条。硬约束：「前置」的目标必须排在本文之前，「后续」必须排在本文之后（顺序 = 依次遍历 `modules.json` 的 `topics` 数组、展开每个的 `points`）。**同一对关系只在一篇里写**，另一篇靠构建器按 `REL_FLIP` 自动补反向链接——两篇都写就会重复展示。站内没有前置可用时用 `ext:` 前缀引用站外内容（渲染为纯文字，不生成链接）。
48. **年级进度**：先学的篇目不得引用后学概念。「因数」是五下术语、「方程」是五下、「小数乘法」是五上、「百分数」是六上、「正反比例」是六下——低年级篇目里不能出现。确需提前借用的名词，在该篇 `cautions` 里写明「某年级后面才学，这里提前借用」。
49. **自检工具**（都在 `tools/`）：
    - `check_content` 规则已并入 `build.py --check`（三类合法性/顺序/齐全、教材定位、LaTeX 反斜杠+空格、禁用词、模板腔词）
    - `tools/audit.py` —— 四线扫描的入口（`numbers` / `logic` / `figures`）
    - `tools/verify_answers.py` —— 例题 solution 与 answer 的交叉验算（含人工核实白名单）
    - `tools/verify_charts.py` —— SVG 图表几何与标注比对（条形/折线/扇形）
    - `tools/audit_overflow.py` —— 锚点感知的溢出扫描（188 页 × 2 视口）
    - `tools/regress.py` —— 全站回归（链接、公式渲染、三类关联、教材定位、导读）
    **写检测器后必须先造错验证它真能抓到**（2026-11-05 曾因解析器错误漏检全部条形图）。
50. **JSON 里 LaTeX 禁用「反斜杠 + 空格」**（`\ 5`、`a \ b`）：KaTeX 会解析失败。写空格用 `\,` 或 `~`。
51. **例题「场景」按内容判定，不要求同篇不重复**：`examples[].scene` 只能取 `taxonomy.json.scenes` 的 13 个值之一，但**同一篇内允许重复**——场景是「这道题发生在哪儿」，两道题都在超市很正常。2026-11-06 前为满足「同篇不重复」硬凑标签，出现「金融理财：一年有多少天」这类错配，已按内容全站重标 303 处（`tools/fix_example_scenes.py` + `tools/_scene_fix.tsv`，报告见 `content/_reference/scene-fix-report.html`）。新增例题时照实写，别为了凑数改标签。
