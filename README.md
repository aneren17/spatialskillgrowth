# SpatialSkillGrowth

这是一个以异常事件检测为核心的 SpatialSkillGrowth 子项目。标准 Skill 白板包含
`embeddingTool.py` 声明的全部 55 个异常事件类别；类别 ID 保持后端要求的英文 `event_type`，
类别标题、说明、框架提示词和工具描述均使用中文。框架先在有真实答案的样本上探索并生长工作流，
再冻结 active Skill 做推理。

55 个类别来自大屏端、RAG 检索/检测端和实时视频流检测页事件表的英文 ID 并集。相同英文 ID
只建立一个 Skill；不同前端对同一 ID 使用的不同中文名称会按来源保存在 `display_names`，完全
相同的中文名称只在 `aliases` 中保留一次。每个白板 Skill 都声明精确 `event_type`、中文别名、
`embeddingTool` 调用模板、布尔答案格式和证据要求，但 `workflows/` 仍只接收经过探索验证的工作流。

默认 benchmark 是 `anomaly_detection`。入口仍兼容其他 benchmark；`--benchmark auto` 会优先读取数据 metadata/source 和路径；
已知 benchmark 使用专属 taxonomy，未知 benchmark 使用数据中的 `problem_class`，也可通过
`--problem-classes` 显式传入。不同 benchmark 默认写入不同结果根目录。

该目录可以整体移动或建立为单独仓库。源码、提示词、标准 Skill 白板、模型客户端、工具客户端、
数据构建脚本和兼容的 Omni3D 评测适配器均已包含；大体积 benchmark、历史 `benchmark_result/`、模型
服务和视觉工具服务不复制。移动后应先进入项目根目录再执行所有 `python -m ...` 命令。

## 核心设计

- 工作流池是扁平的；`derived_from_workflow_id` 只记录来源，不参与主检索。
- 探索和推理共用的 LLM temperature 固定为 `0.7`，由配置中的唯一常量控制。
- JSON 保存工作流诞生时的结构化工具图、检索字段、结构签名和工具许可；同一标准 Skill 的
  `scripts/*.py` 是实际执行源。生成的 `solve(...)` 使用显式变量和 `runtime.call(...)`，可以人工加入
  `if`、`for` 和中间计算。指标更新和状态迁移不会覆盖人工修改的脚本。
- Python Skill 在 AST 校验、受限 builtins 和 JSON 声明工具白名单中执行；报错保留真实脚本路径、
  行号和 traceback。这是进程内受限执行环境，不是操作系统级容器隔离，不应执行不可信第三方脚本。
- 异常检测使用 55 个专用 problem class，每类与 `embeddingTool` 的一个精确 `event_type` 一一对应。
- 检索先按 problem class、槽位、工具契约和答案类型做结构硬过滤，再由多模态 LLM 查看问题、
  图片、槽位、applicability、工具图和历史指标，返回 top-3 或 reject-all。
- top-3 工作流按排名顺序执行；全部未通过证据门控后才进入 ReAct 修复。ReAct 的工具预算
  用完后会额外执行一次无工具 finalization，避免最后一次工具调用耗尽全部步数而没有答案。
- mutation 有两条独立路线：正确父路线进入 success enhancement，错误父路线进入 failure
  repair。默认候选预算分别是 2 和 3。
- success director 的接口不接收 ground truth；failure director 可用 ground truth 做诊断，但其
  方向会再经过一次 LLM 的答案无关改写。文本泄漏不再由字符串规则判断。
- hybrid 证据门对数值类先检查工具成功、定位、合成和格式契约，再由 LLM 判断 observations 是否
  真的支持答案；定性类使用 LLM 语义证据判断。任何一层失败都拒绝候选。
- 去重/合并先比较工具图签名、DAG、参数形状和工具输出契约。只有结构兼容的候选才交给 LLM
  判断自然语言 applicability、exclusions 和 capability boundary 是否兼容。文本语义不使用
  关键词规则。
- 工作流有 `provisional`、`active`、`archive` 三个状态。原始成功路线、success enhancement、
  failure repair 都先进入 provisional，只有在至少两次不同任务上重复正确且重复通过证据门才升级。
  主探索结束后还会在未见过的同类样本上主动验证
  provisional，避免候选只因探索顺序而永远无法晋升。探索可检索 provisional，全量推理只检索 active。
- 每个 problem class 默认保留最多 12 条 active 工作流，并按正确率、证据接受率、工具成本/失败
  和结构覆盖做质量降级及 Pareto 软裁剪；低质量路线会降级或归档。
- `skills/spatialskillgrowth_whiteboard/` 是异常检测的标准技能白板。其他 benchmark 会按照自身
  taxonomy 在新 run 中动态生成相同格式的 `SKILL.md`、`skill.json`、`scripts/` 和
  `workflows/`，不会混入异常事件类别。`--resume` 不会覆盖已有技能。

## 主要类

```text
nodes/mem/spatialskillgrowth/
├── experiment_config.py     # 实验预设、seed 和运行目录隔离
├── models.py                 # 工作流、方向、检索和证据模型
├── growth_store.py           # SQLite 实验事实、轨迹、三状态 JSON/Skill 仓库
├── task_router.py            # BenchmarkProblemClassifier、SlotExtractor、ToolAvailabilityPolicy
├── skill_retriever.py        # multimodal flat、legacy tree、history-only
├── workflow_executor.py      # Python Skill executor、top-3 coordinator、ReAct、Python exporter
├── python_skill_runtime.py   # AST 受限执行、工具白名单、精确脚本报错
├── workflow_slots.py         # 从工具图提取真实槽位并生成安全函数参数
├── workflow_lifecycle.py     # provisional/active/archive 质量升降级
├── evidence_validator.py     # structural、semantic、hybrid evidence validator
├── omni3d_eval_adapter.py    # JSON 推理结果、官方 10% float 与 MRA 适配
├── mutation.py               # 两个 Director、selector、mutation engine、applicability 归纳
├── skill_consolidator.py     # 结构兼容、LLM 语义合并、Pareto pruner
└── pipeline.py               # ExplorationPipeline、InferencePipeline、ExperimentFactory
```

全部提示词位于 `prompt/spatialskillgrowth_prompts.py`，业务代码中没有硬编码提示词正文。

## 环境

- Python 3.10
- OpenAI API 兼容的多模态模型服务
- 项目现有基础工具服务

安装：

```bash
cd spatialskillgrowth
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

工具源码默认连接项目既有服务地址。真实运行前需要检查 `tools/basicTools/` 中 MLLM、SAM、
GroundingDINO、UniDepth、OCR 等服务配置。不要把真实 API key 提交到仓库。

异常检测运行时只会动态加载 `tools/basicTools/`。当前活动工具为 `embeddingTool`、MLLM、
GroundingDINO、SAM3、UniDepth、YOLO、Paddle OCR/检测、图像裁剪和 Python 数值沙箱。
网页搜索、网页访问、ASR 和文档/PDF 解析工具不在活动目录，也不在核心依赖和工具策略中；
`tools/addedTools/` 仅作为非运行代码留存，框架不会扫描该目录。

## 异常检测数据

数据可以是 JSON 数组，也可以放在 `data/items/tasks/questions` 任一字段中。图像或视频字段支持
`image`、`image_path`、`video`、`video_path`、`file`、`file_path`。探索数据必须包含真实答案：

```json
[
  {
    "task_id": "fall_001",
    "video_path": "fall/demo_001.mp4",
    "event_type": "fall",
    "question": "该视频中是否发生人员跌倒事件？",
    "answer": "是",
    "answer_type": "bool"
  }
]
```

异常检测的最小输入只有一个本地视频/图片和一个已确定类别；`task_id`、`question`、`answer_type`
均可省略。类别可以使用精确英文 `event_type`，也可以使用能唯一映射的中文显示名称。加载器会验证
文件类型和文件数量，自动生成中文检测描述，并固定使用 `bool` 答案。探索数据仍必须额外提供真实答案。

单文件可以直接检测，不需要先创建数据集 JSON：

```bash
python -m agents.spatialskillgrowth.anomaly_detection_agent \
  --input-file test/banner.mp4 \
  --event-type banner \
  --experiment retrieval_only \
  --run-id banner_direct_test
```

异常检测结果使用结构化字段：

```json
{
  "event_type": "banner",
  "event_name": "违规横幅检测",
  "media_type": "video",
  "answer": "是",
  "is_anomaly": true,
  "threshold": 0.73
}
```

`embeddingTool` 调用失败、类别不一致或后端没有返回 threshold 时，证据门会拒绝该结果。

## 主实验

先探索。`run-id` 应显式指定，以便推理和复现实验引用同一技能库：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
  --benchmark anomaly_detection \
  --experiment full \
  --run-id explore_anomaly \
  --seed 3407 \
  --dataset benchmark/anomaly/explore.json \
  --img-root benchmark/anomaly/files \
  --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1
```

随后建立独立推理 run。程序会把来源 run 的 active Skill 完整复制到推理 run，并只读取本地快照：

```bash
python -m agents.spatialskillgrowth.anomaly_detection_agent \
  --benchmark anomaly_detection \
  --experiment full \
  --run-id infer_anomaly \
  --source-experiment full \
  --source-run-id explore_anomaly \
  --source-benchmark anomaly_detection \
  --dataset benchmark/anomaly/test.json \
  --img-root benchmark/anomaly/files \
  --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1
```

中断恢复使用 `--resume`。同一 experiment/run-id 的配置或 seed 不一致时程序会拒绝混用。
要完全重新探索，请使用新的 `run-id`；新 run 会自动从技能白板开始，不能用 `--resume` 清空
已有技能。

推理结束后会生成：

```text
<run>/results/per_task.jsonl
<run>/results/per_task.csv
<run>/metrics/summary.json
```

旧的 Omni3D 数据和评测适配器仍保留用于兼容实验；只有 `--benchmark omni3d` 时才会生成
`omni3d_predictions.json` 并使用下面的专用评测命令：

```bash
python evaluate/omni-3d/eval_spatialskillgrowth.py \
  --run-dir benchmark_result/spatialskillgrowth_omni3d/full/infer_omni3d_501_from_256 \
  --annotations benchmark/Omni-3d/annotations.json
```

该评测不读取旧式 `qa_cache` 数据库，而是读取推理 run 的 JSON 结果。float 按 Omni3D 原生
`<10%` 相对误差统计，同时输出十档 MRA。评测产物包括：

```text
metrics/omni3d_official_metrics.json
results/omni3d_native_eval.json
results/omni3d_eval_details.csv
```

### 其他 benchmark

例如探索 STVQA 调试集：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
  --benchmark auto \
  --dataset benchmark/STVQA-7K/spatial_debug_10/toolbatch_spatial_debug_10.json \
  --img-root benchmark/STVQA-7K/images \
  --experiment full \
  --run-id stvqa_debug10
```

使用该 STVQA run 的已冻结 workflow 做同 benchmark 推理：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --dataset benchmark/STVQA-7K/toolbatch.json \
  --img-root benchmark/STVQA-7K/images \
  --benchmark auto \
  --experiment full \
  --run-id stvqa_test \
  --source-experiment full \
  --source-run-id stvqa_debug10 \
  --source-benchmark stvqa
```

跨 benchmark 零样本推理时，目标数据、结果目录仍属于目标 benchmark，但规划和
workflow 检索使用来源 run 的 taxonomy。例如用 Omni3D 探索结果零样本推理
STVQA：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --dataset benchmark/STVQA-7K/toolbatch.json \
  --img-root benchmark/STVQA-7K/images \
  --benchmark stvqa \
  --experiment full \
  --run-id stvqa_zeroshot_from_omni3d \
  --source-experiment full \
  --source-run-id explore_omni3d_256 \
  --source-benchmark omni3d
```

如果来源 run 使用了非默认结果根目录，再传入
`--source-result-root <path>`。跨 benchmark 时，目标数据自带的 problem class 不会被
强行塞进来源 taxonomy，而是由多模态分类器映射到来源技能类别。

未知 benchmark 若数据没有 `problem_class`，默认回退到通用空间分类；为避免类别偏移，
建议显式提供 taxonomy：

```bash
--benchmark custom3d --problem-classes counting,depth_relation,metric_geometry
```

需要重新生成干净的白板文件时运行：

```bash
python -m scripts.build_spatialskillgrowth_whiteboard --force
```

该命令只重建 `skills/spatialskillgrowth_whiteboard/`，不会修改任何已有 run 下的技能。

每个工作流保存时，函数脚本会自动写入对应 skill 的 `scripts/`。例如：

```python
def solve(
    runtime,
    question,
    image_paths,
    *,
    target_a="",
    reference_value="",
):
    image_path = image_paths[0] if image_paths else ""
    detections = runtime.call(
        "groundingdino",
        {"image": image_path, "query": target_a},
        step_id="detect_target",
        purpose="定位待测目标",
    )
    runtime.require(detections, "detect_target")
    if not detections.get("data"):
        return runtime.finish("unknown")
    return runtime.finish(detections)
```

正常执行直接读取该 `.py`。若修改 JSON 后希望重建 Python，显式运行（`--force` 会覆盖人工修改）：

```bash
python -m scripts.generate_workflow_python \
  benchmark_result/.../skills/active/<class>/workflows/<workflow_id>.json \
  --force
```

传入探索入口的 `--export-python` 只会额外复制一份到统一的 `exports/python/`。

### 多 benchmark 共 256 条 zeroshot

先写一个来源清单，例如 `zeroshot_sources.json`：

```json
{
  "sources": [
    {"benchmark": "stvqa", "dataset": "benchmark/STVQA/tasks.json", "image_root": "benchmark/STVQA/images"},
    {"benchmark": "gqa", "dataset": "benchmark/GQA/tasks.json", "image_root": "benchmark/GQA/images"}
  ]
}
```

未指定 `quota` 的来源会轮转等额抽样；也可给每个来源显式设置 quota：

```bash
python -m scripts.build_multibench_zeroshot_subset \
  --manifest zeroshot_sources.json \
  --output benchmark/zeroshot/multibench_256.json \
  --size 256 --seed 3407
```

然后用 Omni3D Skill 做冻结推理：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --dataset benchmark/zeroshot/multibench_256.json \
  --benchmark multibench_zeroshot \
  --experiment full --run-id zeroshot_256_from_omni3d \
  --source-experiment full --source-run-id explore_omni3d_256 \
  --source-benchmark omni3d
```

## 消融实验

可用预设：

```text
full
react_only
retrieval_only
no_retrieval
no_success_enhancement
no_failure_repair
no_ucb
no_evidence_validation
no_semantic_consolidation
legacy_tree
history_only
```

每个端到端消融应使用独立的 experiment 和 run-id 完成自己的探索、技能库和 501 条评测。例如：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent \
  --experiment no_success_enhancement --run-id seed3407

python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --experiment no_success_enhancement --run-id seed3407
```

`retrieval_only` 在探索阶段仍允许 ReAct 产生最初的已验证工作流，冻结推理阶段关闭 ReAct，避免
空技能库使该消融无法启动。

### 固定 full 技能库的检索对照

下面只更换 retriever，技能 JSON 均来自同一个 full run：

```bash
python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --experiment legacy_tree --run-id retrieval_legacy_seed3407 \
  --source-experiment full --source-run-id explore_omni3d_256

python -m agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent \
  --experiment history_only --run-id retrieval_history_seed3407 \
  --source-experiment full --source-run-id explore_omni3d_256
```

主线 multimodal flat 对照也可建立新的输出 run，并用相同的 `--source-*` 指向 full 技能库。

## 运行产物

每次运行位于：

```text
benchmark_result/spatialskillgrowth_omni3d/<experiment>/<run-id>/
├── manifest.json
├── config.json
├── split.json
├── state/spatialskillgrowth.db
├── skills/
│   ├── WHITEBOARD.json
│   ├── SOURCE_SNAPSHOT.json        # 推理使用的来源、文件哈希和迁移记录
│   ├── active/
│   │   ├── SKILLS.json
│   │   └── <problem_class>/
│   │       ├── SKILL.md
│   │       ├── skill.json
│   │       ├── scripts/
│   │       └── workflows/*.json
│   ├── provisional/<problem_class>/{SKILL.md,skill.json,scripts/,workflows/}
│   └── archive/<problem_class>/{SKILL.md,skill.json,scripts/,workflows/}
├── trajectories/<task_id>/*.json
├── retrieval_rankings/<task_id>.json
├── results/per_task.jsonl
├── results/errors.jsonl          # 异常任务；completed=0，可用 --resume 重试
├── results/per_task.csv
├── results/omni3d_predictions.json
├── results/omni3d_native_eval.json       # 手动运行评测后生成
├── results/omni3d_eval_details.csv       # 手动运行评测后生成
├── metrics/summary.json
├── metrics/omni3d_official_metrics.json  # 手动运行评测后生成
├── summary.md
└── exports/python/              # 仅 --export-python 时生成
```

`metrics/summary.json` 按实际样本数报告 overall、seen/heldout、各 problem class、技能库规模和
skill source；`metrics/provisional_validation.json` 记录探索后的候选验证与晋升。轨迹 JSON 只用于
调试，工作流执行源是 Skill 下的 Python 脚本。

## 本地验证

以下命令不访问模型或工具 API：

```bash
python -m scripts.test_spatialskillgrowth_no_api
```

主仓库还可执行同步检查：

```bash
python -m scripts.check_spatialskillgrowth_sync
```

测试覆盖 taxonomy、动态切分、运行隔离、多模态 top-3/reject-all、
双 mutation Director 的答案边界、Python Skill 生成与执行、证据门控、结构后语义合并和
Pareto cap。无 API 测试通过不代表外部模型与工具服务可用。
