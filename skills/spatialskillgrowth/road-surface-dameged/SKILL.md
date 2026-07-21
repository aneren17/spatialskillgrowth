---
name: road-surface-dameged
description: "检测输入视频或图像中是否发生“路面破损”异常事件。"
---

# 路面破损

## Skill 作用

检测输入视频或图像中是否发生“路面破损”异常事件。

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

### road_surface_dameged_image_baseline

- ID：`road_surface_dameged_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 road_surface_dameged 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/road_surface_dameged_96c9e72153f7.json`；`scripts/road_surface_dameged_96c9e72153f7.py`

### road_surface_dameged_detector

- ID：`road_surface_dameged_a073eff56c6a`
- 选择条件：检测输入图像中是否存在路面破损（road_surface_dameged）异常事件。该工作流首先使用 YOLO 工具以 0.3 的置信度阈值进行目标检测，随后结合多模态大语言模型（MLLM）依据视觉证据进行最终判定。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他非路面破损类的异常事件检测
- 执行边界：{"supported_media": ["image"], "event_type": "road_surface_dameged", "detection_method": "yolo_tool_with_mllm_verification", "yolo_threshold": 0.3}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/road_surface_dameged_a073eff56c6a.json`；`scripts/road_surface_dameged_a073eff56c6a.py`

### road_surface_dameged_detector

- ID：`road_surface_dameged_b399a8ddd311`
- 选择条件：基于YOLO目标检测、UniDepth深度估计及多模态大语言模型（MLLM）的联合推理工作流，用于在图像输入中检测路面破损异常。该流程首先利用YOLO以0.3阈值识别潜在破损区域，随后通过UniDepth获取空间深度信息，最后由MLLM综合视觉特征与深度证据判定是否发生road_surface_dameged事件。
- 不选择：非图像类型的媒体输入; 需要调用embeddingTool的场景; 非road_surface_dameged类别的异常检测任务; 缺乏YOLO检测目标或无法进行深度估计的图像场景
- 执行边界：仅支持静态图像输入下的road_surface_dameged事件检测，依赖yoloTool进行初步定位、unidepth进行深度辅助以及MLLM进行最终语义判断，不包含视频流处理或实时动态检测能力。
- 工具链：`yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/road_surface_dameged_b399a8ddd311.json`；`scripts/road_surface_dameged_b399a8ddd311.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
