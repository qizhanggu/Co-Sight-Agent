# Co-Sight Competition Adaptation — Review Snapshot

> 本仓库为技术审查与学习快照，保留 2026 年中兴 Co-Sight 超级智能体比赛提交版本。它不被描述为从零实现的 Agent 框架，也不是最终简历项目。

- **比赛**：中兴捧月“星匠师”Co-Sight 超级智能体开发大赛
- **结果**：区域优胜奖，入围全国决赛
- **个人工作**：负责比赛运行流水线、workspace 隔离、答案抽取与候选聚合、提交打包，以及模型兼容与工具超时等稳定性修复。

## 一分钟说明

本项目基于 Co-Sight 提供的 Planner / Actor / DAG / 工具调用框架，面向 10 道开放式复杂任务进行比赛适配。比赛阶段主要完成批量运行、独立工作区隔离、运行产物保存、答案抽取、候选结果聚合、模型兼容性修复、视频工具超时兜底与提交打包。

当前仓库的目的，是让审查者区分上游框架能力、比赛阶段个人改造和下一代项目的重构方向。

## 比赛任务是什么

中兴捧月“星匠师”巧匠精英挑战赛要求 Agent 自动解决 GAIA 风格开放题，并提交答案、源码和运行日志。10 道题覆盖：

| 任务类型 | 代表题目 | 需要的能力 |
|---|---|---|
| 历史网页 / Wikipedia Revision | 指定年份版本、编辑次数、字节变化 | API 查询、时间过滤、分页、文本解析 |
| 多跳 Web 研究 | 铁路连接关系、子公司国家与国家格言 | 任务拆解、实体跳转、规则过滤、聚合 |
| 文档与精确计算 | 摘要年份统计、旧版食谱页码 | PDF/OCR、文本定位、Python 计算 |
| 代码与视觉 | 函数绘图识别大学缩写 | Python、图像理解、Web 查询 |
| 视频与音频 | 视频片段中的音乐识别 | 时间定位、音视频工具、超时控制 |

原始题目和提交格式说明位于 docs/competition/。

## 上游 Co-Sight 提供了什么

Co-Sight 提供了：

- Planner / Actor 分工；
- 运行时 DAG 与依赖执行；
- 搜索、网页、Python、文件、图片、视频、音频等工具接入；
- 基础服务端与 Web UI；
- 配置、模型调用和部分追踪能力。

上游源码与许可证保留在仓库中，使用 Apache-2.0 许可；请见 LICENSE、README-upstream.md 与 README-upstream-zh.md。

## 比赛阶段的个人改造

| 文件或模块 | 改造内容 |
|---|---|
| legacy_competition/try_many.py | 串行批量执行、每题独立 workspace、运行产物保存、答案抽取、题目策略提示 |
| legacy_competition/try_one_question.py | 单题运行与过程产物保存 |
| legacy_competition/compile_final_results.py | 多次运行候选的启发式聚合 |
| legacy_competition/package_submission.py | 比赛提交包生成 |
| test_run.py | 基础 smoke test |
| app/cosight/llm/chat_llm.py | 模型不支持显式 temperature 参数时的兼容调整 |
| app/cosight/tool/video_analysis_toolkit.py | 视频流读取的 deadline 保护 |

## 技术基础

仓库依赖体现的技术范围包括 Python、FastAPI、MCP、LLM Tool Calling、搜索与网页抓取、Wikipedia、PDF 解析、图像/视频/音频处理、WebSocket、Langfuse 等。

其中这些大部分是 Co-Sight 的框架能力或依赖面，不应全部归因于比赛阶段个人实现；个人改造边界以“比赛阶段的个人改造”一节为准。

## 当前局限

- Planner、Actor、DAG 依赖调度和大部分工具属于上游 Co-Sight；
- 批量脚本是串行执行，不是通用 Scheduler；
- 部分 TASK_HINTS 是比赛题专属策略，不能代表通用 Agent 自主性；
- 当前缺少统一 Trace schema、硬取消、持久化 checkpoint、证据驱动的 Verifier 与可复现评测流水线；
- 比赛运行产物不纳入 Git；它们仅保存在仓库外的 ../../local_artifacts/。

## 拟议的下一代项目

计划另建干净仓库 OpenResearch Agent，不在当前代码上继续堆叠。目标架构：

~~~
LangGraph 任务生命周期
  -> 自定义动态 DAG Scheduler
  -> Web / Wikipedia / Python / PDF 工具
  -> Evidence Store
  -> Verifier
  -> Final Answer + Trace + Evaluation
~~~

重点将从“比赛题适配”转向可解释的状态管理、工具容错、证据验证、可观测性和评测。

## 目录结构

~~~
app/                     上游框架源码与少量本地补丁
config/                  配置代码；真实凭据仅放 .env，且不提交
cosight_server/          上游服务端与 Web UI 基础
tools/                   上游构建工具
legacy_competition/      比赛专属执行、聚合与打包脚本
docs/competition/        原题目与提交格式说明
test_run.py              smoke test
README-upstream*.md      上游 README
~~~

## 本地运行

1. 创建虚拟环境。
2. 安装 requirements.txt。
3. 将 .env_template 复制为 .env，填入自己的服务凭据。
4. 运行 python test_run.py。

.env_template 已去敏，不包含任何可用密钥。
