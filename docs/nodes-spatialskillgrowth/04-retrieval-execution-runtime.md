# Skill 检索和执行顺序

`workflow_structurally_eligible` 检查所需槽位、`embeddingTool` 和允许工具。同类候选按准确率、证据通过
率、平均成本和验证次数排序；Retriever 不再调用 LLM。

`CandidateExecutionCoordinator.run` 的固定顺序：

```text
最多三个已验证 Skill
  → embedding 基线
  → ReAct（仅前两者均未通过时）
```

每次尝试都立即经过异常证据门。通过后不再调用后续候选。

`WorkflowExecutor` 执行 `scripts/<workflow-id>.py`。自动工作流没有脚本时，`WorkflowPythonExporter`
根据 JSON 图生成；人工脚本不会被覆盖。视频任务把原视频交给 embedding，把抽帧交给图片工具。
