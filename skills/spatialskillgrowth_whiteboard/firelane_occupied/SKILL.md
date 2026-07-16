---
name: firelane_occupied
description: "检测输入视频或图像中是否发生“占用消防通道”异常事件（相关显示名称：占用消防通道、消防通道占用）；调用异常检测工具时，必须使用精确类别 ID `firelane_occupied`。"
---

# 占用消防通道

## 用途

检测输入视频或图像中是否发生“占用消防通道”异常事件（相关显示名称：占用消防通道、消防通道占用）；调用异常检测工具时，必须使用精确类别 ID `firelane_occupied`。

## 事件接口

- 精确 `event_type`：`firelane_occupied`
- 主检测工具：`embeddingTool`
- 答案类型：`bool`，输出“是”或“否”
- 结构化结果：必须包含 `is_anomaly` 和 `threshold`

## 各端显示名称

| 来源 | 中文显示名称 |
|---|---|
| 大屏端 | 占用消防通道 |
| RAG 检索/检测端 | 消防通道占用 |

## 工具调用模板

```json
{
  "tool_name": "embeddingTool",
  "args": {
    "file_path": "$image",
    "event_type": "firelane_occupied"
  }
}
```

## 证据要求

- embeddingTool 必须使用精确 event_type `firelane_occupied`。
- 工具调用必须成功返回明确的‘是’或‘否’，并包含判定阈值 threshold。
- 工具失败、event_type 不一致或缺少检测结果时不得接受答案。

## 资源

- `workflows/*.json` 保存可检索的工作流定义。
- `scripts/*.py` 保存实际执行的 Python Skill，函数参数暴露运行时槽位。

## 已验证工作流

当前运行尚无通过验证的工作流。
