# 输入预处理、任务规划和基础工具

本组包含 `media_processing.py`、`task_router.py`、`llm_utils.py` 和 `answer_evaluator.py`。

## `media_processing.py`

### 配置变量

| 常量 | 默认值 | 实际意义 |
|---|---:|---|
| `DEFAULT_SAMPLE_FPS` | 1.0 | 视频每秒一个候选时间点 |
| `DEFAULT_MAX_SAMPLED_FRAMES` | 12 | 控制图片工具成本上限 |
| `DEFAULT_JPEG_QUALITY` | 90 | 抽样帧 JPEG 质量 |

`MediaPreprocessor.__init__` 将外部值限制到安全范围：FPS 至少 0.1，帧数至少 1，JPEG 质量 1～100。
`ExperimentFactory` 从 `config.extra.video_sample_fps` 和 `max_sampled_frames` 构造它；人工验证器也用它
处理测试媒体。

### `prepare(task)` 的分支变量

| 条件 | 返回变化 | 原因 |
|---|---|---|
| `len(image_paths) != 1` | 原样返回 | 本模块只处理单媒体；异常 Planner 会进一步拒绝非法输入 |
| `media_type == image` | `sampled_frame_paths=[原图]` | 图片工具和原媒体是同一路径 |
| `media_type == video` | 调 `_sample_video` | 生成图片工具通道 |
| 其他 media type | 原样返回 | 避免猜测未知格式 |

`_sample_video(video_path, task_id)` 的关键局部变量：

- `output_dir`：`state/sampled_frames/<safe-task-id>`；
- `manifest_path`：抽帧缓存描述；
- `source_stat`：文件大小和 mtime，用于缓存失效；
- `source_fps/frame_count/duration`：OpenCV 读取的媒体属性；
- `timestamps`：由 `_sample_timestamps` 计算的秒数；
- `frames/frame_names`：绝对路径供运行时使用、相对文件名供 manifest 使用。

缓存只有在源路径、大小、mtime、采样 FPS、最大帧数全部相同时命中。修改视频内容或采样配置都会重抽。

### `_sample_timestamps`

假设 `duration_seconds=30`、`sample_fps=1`、`max_frames=12`：先产生约 30 个居中时间点
`0.5...29.5`，再均匀选取 12 个索引。因此长窗口仍覆盖头、中、尾，而不是只分析前 12 秒。

## `task_router.py`

### 槽位和工具常量

`DEFAULT_SLOTS` 是所有可复用运行时槽位的完整字典：

| 槽位 | banner 值 | 主要用途 |
|---|---|---|
| `event_type` | `banner` | embedding 精确类别 |
| `target_a/target_b` | 空 | 旧视觉问题的主/次目标 |
| `sam_query_a/sam_query_b` | 空 | SAM/GroundingDINO 的短英文标签 |
| `reference_frame` | `none` | 参考坐标系 |
| `reference_entity/value/unit` | 空 | 尺度和测量参考 |
| `measurement_dimension` | 空 | count/depth/length 等 |
| `operation` | 空 | count/compare/ratio 等 |

`SLOT_WORD_LIMITS` 把两个 SAM query 限制为最多 3 个词。`CLOSED_SET_DETECTION_TOOLS` 当前包含头盔和
人车闭集检测器；未明确启用时，工具策略会排除，避免对不支持类别误用。

### `BenchmarkProblemClassifier`

构造变量：

- `benchmark`：归一化后的 benchmark ID；
- `problem_classes`：显式类别或 profile 默认类别；
- `metadata`：类别标题和描述；
- `allow_dynamic_problem_classes`：未知 benchmark 才允许新类别。

`classify` 优先使用 `fixed_problem_class`。banner 输入已经携带类别，因此返回：

```json
{"problem_class": "banner", "source": "benchmark"}
```

只有类别缺失时才构造 `PROBLEM_CLASSIFIER_PROMPT` 并通过 `invoke_json` 看图片分类。

### `SlotExtractor`

非异常任务用 LLM 解析槽位；异常类别直接把 `event_type` 设置为 problem class。解析异常时返回
`DEFAULT_SLOTS`，保证规划阶段可继续，但结构过滤会拒绝缺少必需槽位的 Workflow。

### `ToolAvailabilityPolicy`

`select(registry, allowed_closed_set_tools)` 遍历实际注册工具，而不是提示词中想象的工具。返回：

- `selected_tools`：Workflow 和 ReAct 的允许白名单；
- `excluded_tools`：当前任务不可用工具；
- `tool_decisions`：每个工具的 scope、keep/exclude 和原因。

### `TaskPlanner`

`plan` 是上述三部分的组合入口：

1. classifier 得到 `problem_class`；
2. 异常类检查输入媒体数量必须为 1，并固定 `event_type`；
3. 其他类调用 SlotExtractor；
4. ToolAvailabilityPolicy 根据真实 registry 裁剪工具；
5. 异常类若没有注册 `embeddingTool`，立即抛错。

`_compact_value` 用空白切词并截断，避免 LLM 返回长句污染工具 query。

## `llm_utils.py`

`invoke_json(llm, prompt, image_paths)` 是分类、Retriever、变异方向、语义证据和语义合并的统一入口：

```text
prompt 字符串 + image_content(image_paths)
  -> HumanMessage(content=[text block, image blocks...])
  -> llm.invoke
  -> parse_json(response.content)
```

`image_content` 读取本地图片，按扩展名生成 data URL；不存在的路径会跳过。`parse_json` 支持：

- 已经是 dict；
- `AIMessage.content`；
- 纯 JSON 字符串；
- 带 Markdown code fence 的 JSON；
- 文本中嵌入的第一个 `{...}` 对象。

它仍要求最终解析结果是 JSON object，不接受数组，避免调用方字段访问不确定。

## `answer_evaluator.py`

常量：

- `FLOAT_ZERO_ABSOLUTE_TOLERANCE=1e-6`：ground truth 为零时的绝对误差；
- `FLOAT_RELATIVE_TOLERANCE=0.1`：非零浮点答案允许 10% 相对误差。

函数分层：

| 函数 | 例子 | 使用位置 |
|---|---|---|
| `normalize_answer` | `" The Banner! " -> "the banner"` | 通用文本匹配 |
| `answer_matches` | 规范化后精确相等 | 兼容旧调用 |
| `answer_matches_typed` | bool/int/float/text 分类型判断 | 探索、推理评测、provisional 验证 |
| `_extract_number` | 从文本抽第一个数值 | int/float 比较 |
| `_normalize_bool` | `yes/是/true/1 -> True` | bool 比较 |

异常检测的 `answer_type=bool`，所以 `"是"`、`"yes"` 都能和 ground truth `"是"` 对齐；但证据门仍要求
最终答案与 embedding 的结构化 decision 一致，不能仅靠宽松布尔归一化通过。
