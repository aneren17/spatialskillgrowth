# Skill 检索和执行顺序

`workflow_structurally_eligible` 检查所需槽位和允许工具。探索阶段只处理图片并排除
`embeddingTool`；同类候选按准确率、证据通过率、平均成本和验证次数排序。

探索执行顺序：

```text
最多三个图片 Skill
  → 当前媒体基线
  → ReAct（仅前两者均未通过时）
```

冻结视频推理检索全部结构合格图片工作流，随后执行：

```text
原视频 embedding ─┐
                  ├─ 并行执行 → 有效判断取 OR
全部检索工作流 ────┘
```

每个并行结果独立经过异常证据门。任一有效结果为“是”即返回“是”；全部有效结果为“否”才返回“否”。

`WorkflowExecutor` 执行 `scripts/<workflow-id>.py`。自动工作流没有脚本时，`WorkflowPythonExporter`
根据 JSON 图生成；人工脚本不会被覆盖。视频任务把原视频交给 embedding，把抽帧交给图片工具；
图片任务的工具白名单会直接排除 embedding。
