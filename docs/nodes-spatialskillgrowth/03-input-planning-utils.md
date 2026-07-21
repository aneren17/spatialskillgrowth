# 输入、视频抽帧和工具规划

## `online_data.py`

数据集必须是 JSON 数组，不再猜测 benchmark 包装。每项必须有 `event_type`、一个媒体字段；探索时还要
有 `answer`。探索 Pipeline 只接受图片；视频输入只进入冻结推理。`resolve_event_type` 接受英文 ID 或
唯一中文别名，`build_anomaly_task` 用于单媒体输入。

## `pipeline/media_processing.py`

| 属性 | 默认值 | 含义 |
|---|---:|---|
| `sample_fps` | 1.0 | 每秒目标抽帧数 |
| `max_sampled_frames` | 12 | 一个窗口最多给图片工具的帧数 |
| `jpeg_quality` | 90 | 抽帧 JPEG 质量 |

超过上限时在整个窗口均匀取帧。manifest 记录源大小、修改时间和采样参数，完全匹配才复用缓存。

## `pipeline/task_router.py`

`TaskPlanner.plan(event_type, media_paths, registry)` 不持有 LLM。输出包括 `problem_class`、唯一
`event_type` 槽位、允许/排除工具和逐工具原因。

两个闭集检测器默认排除，因为它们需要显式类别映射，不能只凭工具名字自动启用。
图片规划始终排除 `embeddingTool`；视频规划保留它作为工作流之外的原视频并行通道。
