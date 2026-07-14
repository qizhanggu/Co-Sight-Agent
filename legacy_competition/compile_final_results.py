# -*- coding: utf-8 -*-
"""
扫描 runs/ 下所有跑过的 task，对每个 task_id 选最新一次"成功"的答案，
输出比赛提交格式的 submissions/result.jsonl + 人类对照表 submissions/summary.md。

判定 "成功" 的优先级（高→低）：
1. summary.txt 存在 + Extracted answer 非空 + 不含失败短语
2. plan_state.json 存在 + result 字段有内容
3. 都没有 → 跳过这个目录

如果同一个 task_id 有多次跑：
- 默认按 run_dir 的 mtime 倒序，取**最新**的成功结果
- 但如果最新的"看起来差"（步骤未完成或答案太长），自动 fallback 到上一个

用法：
    python compile_final_results.py
"""
import json
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"
QUESTION_FILE = Path(r"D:\Users\Admin\Desktop\中兴比赛\超级智能体\中兴捧月“星匠师”巧匠精英挑战赛-超级智能体开发-省赛试题.txt")
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"
SUBMISSIONS_DIR.mkdir(exist_ok=True)


def load_questions():
    """返回 {task_id: question_text}"""
    qs = {}
    with open(QUESTION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[2].strip().startswith("ZTE Super Agent"):
                qs[parts[2].strip()] = parts[1].strip()
    return qs


def parse_summary_txt(path: Path):
    """从 summary.txt 解析关键字段。返回 dict 或 None。"""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    info = {}

    m = re.search(r"Task ID\s*:\s*(.+)", text)
    info["task_id"] = m.group(1).strip() if m else None

    m = re.search(r"Question\s*:\s*(.+)", text)
    info["question"] = m.group(1).strip() if m else None

    m = re.search(r"Elapsed\s*:\s*([\d.]+)\s*sec", text)
    info["elapsed"] = float(m.group(1)) if m else 0.0

    m = re.search(r"Steps\s*:\s*(\d+)\s*\((\d+)\s+completed\)", text)
    if m:
        info["steps_total"] = int(m.group(1))
        info["steps_done"] = int(m.group(2))
    else:
        info["steps_total"] = 0
        info["steps_done"] = 0

    m = re.search(r"Extracted answer\s*:\s*(.+)", text)
    info["extracted_answer"] = m.group(1).strip() if m else ""

    info["has_error"] = "ERROR:" in text
    return info


def load_plan_state(run_dir: Path):
    """加载 plan_state.json，返回 dict 或 None"""
    p = run_dir / "plan_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def build_reasoning_trace_from_plan(plan_state: dict) -> str:
    """从 plan_state.json 重建 reasoning_trace 字符串（比赛 jsonl 格式）"""
    if not plan_state:
        return ""
    steps = plan_state.get("steps", []) or []
    notes = plan_state.get("step_notes", {}) or {}
    lines = []
    for i, step in enumerate(steps):
        lines.append(f"{i+1}. {step}")
        n = notes.get(step) or ""
        if n:
            short = n.replace("\n", " ").strip()[:300]
            lines.append(f"   - {short}")
    return "\n".join(lines)


def is_answer_useful(ans: str) -> bool:
    if not ans:
        return False
    if len(ans) > 200:
        return False
    bad_phrases = (
        "could not be determined", "unable to", "no answer", "cannot determine",
        "无法确定", "did not find", "unresolved",
    )
    lower = ans.lower()
    for bad in bad_phrases:
        if bad in lower:
            return False
    return True


def score_run(info: dict, plan_state: dict) -> int:
    """给一次 run 打分，越高越好。综合答案质量、步骤完成度、错误信号。"""
    score = 0
    ans = (info or {}).get("extracted_answer", "") if info else ""
    if is_answer_useful(ans):
        score += 100
    if info and not info.get("has_error"):
        score += 20
    if info and info.get("steps_total", 0) > 0:
        ratio = info["steps_done"] / info["steps_total"]
        score += int(ratio * 30)
    # 答案长度越短越像具体答案（数字/单词最佳）
    if ans and len(ans) <= 50:
        score += 10
    elif ans and len(ans) <= 100:
        score += 5
    # plan_state.result 有内容加分
    if plan_state and plan_state.get("result"):
        score += 5
    return score


def scan_all_runs():
    """扫描 runs/ 下所有 batch_*/taskN/ 和 run_taskN_*/ 子目录。

    返回 {task_id: [(run_dir, info, plan_state, score), ...]}
    """
    findings = {}  # task_id -> list of (run_dir, info, plan_state, score, mtime)
    if not RUNS_DIR.exists():
        return findings

    candidates = []

    # 模式 1: batch_*/taskN/
    for batch_dir in sorted(RUNS_DIR.glob("batch_*")):
        if not batch_dir.is_dir():
            continue
        for task_dir in sorted(batch_dir.glob("task*")):
            if task_dir.is_dir():
                candidates.append(task_dir)

    # 模式 2: run_taskN_*/  （单独跑产生的）
    for run_dir in sorted(RUNS_DIR.glob("run_task*")):
        if run_dir.is_dir():
            candidates.append(run_dir)

    # 模式 3: 直接在 runs/ 下的子目录（兜底）
    for d in sorted(RUNS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("batch_") and not d.name.startswith("run_task"):
            # 看里面有没有 summary.txt
            if (d / "summary.txt").exists():
                candidates.append(d)

    for run_dir in candidates:
        info = parse_summary_txt(run_dir / "summary.txt")
        plan_state = load_plan_state(run_dir)
        if not info and not plan_state:
            continue
        task_id = (info or {}).get("task_id") or (plan_state.get("title") if plan_state else None)
        if not task_id:
            # 试从目录名推断
            m = re.search(r"task(\d+)", run_dir.name)
            if m:
                # 用题号反查 task_id
                task_id = f"ZTE Super Agent Challenge_task_id_{m.group(1)}"
        if not task_id:
            continue

        try:
            mtime = run_dir.stat().st_mtime
        except OSError:
            mtime = 0

        score = score_run(info, plan_state)
        findings.setdefault(task_id, []).append((run_dir, info, plan_state, score, mtime))

    # 每个 task_id 排序：score 倒序，mtime 倒序
    for tid in findings:
        findings[tid].sort(key=lambda x: (x[3], x[4]), reverse=True)

    return findings


def pick_best(findings):
    """对每个 task_id 取分数最高（同分则最新）的那个 run。"""
    best = {}
    for tid, runs in findings.items():
        if runs:
            best[tid] = runs[0]  # 已排序，第一个就是最佳
    return best


def main():
    questions = load_questions()
    if not questions:
        print(f"!! No questions loaded from {QUESTION_FILE}")
        return

    findings = scan_all_runs()
    if not findings:
        print("!! No runs found under runs/")
        return

    best = pick_best(findings)

    # 构造 result.jsonl
    result_lines = []
    summary_rows = []

    all_task_ids = list(questions.keys())
    # 按题号排序
    all_task_ids.sort(key=lambda t: int(re.search(r"task_id_(\d+)", t).group(1)))

    for tid in all_task_ids:
        question = questions[tid]
        if tid in best:
            run_dir, info, plan_state, score, mtime = best[tid]
            answer = (info or {}).get("extracted_answer", "") if info else ""
            reasoning_trace = build_reasoning_trace_from_plan(plan_state) if plan_state else ""
            # 若 summary 里的答案不可信，用 plan_state.result 兜底
            if not is_answer_useful(answer) and plan_state and plan_state.get("result"):
                # 取 result 的前 200 字
                answer = str(plan_state["result"]).strip()[:200]
            attempts = len(findings.get(tid, []))
            best_age = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        else:
            answer = ""
            reasoning_trace = ""
            score = 0
            run_dir = None
            attempts = 0
            best_age = "N/A"

        line = {
            "task_id": tid,
            "Question": question,
            "model_answer": answer,
            "reasoning_trace": reasoning_trace,
        }
        result_lines.append(line)
        summary_rows.append({
            "task_id": tid,
            "short": tid.split("_")[-1],
            "answer": answer,
            "score": score,
            "attempts": attempts,
            "run_dir": str(run_dir) if run_dir else "",
            "best_age": best_age,
            "question_short": question[:80] + ("..." if len(question) > 80 else ""),
        })

    # 写 result.jsonl
    jsonl_path = SUBMISSIONS_DIR / "result.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for line in result_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    # 写 summary.md
    md_lines = [
        "# 提交答案对照表",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"题目总数：{len(all_task_ids)}",
        f"已有答案：{sum(1 for r in summary_rows if r['answer'])}",
        "",
        "| # | task_id | 答案 | 分 | 尝试次数 | 来源 batch | 最近一次 | 题目 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in summary_rows:
        ans_display = r["answer"].replace("|", "\\|").replace("\n", " ")
        if len(ans_display) > 60:
            ans_display = ans_display[:60] + "…"
        run_short = Path(r["run_dir"]).name if r["run_dir"] else "—"
        md_lines.append(
            f"| {r['short']} | `{r['task_id']}` | `{ans_display}` | {r['score']} | "
            f"{r['attempts']} | {run_short} | {r['best_age']} | {r['question_short']} |"
        )

    # 列出每题的所有候选 run（debug 用）
    md_lines.extend(["", "## 每题所有候选 run（按分数排序）", ""])
    for tid in all_task_ids:
        md_lines.append(f"### {tid}")
        md_lines.append("")
        runs = findings.get(tid, [])
        if not runs:
            md_lines.append("- _(未跑过)_")
            md_lines.append("")
            continue
        for run_dir, info, plan_state, score, mtime in runs:
            ans = (info or {}).get("extracted_answer", "")[:60] if info else ""
            mtime_str = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
            steps = f"{(info or {}).get('steps_done', 0)}/{(info or {}).get('steps_total', 0)}" if info else "?/?"
            md_lines.append(f"- [{mtime_str}] score={score} steps={steps} ans=`{ans}` ← {run_dir.name}")
        md_lines.append("")

    md_path = SUBMISSIONS_DIR / "summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # 屏幕打印
    print("=" * 70)
    print(f"Compiled {len(result_lines)} task results")
    print("=" * 70)
    print()
    for r in summary_rows:
        flag = "✓" if r["answer"] else "✗"
        ans_display = r["answer"][:60] if r["answer"] else "(empty)"
        print(f"  {flag} task{r['short']:>2}  score={r['score']:>3}  → {ans_display}")
    print()
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
