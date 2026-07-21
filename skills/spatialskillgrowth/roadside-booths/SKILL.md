---
name: roadside-booths
description: "检测输入视频或图像中是否发生“占道经营”异常事件。"
---

# 占道经营

## Skill 作用

检测输入视频或图像中是否发生“占道经营”异常事件。

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

### roadside_booths_detector

- ID：`roadside_booths_45718f0e4667`
- 选择条件：基于图像输入，通过 OCR 文本识别与目标检测（YOLO）收集视觉证据，利用多模态大模型判断是否存在占道经营（roadside_booths）异常事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他非 roadside_booths 类别的异常事件检测; 未包含可见文字或特定目标结构的纯背景图像
- 执行边界：{"required_tools": ["paddleOcrTool", "yoloTool", "MLLM"], "evidence_requirements": ["通过 paddleOcrTool 获取图像中的可见文字信息", "通过 yoloTool 以 0.5 阈值检测相关目标物体", "结合上述视觉证据由 MLLM 进行综合逻辑判断"], "output_format": "布尔值（是/否）", "constraints": "严格限定于 roadside_booths 事件类型，不泛化至其他占道或经营类异常"}
- 工具链：`paddleOcrTool -> yoloTool -> MLLM`
- 资源：`references/workflows/roadside_booths_45718f0e4667.json`；`scripts/roadside_booths_45718f0e4667.py`

### roadside_booths_image_baseline

- ID：`roadside_booths_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 roadside_booths 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/roadside_booths_96c9e72153f7.json`；`scripts/roadside_booths_96c9e72153f7.py`

### roadside_booths_detector

- ID：`roadside_booths_ce5a642d2219`
- 选择条件：基于多模态视觉证据检测图像中是否存在占道经营（roadside_booths）异常事件。通过目标检测识别潜在摊位结构，利用深度估计分析其空间位置关系，并结合OCR提取的文字信息，综合判断是否构成占道经营。
- 不选择：非图像类型的输入数据; 需要调用embeddingTool的场景; 非roadside_booths类别的其他异常事件检测; 缺乏可见文字或目标结构导致无法获取必要视觉证据的场景
- 执行边界：仅适用于静态图像输入，依赖yoloTool进行目标检测（阈值0.5）、unidepth进行深度估计以及paddleOcrTool进行文字识别，最终由多模态大模型依据上述视觉证据判断是否存在占道经营行为。
- 工具链：`paddleOcrTool -> yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/roadside_booths_ce5a642d2219.json`；`scripts/roadside_booths_ce5a642d2219.py`

### roadside_booths_detector

- ID：`roadside_booths_dedd1e22d850`
- 选择条件：针对静态图像输入，检测是否存在占道经营（roadside_booths）异常事件。工作流利用光学字符识别（OCR）工具提取图像中的可见文字信息，随后结合多模态大语言模型（MLLM）综合视觉特征与文字证据，判定是否发生占道经营行为。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本）；需要调用 embeddingTool 进行语义嵌入的场景；非占道经营类别的其他异常事件检测（如交通事故、违停等）；图像中缺乏足够视觉细节或文字信息，导致无法通过 MLLM 进行有效推理的情况。
- 执行边界：{"input_media_type": "image", "event_type": "roadside_booths", "required_evidence": ["通过 paddleOcrTool 提取的图像内可见文字内容", "通过 MLLM 对图像视觉特征及文字证据的综合分析结果"], "output_format": "binary_classification", "allowed_tools": ["paddleOcrTool", "MLLM"], "prohibited_tools": ["embeddingTool"]}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/roadside_booths_dedd1e22d850.json`；`scripts/roadside_booths_dedd1e22d850.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
