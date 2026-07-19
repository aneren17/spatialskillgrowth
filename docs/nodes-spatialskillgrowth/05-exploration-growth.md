# 探索、变异和生命周期

探索不是穷举实验。每条有标签数据只走一条主路线：

- 原答案正确：`SuccessEnhancementDirector` 寻找更可靠或更省成本的证据组合；
- 原答案错误：`FailureRepairDirector` 使用标注诊断，再去除直接答案泄漏。

Director 只能选择 `ParamSpace.atoms_for(event_type)` 中的工具参数。当前 ParamSpace 不做组合爆炸和 UCB
消融：每个首选 atom 形成小候选，必要时补上游检测工具，再按该 atom 的真实成功历史排序。

`WorkflowMutator` 从 ReAct 工具轨迹提取步骤。类别固定后，它保留 SAM/GroundingDINO 的实际查询，不再
改写成不存在的 `target_a`、`sam_query_a` 槽位。

生命周期：

```text
新工作流 → provisional → active
                    ↘ archive
active 质量下降 ─────→ archive
```

`WorkflowConsolidator` 先比较结构，再让 LLM 判断自然语言边界是否可合并；超过 active 软上限时按历史
质量保留较好的工作流。
