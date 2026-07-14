# -*- coding: utf-8 -*-
"""
打包比赛提交：把二次开发的 Co-Sight 源码 + result.jsonl + 部分运行 log 压成 zip。

提交内容（PDF 通知要求）：
  - result.jsonl（10 题答案）
  - 完整源码（含我们改的 chat_llm.py、try_many.py、compile_final_results.py、package_submission.py）
  - 运行 log（co-sight.log + work_space 关键中间文件，每题挑最近一次跑的）

排除：
  - .venv/  （太大）
  - runs/   （只保留每题最佳那次的部分，避免 zip 超 200MB）
  - __pycache__/
  - .git/

用法：
    python package_submission.py
"""
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"
SUBMISSIONS_DIR.mkdir(exist_ok=True)

# zip 内顶层目录名
ZIP_TOP = f"co-sight-submission-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
ZIP_PATH = SUBMISSIONS_DIR / f"{ZIP_TOP}.zip"

# 源码相对路径列表（相对 PROJECT_ROOT）
SOURCE_INCLUDE = [
    "app/",
    "config/",
    "cosight_server/",
    "tools/",
    "CoSight.py",
    "llm.py",
    "try_one_question.py",
    "try_many.py",
    "test_run.py",
    "compile_final_results.py",
    "package_submission.py",
    "requirements.txt",
    ".env_template",
    ".python-version",
    "README.md",
    "README-zh.md",
    "LICENSE",
]

# 一定排除的路径片段
EXCLUDE_FRAGMENTS = (
    "/.venv/", "\\.venv\\",
    "/__pycache__/", "\\__pycache__\\",
    "/.git/", "\\.git\\",
    "/.idea/", "\\.idea\\",
    "/.vscode/", "\\.vscode\\",
    "/node_modules/", "\\node_modules\\",
    "/runs/", "\\runs\\",
    "/submissions/", "\\submissions\\",
    "/work_space/", "\\work_space\\",
    "/.pytest_cache/", "\\.pytest_cache\\",
)
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".log",)  # log 在源码里基本是临时的


def should_include(rel_posix: str) -> bool:
    """根据相对路径（forward slashes）判断是否纳入 zip"""
    p = "/" + rel_posix.lstrip("/")  # 统一前缀
    for frag in EXCLUDE_FRAGMENTS:
        if frag in p or frag in p.replace("/", "\\"):
            return False
    for suf in EXCLUDE_SUFFIX:
        if p.endswith(suf):
            return False
    return True


def add_path_to_zip(zf: zipfile.ZipFile, abs_path: Path, arc_prefix: str):
    """把 abs_path（文件或目录）加入 zip。arc_prefix 是 zip 内目标路径前缀。"""
    if not abs_path.exists():
        print(f"  skip (not exist): {abs_path}")
        return
    if abs_path.is_file():
        arcname = arc_prefix
        if should_include(arcname.replace("\\", "/")):
            zf.write(abs_path, arcname)
        return
    # 目录：递归
    for child in abs_path.rglob("*"):
        if not child.is_file():
            continue
        rel = child.relative_to(abs_path).as_posix()
        arcname = f"{arc_prefix.rstrip('/')}/{rel}"
        if should_include(arcname):
            zf.write(child, arcname)


def find_best_runs() -> dict:
    """返回 {task_id_短编号: run_dir Path}"""
    runs_dir = PROJECT_ROOT / "runs"
    if not runs_dir.exists():
        return {}

    # 收集所有候选 task 目录
    candidates_by_task = {}  # short_id -> list of (run_dir, mtime, has_summary)
    for batch_dir in runs_dir.glob("batch_*"):
        for task_dir in batch_dir.glob("task*"):
            if not task_dir.is_dir():
                continue
            m = re.match(r"task(\d+)", task_dir.name)
            if not m:
                continue
            short = m.group(1)
            has_summary = (task_dir / "summary.txt").exists()
            try:
                mtime = task_dir.stat().st_mtime
            except OSError:
                mtime = 0
            candidates_by_task.setdefault(short, []).append((task_dir, mtime, has_summary))
    for run_dir in runs_dir.glob("run_task*"):
        if not run_dir.is_dir():
            continue
        m = re.match(r"run_task(\d+)", run_dir.name)
        if not m:
            continue
        short = m.group(1)
        has_summary = (run_dir / "summary.txt").exists()
        try:
            mtime = run_dir.stat().st_mtime
        except OSError:
            mtime = 0
        candidates_by_task.setdefault(short, []).append((run_dir, mtime, has_summary))

    # 对每个 task：优先选有 summary.txt 且 mtime 最新的
    best = {}
    for short, runs in candidates_by_task.items():
        # 排序：(有 summary 优先, mtime 倒序)
        runs.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best[short] = runs[0][0]
    return best


def main():
    # 检查 result.jsonl
    result_path = SUBMISSIONS_DIR / "result.jsonl"
    if not result_path.exists():
        print("!! submissions/result.jsonl 不存在，请先跑 python compile_final_results.py")
        return

    # 检查答案完整性
    with open(result_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    print(f"result.jsonl 包含 {len(lines)} 行")
    missing = [ln["task_id"] for ln in lines if not ln.get("model_answer")]
    if missing:
        print(f"⚠ 以下 task 仍无答案（zip 会包含空字符串）：")
        for m in missing:
            print(f"  - {m}")

    print(f"\n开始打包到 {ZIP_PATH} ...\n")

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. result.jsonl 放最顶层
        zf.write(result_path, f"{ZIP_TOP}/result.jsonl")
        print(f"  + result.jsonl")

        # 2. 把 summary.md 也放进去（评审好查看）
        md = SUBMISSIONS_DIR / "summary.md"
        if md.exists():
            zf.write(md, f"{ZIP_TOP}/answers_summary.md")
            print(f"  + answers_summary.md")

        # 3. 源码
        print("\n  源码：")
        for rel in SOURCE_INCLUDE:
            abs_p = PROJECT_ROOT / rel
            if abs_p.exists():
                add_path_to_zip(zf, abs_p, f"{ZIP_TOP}/{rel}")
                print(f"  + {rel}")
            else:
                print(f"  - {rel} (跳过：不存在)")

        # 4. README 提交说明
        readme_content = (
            "# Co-Sight 二次开发提交包\n\n"
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 内容\n\n"
            "- `result.jsonl` — 10 题答案（比赛提交格式）\n"
            "- `answers_summary.md` — 答案对照表（每题来源 batch、分数等）\n"
            "- 源码（基于 ZTE 开源 Co-Sight，已应用本队二次开发）\n"
            "- `run_logs/` — 每题最近一次跑的运行 log（含 co-sight.log + 步骤中间产物）\n\n"
            "## 本队改动概览\n\n"
            "1. **修复 GPT-5 系列 temperature 参数不兼容 bug**（`app/cosight/llm/chat_llm.py`）\n"
            "2. **5 层模型路由配置**（`.env_template` 见 `PLAN_/ACT_/TOOL_/VISION_/CREDIBILITY_` 块）\n"
            "3. **新增批量答题脚本**（`try_many.py`）：支持答案抽取多模式 + LLM 兜底\n"
            "4. **新增结果聚合脚本**（`compile_final_results.py`）：从多次 batch 取最佳答案\n"
            "5. **每题专属 prompt hint**（`try_many.py` 的 `TASK_HINTS` 字典）\n\n"
            "## 如何复现\n\n"
            "```bash\n"
            "# 1. 配置环境\n"
            "python -m venv .venv\n"
            ".venv/Scripts/activate.bat  # Windows\n"
            "pip install -r requirements.txt\n\n"
            "# 2. 复制 .env_template 为 .env，填入你的 LLM API key\n"
            "cp .env_template .env\n\n"
            "# 3. 跑全部 10 题\n"
            "python try_many.py 1 2 3 4 5 6 7 8 9 10\n\n"
            "# 4. 聚合结果\n"
            "python compile_final_results.py\n\n"
            "# 5. 查看 submissions/result.jsonl\n"
            "```\n"
        )
        zf.writestr(f"{ZIP_TOP}/SUBMISSION_README.md", readme_content)
        print(f"\n  + SUBMISSION_README.md")

        # 5. 运行 log（每题最佳那次）
        print("\n  运行 log：")
        best_runs = find_best_runs()
        for short, run_dir in sorted(best_runs.items(), key=lambda x: int(x[0])):
            # 只装关键文件：summary, plan_state, tool_calls, final_report, work_space/logs/co-sight.log
            target_prefix = f"{ZIP_TOP}/run_logs/task{short}"
            key_files = [
                "summary.txt",
                "plan_state.json",
                "tool_calls.json",
                "final_report.md",
            ]
            for kf in key_files:
                p = run_dir / kf
                if p.exists():
                    zf.write(p, f"{target_prefix}/{kf}")
            # work_space 里的内容（不包括 logs/ 下的大日志）
            ws = run_dir / "work_space"
            if ws.exists():
                for child in ws.rglob("*"):
                    if not child.is_file():
                        continue
                    rel = child.relative_to(ws).as_posix()
                    # 跳过 logs 下的二进制 / 跳过过大文件
                    if rel.startswith("logs/"):
                        # 只留 co-sight.log 末尾片段太麻烦，全部留更直观
                        if child.stat().st_size > 2 * 1024 * 1024:  # > 2MB 跳过
                            continue
                    if child.suffix in (".png", ".jpg", ".pdf") and child.stat().st_size > 5 * 1024 * 1024:
                        continue
                    arcname = f"{target_prefix}/work_space/{rel}"
                    if should_include(arcname):
                        zf.write(child, arcname)
            print(f"  + run_logs/task{short}/  (from {run_dir.name})")

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print()
    print("=" * 70)
    print(f"DONE: {ZIP_PATH}")
    print(f"      size: {size_mb:.1f} MB")
    print("=" * 70)
    print("\n提交时上传这个 zip 即可。")


if __name__ == "__main__":
    main()
