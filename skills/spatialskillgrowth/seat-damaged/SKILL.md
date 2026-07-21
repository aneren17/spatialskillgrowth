---
name: seat-damaged
description: "检测输入视频或图像中是否发生“座椅损坏”异常事件。"
---

# 座椅损坏

## Skill 作用

检测输入视频或图像中是否发生“座椅损坏”异常事件。

## 工作流选择

- 探索阶段只处理图片；`embeddingTool` 可按图片工具参与，但图片基线仍为单步 MLLM。
- 图片及视频抽样帧使用同一套图片工作流，可组合 embeddingTool、MLLM 或其他图像工具。
- 冻结视频推理并行执行原视频 `embeddingTool` 和所有检索工作流。
- 汇总使用确定性 OR：任一有效通道判断为“是”，最终结果即为“是”。
- 工作流生命周期只累计图片探索的总指标，不维护跨媒体资格和分媒体指标。
- 已有工作流的“不选择/执行边界”如写明不用 embedding，只约束该工作流的既有工具图，不是框架全局禁令。
- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前输入图像或视频抽样帧，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

根据当前输入选择下列工作流；详细参数按需读取对应资源。

### seat_damaged_detector

- ID：`seat_damaged_1f1305676bb6`
- 选择条件：基于图像输入，利用多模态大语言模型（MLLM）分析视觉证据，检测座椅结构、表面或功能部件是否存在物理损坏（如裂痕、断裂、变形、破损、撕裂、脱落、缺失等），并输出二元判断结果。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）；需要调用 embeddingTool 的特征提取任务；非座椅损坏类别的其他异常事件检测；座椅清洁度问题（如污渍、灰尘）；座椅位置偏移、未归位或配置错误等非损坏类异常；其他非座椅类物体（如桌子、地板）的损坏检测；需要返回详细损坏程度评分或具体维修建议的场景。
- 执行边界：严格限定于 event_type 为 'seat_damaged' 且 media_type 为 'image' 的场景。检测逻辑完全依赖 MLLM 对图像中座椅视觉特征的直接分析，不包含任何中间推理步骤、外部工具调用或向量检索，仅输出‘是’或‘否’的二元判断。
- 工具链：`MLLM`
- 资源：`references/workflows/seat_damaged_1f1305676bb6.json`；`scripts/seat_damaged_1f1305676bb6.py`

### seat_damaged_image_baseline

- ID：`seat_damaged_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 seat_damaged 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/seat_damaged_96c9e72153f7.json`；`scripts/seat_damaged_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
