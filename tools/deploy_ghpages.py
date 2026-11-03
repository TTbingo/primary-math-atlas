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
REMOTE = "git@github.com:TTbingo/primary-math-atlas.git"
BRANCH = "gh-pages"


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    if not os.path.isdir(DIST):
        sys.exit("dist/ 不存在，请先运行: python build.py")

    msg = sys.argv[1] if len(sys.argv) > 1 else "site: 更新静态站点"
    n_src = sum(len(f) for _, _, f in os.walk(DIST))

    if os.path.isdir(WORK):
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    shutil.copytree(DIST, WORK, dirs_exist_ok=True)
    open(os.path.join(WORK, ".nojekyll"), "w").close()

    is_repo = os.path.isdir(os.path.join(WORK, ".git"))
    if not is_repo:
        run(["git", "init", "-q", "-b", BRANCH], WORK)
        run(["git", "remote", "add", "origin", REMOTE], WORK)
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
