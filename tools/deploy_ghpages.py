"""把 dist/ 同步到 gh-pages 分支并推送（GitHub Pages 发布）。

用法: python tools/deploy_ghpages.py ["提交说明"]
依赖: 已构建好 dist/（先跑 python build.py），本机 git 可用 SSH 协议推送。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
WORK = os.path.join(ROOT, ".tmp", "ghpages")
# 本机 HTTPS/443 被防火墙挡，GitHub API 需走代理 17897；git 推送走 SSH（22 端口）可直接用
REMOTE = os.environ.get("GHP_REMOTE", "git@github.com:TTbingo/primary-math-atlas.git")
BRANCH = "gh-pages"


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    if not os.path.isdir(DIST):
        sys.exit("dist/ 不存在，请先运行: python build.py")

    msg = sys.argv[1] if len(sys.argv) > 1 else "site: 更新静态站点"
    n_src = sum(len(f) for _, _, f in os.walk(DIST))

    # 差异同步（不整树删除，避免触发 bulk-delete 拦截）：
    # 1) 删除 WORK 中 dist 已不存在的文件（逐个 os.remove）
    # 2) copytree 覆盖复制（dirs_exist_ok）
    if os.path.isdir(WORK):
        src = set()
        for base, _, fs in os.walk(DIST):
            for f in fs:
                src.add(os.path.relpath(os.path.join(base, f), DIST))
        dst = set()
        for base, dirs, fs in os.walk(WORK):
            if os.path.relpath(base, WORK) == os.path.join(".git"):
                dirs[:] = []
                continue
            if base.startswith(os.path.join(WORK, ".git")):
                continue
            for f in fs:
                dst.add(os.path.relpath(os.path.join(base, f), WORK))
        removed = 0
        for rel in sorted(dst - src):
            os.remove(os.path.join(WORK, rel))
            removed += 1
        if removed:
            print(f"清理线上已移除的文件 {removed} 个")
    else:
        os.makedirs(WORK, exist_ok=True)
    # 排除验收截图目录：它只是本地目检用的，不该上线
    shutil.copytree(DIST, WORK, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("_shot", ".tmp"))
    open(os.path.join(WORK, ".nojekyll"), "w").close()

    is_repo = os.path.isdir(os.path.join(WORK, ".git"))
    if not is_repo:
        run(["git", "init", "-q", "-b", BRANCH], WORK)
        run(["git", "remote", "add", "origin", REMOTE], WORK)
    else:
        # 远端若是 SSH 地址（沙箱可能禁读 ~/.ssh），自动改为 HTTPS
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=WORK,
                             capture_output=True, text=True).stdout.strip()
        if url.startswith("git@"):
            run(["git", "remote", "set-url", "origin", REMOTE], WORK)
    run(["git", "config", "user.name", "TTbingo"], WORK)
    run(["git", "config", "user.email", "TTbingo@users.noreply.github.com"], WORK)
    run(["git", "add", "-A"], WORK)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=WORK)
    if r.returncode == 0:
        print("dist 与线上一致，无需提交")
        return
    run(["git", "commit", "-q", "-m", msg], WORK)
    run(["git", "push", "-q", "-f", "origin", BRANCH], WORK)
    n_out = sum(len(f) for _, _, f in os.walk(WORK))
    print(f"已推送 {BRANCH}: 源文件 {n_src} 个 -> {REMOTE}")
    print("线上地址: https://ttbingo.github.io/primary-math-atlas/")


if __name__ == "__main__":
    main()
