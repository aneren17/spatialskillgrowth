# `nodes/mem/spatialskillgrowth` 架构说明

这组文档说明 `nodes/mem/spatialskillgrowth/` 下 26 个 Python 模块在异常检测框架中的职责、输入输出、
关键变量和实际调用位置。当前源码约 8954 行，若按文件逐行解释会掩盖主链路，因此采用两层结构：

源码目录：[nodes/mem/spatialskillgrowth](../../nodes/mem/spatialskillgrowth/)。

1. 分组文档解释数据如何流过框架，并解释关键函数内部变量；
2. [完整符号索引](08-symbol-index.md) 枚举模块级常量、类、属性、函数和方法，避免遗漏小函数。

局部变量不会脱离函数逐个罗列，而是在所属函数的数据流表中解释。例如 `plan`、`workflow`、
`execution`、`attempt` 在不同阶段含义不同，必须结合函数上下文理解。

## 推荐阅读顺序

如果只会基础 Python，先不要读完整架构，按下面三篇动手教程开始：

1. [Runtime 与 WORKFLOW_CONTRACT 从零解释](10-runtime-and-contract-tutorial.md)。
2. [12 个工具逐一使用教程](09-tool-cookbook.md)。
3. [探索 Skill 来源与三状态目录](11-exploration-skill-source.md)。

理解脚本后，再按完整架构顺序阅读：

1. [banner 贯穿案例](01-banner-data-walkthrough.md)：先看一条数据怎样从输入走到结果。
2. [数据模型、类别与运行配置](02-models-profiles-config.md)。
3. [输入预处理、任务规划与基础工具](03-input-planning-utils.md)。
4. [Skill 检索、执行与工具运行时](04-retrieval-execution-runtime.md)。
5. [探索、变异、合并与生命周期](05-exploration-growth.md)。
6. [存储、流水线和对话轨迹](06-store-pipeline-trace.md)。
7. [证据验证、人工 Skill 和评测](07-validation-evaluation.md)。
8. [完整符号索引](08-symbol-index.md)。
9. [12 个工具逐一使用教程](09-tool-cookbook.md)。
10. [Runtime 与 WORKFLOW_CONTRACT 从零解释](10-runtime-and-contract-tutorial.md)。
11. [探索 Skill 来源与三状态目录](11-exploration-skill-source.md)。

## 26 个文件的职责地图

| 文件 | 一句话职责 | 主调用方 |
|---|---|---|
| `__init__.py` | 包标记，目前没有导出逻辑 | Python 导入系统 |
| `answer_evaluator.py` | 严格比较 bool/int/float/text 答案 | `pipeline.py`、评测脚本 |
| `benchmark_profiles.py` | benchmark 名称、55 类异常事件和类别元数据 | 输入解析、规划器、运行目录 |
| `conversation_trace.py` | 将 JSON 轨迹重建为直观的 `conversation.md` | `ExperimentStore.complete_task` |
| `evidence_validator.py` | 判断最终答案是否有足够且合规的工具证据 | 执行协调器、人工验证器 |
| `experiment_config.py` | 实验预设、run 隔离和标准 Skill 初始化 | 探索/推理入口、工厂 |
| `growth_store.py` | SQLite 实验事实和三状态 Skill 文件仓库 | `pipeline.py`、Retriever、生命周期 |
| `human_skill_validation.py` | 校验、试跑并安装人工或生成脚本 | 验证 CLI、测试 |
| `llm_utils.py` | 统一构造多模态消息并解析 JSON | 分类、检索、变异、语义证据 |
| `media_processing.py` | 保留原视频并为图片工具抽样代表帧 | 探索/推理 Pipeline、人工验证 |
| `models.py` | Task、Workflow、证据、检索等 JSON 数据模型 | 几乎所有核心模块 |
| `mutation.py` | 选择增强/修复方向和候选组合 | 探索 Pipeline |
| `omni3d_eval_adapter.py` | 旧 benchmark 的结果导出与兼容评测 | 手工评测命令；异常主链路不依赖 |
| `param_space.py` | 工具/参数原子空间和 UCB/Pareto 候选评分 | `mutation.py` |
| `pipeline.py` | 组装并驱动探索、验证和推理全流程 | 两个 agent 入口 |
| `python_skill_runtime.py` | 受限 AST 环境中执行 `scripts/*.py` | `WorkflowExecutor`、人工验证器 |
| `skill_consolidator.py` | 结构去重、语义合并、容量裁剪 | 探索 Pipeline |
| `skill_layout.py` | 标准 Skill 路径和连字符名称 | 白板、仓库、人工验证、运行配置 |
| `skill_retriever.py` | 结构硬过滤后对 active/provisional 工作流排序 | 探索/推理 Pipeline |
| `task_router.py` | 类别确认、槽位构造和可用工具裁剪 | `ExperimentFactory` |
| `tool_contracts.py` | 描述各工具输入输出和生产者/消费者关系 | 变异器、结构合并、运行时 |
| `tool_runtime.py` | 调用工具、统一返回结构、解析异常阈值、执行 JSON 图 | Python Runtime、ReAct、验证器 |
| `workflow_executor.py` | Python Skill 执行、top-3、ReAct 回退和脚本导出 | `pipeline.py`、仓库 |
| `workflow_lifecycle.py` | provisional/active/archive 的升降级规则 | 探索 Pipeline |
| `workflow_mutator.py` | 从轨迹抽工作流、应用参数原子并生成工具 DAG | `mutation.py`、异常 baseline |
| `workflow_slots.py` | 从 `$slot.*` 引用推导 Python 函数参数 | 脚本导出、变异方向 |

## 推理主链路

```text
TaskRecord
  -> MediaPreprocessor.prepare
  -> TaskPlanner.plan
  -> WorkflowRetriever.retrieve
  -> CandidateExecutionCoordinator.run
       -> WorkflowExecutor.execute
          -> PythonSkillExecutor.execute
             -> SkillExecutionContext.call
                -> ToolRuntime.execute
       -> EvidenceValidator.validate
       -> 全部失败时 ReactSolver.solve / anomaly baseline
  -> InferencePipeline 写 summary、trial、conversation.md
```

## 探索主链路

```text
输入与规划
  -> 检索并执行已有 workflow
  -> 没有父 workflow 时从成功轨迹 extract baseline
  -> SuccessEnhancementDirector 或 FailureRepairDirector
  -> ParamSpace 产生候选组合
  -> WorkflowMutator 生成候选 DAG 和 Python 脚本
  -> 执行、答案比较、证据验收
  -> WorkflowConsolidator 去重/合并
  -> WorkflowLifecycleManager 决定 provisional/active/archive
  -> validate_provisional 用同类未见样本复验
```

## 三类最容易混淆的数据

| 名称 | 示例 | 含义 |
|---|---|---|
| `problem_class` / `event_type` | `banner` | 后端和 embedding 使用的精确异常类别 ID |
| `skill_name` | `fire-door-unclosed` | 标准 Skill 目录名；可与下划线类别 ID 不同 |
| `workflow_id` | `banner-human-review-v1` | 一个类别下某条具体执行路线的唯一 ID |

## 文档边界

- 重点是当前异常检测路径；Omni3D 兼容模块会说明但不会扩展旧实验细节。
- “被使用位置”指源码直接调用关系。由 CLI、框架反射或 Python 属性机制触发的地方会单独标注。
- 提示词正文在 `prompt/spatialskillgrowth_prompts.py`，本文只解释哪个模块使用哪个提示词。
