# 当前主要符号索引

| 文件 | 主要公开符号 | 用途 |
|---|---|---|
| `core/anomaly_events.py` | `ANOMALY_EVENT_TYPES`, `class_metadata_for_anomaly` | 55 类事件 |
| `core/models.py` | `TaskRecord`, `WorkflowSpec`, `WorkflowStep`, `WorkflowMetrics` | 核心数据 |
| `core/experiment_config.py` | `ExperimentConfig`, `ExperimentPaths` | 参数和目录 |
| `pipeline/media_processing.py` | `MediaPreprocessor`, `_sample_timestamps` | 视频双通道 |
| `pipeline/task_router.py` | `TaskPlanner` | 确定性工具计划 |
| `pipeline/evidence_validator.py` | `AnomalyEvidenceValidator` | 阈值证据门 |
| `pipeline/orchestrator.py` | `ExplorationPipeline`, `InferencePipeline`, `ExperimentFactory` | 总编排 |
| `skills/skill_retriever.py` | `WorkflowRetriever`, `workflow_structurally_eligible` | 同类历史检索 |
| `skills/human_skill_validation.py` | `validate_human_skill` | 人工脚本验收 |
| `runtime/tool_runtime.py` | `ToolRuntime`, `parse_anomaly_tool_output`, `extract_anomaly_result` | 统一工具结果 |
| `runtime/python_skill_runtime.py` | `SkillExecutionContext`, `PythonSkillExecutor` | Skill 脚本运行时 |
| `runtime/workflow_executor.py` | `WorkflowExecutor`, `ReactSolver`, `CandidateExecutionCoordinator` | 执行与回退 |
| `growth/param_space.py` | `COMMON_MUTATIONS`, `ParamSpace` | 定向候选 |
| `growth/mutation.py` | `SuccessEnhancementDirector`, `FailureRepairDirector`, `WorkflowMutationEngine` | 两条变异路线 |
| `growth/workflow_mutator.py` | `WorkflowMutator`, `build_anomaly_baseline_workflow` | 轨迹转工作流 |
| `growth/workflow_lifecycle.py` | `WorkflowLifecycleManager` | 状态转换 |
| `storage/growth_store.py` | `ExperimentStore`, `WorkflowRepository` | 数据库和 Skill 文件 |

已删除 Omni3D taxonomy/evaluator、BenchmarkProblemClassifier、SlotExtractor、LegacyTreeRetriever、多证据
策略和 experiment presets。
