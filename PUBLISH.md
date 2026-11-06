# 发布说明 · 小学数学知识点图谱

线上地址：
- GitHub Pages：<https://ttbingo.github.io/primary-math-atlas/>
- workbuddy.host：<https://primary-math-atlas.app.workbuddy.host/?sharecode=BYT4SQX5HE>

仓库：<https://github.com/TTbingo/primary-math-atlas>

> ⚠️ **两个平台都要发，缺一不可。** 2026-11-05 那轮只推了 GitHub Pages，
> 导致 workbuddy.host 停留在 136 篇旧版，直到 2026-11-06 才补发。
> 发完必须**回读线上内容**验证，不能只看本地 git 状态。

## 一、GitHub Pages 发布

源分支 `gh-pages`，产物目录 `dist/`。

```bash
# 1. 构建（沙箱拦截整树删除时加 MATH_NO_CLEAN=1；常规构建可直接跑）
python build.py

# 2. 清理验收截图（它们只是本地目检用的，不上线）
rm -rf dist/_shot

# 3. 同步 dist/ 到 gh-pages 分支并推送
GIT_SSH_COMMAND="ssh -o ConnectTimeout=20" \
  python tools/deploy_ghpages.py "site: <提交说明>"

# 4. 验证线上（curl 直连，Chromium 会走系统代理导致误判失败）
env -u HTTPS_PROXY -u HTTP_PROXY \
  curl -s -o /dev/null -w "%{http_code}\n" \
  https://ttbingo.github.io/primary-math-atlas/
```

## 二、workbuddy.host 发布

用 `workbuddy_sites_deploy` 工具（不是脚本），参数固定：

| 参数 | 值 |
|---|---|
| `directory` | `math-site/dist` |
| `appId` | `wbapp_kHGLrsiTw1074ukrOuud1h` |
| `domainPrefix` | `primary-math-atlas` |
| `language` | `static` |
| `userAskedToPublish` | `true`（用户明确要求发布时） |

**发布前必须 `rm -rf dist/_shot`** —— `sites_deploy` 不吃
`deploy_ghpages.py` 里的 `ignore_patterns`，验收截图会跟着上线。

发布后验证：

```bash
# 知识点数应与 modules.json 一致（当前 90）
curl -s "https://primary-math-atlas.app.workbuddy.host/?sharecode=BYT4SQX5HE" \
  | grep -o 'points/[a-z0-9-]*/' | sort -u | wc -l
```

### 分享码门禁机制（实测）

- 门禁是 **cookie 型**：首次访问带 `?sharecode=XXX` 的 URL 会种下 cookie，
  之后同域下不带 sharecode 的页面和子资源也能正常访问。
- 所以**产物 HTML 里不需要追加 sharecode**，也不用 sed 处理。
- 直接 curl 一个不带 sharecode 的 URL 会得到 403「链接不完整」——这是门禁正常表现，
  **不是死链**。要判断真实状态，用 `curl -c/-b` 携带 cookie 复测。

### 并发核验的坑

`xargs -P 12` 批量打 GitHub Pages 会偶发 `000`（连接超时，非 404）。
判定死链只看 `404`，`000` 必须重试确认。

### 本机网络注意

- `gh` CLI 在 `D:\tools\gh\bin\gh.exe`（不在 PATH）。
- HTTPS/443 被防火墙挡：调 GitHub API 需 `HTTPS_PROXY=http://127.0.0.1:17897`。
- git 推送走 SSH（22 端口）可直接用，**不要**用 HTTPS 远端。
- 线上验证用 `curl` 直连（去掉代理环境变量）比 Playwright 可靠——Chromium 会自动走系统代理，
  表现为连接被重置，但站点本身是好的。
- GitHub 偶发返回 `500 Internal Server Error`（服务端瞬时故障），等 25 秒重试即可。
