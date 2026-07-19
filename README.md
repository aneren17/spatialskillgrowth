# SpatialSkillGrowth 异常检测框架

本项目只解决一个问题：给定一个短视频或图片，以及调用方已经确定的异常事件类别，判断该异常是否发生。

框架保留原来的核心思路：探索阶段用少量有标签样本执行 ReAct、提取/修复工作流并形成 Skill；推理阶段冻结
探索结果，优先执行通过验证的 Skill，失败时使用 embedding 基线，最后才回退 ReAct。

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
  "selected_workflow_id": "banner-human-review-v1",
  "error": ""
}
```

`embeddingTool` 是强制工具。结果只有同时包含匹配的 `event_type`、明确判断和数值 `threshold` 才能通过
证据契约。

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

详细目录边界和依赖方向见
[docs/nodes-spatialskillgrowth/00-package-layout.md](docs/nodes-spatialskillgrowth/00-package-layout.md)。

已移除的设计包括：Omni3D 数据加载与评测、其他 benchmark taxonomy、float/int/str 答案验证、动态问题
类别、seen/heldout 评测、树检索和消融 experiment presets。

## 媒体处理

图片会直接成为唯一视觉帧。视频采用双通道：

1. 原视频路径传给可处理视频的 `embeddingTool`；
2. 按默认 1 fps 抽取最多 12 帧，提供给只能处理图片的辅助工具；
3. 抽帧结果按源文件大小、修改时间和采样参数缓存。

检测窗口由上游传入。框架不再实现流式窗口增长/缩短状态机，收到多长视频就把它视为本次检测窗口。

## 探索

```bash
python -m agents.spatialskillgrowth.exploration_agent \
  --dataset benchmark/anomaly/banner_demo/explore.json \
  --media-root benchmark/anomaly/banner_demo/images \
  --run-id banner_explore_10
```

探索顺序：

```text
解析任务
  → 视频抽帧
  → 按 event_type 检索同类 Skill
  → 执行候选 Skill
  → 未通过则执行 embedding 基线
  → 仍未通过才进入 ReAct
  → 与 answer 比对
  → 成功增强或失败修复
  → 生命周期与去重
```

类别由输入确定，所以规划器不会再调用 LLM 做分类或槽位抽取。Retriever 也不再调用 LLM：同一事件类别
里的工作流按准确率、证据通过率、调用成本和验证次数排序。

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

如果不提供 `--source-run-id`，推理只使用 `skills/spatialskillgrowth/` 中的人工 Skill 和确定性 embedding
基线。

## FastAPI 接口

安装依赖并启动单进程服务：

```bash
pip install -r requirements.txt
uvicorn server.anomaly_detection_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1
```

服务只暴露一个业务接口：

```text
POST /detect
Content-Type: multipart/form-data

file=<图片或短视频>
event_type=<固定异常类别>
```

调用示例：

```bash
curl -X POST http://127.0.0.1:8000/detect \
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

人工 Skill 说明见 [docs/spatialskillgrowth-skill-authoring.md](docs/spatialskillgrowth-skill-authoring.md)。

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
  --script skills/spatialskillgrowth/banner/scripts/banner-human-review-v1.py \
  --media benchmark/anomaly/banner_demo/images/banner_00_00252ms.jpg \
  --event-type banner
```

运行 10 条离线 banner 探索：

```bash
python -m scripts.run_banner_demo_exploration \
  --run-id banner_demo_mock_explore \
  --force
```
