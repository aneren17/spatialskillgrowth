# Store、Repository 和 Pipeline

`ExperimentStore` 用 SQLite 保存任务、尝试、检索、变异方向、生命周期事件和 atom 历史。轨迹同时写入
JSON 和对话 Markdown，最终结果追加到 `per_task.jsonl`。

`WorkflowRepository` 只读取标准目录：

```text
<status>/<event-type>/references/workflows/*.json
<status>/<event-type>/scripts/*.py
```

旧 `workflows/` 路径和旧 Python wrapper 迁移已删除。`snapshot_active_from` 复制来源 active Skill，并写
`SOURCE_SNAPSHOT.json` 和文件哈希。

`ExplorationPipeline` 负责规划、检索、执行、标注比对、变异、指标、生命周期和 provisional 二次验证；
按 event_type 加锁避免并发写冲突。

`InferencePipeline` 只执行和记录，不变异 Skill。图片沿用普通候选执行；视频会检索全部结构合格的图片
工作流，并行执行原视频 embedding 与这些工作流，再对证据验收通过的判断取 OR。无标签任务的
`correct` 为 `null`。

`ExperimentFactory` 集中装配所有组件，不再接收 benchmark classifier 或多答案格式配置。
