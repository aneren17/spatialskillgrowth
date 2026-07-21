# SpatialSkillGrowth 异常检测框架

本项目只解决一个问题：给定一个短视频或图片，以及调用方已经确定的异常事件类别，判断该异常是否发生。

框架保留原来的核心思路：探索阶段只用少量有标签图片执行 ReAct、提取/修复工作流并形成 Skill；视频
推理阶段冻结探索结果，并行执行原视频 embedding 与全部检索图片工作流，再用确定性 OR 规则汇总。

## 输入和输出

单次输入：

```text
媒体文件路径 + event_type
```

批量数据集是 JSON 数组，每条数据与 banner 示例一致：

```json
[
  {
    "task_id": "banner_demo_00",
    "image_path": "banner_00_00252ms.jpg",
    "event_type": "banner",
    "answer": "是"
  }
]
```

探索数据必须提供 `answer`；无标签推理可以不提供。媒体字段允许使用 `media_path`、`image_path`、
`video_path` 或 `file_path`，但一条任务只能解析出一个媒体文件。

输出的关键字段：

```json
{
  "event_type": "banner",
  "is_anomaly": true,
  "answer": "是",
  "threshold": 0.66,
  "selected_workflow_id": "<实际选中的 workflow_id>",
  "error": ""
}
```

`embeddingTool` 同时支持图片和原始视频。探索只使用它的图片能力，且冷启动图片基线仍是
单步 MLLM；原始视频能力仍作为冻结视频推理中的独立 embedding 工作流。embedding 成功结果必须包含
匹配的 `event_type`、明确判断和数值 `threshold`。

## 当前架构

```text
agents/spatialskillgrowth/
├── online_data.py               # 解析媒体 + event_type，生成固定中文问题
├── exploration_agent.py         # 有标签小样本探索入口
└── anomaly_detection_agent.py   # 单媒体或批量冻结推理入口

nodes/mem/spatialskillgrowth/
├── core/                        # 事件元数据、数据模型、配置、LLM 通用函数
├── runtime/                     # 工具契约、工具执行、Python Skill、工作流执行
├── skills/                      # Skill 目录规则、检索、人工 Skill 验证
├── growth/                      # 工作流提取、变异、合并和生命周期
├── storage/                     # SQLite、Skill 文件仓库和对话轨迹
└── pipeline/                    # 媒体处理、规划、证据校验和总编排
```

面向新人的架构、工具与手工 Skill 编写入口见
[docs/nodes-spatialskillgrowth/README.md](docs/nodes-spatialskillgrowth/README.md)。

已移除的设计包括：Omni3D 数据加载与评测、其他 benchmark taxonomy、float/int/str 答案验证、动态问题
类别、seen/heldout 评测、树检索和消融 experiment presets。

## 媒体处理

图片会直接成为唯一视觉帧。视频采用双通道：

1. 原视频路径传给可处理视频的 `embeddingTool`；
2. 按默认 1 fps 抽取最多 12 帧，提供给图片探索积累的帧级 Skill；
3. 抽帧结果按源文件大小、修改时间和采样参数缓存。

探索阶段只加载图片，工具计划不再排除 `embeddingTool`。它与其他图片工具一样可用于提取、变异和验证
图片工作流，但初始图片基线仍是单步 MLLM。工作流生命周期仍只依据统一的
trial、correct、evidence 和成本指标。冻结视频推理会先检索同类全部结构合格工作流，然后并行执行：

1. 原视频 `embeddingTool`；
2. 抽样帧上的全部检索工作流。

汇总不调用 LLM，而是使用确定性 OR：任一证据验收通过的通道判断为“是”，最终结果即为“是”；
所有有效通道均为“否”时才返回“否”。检索图片工作流中的 embedding 步骤使用 `$image`，不会取代或重复外层的
原视频 embedding 工作流。

检测窗口由上游传入。框架不再实现流式窗口增长/缩短状态机，收到多长视频就把它视为本次检测窗口。

## 探索

旧运行的工具计划和轨迹仍会记录 embedding 被排除，`--resume` 不会重算这些已完成任务。要让 embedding 参与图片探索，
应使用新的 `--run-id`。

对 `benchmark/anomaly/skill_datasets/` 下的全部 55 个类别运行探索：

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset-root benchmark/anomaly/skill_datasets \
  --run-id anomaly_explore_55
```

默认同时使用以下三个模型服务：

```text
http://127.0.0.1:8861/v1
http://127.0.0.1:8862/v1
http://127.0.0.1:8863/v1
```

类别按照 `INDEX.json` 中的固定顺序轮询分配。同一个异常类别的全部图片始终由同一个模型处理；
三个模型并行运行，各模型内部按顺序处理自己的类别。正式运行前可以只检查分配：

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset-root benchmark/anomaly/skill_datasets \
  --run-id plan_check \
  --plan-only
```

只探索部分异常类别：

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset-root benchmark/anomaly/skill_datasets \
  --event-types banner,fire,fall \
  --run-id anomaly_explore_subset
```

如需覆盖模型地址，可以使用逗号分隔的 `--base-urls`。`--base-url` 则会退化为单模型运行：

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset-root benchmark/anomaly/skill_datasets \
  --base-urls http://127.0.0.1:8861/v1,http://127.0.0.1:8862/v1,http://127.0.0.1:8863/v1 \
  --run-id anomaly_explore_55
```

单个数据集仍然兼容：

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset benchmark/anomaly/banner_demo/explore.json \
  --media-root benchmark/anomaly/banner_demo/images \
  --base-url http://127.0.0.1:8861/v1 \
  --run-id banner_explore_10
```

探索顺序：

```text
解析图片任务
  → 按 event_type 检索同类 Skill
  → 执行候选 Skill
  → 未通过才进入 ReAct
  → 与 answer 比对
  → 成功增强或失败修复
  → 生命周期与去重
```

类别由输入确定，所以规划器不会再调用 LLM 做分类或槽位抽取。探索 Retriever 可依据同类
`SKILL.md` 和图片证据选择 Top-K，失败时按历史指标排序；冻结推理不调用该语义淘汰逻辑，直接返回
同类全部结构合格工作流。

## 冻结推理

使用探索 run 的 active Skill 创建独立推理快照：

```bash
python -m agents.spatialskillgrowth.anomaly_detection_agent \
  --input-file test/banner.mp4 \
  --event-type banner \
  --run-id banner_infer_01 \
  --source-run-id banner_explore_10
```

批量推理：

```bash
python -m agents.spatialskillgrowth.anomaly_detection_agent \
  --dataset benchmark/anomaly/test.json \
  --media-root benchmark/anomaly/files \
  --run-id anomaly_infer_01 \
  --source-run-id anomaly_explore_10
```

如果不提供 `--source-run-id`，推理使用 `skills/spatialskillgrowth/` 中的人工 Skill。视频输入仍会额外并行
执行确定性 embedding 通道，并与全部结构合格的图片工作流取 OR。

## FastAPI 接口

安装依赖：

```bash
pip install -r requirements.txt
```

服务使用两个独立 Shell 脚本启动：

```bash
./server/start_61.sh  # HTTP 18061 -> MLLM 8861/v1
./server/start_62.sh  # HTTP 18062 -> MLLM 8862/v1
```

两个进程使用不同的 `SPATIAL_SKILL_GROWTH_API_RUN_ID`，可同时运行。完整端口、输入、输出和错误说明见
[server/API.md](server/API.md)。

服务只暴露一个业务接口：

```text
POST /detect
Content-Type: multipart/form-data

file=<图片或短视频>
event_type=<固定异常类别>
```

调用示例：

```bash
curl -X POST http://127.0.0.1:18061/detect \
  -F "file=@test/banner.mp4" \
  -F "event_type=banner"
```

响应只包含异常判断和阈值：

```json
{
  "is_anomaly": 1,
  "threshold": 0.66
}
```

`is_anomaly` 只会是 `0` 或 `1`。正常情况下保留 `embeddingTool` 返回的阈值；如果 embedding 判断为无异常，
但某条成功执行的候选通过其他工具得到异常结论，则返回 `is_anomaly=1`，并把 `threshold` 置为 `1.0`。
上传文件采用分块读取，推理结束后删除临时文件。默认最大上传大小为 256 MiB。

默认使用 `skills/spatialskillgrowth/` 中的人工 Skill。需要使用某次探索生成的 active Skill 时，在启动前设置：

```bash
export SPATIAL_SKILL_GROWTH_API_SOURCE_RUN_ID=banner_explore_10
```

其他可选配置：

| 环境变量 | 默认值 | 含义 |
|---|---|---|
| `SPATIAL_SKILL_GROWTH_API_RUN_ID` | `api_server` | 服务运行结果目录名称 |
| `SPATIAL_SKILL_GROWTH_API_RESULT_ROOT` | 框架默认结果目录 | 服务结果根目录 |
| `SPATIAL_SKILL_GROWTH_API_SOURCE_RESULT_ROOT` | 与服务结果根目录相同 | 探索 Skill 所在结果根目录 |
| `SPATIAL_SKILL_GROWTH_API_MAX_REACT_STEPS` | `8` | ReAct 最大步数 |
| `SPATIAL_SKILL_GROWTH_API_MAX_UPLOAD_BYTES` | `268435456` | 单文件最大字节数 |

## Skill 目录

```text
skills/spatialskillgrowth/<event-type>/
├── SKILL.md
├── scripts/
└── references/
    ├── skill.json
    └── workflows/
```

- `skills/spatialskillgrowth_whiteboard/` 是可重建的空标准模板，不写人工代码；
- `skills/spatialskillgrowth/` 是人工维护区；
- 新运行从人工维护区复制 `SKILL.md`，active 同时复制脚本和工作流；
- 自动生成和人工编写的脚本经过同一个执行器与证据验证器。

全部工具和中间结果见
[docs/nodes-spatialskillgrowth/01-tools-and-intermediate-results.md](docs/nodes-spatialskillgrowth/01-tools-and-intermediate-results.md)；
从零手工编写工作流见
[docs/nodes-spatialskillgrowth/02-manual-skill-authoring.md](docs/nodes-spatialskillgrowth/02-manual-skill-authoring.md)。

## 结果目录

```text
benchmark_result/spatialskillgrowth_anomaly_detection/full/<run-id>/
├── manifest.json
├── config.json
├── split.json
├── skills/
│   ├── SKILLSET.json
│   ├── active/
│   ├── provisional/
│   └── archive/
├── state/spatialskillgrowth.db
├── trajectories/<task-id>/
├── retrieval_rankings/
├── results/per_task.jsonl
└── metrics/
```

## 无网络验证

```bash
python -m scripts.test_spatialskillgrowth_no_api
```

该测试覆盖当前异常检测主链路，不再测试已删除 benchmark 或消融分支。

验证人工 banner Skill：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

校验并部署人工 Skill，使其生成可检索 Workflow JSON 并进入 active：

```bash
python -m scripts.deploy_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

部署后使用新的推理 `run-id`；`--resume` 不会刷新旧 run 的 Skill 快照。

运行 10 条离线 banner 探索：

```bash
python -m scripts.run_banner_demo_exploration \
  --run-id banner_demo_mock_explore \
  --force
```
