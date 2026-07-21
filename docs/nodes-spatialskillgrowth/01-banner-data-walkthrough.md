# Banner 单条数据全链路

输入示例：

```json
{
  "task_id": "banner_demo_00",
  "image_path": "banner_00_00252ms.jpg",
  "event_type": "banner",
  "answer": "是"
}
```

`online_data.parse_online_item` 解析类别、拼接媒体路径、检查文件，并构造固定中文问题。它生成的
`TaskRecord` 主要值如下：

| 属性 | 示例 | 使用位置 |
|---|---|---|
| `task_id` | `banner_demo_00` | SQLite、轨迹目录、结果行 |
| `event_type` | `banner` | Planner 和 Skill 类别目录 |
| `media_path` | 一个绝对路径 | 原始媒体输入 |
| `media_type` | `image` | 决定直通或视频抽帧 |
| `question` | 固定中文检测要求 | Skill 辅助工具和 ReAct |
| `groundtruth` | `是` | 仅探索和有标签评测使用 |

图片经过 `MediaPreprocessor.prepare` 后，`sampled_frame_paths` 就是该图片。视频则保留原视频，同时把
抽出的帧放进 `sampled_frame_paths`。

`TaskPlanner.plan` 不分析问题文本，只验证类别、单媒体约束和媒体类型。运行时槽位是：

```python
{"event_type": "banner", "media_type": "image"}
```

图片计划会排除 `embeddingTool`。探索阶段只读取同类别图片工作流；没有合格 Skill 时进入图像工具
ReAct。视频推理会检索同类别全部结构合格图片工作流，并行执行原视频 embedding 与这些抽样帧工作流，
最后用确定性 OR 规则汇总。

探索阶段把最终“是”与标注比较，正确工作流进入指标和生命周期更新，错误结果进入失败修复。推理阶段只
执行和记录，不修改 Skill。
