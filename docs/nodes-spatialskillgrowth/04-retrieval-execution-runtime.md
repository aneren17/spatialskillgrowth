# Skill 检索、执行和工具运行时

本组包含 `skill_retriever.py`、`workflow_executor.py`、`python_skill_runtime.py`、`tool_runtime.py`、
`tool_contracts.py` 和 `workflow_slots.py`。这是推理阶段最核心的执行链。

## `skill_retriever.py`

### 两阶段筛选

所有 Retriever 都先经过 `WorkflowRetriever._structured_candidates`，再调用各自 `rank`：

```text
Repository.list_retrievable(problem_class)
  -> workflow_structurally_eligible
  -> rank(candidates)
```

`WorkflowRetriever` 的实例变量：

| 变量 | 含义 |
|---|---|
| `repository` | active/provisional Workflow 来源 |
| `top_k` | 强制限制在 1～3 |
| `include_provisional` | 探索为 true，正式推理通常为 false |

`workflow_structurally_eligible` 的硬条件是槽位非空、required tools 和图中 tools 均可用、答案类型兼容；
异常类还要求图中存在 `embeddingTool`。这里不做关键词语义匹配。

### 三种 Retriever

`MultimodalLLMFlatRetriever` 是主线：把同类别 `SKILL.md`、问题、图片、槽位、每条 Workflow 的
applicability、DAG 和 metrics 一起交给 `FLAT_WORKFLOW_RETRIEVAL_PROMPT`。`candidate_cap=0` 表示不在
LLM 前额外截断。返回无效 ID 或 LLM 出错时 reject-all，不私自按 ID 排序兜底。

`HistoryOnlyRetriever` 是对照路线，排序键依次为：高 accuracy、高 evidence rate、低 average cost、
高 trial count、workflow ID。人工新路线 metrics 全零时不会获得隐藏优势。

`LegacyTreeRetriever` 仅保留旧消融：`_tree_payload` 用 `derived_from_workflow_id` 临时构造树；当前扁平
主线不会依赖树结构。

`build_retriever` 是工厂，由 `ExperimentFactory` 根据 `config.retriever` 调用。

## `workflow_executor.py`

### `WorkflowExecutor`

构造变量：

- `runtime`：工具注册表和统一调用器；
- `repository`：查找正式 `scripts/<workflow_id>.py`；
- `candidate_script_root`：尚未入库候选的临时脚本目录；
- `python_executor`：`PythonSkillExecutor(runtime)`。

`execute` 先从 Repository 找人工/已生成脚本；找不到时由 `WorkflowPythonExporter` 为候选生成脚本，
随后统一进入 Python executor。因此人工和自动路线的最终执行入口相同。

### `CandidateExecutionCoordinator`

`run` 的关键输入：

| 参数 | banner 例子 |
|---|---|
| `problem_class` | `banner` |
| `question` | 中文异常问题 |
| `image_paths` | 图片或视频抽样帧 |
| `answer_type` | `bool` |
| `workflows` | Retriever 排好的最多三条路线 |
| `slot_bindings` | 至少含 `event_type=banner` |
| `allowed_tool_names` | Planner 选中的真实工具 |
| `media_path` | 原始图片或视频 |

执行顺序是 top-k 逐条尝试，每次得到 `result`、`answer` 和 `EvidenceDecision`。第一条 accepted 立即返回。
全部失败时：

1. 异常类尝试 `build_anomaly_baseline_workflow(problem_class)`，保证最短 embedding 路线；
2. 若仍失败且 `use_react=true`，把拒绝原因放入 `repair_context` 调 `ReactSolver`；
3. 返回所有 `attempts`，而不是只留下最后一次。

### `ReactSolver`

它只向模型绑定 `allowed_tool_names` 对应工具。循环变量包括 `messages`、`observations`、`used_tools` 和
`steps`。达到工具预算后会额外发送 `REACT_FINALIZATION_PROMPT`，该次不再绑定工具，避免最后一步只
调用工具却没有最终答案。

### `FinalAnswerNormalizer`

对原始答案做格式整理；bool/int/float 可先由确定性规则提取，必要时才用 LLM。它不能重新看图解题。

### `WorkflowPythonExporter`

`export(workflow, force)` 把 Workflow DAG 变成可编辑 Python：

- `WORKFLOW_ID/PROBLEM_CLASS/DECLARED_TOOLS`：脚本契约常量；
- `WORKFLOW_GRAPH_SHA256`：生成时 DAG 哈希；
- `WORKFLOW_CONTRACT`：供人工验证器比较；
- `solve(runtime, question, image_paths, *, slots...)`：实际入口。

`legacy_python_wrapper` 识别旧包装脚本；snapshot 时可显式迁移。`_python_value` 把 `$slot.*` 等引用转成
函数变量，`_safe_python_identifier` 清洗 step ID。

## `python_skill_runtime.py`

### 安全边界常量

`SAFE_BUILTINS` 只开放必要的纯 Python 操作；`BANNED_CALL_NAMES` 禁止 `eval/exec/open/__import__` 等；
`BANNED_NODES` 禁止 import、class、lambda、with、try 等不需要的语法。它是进程内受限环境，不等价于
操作系统沙箱。

### `SkillExecutionContext`

脚本中的 `runtime` 实际是这个对象，不是底层 `ToolRuntime`。核心实例变量：

- `tool_runtime`：真正执行服务调用；
- `workflow`：用于工具白名单和 DAG 校验；
- `question/image_paths/slot_bindings/media_path`：当前任务上下文；
- `observations`：每次 `call` 的完整轨迹；
- `step_results`：按 `step_id` 索引结果；
- `failed_step_ids`：失败步骤列表；
- `final_answer`：`finish` 设置的答案。

`call` 校验工具已声明、step ID 有效，然后决定是否对视频抽样帧 fan-out。图片工具满足
`FRAME_INDEPENDENT_IMAGE_TOOLS` 且存在多帧时，`_call_sampled_frames` 并行调用每帧，并由
`_frame_result_score` 选代表结果；所有帧结果仍保存在 data 中。

Runtime API：

| 方法 | 返回/效果 |
|---|---|
| `require(result, step_id)` | 失败时抛 `SkillStepExecutionError`，保留精确步骤 |
| `value(result, field, default)` | 从顶层或 `data` 读结构化字段 |
| `media_path()` | 原始视频或图片 |
| `image_path()` | 当前最佳代表帧 |
| `evidence_text()` | observations 的紧凑文本 |
| `evidence_image()` | 当前优先级最高的证据图 |
| `render(value)` | 展开 `$question/$slot.*/$step.*` |
| `finish(value)` | 提取并保存最终答案 |
| `result(...)` | 组装 executor 返回字典和异常字段 |

`PythonSkillExecutor.execute` 调 `load_skill_script` 做 AST 校验和加载，再检查 `solve`，注入 runtime 和
槽位参数。异常会保留脚本绝对路径和 traceback。

逐个内部属性、公开方法和返回字典的初学者说明见
[Runtime 与 WORKFLOW_CONTRACT 从零解释](10-runtime-and-contract-tutorial.md)。

## `tool_runtime.py`

### 解析常量

| 常量 | 用途 |
|---|---|
| `STEP_REFERENCE_PATTERN` | 识别 `$step.<id>.<field>` |
| `SLOT_REFERENCE_PATTERN` | 识别 `$slot.<name>` |
| `SEMANTIC_EMPTY_MARKERS` | 判断工具“成功但无有效内容” |
| `ERROR_PREFIXES` | 从文本识别服务错误 |
| `ANOMALY_RESULT_PATTERN` | 解析“是/否（判定阈值）” |
| `EVIDENCE_IMAGE_PRIORITY` | mask/crop/detection 等证据图优先级 |

`build_default_registry` 注册当前项目允许的工具；被删除的 Web/ASR/PDF 工具不会进入这里。

### `ToolRuntime.execute`

流程如下：

1. 检查 `tool_name` 是否在 registry；
2. `_prepare_args` 适配各工具参数名；
3. `tool.invoke(args)`；
4. `_normalize_result` 转统一协议；
5. 异常时 `_failure` 返回结构化失败，不让任意服务异常格式扩散。

统一结果的核心键是 `ok/status/tool/output_type/output_types/content/data/raw/error`。检测框由
`_coerce_detections`、`_canonical_detection` 和 `_normalize_detection_boxes` 统一成像素坐标；图片引用由
`_extract_image_refs` 收集。

### JSON Workflow 执行兼容层

`execute_workflow_payload`、`normalize_workflow_steps`、`workflow_step_groups` 和 `execute_parallel_tools` 是
JSON DAG 兼容执行能力。当前正式 Skill 以 Python 为执行源，但变异、验证和旧数据仍使用这些函数做
DAG 规范化或参数解析。

`resolve_workflow_args` 递归展开：

```text
$media -> 原视频/图片
$image -> 当前代表帧
$frames -> 所有抽样帧
$slot.event_type -> banner
$step.embedding.threshold -> 0.66
$evidence_image -> 当前最佳证据图
```

### 异常结果函数

- `parse_anomaly_tool_output(raw)`：把文本或嵌套 JSON 归一成 `is_anomaly/decision/threshold`；
- `extract_anomaly_result(result)`：从 observations 逆序找最后一次成功 embedding；
- `_normalize_threshold`：数值字符串转 float，未知标记转 `None`；
- `extract_final_answer`：从最终文本提取 bool、选项或数值答案。

`build_evidence_text`、`_best_evidence_image`、`_extract_image_reference` 支持后续工具和 MLLM 使用已有证据。

## `tool_contracts.py`

`TOOL_CONTRACTS` 是工具的输入约束和输出类型表。派生变量：

- `PIXEL_DETECTION_TOOLS`：产生像素框的工具；
- `PRODUCED_RESOURCE_TYPES`：所有可生产资源类型；
- `DEPENDENT_TOOLS`：需要前置资源的消费者；
- `FRAME_INDEPENDENT_IMAGE_TOOLS`：视频时可逐帧并行的图片工具。

函数用途：

| 函数 | 示例 |
|---|---|
| `output_types("embeddingTool")` | 包含 `anomaly_decision` |
| `output_type(tool)` | 返回主输出类型 |
| `input_constraints(tool)` | 返回该工具依赖资源 |
| `contract_signature(tool)` | Consolidator 比较工具语义签名 |
| `compatible_producers(tool)` | 找能为 crop 等消费者提供输入的工具 |
| `can_add_tool(tool, existing_tools)` | 变异器判断加入工具后依赖是否满足 |

## `workflow_slots.py`

`referenced_slot_names(workflow)` 递归扫描所有 step args 中的 `$slot.*`。banner 得到
`["event_type"]`。`python_slot_parameters` 将槽位转为安全 Python 参数名，并拒绝与
`runtime/question/image_paths` 冲突。`slot_bindings_from_locals` 在生成脚本中把函数局部变量重新组成
运行时槽位字典。`_collect_slots` 是其递归实现。
