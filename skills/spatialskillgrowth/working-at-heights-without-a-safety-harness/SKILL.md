---
name: working-at-heights-without-a-safety-harness
description: "检测输入视频或图像中是否发生“高空作业未系安全带”异常事件（相关显示名称：高空作业未系安全带）；调用异常检测工具时，必须使用精确类别 ID `working_at_heights_without_a_safety_harness`。"
---

# 高空作业未系安全带

## 用途

检测输入视频或图像中是否发生“高空作业未系安全带”异常事件（相关显示名称：高空作业未系安全带）；调用异常检测工具时，必须使用精确类别 ID `working_at_heights_without_a_safety_harness`。

## 事件接口

- 精确 `event_type`：`working_at_heights_without_a_safety_harness`
- 主检测工具：`embeddingTool`
- 答案类型：`bool`，输出“是”或“否”
- 结构化结果：必须包含 `is_anomaly` 和 `threshold`

## 各端显示名称

| 来源 | 中文显示名称 |
|---|---|
| RAG 检索/检测端 | 高空作业未系安全带 |

## 工具调用模板

```json
{
  "tool_name": "embeddingTool",
  "args": {
    "file_path": "$media",
    "event_type": "working_at_heights_without_a_safety_harness"
  }
}
```

## 证据要求

- embeddingTool 必须使用精确 event_type `working_at_heights_without_a_safety_harness`。
- 工具调用必须成功返回明确的‘是’或‘否’，并包含判定阈值 threshold。
- 工具失败、event_type 不一致或缺少检测结果时不得接受答案。

## 资源

- `scripts/*.py` 保存人工或自动生成的实际执行脚本。
- `references/skill.json` 保存机器可读的 Skill 索引。
- `references/workflows/*.json` 保存可检索工作流契约。
- 修改脚本前阅读项目级 `docs/spatialskillgrowth-skill-authoring.md`。

## 已验证工作流

当前运行尚无通过验证的工作流。
