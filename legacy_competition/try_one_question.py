# -*- coding: utf-8 -*-
"""
跑一道省赛真题，验证 Co-Sight 全链路。
默认跑 task_id_2（ZTE Wikipedia 编辑次数）。
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

# ===== 配置 =====
PROJECT_ROOT = Path(__file__).resolve().parent
QUESTION_FILE = Path(r"D:\Users\Admin\Desktop\中兴比赛\超级智能体\中兴捧月“星匠师”巧匠精英挑战赛-超级智能体开发-省赛试题.txt")
TARGET_TASK_ID = sys.argv[1] if len(sys.argv) > 1 else "ZTE Super Agent Challenge_task_id_2"


# ===== 加载题目 =====
def load_question(task_id: str):
    """从试题 txt 里找出指定 task_id 的题目文本"""
    with open(QUESTION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[2].strip() == task_id:
                return parts[1].strip()
    raise ValueError(f"Task ID not found in question file: {task_id}")


# ===== 准备运行目录（隔离的 work_space）=====
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
short_id = TARGET_TASK_ID.split("_")[-1]  # 例如 "2"
RUN_DIR = PROJECT_ROOT / "runs" / f"run_task{short_id}_{timestamp}"
WORK_SPACE = RUN_DIR / "work_space"
WORK_SPACE.mkdir(parents=True, exist_ok=True)

# 关键：把 cwd 切到 work_space，防止文件工具误扫项目根
os.chdir(WORK_SPACE)
os.environ["WORKSPACE_PATH"] = str(WORK_SPACE)

# 延迟到 chdir 之后再 import CoSight，避免它把 cwd 当成 base
from CoSight import CoSight  # noqa: E402
from llm import llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision  # noqa: E402

# ===== 准备问题 =====
question_text = load_question(TARGET_TASK_ID)
output_format = "Reply with the final answer only (a single integer when applicable). Avoid full sentences."

print("=" * 70)
print(f"Task ID  : {TARGET_TASK_ID}")
print(f"Question : {question_text}")
print(f"Run dir  : {RUN_DIR}")
print(f"Started  : {timestamp}")
print("=" * 70)
print()

# ===== 执行 =====
cosight = CoSight(
    llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision,
    work_space_path=str(WORK_SPACE),
    message_uuid=TARGET_TASK_ID,
)

start_ts = time.time()
final_report = None
err = None
try:
    final_report = cosight.execute(question_text, output_format=output_format)
except Exception as e:
    err = traceback.format_exc()
    print("\n!! Execution raised an exception:\n", err)
elapsed = time.time() - start_ts


# ===== 保存产物 =====
# 1. final_report.md（CoSight 返回值）
if final_report:
    (RUN_DIR / "final_report.md").write_text(str(final_report), encoding="utf-8")

# 2. plan_state.json（完整 Plan 状态）
plan = cosight.plan
plan_state = {
    "title": plan.title,
    "steps": plan.steps,
    "step_statuses": plan.step_statuses,
    "step_notes": plan.step_notes,
    "step_details": plan.step_details,
    "step_files": getattr(plan, "step_files", {}),
    "dependencies": plan.dependencies,
    "result": plan.result,
}
(RUN_DIR / "plan_state.json").write_text(
    json.dumps(plan_state, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
)

# 3. tool_calls.json（按步骤列出所有工具调用）
tool_calls_dump = {}
for step, calls in plan.step_tool_calls.items():
    tool_calls_dump[step] = calls
(RUN_DIR / "tool_calls.json").write_text(
    json.dumps(tool_calls_dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
)

# 4. summary.txt（人类可读总结）
summary_lines = [
    f"Task ID    : {TARGET_TASK_ID}",
    f"Question   : {question_text}",
    f"Elapsed    : {elapsed:.1f} sec",
    f"Plan title : {plan.title}",
    f"Steps      : {len(plan.steps)}",
    "",
]
for i, step in enumerate(plan.steps):
    status = plan.step_statuses.get(step, "?")
    notes = (plan.step_notes.get(step) or "").replace("\n", " ")[:200]
    summary_lines.append(f"  Step {i} [{status}] {step}")
    if notes:
        summary_lines.append(f"      notes: {notes}")
    tools = [tc.get("tool_name") for tc in plan.step_tool_calls.get(step, [])]
    if tools:
        summary_lines.append(f"      tools: {tools}")
summary_lines.append("")
summary_lines.append(f"Plan.result (final answer field):")
summary_lines.append(str(plan.result))
summary_lines.append("")
if err:
    summary_lines.append("ERROR (during execute):")
    summary_lines.append(err)

(RUN_DIR / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")


# ===== 屏幕打印 =====
print("\n" + "=" * 70)
print(f"DONE in {elapsed:.1f} sec, {len(plan.steps)} steps")
print("=" * 70)
for line in summary_lines:
    print(line)
print()
print(f"All artifacts saved to: {RUN_DIR}")
if final_report:
    print("\n----- FINAL REPORT (last 800 chars) -----")
    rep = str(final_report)
    print(rep[-800:] if len(rep) > 800 else rep)
