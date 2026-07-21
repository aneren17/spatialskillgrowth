---
name: license-plate-is-not-standard
description: "检测输入视频或图像中是否发生“车牌不规范”异常事件。"
---

# 车牌不规范

## Skill 作用

检测输入视频或图像中是否发生“车牌不规范”异常事件。

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

### license_plate_is_not_standard_detector

- ID：`license_plate_is_not_standard_5e16b30de642`
- 选择条件：针对图像输入，通过光学字符识别提取可见文字，并结合多模态大模型视觉分析，检测车牌是否存在不规范异常事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 license_plate_is_not_standard 类别的其他异常检测任务
- 执行边界：严格限定于 event_type 为 license_plate_is_not_standard 且 media_type 为 image 的场景，依赖 paddleOcrTool 提取文字证据及 MLLM 进行最终视觉判定。
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/license_plate_is_not_standard_5e16b30de642.json`；`scripts/license_plate_is_not_standard_5e16b30de642.py`

### license_plate_is_not_standard

- ID：`license_plate_is_not_standard_bbef2b8a62b4`
- 选择条件：检测输入图像中车辆车牌是否存在不规范情况（如模糊、遮挡、污损、角度严重倾斜或字符缺失等），依据视觉证据判断是否构成 license_plate_is_not_standard 异常事件。
- 不选择：非图像类型的媒体输入; 图像中未包含车辆或车牌区域; 需要调用 embeddingTool 进行特征提取的场景; 涉及其他类型异常（如违章停车、超速等）的检测任务
- 执行边界：{"event_type": "license_plate_is_not_standard", "media_type": "image", "required_tools": ["MLLM"], "forbidden_tools": ["embeddingTool"], "evidence_requirement": "必须基于图像中的视觉特征（如车牌清晰度、完整性、规范性）提供判断依据", "output_format": "是/否"}
- 工具链：`MLLM`
- 资源：`references/workflows/license_plate_is_not_standard_bbef2b8a62b4.json`；`scripts/license_plate_is_not_standard_bbef2b8a62b4.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
