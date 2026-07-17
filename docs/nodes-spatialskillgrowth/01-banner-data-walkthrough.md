# Banner 数据贯穿案例

本文用仓库中已有的 banner 数据解释同一条记录在各模块中的形态变化。示例不是伪造接口：输入字段来自
`benchmark/anomaly/banner_demo/explore.json`，人工工作流来自
`skills/spatialskillgrowth/banner/`，历史输出来自
`benchmark_result/spatialskillgrowth_anomaly_detection/full/banner_demo_real_explore/`。

## 1. 数据集原始记录

第一条探索记录的核心字段如下：

```json
{
  "task_id": "banner_demo_00",
  "image_path": "banner_00_00252ms.jpg",
  "event_type": "banner",
  "answer": "是",
  "answer_type": "bool",
  "metadata": {
    "timestamp_seconds": 0.252083,
    "demo_dataset": true
  }
}
```

输入层把它转换为 `models.TaskRecord`：

```python
TaskRecord(
    task_id="banner_demo_00",
    question="请检测输入图像中是否发生‘违规横幅检测’异常事件……",
    groundtruth="是",
    image_paths=[".../banner_00_00252ms.jpg"],
    capability="banner",
    answer_type="bool",
    media_type="image",
)
```

字段对应关系：

| 原始字段 | `TaskRecord` 字段 | 谁产生/使用 |
|---|---|---|
| `task_id` | `task_id` | 输入解析产生；Store 用作数据库和轨迹主键 |
| `image_path` | `image_paths[0]` | 输入解析补全根路径；媒体处理和工具运行时使用 |
| `event_type` | `capability` | Planner 作为固定 `problem_class`，不再分类 |
| `answer` | `groundtruth` | 探索时比较正确性；推理可为空 |
| `answer_type` | `answer_type` | Retriever 结构过滤和答案校验使用 |

## 2. 媒体预处理后的数据

`MediaPreprocessor.prepare(task)` 对图片不重新编码，只补充：

```json
{
  "sampled_frame_paths": ["/abs/path/banner_00_00252ms.jpg"],
  "media_metadata": {
    "media_type": "image",
    "source": "/abs/path/banner_00_00252ms.jpg",
    "sample_fps": 0.0,
    "sampled_frame_count": 1,
    "duration_seconds": 0.0
  }
}
```

若输入是 `test/banner.mp4`，则数据会分成两条通道：

- `task.media_path` 仍为原视频，传给 `embeddingTool`；
- `task.visual_paths` 变成最多 12 张 1 FPS 抽样帧，传给 OCR、检测器、MLLM 等图片工具。

例如 5 秒视频默认抽样时间近似为 `0.5, 1.5, 2.5, 3.5, 4.5` 秒。若视频较长导致超过
`max_sampled_frames=12`，`_sample_timestamps` 会在所有候选时间点中均匀保留 12 个，而不是只取前
12 秒。

## 3. Planner 输出

`TaskPlanner.plan(...)` 收到固定类别 `banner`，因此不会请求 LLM 重新分类，也不会用 LLM 抽槽位。
输出的关键部分如下：

```json
{
  "problem_class": "banner",
  "classification": {
    "problem_class": "banner",
    "source": "benchmark"
  },
  "slot_bindings": {
    "event_type": "banner",
    "target_a": "",
    "reference_frame": "none"
  },
  "selected_tools": [
    "groundingdino", "MLLM", "paddleOcrTool", "embeddingTool"
  ],
  "excluded_tools": [
    "paddleHeadDetTool", "paddlePedriderDetTool"
  ]
}
```

这里 `slot_bindings` 实际包含 `DEFAULT_SLOTS` 的全部键，表中只截取了三项。异常检测强制
`event_type=problem_class`，避免 LLM 把 `banner` 改写成中文或近义类别。

## 4. Skill 和 Workflow 的关系

`banner/SKILL.md` 是类别级人工指引，说明什么时候使用、如何降级、哪些证据不可替代主判断。
`references/workflows/banner-human-review-v1.json` 是机器可读的具体路线：

```json
{
  "workflow_id": "banner-human-review-v1",
  "applicability": {
    "problem_class": "banner",
    "required_slots": ["event_type"],
    "required_tools": ["embeddingTool", "paddleOcrTool", "MLLM"],
    "answer_types": ["bool"]
  },
  "steps": [
    {"step_id": "embedding", "tool_name": "embeddingTool", "depends_on": []},
    {"step_id": "ocr", "tool_name": "paddleOcrTool", "depends_on": []},
    {
      "step_id": "visual-review",
      "tool_name": "MLLM",
      "depends_on": ["embedding", "ocr"]
    }
  ],
  "status": "active",
  "mutation_mode": "manual"
}
```

Retriever 首先用 `workflow_structurally_eligible` 检查：

1. `slot_bindings.event_type` 非空；
2. 三个 required tool 都在 `selected_tools`；
3. `answer_type=bool` 在允许列表中；
4. 异常类工作流的图中确实包含 `embeddingTool`。

全部通过后，主线 Retriever 才把 `SKILL.md`、自然语言 applicability、工具 DAG 和历史指标交给
多模态 LLM 排序。人工和生成路线没有来源加权。

## 5. Python Skill 执行

实际执行源是 `scripts/banner-human-review-v1.py`，不是 JSON。JSON 用于检索和一致性校验。脚本里的：

```python
embedding = runtime.call(
    "embeddingTool",
    {
        "file_path": runtime.media_path(),
        "event_type": event_type,
    },
    step_id="embedding",
)
```

进入 `SkillExecutionContext.call` 后，变量含义为：

| 变量 | 本例值 | 作用 |
|---|---|---|
| `tool_name` | `embeddingTool` | 必须属于 `DECLARED_TOOLS` 和 Workflow 工具图 |
| `args.file_path` | 原始图片或原视频路径 | embedding 始终走原媒体通道 |
| `args.event_type` | `banner` | 后端精确类别 ID |
| `step_id` | `embedding` | 轨迹、依赖关系和报错定位键 |
| `result` | 标准工具结果字典 | 后续 evidence 和最终答案来源 |

假设工具原始返回：

```text
是 (判定阈值: 0.66)
```

`ToolRuntime._normalize_result` 和 `parse_anomaly_tool_output` 会得到：

```json
{
  "ok": true,
  "status": "success",
  "tool": "embeddingTool",
  "output_type": "anomaly_decision",
  "data": {
    "event_type": "banner",
    "is_anomaly": true,
    "decision": "是",
    "threshold": 0.66
  }
}
```

`runtime.finish(embedding)` 最终产生 `final_answer="是"`，但完整结构仍保留工具 observations 和阈值。

## 6. 证据门

`AnomalyEvidenceValidator.validate` 不只检查字符串“是”。本例必须同时满足：

```json
{
  "single_media_input": true,
  "successful_result": true,
  "embedding_called": true,
  "event_type_matches": true,
  "decision_present": true,
  "answer_matches_decision": true,
  "threshold_numeric": true
}
```

因此以下结果都会被拒绝：

- MLLM 说“是”，但没有调用 embedding；
- embedding 调用了 `flag` 而任务是 `banner`；
- 返回“是”但没有数值阈值；
- embedding 判断“否”，脚本却最终返回“是”；
- OCR 或裁剪步骤抛错导致 `success=false`。

## 7. 探索数据中的真实失败例子

历史 `banner_demo_real_explore` 中有一个增强候选加入 `crop_detections`，实际失败信息为：

```text
SkillStepExecutionError: Step crop_detections_0 failed:
crop_detections returned no cropped image
```

对应变量变化：

| 阶段 | 变量 | 值 |
|---|---|---|
| 方向生成 | `mutation_direction.objective` | 通过 OCR 验证横幅文本内容 |
| 候选生成 | `mutant.workflow_id` | `banner_11d8840ba255` |
| 工具执行 | `failed_step_ids` | 包含 `crop_detections_0` |
| 证据验收 | `successful_result` | `false` |
| 最终处置 | `correct` | `false`，不能进入 active |

这个例子说明：变异方向在语义上合理，不代表工具链在当前图像上可执行；证据门和生命周期必须保留。

## 8. 最终 summary

一次成功推理的核心 summary 类似：

```json
{
  "task_id": "banner_demo_00",
  "problem_class": "banner",
  "answer": "是",
  "event_type": "banner",
  "is_anomaly": true,
  "threshold": 0.66,
  "selected_workflow_id": "banner-human-review-v1",
  "fallback_react": false,
  "accepted": true
}
```

它会同时进入：

- `results/per_task.jsonl`：机器汇总；
- SQLite `tasks.summary_json`：恢复运行；
- `trajectories/<state_task_id>/conversation.md`：人工查看；
- `retrieval_rankings/<state_task_id>.json`：解释为何选中该 workflow。
