---
name: working-at-heights-without-a-safety-harness
description: "检测输入视频或图像中是否发生“高空作业未系安全带”异常事件。"
---

# 高空作业未系安全带

## Skill 作用

检测输入视频或图像中是否发生“高空作业未系安全带”异常事件。

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

### working_at_heights_without_a_safety_harness_detector

- ID：`working_at_heights_without_a_safety_harness_0f06bc037ef7`
- 选择条件：基于YOLO目标检测、UniDepth深度估计及多模态大模型（MLLM）的视觉证据链，检测输入图像中是否存在人员处于高空作业状态但未佩戴安全带的异常事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用embeddingTool进行语义嵌入的场景; 非高空作业场景（如地面作业、室内低处作业）; 已正确佩戴安全带的高空作业场景; 无法通过YOLO检测出人员或安全装备的极端遮挡或模糊图像; 涉及其他类型异常事件（如火灾、入侵、设备故障等）的检测需求
- 执行边界：{"required_event_type": "working_at_heights_without_a_safety_harness", "required_media_type": "image", "detection_logic": "通过YOLO检测人员及潜在安全装备，结合UniDepth估算相对高度以确认‘高空’属性，最终由MLLM综合视觉证据判断是否缺失安全带", "abstractable_entities": "无（工具图中无通用物体槽位，检测器严格限定于‘人员’与‘安全带’相关视觉特征）", "output_format": "二元分类（是/否）"}
- 工具链：`yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/working_at_heights_without_a_safety_harness_0f06bc037ef7.json`；`scripts/working_at_heights_without_a_safety_harness_0f06bc037ef7.py`

### working_at_heights_without_a_safety_harness_detector

- ID：`working_at_heights_without_a_safety_harness_1c6421c5bcc9`
- 选择条件：本工作流专门用于检测静态图像中是否发生‘高空作业未系安全带’的特定安全违规事件。通过集成目标检测（YOLO）、人头检测（PaddleHeadDet）、深度估计（UniDepth）及多模态大模型（MLLM），系统定位作业区域与人员，利用深度信息辅助判断作业高度，最终由多模态模型综合分析人员是否处于高空作业状态且未佩戴安全带。该流程严格针对已定义的 event_type，不泛化至其他类型的安全违规。
- 不选择：不适用于视频流、音频或纯文本输入，仅支持静态图像；不适用于非高空作业场景（如地面作业、室内低处活动）的安全带检测，必须结合深度估计判断高度；不适用于检测其他类型的安全违规（如未戴安全帽、火灾、入侵等）；不适用于图像质量极低、严重遮挡或无法清晰辨识人员与安全带状态的输入；不包含对作业环境合规性的全面评估，仅聚焦于人员安全带佩戴状态与高空作业关联性。
- 执行边界：支持清晰可见作业人员与潜在安全带特征的静态图像，以及包含足够深度线索以判断作业高度的图像。所需证据包括：YOLO检测到的相关作业对象或环境特征、PaddleHeadDet定位的人头位置、UniDepth估算的深度信息、以及MLLM基于上述视觉证据对‘未系安全带’状态的语义判断。局限性包括：依赖前置检测工具输出质量，目标检测失败或深度估计偏差大可能导致误判；无法区分安全带类型（如全身式 vs 半身式），仅判断是否存在有效佩戴；对‘高空’的定义依赖深度估计的相对高度判断，无绝对高度阈值；不处理动态行为分析，仅基于单帧图像进行静态快照判断；无法检测非视觉可辨或隐蔽式安全带。
- 工具链：`yoloTool -> paddleHeadDetTool -> unidepth -> MLLM`
- 资源：`references/workflows/working_at_heights_without_a_safety_harness_1c6421c5bcc9.json`；`scripts/working_at_heights_without_a_safety_harness_1c6421c5bcc9.py`

### working_at_heights_without_a_safety_harness_image_baseline

- ID：`working_at_heights_without_a_safety_harness_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 working_at_heights_without_a_safety_harness 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/working_at_heights_without_a_safety_harness_96c9e72153f7.json`；`scripts/working_at_heights_without_a_safety_harness_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
