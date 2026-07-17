# 探索、变异、合并和生命周期

本组包含 `param_space.py`、`mutation.py`、`workflow_mutator.py`、`skill_consolidator.py` 和
`workflow_lifecycle.py`。它们只在探索或 provisional 复验阶段改变 Skill 库；正式推理不会生成新路线。

## `param_space.py`：候选坐标系

`COMMON_MUTATIONS` 是跨类别原子集合，包括：

- 强制 `embeddingTool:event_type:runtime_event_type`；
- MLLM 全图/局部/显式证据；
- YOLO、SAM3、GroundingDINO 阈值和定位角色；
- OCR 文本证据；
- crop、relative cut、Python 验算等结构操作。

`CLASS_MUTATIONS` 是类别专属原子，`OMNI3D_CLASS_MUTATIONS` 是旧 benchmark 的结构化扩展，随后合并
进 `CLASS_MUTATIONS`。异常类别目前主要使用 common 原子；也可通过 `extra_atoms` 人工补充。

### `ParamSpace` 数据流

`replace_extra_atoms` 用新字典完全替换扩展原子；`atoms_for(problem_class)` 合并 common、类别、全局
扩展、类别扩展，并按 `atom_id` 去重排序。

`candidate_portfolios` 的关键变量：

| 变量 | 含义 |
|---|---|
| `parent_tools` | 父 Workflow 已有工具 |
| `available_tools` | Planner 允许工具 |
| `preferred_atom_ids` | Director 推荐集合 |
| `avoid_atom_ids` | Director 排除集合 |
| `placements` | 插入工具 DAG 的位置 |
| `atoms_per_portfolio` | 每个组合最多原子数，默认 3 |

它会用 `can_add_tool` 检查消费者依赖。例如增加 `crop_detections` 前必须存在能生产 detection boxes 的
工具，不能只因 LLM 推荐就生成必然失败的孤立节点。

候选评分函数：

- `_atom_index`：结合历史成功/尝试次数计算 UCB；
- `_mutation_quality`：聚合组合中原子质量；
- `workflow_features`：Workflow 已覆盖的工具/参数/结构特征；
- `workflow_marginal_gain`：相对 active 集新增覆盖；
- `select_workflow_mutations`：综合边际增益和质量选预算内路线；
- `merge_candidates`：结构相近候选的辅助合并选择。

`_best_coverage/_marginal_gain/_operation` 是这些评分的私有组成部分。

## `mutation.py`：决定往哪个方向探索

### 两个 Director

`MutationDirector._validated_direction` 不信任 LLM 原始输出，只保留真实 `allowed_atom_ids` 和
`allowed_tool_names`；tool hint 最多 8 个词，objective/diagnosis 也限制长度。若没有有效 preferred atom，
`_ensure_directed` 用重试提示再请求一次。

`SuccessEnhancementDirector.direct` 的签名刻意没有 `groundtruth`。它只能看到问题、正确父路线、工具
observations、槽位和可选原子，用于增强鲁棒性。

`FailureRepairDirector.direct` 可看到错误预测与 ground truth 以诊断失败，但随后用
`GROUNDTRUTH_SAFE_DIRECTION_PROMPT` 改写，并再次经过允许集合校验，防止把答案文本写入 Skill。

### `MutationCandidateSelector`

三种策略：

- `uniform`：固定 seed 的随机对照；
- `direction_only`：只按 mutation ID 稳定排序；
- `direction_ucb`：主线，调用 ParamSpace 的覆盖和 UCB 评分。

### `WorkflowMutationEngine`

构造时持有两个 Director、selector、ParamSpace 和 `WorkflowMutator`。`extract_parent` 在没有可复用父
路线时从本次成功执行轨迹抽取 baseline。`generate` 完成：选 mode → Director → portfolios → mutator →
selector，并返回预算内 `(MutationSpec, WorkflowSpec)`。

`ApplicabilityGeneralizer.generalize` 只更新 Workflow reference 中的 name/description/exclusions/boundary，
不覆盖人工 `SKILL.md` 或 Python 脚本。`_safe_name/_clean_text` 清洗 LLM 输出。

## `workflow_mutator.py`：把方向变成可执行 DAG

`CLASS_DESCRIPTIONS` 提供默认类别描述；`PYTHON_DETECTION_SUMMARY_CODE` 是需要确定性检测汇总时使用的
代码模板。

### 主要入口

- `register_problem_class`：为动态 benchmark 加类别描述；
- `extract`：把成功 trajectory 的工具调用变成父 Workflow；
- `generalize`：无 LLM 的基础适用性清理；
- `mutate`：把 `MutationSpec` 的原子应用到父路线；
- `workflow_signature`：对规范化工具图哈希，支持去重；
- `build_anomaly_baseline_workflow(event_type)`：创建只含 embedding 的最短可靠路线。

### `mutate` 内部关键变量

| 变量 | 作用 |
|---|---|
| `steps` | 父路线步骤的可修改副本 |
| `applicability` | 同步更新 required tools/slots 和边界 |
| `selected_atoms` | 当前 portfolio 中的原子 |
| `tool_hints` | Director 给工具的短运行时目标 |
| `slot_bindings` | 将样本具体值替换为 `$slot.*` 的依据 |
| `source_task_id` | provenance，不应进入适用性文本 |

`_apply_atom` 决定替换、调参或插入；`_steps_for_atom` 为新工具建立节点；`_normalize_args` 把参数统一成
运行时引用；`_compact_steps` 去除无效重复；`_order_and_wire` 建立合法 DAG 顺序和 depends_on。

`_default_step` 保证异常 baseline 含 embedding；`_replace_axis` 避免同一工具同一 axis 保留冲突值；
`_required_slots` 最终从图引用推导，而不是相信自然语言；`_workflow_id` 对类别和步骤哈希生成稳定 ID。

其余 `_numeric_value/_grounding_query/_multiple_grounding_targets/_semantic_query_for_atoms/_step_purpose`
负责把参数原子翻译为具体工具参数和中文步骤目的。

## `skill_consolidator.py`：去重与容量控制

### 结构门

`StructuralCompatibilityChecker.graph_payload` 保留：步骤顺序、工具名、输出 contract、参数形状、依赖
索引和 param axes。`compatibility_payload` 忽略具体参数值但仍保留工具契约和 DAG。只有 problem class
相同且两种 payload 至少一种一致，才进入语义判断。

`_argument_shape` 只描述 dict/list/reference/literal 形状，避免把某个样本值当结构差异。

### 语义门和合并

`ApplicabilityCompatibilityJudge.judge` 比较两条结构兼容路线的 description、exclusions 和 boundary，
只能返回 `merge` 或 `separate`。`WorkflowConsolidator.consolidate` 只接受至少一次正确的 Workflow：

1. 找 active 中结构兼容路线；
2. 可选调用语义 judge；
3. `_merge` 选代表路线、合并 metrics 和来源任务；
4. 被合并路线归档；
5. 保存 representative；
6. 调 Pareto pruner 执行每类 soft cap。

`_representative_key` 决定合并后谁保留 ID，`_merge_metrics` 聚合计数，`_retention_key` 和 `_dominates`
用于容量裁剪。

### `ParetoWorkflowPruner`

比较维度是 accuracy、evidence rate、average cost 和 structural coverage。先归档被其他路线支配的项；
若非支配集仍超过 `cap_per_class`，再按 retention key 去掉最低项。

## `workflow_lifecycle.py`

`WorkflowLifecycleManager.register` 默认把新路线放入 provisional。仅当 `one_shot_activation=true`、路线是
`extracted` 且证据通过时才可直接 active。

`review` 重新读取 Repository 最新 metrics，再由 `_target_status` 判断：

| 迁移 | 默认条件 |
|---|---|
| provisional → active | 至少 2 次 trial、2 次正确、2 次证据通过，accuracy/evidence rate ≥ 0.6 |
| active → provisional | 至少 3 次 trial，accuracy 或 evidence rate < 0.4 |
| 任意 → archive | 至少 5 次 trial 且 accuracy < 0.25 |

具体数值来自 `ExperimentConfig`，表中是默认值。`_reason` 生成包含 trials、accuracy、evidence rate 的
可审计迁移原因；Store 同时记录 workflow event。

人工 `--install` 路线直接进入 active，这是明确的人审入口；之后仍通过相同 metrics 更新和生命周期
机制接受质量审查。
