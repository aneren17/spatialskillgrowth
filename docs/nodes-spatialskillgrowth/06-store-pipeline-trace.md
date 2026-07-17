# 存储、流水线和对话轨迹

本组包含 `growth_store.py`、`pipeline.py` 和 `conversation_trace.py`。前两者分别负责“事实落盘”和
“流程编排”，后者把机器轨迹转成人可读对话。

## `growth_store.py`

### `ExperimentStore`：SQLite 事实库

构造变量 `paths` 提供 run 路径，`db_path` 指向 `state/spatialskillgrowth.db`，`_lock` 保护同进程并发。
`_connect` 是带 commit/rollback 的 context manager；`_init_schema` 创建：

| 表 | 主键/核心字段 | 谁写入 |
|---|---|---|
| `tasks` | `task_id`、completed、summary_json | Pipeline begin/complete/fail |
| `trials` | `(task_id, trial_id)`、workflow、answer、result | 每次候选执行 |
| `retrievals` | `(task_id, strategy)`、decision_json | Retriever 结束后 |
| `mutation_directions` | `(task_id, mode)`、direction_json | 探索方向生成后 |
| `workflow_events` | 自增 event_id、workflow_id、event_type | 注册、迁移、合并、归档 |
| `atom_coverage` | `(problem_class, atom_id)`、trial/success | 参数空间 UCB |

方法按任务生命周期排列：

- `begin_task`：插入或刷新未完成任务；
- `is_complete/get_summary`：`--resume` 跳过已完成任务；
- `save_retrieval/save_direction`：保存决策，不依赖 Markdown 轨迹；
- `save_trial`：保存候选结果和 EvidenceDecision；
- `complete_task`：标记完成、写 summary、追加 `per_task.jsonl`、生成 conversation；
- `fail_task`：保留 traceback，写 `errors.jsonl`，任务保持可重试；
- `save_trajectory`：保存额外 JSON 阶段产物；
- `_append_result`：加锁追加 JSONL。

工作流/原子方法：

- `record_workflow_event`：写状态变化事实；
- `atom_stats`：读取某类别原子历史；
- `record_atom_results`：累计尝试/成功；
- `workflow_task_ids`：生命周期判断是否来自不同任务。

### `WorkflowRepository`：文件 Skill 仓库

与 SQLite 的分工：SQLite 保存实验事实，Repository 保存可迁移 Skill：

```text
skills/active/<skill-name>/
├── SKILL.md
├── scripts/<workflow-id>.py
└── references/
    ├── skill.json
    └── workflows/<workflow-id>.json
```

`save(workflow)`：根据 `workflow.status` 选根目录，移除其他状态同 ID 文件，写 JSON；若状态迁移则复制
已有脚本；没有脚本时由 exporter 生成；最后更新 metadata 和 `SKILLS.json`。已有人工脚本和
`SKILL.md` 不会被覆盖。

读取方法：`load/get/script_path/list_active/list_provisional/list_archive/list_retrievable`。`_list` 同时兼容
标准 `references/workflows` 和历史根 `workflows`，按 workflow ID 去重并跳过 `.archive.json`。

`skill_guidance(problem_class)` 读取 active、其次 provisional 的 `SKILL.md`，限制默认 6000 字符，供主线
Retriever 使用。

状态与指标：

- `transition`：保存到新状态，archive 时可写原因 reference；
- `archive`：transition 的快捷入口；
- `update_metrics`：重新读取最新 Workflow，更新计数和 source task，再保存；
- `_remove_from_other_statuses`：保证同 ID 不同时出现在多个状态。

文档和索引：

- `_rebuild_docs`：更新 `references/skill.json`，保留 `authorship`；仅缺少 SKILL 时生成默认文件；
- `_rebuild_skill_index`：聚合状态根下所有 skill metadata；
- `_default_skill_markdown`：新动态类别的最小标准模板；
- `_write_json_atomic`：临时文件加 `os.replace`，避免中途写坏。

`snapshot_active_from` 在跨 run 推理时复制来源 active Skill，并记录来源根、哈希和旧脚本迁移信息，之后
目标 run 只读自己的快照，避免源 run 后续变化污染结果。

`TrajectoryRecorder.record` 是 `store.save_trajectory` 的轻量包装。

## `pipeline.py`

### 并发锁

`PROBLEM_CLASS_LOCKS` 保存每类别的 `RLock`，`PROBLEM_CLASS_LOCK_GUARD` 保护锁字典本身。
`problem_class_lock(problem_class)` 确保同类别多个探索任务不会同时修改 Skill 库；不同类别仍可并发。

### `ExplorationPipeline`

`ask(task, resume)` 先做媒体预处理和 Planner；若 resume 且 Store 已完成则直接返回缓存。随后取得类别锁
并进入 `_ask_locked`。

`_ask_locked` 的主要阶段变量：

| 变量 | 含义 |
|---|---|
| `plan` | problem class、槽位和允许工具 |
| `workflows/retrieval` | 候选路线和排序记录 |
| `execution` | top-k/baseline/ReAct 的所有 attempts |
| `attempt` | 被选中或最终候选执行 |
| `parent` | 用于增强/修复的父 Workflow |
| `mutations` | 预算内 `(MutationSpec, WorkflowSpec)` |
| `mutants` | 每条新路线执行、正确性和证据结果 |
| `consolidation` | 合并/归档记录 |

辅助方法：

- `_persist_execution_attempts`：每次 attempt 写 trial，可选择更新已存在 Workflow metrics；
- `_parent_workflow`：优先使用选中 Workflow，否则从成功轨迹抽取；
- `_persist_correct_workflow`：为正确路线更新结构覆盖并注册生命周期；
- `_execute_mutant`：执行单个变异、比较答案、验收证据和落 trial；
- `validate_provisional(tasks)`：探索结束后，用同类未见任务主动复验 provisional 并触发 review。

最终 summary 包含 base workflow、方向、mutants、activated/provisional IDs、consolidation、tool plan 和
媒体信息。

### `InferencePipeline`

`ask` 负责 resume、媒体预处理和异常落盘；`_ask` 执行固定流程：plan → retrieve → coordinator → 保存
attempts → 计算可选 ground truth 正确性 → summary → complete。

与探索相比，它不会调用 mutation、consolidator 或 lifecycle，也不会更新来源 Workflow 的结构。

### `ExperimentFactory`

构造时集中创建：Store、Repository、MediaPreprocessor、Classifier、SlotExtractor、ToolPolicy、Retriever、
WorkflowExecutor、EvidenceValidator、CandidateCoordinator。

`build_exploration` 再创建 MutationEngine、Consolidator、Lifecycle；`build_inference` 只返回冻结推理链。
Agent 入口因此不需要手工拼装几十个依赖。

### 汇总函数

`write_evaluation_summary(paths)` 读取结果 JSONL，按 overall、split、problem class 计算 `_metrics`，写 JSON、
CSV 和 summary.md。`_update_workflow_metrics` 统一从 result 统计工具调用/失败；`_selected_attempt` 找最终
attempt；`_observations` 兼容 evidence/observations 键；`_structural_coverage` 计算工具数加 DAG 边数；
`_serializable_attempt` 去除不能直接落 JSON 的对象。

## `conversation_trace.py`

`TRIAL_FILE_PREFIXES` 定义哪些 trajectory JSON 属于执行轮次。`write_conversation_trace` 读取当前任务目录
的 retrieval 和 trials，再写 `conversation.md`。

内部函数：

- `_load_trials`：按文件名排序并加载 trial JSON；
- `_load_json`：文件不存在/损坏时返回空对象；
- `_render`：构建用户输入、规划、检索、每轮工具调用、证据验收和最终结果；
- `_question_from_trials`：优先从 trial 找原问题；
- `_reconstructed_question`：旧轨迹缺问题时从 summary 重建；
- `_compact_tool_result`：缩减过长服务响应但保留状态、结构化字段和错误；
- `_code_list/_json`：Markdown 安全格式化。

它不参与模型推理，也不会反向改变结果；作用是让人工能看到诸如：

```text
用户：检测 banner
规划：event_type=banner
检索：banner-human-review-v1
工具：embeddingTool -> 是，threshold=0.66
证据门：accepted
最终：是
```

这比直接阅读 SQLite 或大型 JSONL 更适合排查实习生脚本。
