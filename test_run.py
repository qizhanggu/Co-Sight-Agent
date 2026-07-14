# 最小化端到端测试：用一道简单题验证 Co-Sight 全链路
import os
from datetime import datetime
from CoSight import CoSight
from llm import llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision

# work_space 一定要是一个独立的空目录，否则 file_toolkit 会把整个项目目录翻一遍
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
work_space_path = os.path.join(BASE_DIR, 'work_space', f'smoke_{timestamp}')
os.makedirs(work_space_path, exist_ok=True)

# 关键：把 cwd 也切到 work_space，防止工具默认从项目根目录开始搜
os.chdir(work_space_path)
os.environ["WORKSPACE_PATH"] = work_space_path

cosight = CoSight(
    llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision,
    work_space_path=work_space_path,
    message_uuid="smoke_test_001",
)

# 用一道纯算术题，最理想情况 planner 应该一步就回答出来，不调用任何工具
question = "What is 12 + 7? Reply with the single integer answer only, nothing else."
result = cosight.execute(question, output_format="")

print("\n" + "=" * 60)
print("FINAL RESULT:")
print(result)
print("=" * 60)
print(f"Work space: {work_space_path}")
