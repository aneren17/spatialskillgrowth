---
name: guardrail-damaged
description: "检测输入视频或图像中是否发生“护栏损坏”异常事件。"
---

# 护栏损坏

## Skill 作用

检测输入视频或图像中是否发生“护栏损坏”异常事件。

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

### guardrail_damaged_detector

- ID：`guardrail_damaged_74b0c3f20721`
- 选择条件：基于 YOLO 目标检测（阈值 0.5）与多模态大模型推理，针对输入图像中护栏结构完整性进行异常检测，识别护栏损坏事件。
- 不选择：非图像类型的媒体输入; 护栏缺失但非损坏的情况; 其他非护栏类基础设施的损坏事件; 需要调用 embeddingTool 的场景
- 执行边界：{"event_type": "guardrail_damaged", "media_type": "image", "required_evidence": ["yoloTool 检测结果（阈值 0.5）", "MLLM 基于视觉证据的损坏判定"], "output_format": "binary_yes_no"}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/guardrail_damaged_74b0c3f20721.json`；`scripts/guardrail_damaged_74b0c3f20721.py`

### guardrail_damaged_detector

- ID：`guardrail_damaged_96c9e72153f7`
- 选择条件：基于图像输入，利用多模态大语言模型（MLLM）分析视觉证据，检测护栏是否存在物理完整性受损（如断裂、变形、缺失），并输出二值化判断结果。
- 不选择：非图像类型的媒体输入（如纯文本、音频、视频流）；需要调用 embeddingTool 进行特征提取的场景；涉及其他类型异常事件（如入侵、火灾、设备故障、护栏缺失、遮挡、颜色异常等）的检测任务；需要输出详细损坏程度评分、具体损坏位置坐标、修复建议或实时动态分析的场景；护栏外观脏污、褪色但未发生结构性损坏的情况；图像中未包含护栏或类似防护结构设施的通用场景。
- 执行边界：支持事件类型：guardrail_damaged；支持媒体类型：image；证据要求：视觉证据需明确显示护栏结构存在物理性损坏（如断裂、严重变形、部件缺失）；输出格式：布尔值（是/否）；工具依赖：仅依赖 MLLM 进行端到端的视觉分析与判断，不依赖其他中间处理工具，禁止使用 embeddingTool。
- 工具链：`MLLM`
- 资源：`references/workflows/guardrail_damaged_96c9e72153f7.json`；`scripts/guardrail_damaged_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
