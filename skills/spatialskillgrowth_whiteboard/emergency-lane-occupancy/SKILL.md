---
name: emergency-lane-occupancy
description: "检测输入视频或图像中是否发生“占用应急车道”异常事件（相关显示名称：占用应急车道、应急车道占用）；调用异常检测工具时，必须使用精确类别 ID `emergency_lane_occupancy`。"
---

# 占用应急车道

## 用途

检测输入视频或图像中是否发生“占用应急车道”异常事件（相关显示名称：占用应急车道、应急车道占用）；调用异常检测工具时，必须使用精确类别 ID `emergency_lane_occupancy`。

## 事件接口

- 精确 `event_type`：`emergency_lane_occupancy`
- 主检测工具：`embeddingTool`
- 答案类型：`bool`，输出“是”或“否”
- 结构化结果：必须包含 `is_anomaly` 和 `threshold`

## 各端显示名称

| 来源 | 中文显示名称 |
|---|---|
| 大屏端 | 占用应急车道 |
| RAG 检索/检测端 | 应急车道占用 |
| 实时视频流检测页 | 应急车道占用 |

## 工具调用模板

```json
{
  "tool_name": "embeddingTool",
  "args": {
    "file_path": "$media",
    "event_type": "emergency_lane_occupancy"
  }
}
```

## 证据要求

- embeddingTool 必须使用精确 event_type `emergency_lane_occupancy`。
- 工具调用必须成功返回明确的‘是’或‘否’，并包含判定阈值 threshold。
- 工具失败、event_type 不一致或缺少检测结果时不得接受答案。

## 资源

- 本 whiteboard 的 `scripts/` 只是空模板，不在这里编写人工脚本。
- `references/skill.json` 保存机器可读的 Skill 索引。
- 本 whiteboard 的 `references/workflows/` 保持为空。
- 人工工作请复制到 `skills/spatialskillgrowth/` 并阅读项目级编写说明。

## 已验证工作流

当前运行尚无通过验证的工作流。
