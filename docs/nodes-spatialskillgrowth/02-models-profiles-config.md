# 数据模型、事件元数据和配置

## `core/models.py`

- `TaskRecord`：一条输入；`media_path` 返回原媒体，`visual_paths` 返回抽帧图片；
- `WorkflowStep`：工具名、参数、步骤 ID、依赖、目的和变异 atom；
- `ApplicabilitySpec`：异常类别、必需槽位、必需工具和自然语言边界；
- `WorkflowSpec`：完整工作流、状态、来源、变异方向和历史统计；
- `WorkflowMetrics`：试验、正确、证据通过、工具失败、调用数和耗时；
- `MutationDirection/MutationSpec/ParamAtom`：变异方向与具体候选；
- `RetrievalDecision/EvidenceDecision`：检索和证据门结论。

最终答案固定为异常布尔判断，所以模型中不再保存 `answer_type`。

## `core/anomaly_events.py`

该文件只从 `embeddingTool.py` 读取 55 类事件并构造：

- `ANOMALY_EVENT_TYPES`；
- `ANOMALY_CLASS_METADATA`；
- `class_metadata_for_anomaly()`。

## `core/experiment_config.py`

`ExperimentConfig` 只保留候选数、生命周期阈值、ReAct、两条变异路线和 `extra`。没有 experiment preset。

`ExperimentPaths(run_id, result_root, problem_classes, class_metadata)` 创建固定 `full/<run-id>` 目录。新
run 从 `skills/spatialskillgrowth/` 初始化；恢复 run 不覆盖原 Skill。
