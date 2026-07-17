# 证据验证、人工 Skill 和评测

本组包含 `evidence_validator.py`、`human_skill_validation.py` 和 `omni3d_eval_adapter.py`。

## `evidence_validator.py`

### 常量

`NUMERICAL_PROBLEM_CLASSES` 标识需要定位、计算等结构证据的旧数值问题；`LOCALIZATION_TOOLS` 是能够
提供定位证据的工具集合。异常检测不依赖这两组启发式，而是走专门 anomaly contract。

### Validator 层次

`EvidenceValidator` 是抽象接口，统一签名：

```python
validate(problem_class, question, answer, answer_type, result, image_paths)
```

返回 `EvidenceDecision(accepted, validator, reason, contract_checks)`。

`AnomalyEvidenceValidator` 检查：单媒体、执行成功、embedding 调用、event type 一致、判断存在、最终
答案一致、threshold 是数值。banner 工具返回“是，0.66”时七项均为 true。

`AnomalyAwareEvidenceValidator` 是包装器：55 个异常类总是转交 anomaly validator，其他类才使用传入的
delegate。这意味着即使实验配置为 `evidence_validation=none`，异常任务仍不能绕过 embedding 契约。

其他实现：

- `NoEvidenceValidator`：只检查答案格式，用于消融；
- `StructuralEvidenceValidator`：检查成功 observations、定位、合成、工具失败和答案格式；
- `SemanticEvidenceValidator`：把问题、答案和紧凑 observations 交给 LLM 判断支持性；
- `HybridEvidenceValidator`：数值任务先结构后语义，其他任务走语义。

`build_evidence_validator(strategy, llm)` 创建 delegate 后总是包一层 anomaly-aware。`answer_format_valid`
严格判断 int/float/bool/text 是否非空；`_answer_format_valid` 是兼容旧调用的别名。

## `human_skill_validation.py`

### 验证入口

`REQUIRED_SCRIPT_PARAMETERS=("runtime", "question", "image_paths")` 固定 solve 前三个参数；
`ALLOWED_SKILL_ENTRIES` 限制 Skill 根只有 `SKILL.md/scripts/references`。

`validate_human_skill(...)` 的阶段：

```text
目录与 frontmatter
  -> 安全 AST 加载
  -> 脚本/Workflow 契约一致性
  -> mock 或真实工具执行
  -> anomaly evidence contract
  -> 可选 install
```

返回报告中的 `checks` 分别是 `standard_skill_layout`、`safe_python_ast`、`script_contract`、`execution`、
`evidence_contract`；`errors` 保留所有可行动错误，CLI 据此返回非零退出码。

### 目录和 frontmatter

`_validate_skill_directory` 检查标准路径和根目录多余文件；`_parse_frontmatter` 要求且只允许：

```yaml
name: banner
description: "何时使用以及能力是什么"
```

name 必须与目录一致并满足连字符格式。

### 脚本契约

`_validate_script_contract` 校验：

- 文件名等于 `WORKFLOW_ID`；
- `PROBLEM_CLASS` 与目录和 SKILL name 一致；
- `DECLARED_TOOLS` 非空；
- solve 前三参数和 required slots 完整；
- `WORKFLOW_CONTRACT` 或 reference 可转成 WorkflowSpec；
- 脚本内 contract 与已安装 reference 的稳定字段一致；
- contract tools、required tools、AST 中实际 `runtime.call` 工具完全一致；
- contract step IDs 与实际调用 step IDs 完全一致。

`_workflow_from_contract` 为新脚本构建 `status=active, mutation_mode=manual` 的 WorkflowSpec；
`_stable_contract` 排除会随运行变化的 metrics/status，只比较执行与适用性契约；`_runtime_calls` 用 AST
读取静态工具名和 step ID，不执行脚本来猜声明。

### 执行和安装

`_execute_validation` 构造临时 `TaskRecord`，经过 MediaPreprocessor 后用 PythonSkillExecutor 执行。默认
`_mock_registry` 为声明工具提供确定性结果，`_MockTool.invoke` 模拟统一工具接口；`real_tools=true` 才用
真实服务。

`_install_human_script` 在验证全通过后：

1. 复制到 `scripts/`，默认拒绝覆盖；
2. 写 `references/workflows/<id>.json`；
3. 更新 `references/skill.json`，标记 `authorship=human`；
4. 重建父目录 `SKILLS.json`。

同一验证器也能验证 exporter 生成脚本，因此“人工和生成同执行契约”是实际测试过的代码路径。

## `omni3d_eval_adapter.py`

此文件是原框架 benchmark 兼容层，不参与异常判断。保留它的原因是已有 Omni3D 结果仍可导出评测，
而不是异常架构依赖它。

常量：

- `FLOAT_ACC_TOLERANCE`：旧浮点准确率容差；
- `MRA_THRESHOLDS`：Mean Relative Accuracy 阈值；
- `CATEGORY_NAMES`：旧答案类别显示名。

主函数：

- `export_inference_predictions(run_root)`：从 `per_task.jsonl` 导出旧评测格式；
- `evaluate_run(...)`：读取 annotations 和 predictions，逐题计算并写结果；
- `categorize_question`：按答案类型/ground truth 分类；
- `check_answer_match`：类别相关精确或容差匹配；
- `normalize_answer/fuzzy_match`：旧文本答案兼容；
- `calculate_mra_score`：浮点相对误差阈值评分；
- `summarize/print_summary`：聚合并打印指标；
- `_task_id/_extract_number/_write_outputs`：ID、数字解析和落盘辅助。

异常检测当前使用 `pipeline.write_evaluation_summary` 和 anomaly evidence contract，不需要调用这里。
