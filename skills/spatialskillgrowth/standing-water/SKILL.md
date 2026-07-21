---
name: standing-water
description: "检测输入视频或图像中是否发生“积水检测”异常事件。"
---

# 积水检测

## Skill 作用

检测输入视频或图像中是否发生“积水检测”异常事件。

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

### standing_water_detector

- ID：`standing_water_2eed20ca5774`
- 选择条件：基于多模态视觉证据检测图像中是否存在积水异常。工作流首先利用开放词汇检测模型定位潜在积水区域，随后通过深度估计分析其空间形态，最终由多模态大模型综合视觉特征判定是否构成积水事件。
- 不选择：非图像类型的媒体输入；需要语义嵌入处理的场景；非积水类别的异常检测任务；缺乏明确视觉边界的模糊积水疑似区域；未提供原始图像数据的请求
- 执行边界：仅针对 event_type 为 standing_water 的图像输入进行异常判定；必须使用 groundingdino 进行初始检测，unidepth 进行深度估计，MLLM 进行最终推理；禁止使用 embeddingTool；最终输出仅为二元判断（是/否）
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/standing_water_2eed20ca5774.json`；`scripts/standing_water_2eed20ca5774.py`

### standing_water_image_baseline

- ID：`standing_water_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 standing_water 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/standing_water_96c9e72153f7.json`；`scripts/standing_water_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
