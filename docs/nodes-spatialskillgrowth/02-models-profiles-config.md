# 数据模型、类别、运行配置与 Skill 路径

本组包含 `models.py`、`benchmark_profiles.py`、`experiment_config.py` 和 `skill_layout.py`。它们不负责
真正调用视觉工具，而是定义其他模块共同遵守的数据语言和目录边界。

## `models.py`：跨模块数据协议

### 基础序列化

`T` 是 `TypeVar`，用于让 `SerializableRecord.from_dict` 返回具体子类类型。`SerializableRecord` 提供：

- `to_dict()`：通过 `dataclasses.asdict` 递归转字典；Store 写 JSON 时使用。
- `from_dict(value)`：基础实现直接 `cls(**value)`；含嵌套对象的子类会覆盖。

### 枚举

| 枚举 | 值 | 框架中的作用 |
|---|---|---|
| `WorkflowStatus` | `provisional/active/archive` | Repository 选择保存根目录，生命周期决定迁移方向 |
| `MutationMode` | `success_enhancement/failure_repair/extracted` | 标记候选来源；人工路线额外使用字符串 `manual` |

### `TaskRecord`

| 字段 | banner 图片例子 | 使用位置 |
|---|---|---|
| `task_id` | `banner_demo_00` | Store 主键、缓存键、抽帧目录名 |
| `question` | 中文异常检测问题 | Planner、Retriever、工具 query、轨迹 |
| `groundtruth` | `是` | 探索正确性和评测；在线推理可为空 |
| `image_paths` | `[/abs/banner.jpg]` | 原始输入；异常任务要求长度恰好为 1 |
| `capability` | `banner` | 固定 problem class，阻止重复分类 |
| `answer_type` | `bool` | Retriever 和答案比较 |
| `media_type` | `image` | 决定是否抽帧 |
| `sampled_frame_paths` | 图片本身或视频帧 | 图片工具通道 |
| `media_metadata` | FPS、时长、帧数 | summary 和诊断 |

属性 `media_path` 返回唯一原始媒体；属性 `visual_paths` 优先返回抽样帧。这两个属性实现“视频给
embedding、帧给图片工具”的双路由。

### 工作流相关模型

`ParamAtom` 表示一个最小变异原子，例如：

```json
{
  "tool_name": "paddleOcrTool",
  "axis": "evidence_role",
  "value": "text_reading",
  "kind": "tool"
}
```

其 `atom_id` 自动拼成 `paddleOcrTool:evidence_role:text_reading`，用于方向提示、UCB 统计和日志。

`MutationSpec` 表示一次候选组合：

- `atom`：兼容旧单原子逻辑的主原子；
- `atoms`：实际组合的全部原子；
- `operation`：add/replace/tune 等操作；
- `score_parts`：coverage、quality、UCB 等评分分解；
- `placements`：工具插入 DAG 的位置提示；
- `selected_atoms`：优先返回 `atoms`，为空时回退 `[atom]`。

`WorkflowStep` 是 DAG 节点。banner 的 embedding 节点为：

```json
{
  "tool_name": "embeddingTool",
  "args": {"file_path": "$media", "event_type": "$slot.event_type"},
  "step_id": "embedding",
  "depends_on": [],
  "purpose": "取得异常判断和阈值"
}
```

`ApplicabilitySpec` 分成两类条件：

- `problem_class/required_slots/required_tools/answer_types`：可确定性硬过滤；
- `description/exclusions/capability_boundary`：交给主线多模态 Retriever 做语义判断。

`WorkflowMetrics` 的原始计数与派生属性：

| 原始字段 | 示例 | 派生结果 |
|---|---:|---|
| `trial_count` | 10 | 分母 |
| `correct_count` | 8 | `accuracy=0.8` |
| `evidence_accept_count` | 7 | `evidence_rate=0.7` |
| `total_tool_calls` | 25 | 与失败数共同构成成本 |
| `tool_failure_count` | 2 | `average_cost=(25+2)/10=2.7` |
| `total_latency_ms` | 12000 | 当前用于记录，未直接参与上述三属性 |
| `structural_coverage` | 5.0 | 合并/裁剪的结构信息量 |

`WorkflowSpec` 聚合唯一 ID、名称、applicability、steps、状态、父路线、变异信息、指标和来源任务。
它是 Repository、Retriever、Executor、Consolidator 和 Lifecycle 之间最关键的共享对象。

`MutationDirection`、`RetrievalDecision`、`EvidenceDecision` 分别是方向 LLM、Retriever、证据门的
结构化输出，都会写入轨迹和数据库。

## `benchmark_profiles.py`：类别真值表

### 核心常量

| 常量 | 当前值/规模 | 作用 |
|---|---|---|
| `DEFAULT_BENCHMARK` | `anomaly_detection` | 未指定 benchmark 时的默认值 |
| `ANOMALY_BENCHMARK` | `anomaly_detection` | 异常分支判断 |
| `ANOMALY_EVENT_TYPES` | 55 个精确英文 ID | Planner 合法类别、白板生成、证据门识别 |
| `ANOMALY_CLASS_METADATA` | 每类标题、别名、描述等 | 中文问题、Skill 元数据、结果展示 |
| `BENCHMARK_ALIASES` | benchmark 别名映射 | CLI 输入归一化 |
| `BENCHMARK_PROBLEM_CLASSES` | benchmark 到类别元组 | 动态初始化运行目录 |
| `LEGACY_* / OMNI3D_*` | 兼容旧任务 | 异常主链路通常不用 |

以 `banner` 为例，元数据中包含中文标题“违规横幅检测”、来自不同前端的显示名称、别名、
`primary_tool=embeddingTool`、`answer_type=bool` 和证据要求。

### 对外函数

- `normalize_benchmark(benchmark)`：`anomaly` 等别名归一成正式 ID。
- `problem_classes_for(benchmark)`：返回该 benchmark 的类别元组。
- `class_metadata_for(benchmark)`：返回一份元数据字典副本，避免调用方直接修改全局表。
- `has_benchmark_profile(benchmark)`：决定分类器是否允许数据中出现动态类别。
- `resolve_benchmark_skill_root(skill_root, benchmark)`：兼容按 benchmark 分层的 Skill 来源路径。
- `heuristic_problem_class(question, benchmark)`：旧数据缺少类别时的确定性兜底。

其余 `_contains_*` 和 `_heuristic_*` 函数只服务旧 benchmark 的启发式分类，不进入已经明确
`event_type` 的异常检测任务。

## `experiment_config.py`：实验开关与目录隔离

### 全局默认值

| 变量 | 值 | 影响 |
|---|---|---|
| `PROJECT_ROOT` | 从当前文件向上三级 | 定位白板和默认结果根 |
| `DEFAULT_RESULT_ROOT` | `benchmark_result/spatialskillgrowth_anomaly_detection` | 默认输出目录 |
| `DEFAULT_SKILL_WHITEBOARD_ROOT` | `skills/spatialskillgrowth_whiteboard` | 只读模板位置；不再是 run 来源 |
| `DEFAULT_EDITABLE_SKILL_ROOT` | `skills/spatialskillgrowth` | 人工 Skill 来源，复制到新 run 的 active |
| `RUN_SKILLSET_FILE` | `SKILLSET.json` | run 内记录真实来源和类别的清单 |
| `DEFAULT_SEED` | `3407` | 方向选择和实验复现 |
| `DEFAULT_TOP_K` | `3` | Retriever 最大候选数 |
| `DEFAULT_ACTIVE_CAP` | `12` | 每类 active 上限 |

### `ExperimentConfig`

重要字段按阶段分组：

| 分组 | 字段 | 用途 |
|---|---|---|
| 检索/执行 | `retriever/use_retrieval/use_react/workflow_top_k` | 选择检索器、是否回退 ReAct |
| 探索 | `exploration_use_react/success_enhancement/failure_repair` | 控制父路线和两种变异 |
| 候选预算 | `success_candidate_budget/failure_candidate_budget` | 每条样本最多试多少增强/修复路线 |
| 生命周期 | `provisional_*`, `promotion_accuracy`, `demotion_accuracy`, `archive_accuracy` | 升级、降级、归档阈值 |
| 合并 | `semantic_consolidation/active_cap_per_class` | 是否调用语义判断和容量裁剪 |
| 扩展 | `extra` | 视频 FPS、最大帧数、演示标记等非固定项 |

`EXPERIMENT_PRESETS` 只覆盖与 `full` 不同的字段。例如 `retrieval_only` 关闭 ReAct 和两条变异，
`history_only` 只替换 Retriever。`build_experiment_config` 校验名称后合并默认值；`to_dict` 用于
`config.json` 和恢复一致性检查。

### `ExperimentPaths`

构造后最重要的路径变量：

```text
root
├── state_dir
├── skill_root
│   ├── active_skill_root
│   ├── provisional_skill_root
│   └── archive_skill_root
├── trajectory_root
├── retrieval_root
├── results_root
├── metrics_root
└── export_root
```

`ensure(config, mode, resume)` 做四件事：

1. 校验已有 manifest 的 experiment/run_id/benchmark 和 config 完全一致；
2. 新 run 调 `_initialize_skill_workspace`；
3. 创建所有目录；
4. 写 `manifest.json` 和 `config.json`。

若异常 run 只指定 `problem_classes=["banner"]`，初始化器先用代码中的 55 类标准表校验 banner，再从
可编辑 `skills/spatialskillgrowth/banner` 复制 active Skill，而不是读取 whiteboard 或生成空白 Skill。
provisional/archive 复制同一份人工 `SKILL.md`，但 workflow/script 按状态保持为空。这保证人工说明和
脚本来源清楚。非异常 benchmark 调
`_initialize_dynamic_skill_workspace` 生成标准空 Skill。

私有辅助函数：

- `_write_blank_skill`：创建 SKILL、scripts、references，并写空索引；
- `_safe_component`：清洗 run/experiment 路径段，防止非法路径；
- `_default_run_id`：生成 UTC 时间戳 ID；
- `_write_json`：统一中文 JSON 写入。

## `skill_layout.py`：目录单一真值源

四个常量分别固定 `references`、`scripts`、`skill.json`、`workflows` 名称。函数关系如下：

```python
standard_skill_name("fire_door_unclosed")
# "fire-door-unclosed"

skill_directory(active_root, "fire_door_unclosed")
# active_root / "fire-door-unclosed"

skill_metadata_path(directory)
# directory / "references" / "skill.json"

workflow_reference_directory(directory)
# directory / "references" / "workflows"
```

白板构建、可编辑 Skill 初始化、Repository 和人工验证都调用这些函数，避免各模块自行拼接出不同格式。
