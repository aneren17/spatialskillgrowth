---
name: track-obstacle
description: "检测输入视频或图像中是否发生“轨道异物”异常事件。"
---

# 轨道异物

## Skill 作用

检测输入视频或图像中是否发生“轨道异物”异常事件。

## 工作流选择

- 探索阶段只处理图片，所有 Skill 工作流禁止调用 `embeddingTool`。
- 图片及视频抽样帧使用同一套 MLLM 或图像工具工作流形成明确的“是/否”判断。
- 冻结视频推理并行执行原视频 `embeddingTool` 和所有检索工作流。
- 汇总使用确定性 OR：任一有效通道判断为“是”，最终结果即为“是”。
- 工作流生命周期只累计图片探索的总指标，不维护跨媒体资格和分媒体指标。
- 先检查候选工作流的适用范围、排除条件和能力边界。
- 再结合当前输入图像或视频抽样帧，判断其工具链是否适合当前输入。
- 历史准确率、证据通过率和调用成本只用于适用性相近时的排序。
- 不要仅根据工作流名称、ID 或工具数量选择工作流。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

根据当前输入选择下列工作流；详细参数按需读取对应资源。

### track_obstacle_detector

- ID：`track_obstacle_87fbd3cbd1af`
- 选择条件：基于图像输入，利用 GroundingDINO 进行开放词汇目标检测，并结合多模态大语言模型（MLLM）分析视觉证据，以判定是否存在轨道异物异常事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 track_obstacle 类别的异常检测任务
- 执行边界：仅针对 event_type 为 track_obstacle 且 media_type 为 image 的场景有效；依赖 GroundingDINO 0.3 阈值检测结果作为 MLLM 判断的前置证据。
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/track_obstacle_87fbd3cbd1af.json`；`scripts/track_obstacle_87fbd3cbd1af.py`

### track_obstacle_image_baseline

- ID：`track_obstacle_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 track_obstacle 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/track_obstacle_96c9e72153f7.json`；`scripts/track_obstacle_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
