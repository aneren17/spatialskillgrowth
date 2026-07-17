# 完整符号索引

本索引覆盖 26 个模块中的模块级常量、类、属性、函数和类方法。以 `_` 开头的符号是模块内部实现，
仍列出其作用。详细数据例子见同目录的数据案例、工具教程和 Runtime/Contract 教程。

## `__init__.py`

当前为空，只标记 `nodes.mem.spatialskillgrowth` 是 Python 包；没有运行变量或导出函数。

## `answer_evaluator.py`

| 符号 | 作用/调用位置 |
|---|---|
| `FLOAT_ZERO_ABSOLUTE_TOLERANCE` | 零值浮点绝对容差；`answer_matches_typed` 使用 |
| `FLOAT_RELATIVE_TOLERANCE` | 非零浮点相对容差；`answer_matches_typed` 使用 |
| `answer_matches` | 通用规范化精确匹配；兼容旧调用 |
| `normalize_answer` | 小写、去标点、压缩空白；文本匹配使用 |
| `answer_matches_typed` | bool/int/float/text 分类型比较；两个 Pipeline 使用 |
| `_extract_number` | 从字符串抽数值；typed evaluator 内部使用 |
| `_normalize_bool` | 中英文布尔归一化；typed evaluator 内部使用 |

## `benchmark_profiles.py`

| 符号 | 作用/调用位置 |
|---|---|
| `DEFAULT_BENCHMARK` | 默认 benchmark ID；入口和归一化使用 |
| `ANOMALY_BENCHMARK` | 异常 benchmark ID；配置、输入、Pipeline 使用 |
| `ANOMALY_EVENT_TYPES` | 55 类精确 event type；Planner、证据门、白板使用 |
| `ANOMALY_CLASS_METADATA` | 55 类中文元数据；问题、Skill、结果显示使用 |
| `LEGACY_PROBLEM_CLASSES/LEGACY_CLASS_METADATA` | 旧通用类别兼容 |
| `OMNI3D_PROBLEM_CLASSES/OMNI3D_CLASS_METADATA` | Omni3D 类别兼容 |
| `BENCHMARK_ALIASES` | CLI 别名到正式 ID |
| `BENCHMARK_PROBLEM_CLASSES` | benchmark 到类别列表 |
| `normalize_benchmark` | 归一化名称；ExperimentPaths、Classifier 使用 |
| `problem_classes_for` | 取类别元组；配置和入口使用 |
| `class_metadata_for` | 取元数据副本；Factory、输入、白板使用 |
| `has_benchmark_profile` | 判断是否允许动态类；Classifier 使用 |
| `resolve_benchmark_skill_root` | 兼容 benchmark 分层 Skill 根；入口使用 |
| `heuristic_problem_class` | 旧数据缺类别时的总启发式入口 |
| `_heuristic_legacy_class` | 旧通用任务启发式 |
| `_heuristic_omni3d_class` | Omni3D 启发式 |
| `_contains_metric_distance_scaling` | 识别距离缩放问题；Omni3D 启发式调用 |
| `_contains_metric_dimension_scaling` | 识别尺寸缩放 |
| `_contains_linear_fit` | 识别线性摆放/堆叠 |
| `_contains_depth_filtered_count` | 识别深度过滤计数 |
| `_contains_count_arithmetic` | 识别计数算术 |
| `_contains_count_comparison` | 识别数量比较 |
| `_contains_object_count` | 识别物体计数 |
| `_contains_occlusion` | 识别遮挡可见性 |
| `_contains_physical_interaction` | 识别物理交互 |
| `_contains_depth_ordering` | 识别深度排序 |
| `_contains_dimension_ratio` | 识别尺寸比例 |
| `_contains_size_fit_comparison` | 识别大小/容纳比较 |
| `_contains_relative_position` | 识别相对三维位置 |
| `_contains_visual_attribute` | 识别视觉属性 |

## `conversation_trace.py`

| 符号 | 作用/调用位置 |
|---|---|
| `TRIAL_FILE_PREFIXES` | 轨迹轮次文件名前缀；`_load_trials` 使用 |
| `write_conversation_trace` | 生成 conversation.md；Store complete 调用，失败任务保留 error.json |
| `_load_trials` | 加载并排序 trial JSON |
| `_load_json` | 容错读取单个 JSON |
| `_render` | 渲染完整 Markdown 对话 |
| `_question_from_trials` | 从 trial 找原问题 |
| `_reconstructed_question` | 从 summary 为旧轨迹补问题 |
| `_compact_tool_result` | 压缩工具输出供人阅读 |
| `_code_list` | Markdown 行内代码列表 |
| `_json` | 中文 JSON code block 格式化 |

## `evidence_validator.py`

| 符号 | 作用/调用位置 |
|---|---|
| `NUMERICAL_PROBLEM_CLASSES` | 数值任务集合；Structural/Hybrid 使用 |
| `LOCALIZATION_TOOLS` | 定位工具集合；结构证据检查使用 |
| `EvidenceValidator.validate` | Validator 抽象接口 |
| `AnomalyEvidenceValidator.validate` | embedding/event type/threshold 七项契约 |
| `AnomalyAwareEvidenceValidator.__init__` | 保存非异常 delegate |
| `AnomalyAwareEvidenceValidator.validate` | 55 类异常强制转 anomaly validator |
| `NoEvidenceValidator.validate` | 消融：只检查答案格式 |
| `StructuralEvidenceValidator.validate` | 检查 observations 的结构证据 |
| `SemanticEvidenceValidator.__init__` | 保存 LLM |
| `SemanticEvidenceValidator.validate` | LLM 判断证据是否支持答案 |
| `HybridEvidenceValidator.__init__` | 组合 structural 与 semantic |
| `HybridEvidenceValidator.validate` | 数值先结构后语义，其余走语义 |
| `build_evidence_validator` | Factory 调用的策略工厂 |
| `answer_format_valid` | 严格答案类型格式检查 |
| `_answer_format_valid` | 旧名称兼容别名 |

## `experiment_config.py`

| 符号 | 作用/调用位置 |
|---|---|
| `PROJECT_ROOT` | 项目根路径 |
| `DEFAULT_RESULT_ROOT` | 异常结果默认根 |
| `DEFAULT_SKILL_WHITEBOARD_ROOT` | 只读标准模板根，不作为新 run 来源 |
| `DEFAULT_EDITABLE_SKILL_ROOT` | 人工可编辑 Skill 根，新异常 run 的 active 来源 |
| `RUN_SKILLSET_FILE` | run 内 `SKILLSET.json` 文件名 |
| `DEFAULT_SEED/DEFAULT_TOP_K/DEFAULT_ACTIVE_CAP` | 实验、检索、容量默认值 |
| `ExperimentConfig` | 所有实验开关 dataclass |
| `ExperimentConfig.to_dict` | manifest/config 一致性序列化 |
| `EXPERIMENT_PRESETS` | full 和消融覆盖项 |
| `build_experiment_config` | CLI/测试构造配置 |
| `result_root_for_benchmark` | 按 benchmark 生成默认结果根 |
| `ExperimentPaths.__init__` | 计算 run 的所有路径变量 |
| `ExperimentPaths.ensure` | 校验/初始化/创建/写 manifest |
| `ExperimentPaths._initialize_skill_workspace` | 用 55 类标准表校验，从可编辑根复制全部或子集 Skill |
| `ExperimentPaths._initialize_dynamic_skill_workspace` | 为非异常 benchmark 建运行内标准 Skill |
| `_write_json` | 配置模块 JSON 写入 |
| `_write_blank_skill` | 创建空 SKILL/scripts/references |
| `_safe_component` | 清洗 experiment/run 路径段 |
| `_default_run_id` | UTC 时间 run ID |

## `growth_store.py`

### `ExperimentStore`

| 方法 | 作用 |
|---|---|
| `__init__` | 设置 DB 路径、锁并建表 |
| `_connect` | commit/rollback 数据库上下文 |
| `_init_schema` | 创建六张事实表 |
| `begin_task` | 注册任务开始 |
| `is_complete/get_summary` | resume 查询 |
| `save_trial` | 保存一次候选执行 |
| `save_retrieval` | 保存 RetrievalDecision |
| `save_direction` | 保存 MutationDirection |
| `record_workflow_event` | 保存生命周期事件 |
| `atom_stats/record_atom_results` | 读写原子覆盖统计 |
| `workflow_task_ids` | 查询 Workflow 已验证任务 |
| `complete_task` | 完成、追加结果、写 conversation |
| `fail_task` | 保存失败并保持可重试 |
| `save_trajectory` | 写任意阶段 JSON |
| `_append_result` | 加锁追加 per_task.jsonl |

### `WorkflowRepository` 及辅助符号

| 方法/函数 | 作用 |
|---|---|
| `WorkflowRepository.__init__` | 保存 paths 和仓库锁 |
| `save/load/get/script_path` | Workflow 和执行脚本 CRUD |
| `snapshot_active_from` | 固化跨 run active 来源 |
| `list_active/list_provisional/list_archive` | 分状态读取 |
| `list_retrievable` | active 加可选 provisional |
| `skill_guidance` | 读取类别 SKILL.md 给 Retriever |
| `transition/archive` | 状态迁移 |
| `update_metrics` | 更新质量计数并保存 |
| `_list` | 标准/旧目录兼容扫描和去重 |
| `_rebuild_docs` | 更新 skill metadata，保护人工文件 |
| `_remove_from_other_statuses` | 保证状态唯一 |
| `_root_for_status/_status_roots` | 状态到路径映射 |
| `_rebuild_skill_index` | 重建 SKILLS.json |
| `_default_skill_markdown` | 动态空 Skill 模板 |
| `TrajectoryRecorder.__init__/record` | Store trajectory 轻包装 |
| `_write_json` | 普通 JSON 写入 |
| `_write_json_atomic` | 临时文件原子替换 |

## `human_skill_validation.py`

| 符号 | 作用 |
|---|---|
| `REQUIRED_SCRIPT_PARAMETERS` | solve 固定前三参数 |
| `ALLOWED_SKILL_ENTRIES` | Skill 根允许项 |
| `validate_human_skill` | 完整校验/执行/安装入口 |
| `_validate_skill_directory` | 标准目录和 name 校验 |
| `_parse_frontmatter` | 解析仅含 name/description 的 frontmatter |
| `_validate_script_contract` | 常量、工具、step、slot 一致性 |
| `_workflow_from_contract` | 人工 dict 转 WorkflowSpec |
| `_stable_contract` | 排除 metrics/status 的稳定比较视图 |
| `_runtime_calls` | AST 提取实际 runtime.call |
| `_execute_validation` | 构造测试任务并执行证据门 |
| `_MockTool.__init__/invoke` | 确定性工具模拟 |
| `_mock_registry` | 按声明工具创建 mock registry |
| `_install_human_script` | 复制脚本、写 reference 和索引 |

## `llm_utils.py`

| 符号 | 作用 |
|---|---|
| `invoke_json` | 统一多模态调用并解析 object |
| `image_content` | 本地图片转消息 data URL block |
| `parse_json` | 容错解析消息、fence 或嵌入 JSON |

## `media_processing.py`

| 符号 | 作用 |
|---|---|
| `DEFAULT_SAMPLE_FPS` | 默认 1 FPS |
| `DEFAULT_MAX_SAMPLED_FRAMES` | 默认最多 12 帧 |
| `DEFAULT_JPEG_QUALITY` | 默认 JPEG 90 |
| `MediaPreprocessor.__init__` | 约束并保存采样配置 |
| `MediaPreprocessor.prepare` | 图片补 metadata，视频抽帧 |
| `MediaPreprocessor._sample_video` | 缓存校验、OpenCV 定点取帧、写 manifest |
| `_sample_timestamps` | 居中时间点和长视频均匀下采样 |
| `_safe_component` | 清洗 task ID 目录名 |

## `models.py`

| 类/符号 | 字段或方法 |
|---|---|
| `T` | `SerializableRecord.from_dict` 类型变量 |
| `SerializableRecord` | `to_dict/from_dict` |
| `WorkflowStatus` | `ACTIVE/PROVISIONAL/ARCHIVE` |
| `MutationMode` | `SUCCESS_ENHANCEMENT/FAILURE_REPAIR/EXTRACTED` |
| `TaskRecord` | task_id、question、groundtruth、image/media 字段；`media_path/visual_paths` 属性 |
| `ParamAtom` | tool_name、axis、value、kind、description、args；`atom_id` 属性 |
| `MutationSpec` | mutation、原子、评分、placement；`selected_atoms/from_dict` |
| `WorkflowStep` | tool、args、param_atoms、purpose、step_id、depends_on；`from_dict` |
| `ApplicabilitySpec` | class、slots、tools、answer types、三类语义边界；`from_dict` |
| `WorkflowMetrics` | 七个计数字段；`accuracy/evidence_rate/average_cost/from_dict` |
| `WorkflowSpec` | ID、applicability、DAG、状态、来源、metrics；`from_dict` |
| `MutationDirection` | mode、objective、preferred/avoid atoms、hints、diagnosis |
| `RetrievalDecision` | strategy、ranked IDs、reject、reason、raw response |
| `EvidenceDecision` | accepted、validator、reason、contract checks |

## `mutation.py`

| 类/方法 | 作用 |
|---|---|
| `MutationDirector.__init__` | 保存 LLM |
| `MutationDirector.direct` | 抽象方向接口 |
| `_validated_direction` | 过滤非法原子/工具并限长 |
| `_ensure_directed` | 无有效 preferred atom 时重试 |
| `SuccessEnhancementDirector.direct` | 不看 ground truth 的成功增强 |
| `FailureRepairDirector.direct` | 看答案诊断后做安全改写 |
| `MutationCandidateSelector.__init__` | 保存策略和固定随机源 |
| `MutationCandidateSelector.select` | uniform/direction/direction-UCB 选预算 |
| `WorkflowMutationEngine.__init__` | 组装 directors、selector、ParamSpace、mutator |
| `extract_parent` | 从成功执行抽父路线 |
| `generate` | 方向→portfolio→变异→选择 |
| `ApplicabilityGeneralizer.__init__/generalize` | LLM 归纳 reference 语义边界 |
| `_safe_name` | 清洗 Workflow 名称 |
| `_clean_text` | 清洗并限长语义字段 |

## `omni3d_eval_adapter.py`

| 符号 | 作用 |
|---|---|
| `FLOAT_ACC_TOLERANCE` | Omni3D 浮点容差 |
| `MRA_THRESHOLDS` | MRA 阈值序列 |
| `CATEGORY_NAMES` | 旧评测类别显示名 |
| `export_inference_predictions` | per_task 转旧预测格式 |
| `evaluate_run` | 旧 benchmark 完整评测 |
| `categorize_question` | 按答案类型分类 |
| `check_answer_match` | 类别相关匹配 |
| `normalize_answer/fuzzy_match` | 文本归一和模糊匹配 |
| `calculate_mra_score` | 相对误差积分数 |
| `summarize/print_summary` | 聚合/显示指标 |
| `_task_id/_extract_number/_write_outputs` | ID、数字、落盘辅助 |

## `param_space.py`

| 符号 | 作用 |
|---|---|
| `COMMON_MUTATIONS` | 通用 ParamAtom 坐标 |
| `CLASS_MUTATIONS` | 类别专属坐标，含合并后的 Omni3D 坐标 |
| `OMNI3D_CLASS_MUTATIONS` | 旧 benchmark 专属坐标 |
| `ParamSpace.__init__/replace_extra_atoms` | 设置人工扩展原子 |
| `atoms_for` | 合并去重某类别原子 |
| `candidate_portfolios` | 按方向、工具依赖和 placement 生成组合 |
| `select_workflow_mutations` | 主线 UCB/覆盖选择 |
| `workflow_marginal_gain` | 相对 active 的新增覆盖 |
| `merge_candidates` | 合并候选选择辅助 |
| `workflow_features` | 提取工具、参数、结构特征 |
| `_mutation_spec` | 从原子组合建立 MutationSpec |
| `_atom_index` | 原子 UCB 指数 |
| `_mutation_quality/_workflow_quality` | 候选/Workflow 质量分 |
| `_best_coverage/_marginal_gain` | Pareto 覆盖计算 |
| `_operation` | ParamAtom 到变异操作映射 |

## `pipeline.py`

| 符号 | 作用 |
|---|---|
| `PROBLEM_CLASS_LOCKS` | 类别到 RLock |
| `PROBLEM_CLASS_LOCK_GUARD` | 保护锁字典 |
| `problem_class_lock` | 获取/创建类别锁 |
| `ExplorationPipeline.__init__` | 注入探索全依赖 |
| `ExplorationPipeline.ask` | resume、媒体、规划、类别加锁入口 |
| `_ask_locked` | 完整探索主流程 |
| `_persist_execution_attempts` | trial 落盘和可选 metrics 更新 |
| `_parent_workflow` | 选中父路线或从轨迹抽取 |
| `_persist_correct_workflow` | 注册正确 Workflow |
| `_execute_mutant` | 执行并评价一个候选 |
| `validate_provisional` | 探索后主动复验 |
| `InferencePipeline.__init__` | 注入冻结推理依赖 |
| `InferencePipeline.ask/_ask` | 推理恢复、执行、summary 落盘 |
| `ExperimentFactory.__init__` | 统一组装共享组件 |
| `build_exploration/build_inference` | 创建两种 Pipeline |
| `write_evaluation_summary` | JSON/CSV/Markdown 指标汇总 |
| `_update_workflow_metrics` | 从执行结果更新 Workflow 质量 |
| `_selected_attempt` | 找最终/选中 attempt |
| `_observations` | 兼容读取 observations/evidence |
| `_structural_coverage` | 工具数加 DAG 边数 |
| `_serializable_attempt` | attempt 精简成 JSON |
| `_metrics` | 计算 labeled accuracy 和 prediction 数 |

## `python_skill_runtime.py`

| 符号 | 作用 |
|---|---|
| `SAFE_BUILTINS` | 脚本允许内置函数 |
| `BANNED_CALL_NAMES/BANNED_NODES` | AST 禁止调用和节点 |
| `SkillScriptValidationError` | 静态脚本非法异常 |
| `SkillStepExecutionError` | 具体工具步骤失败异常 |
| `SkillExecutionContext.__init__` | 建立任务、DAG、槽位和 observation 状态 |
| `call` | 校验并执行声明工具 |
| `_should_fan_out/_call_sampled_frames` | 视频图片工具逐帧并行 |
| `require/value` | 强制成功/取结构字段 |
| `media_path/image_path/filename` | 双媒体路径 API |
| `evidence_text/evidence_image` | 累积证据 API |
| `render` | 展开 Workflow 引用 |
| `finish/result` | 收口答案/组装结果 |
| `PythonSkillExecutor.__init__/execute/_load` | 安全加载并运行 solve |
| `load_skill_script` | 人工验证和 executor 共用加载入口 |
| `_frame_result_score/_frame_result_records` | 多帧结果选择和记录 |
| `_validate_tree` | 遍历 AST 执行安全策略 |

## `skill_consolidator.py`

| 符号 | 作用 |
|---|---|
| `StructuralCompatibilityChecker.signature` | 工具图稳定哈希 |
| `compatible` | class + graph/compat payload 硬门 |
| `graph_payload` | 保留参数形状的结构数据 |
| `compatibility_payload` | 忽略具体值的结构数据 |
| `ApplicabilityCompatibilityJudge.__init__/judge` | LLM 语义 merge/separate |
| `ParetoWorkflowPruner.__init__/select_archive` | soft cap 归档选择 |
| `WorkflowConsolidator.__init__/consolidate` | 去重、合并、激活、裁剪 |
| `WorkflowConsolidator._merge` | 合并两条 Workflow |
| `_argument_shape` | 递归参数形状 |
| `_semantic_payload` | 语义 judge 输入 |
| `_merge_metrics` | 聚合质量计数 |
| `_representative_key` | 代表路线选择键 |
| `_retention_key` | 归档排序键 |
| `_dominates` | Pareto 支配关系 |

## `skill_layout.py`

| 符号 | 作用 |
|---|---|
| `REFERENCES_DIR_NAME/SCRIPTS_DIR_NAME` | 标准目录名 |
| `SKILL_METADATA_FILE/WORKFLOWS_DIR_NAME` | reference 文件/目录名 |
| `standard_skill_name` | problem class 转连字符目录名 |
| `skill_directory` | 计算某状态下 Skill 目录 |
| `skill_metadata_path` | 计算 references/skill.json |
| `workflow_reference_directory` | 计算 references/workflows |

## `skill_retriever.py`

| 符号 | 作用 |
|---|---|
| `WorkflowRetriever.__init__` | 保存 repository/top-k/provisional 开关 |
| `retrieve` | 结构候选后调用 rank |
| `_structured_candidates` | Repository + 硬过滤 |
| `rank` | 抽象排序接口 |
| `MultimodalLLMFlatRetriever.__init__` | 保存 LLM 和 candidate cap |
| `MultimodalLLMFlatRetriever.rank` | SKILL+图片+Workflow 多模态排序 |
| `MultimodalLLMFlatRetriever._payload` | Workflow 候选 JSON |
| `workflow_structurally_eligible` | slots/tools/type/embedding 硬门 |
| `HistoryOnlyRetriever.rank` | 按历史质量排序 |
| `LegacyTreeRetriever.__init__/rank` | 旧树消融 |
| `build_retriever` | Retriever 工厂 |
| `_tree_payload` | provenance 临时树形化 |

## `task_router.py`

| 符号 | 作用 |
|---|---|
| `DEFAULT_SLOTS` | 完整运行时槽位默认值 |
| `SLOT_WORD_LIMITS` | SAM query 最多三词 |
| `CLOSED_SET_DETECTION_TOOLS` | 默认需排除的闭集检测器 |
| `BenchmarkProblemClassifier.__init__/classify` | 固定类优先，缺失时 LLM 分类 |
| `SlotExtractor.__init__/extract` | LLM 抽槽；异常固定 event type |
| `ToolAvailabilityPolicy.select` | 按真实 registry 和闭集许可裁剪 |
| `TaskPlanner.__init__/plan` | 组合分类、槽位、工具决策 |
| `_compact_value` | 槽位切词限长 |

## `tool_contracts.py`

| 符号 | 作用 |
|---|---|
| `TOOL_CONTRACTS` | 工具输入输出单一真值表 |
| `output_types/output_type` | 查询全部/主输出类型 |
| `PIXEL_DETECTION_TOOLS` | 产生像素检测框的工具 |
| `PRODUCED_RESOURCE_TYPES` | 所有生产资源类型 |
| `DEPENDENT_TOOLS` | 需要前置资源的工具 |
| `FRAME_INDEPENDENT_IMAGE_TOOLS` | 视频可逐帧并行工具 |
| `input_constraints` | 查询工具输入依赖 |
| `contract_signature` | 合并器结构签名 |
| `compatible_producers` | 查询依赖的生产者 |
| `can_add_tool` | 变异时检查依赖闭包 |

## `tool_runtime.py`

| 符号 | 作用 |
|---|---|
| `STEP_REFERENCE_PATTERN/SLOT_REFERENCE_PATTERN` | Workflow 引用正则 |
| `SEMANTIC_EMPTY_MARKERS/ERROR_PREFIXES` | 空结果和错误文本识别 |
| `ANOMALY_RESULT_PATTERN` | 是/否与阈值解析 |
| `EVIDENCE_IMAGE_PRIORITY` | 最佳证据图排序 |
| `build_default_registry` | 注册当前基础工具 |
| `ToolRuntime.__init__/execute/skipped` | 工具注册、调用、跳过结果 |
| `_failure/_prepare_args` | 失败结构和参数适配 |
| `_coerce_detections/_normalize_detection_boxes` | 检测框解析和像素化 |
| `_normalize_result` | 任意工具响应转统一协议 |
| `_parse_json/_extract_detections/_canonical_detection/_extract_image_refs` | 响应内部解析辅助 |
| `execute_workflow_payload` | JSON Workflow 兼容执行器 |
| `normalize_workflow_steps` | 补 step ID、校验依赖并排序 |
| `workflow_step_groups` | 计算可并行 DAG 层 |
| `execute_parallel_tools` | 同层工具并行执行 |
| `resolve_workflow_args` | 递归展开 media/image/slot/step 引用 |
| `build_evidence_text` | observations 转证据文本 |
| `parse_anomaly_tool_output` | 解析异常 decision/threshold |
| `extract_anomaly_result` | 从执行结果取最后成功 embedding |
| `_normalize_threshold` | threshold 类型归一 |
| `extract_final_answer` | 提取最终 bool/数值/选项 |
| `_step_references/_step_result_field/_stringify_reference` | step 引用内部辅助 |
| `_best_evidence_image/_extract_image_reference` | 证据图发现与选择 |

## `workflow_executor.py`

| 符号 | 作用 |
|---|---|
| `FinalAnswerNormalizer.__init__/normalize` | 只做最终格式规范 |
| `WorkflowExecutor.__init__/execute` | 找 Python 脚本并统一执行 |
| `ReactSolver.__init__/solve` | 候选失败后的受限 ReAct |
| `CandidateExecutionCoordinator.__init__/run` | top-k→baseline→ReAct 和证据门 |
| `WorkflowPythonExporter.__init__/export` | WorkflowSpec 生成标准 Python Skill |
| `legacy_python_wrapper` | 识别旧 JSON wrapper |
| `_validation_paths` | 证据门的原媒体路径列表 |
| `_execute_workflow_with_media` | 兼容 executor 签名的媒体调用 |
| `_python_value` | Workflow 参数转 Python 表达式 |
| `_workflow_contract` | 生成脚本内稳定契约 |
| `_safe_python_identifier` | step/slot 安全标识符 |
| `_serialize_messages` | ReAct 消息转可落盘结构 |

## `workflow_lifecycle.py`

| 符号 | 作用 |
|---|---|
| `WorkflowLifecycleManager.__init__` | 保存 config/repository/store |
| `register` | 新路线进入 provisional 或 one-shot active |
| `review` | 读取最新 metrics 并执行迁移 |
| `_target_status` | 升级、降级、归档条件 |
| `_reason` | 生成可审计质量原因 |

## `workflow_mutator.py`

| 符号 | 作用 |
|---|---|
| `CLASS_DESCRIPTIONS` | 默认 problem class 说明 |
| `PYTHON_DETECTION_SUMMARY_CODE` | 确定性检测汇总代码模板 |
| `WorkflowMutator.__init__/register_problem_class` | 初始化/扩展类别描述 |
| `extract` | 成功 trajectory 抽父 Workflow |
| `generalize` | 基础适用性泛化 |
| `mutate` | ParamAtom 组合应用到父 DAG |
| `workflow_signature` | 规范工具图哈希 |
| `_apply_atom/_steps_for_atom` | 应用原子/生成新节点 |
| `_normalize_args` | 样本参数转运行时引用 |
| `_compact_steps/_order_and_wire` | 去重、排序并连接 DAG |
| `_default_step` | 类别无步骤时的默认节点 |
| `_replace_axis` | 替换冲突的同轴原子 |
| `_numeric_value` | 原子数值解析 |
| `_grounding_query/_multiple_grounding_targets` | 开放词汇目标构造 |
| `_semantic_query_for_atoms` | MLLM query 构造 |
| `_step_purpose` | 中文步骤目的 |
| `_workflow_id` | 类别+DAG 稳定哈希 ID |
| `_required_slots` | 从最终图推导必需槽位 |
| `build_anomaly_baseline_workflow` | 单 embedding 异常 baseline |

## `workflow_slots.py`

| 符号 | 作用 |
|---|---|
| `SLOT_REFERENCE_PATTERN` | `$slot.<name>` 正则 |
| `referenced_slot_names` | 扫描 Workflow 全部槽位 |
| `python_slot_parameters` | 槽位转安全 solve 参数 |
| `slot_bindings_from_locals` | 函数 locals 重建槽位字典 |
| `_collect_slots` | dict/list/string 递归扫描实现 |
