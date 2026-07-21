---
name: fall
description: "检测输入视频或图像中是否发生“人员摔倒”异常事件。"
---

# 人员摔倒

## Skill 作用

检测输入视频或图像中是否发生“人员摔倒”异常事件。

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

### fall_detection_workflow

- ID：`fall_68edd8ec2f06`
- 选择条件：基于多模态视觉证据的静态图像人员摔倒检测工作流。该流程通过 GroundingDINO 进行开放词汇目标定位，结合 YOLO 进行高精度目标检测，并利用 UniDepth 估计目标深度信息，最终由多模态大语言模型综合几何与空间证据判断是否发生摔倒事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）。; 场景中不存在人类主体的情况。; 图像质量严重受损导致无法提取有效视觉特征（如极度模糊、过曝或完全遮挡）。; 需要时间序列分析才能判定的动态跌倒过程（本工作流仅适用于单帧静态图像分析）。
- 执行边界：{"supported_event_type": "fall", "supported_media_type": "image", "evidence_requirements": ["必须包含由 groundingdino 和 yolotool 提供的人体目标边界框。", "必须包含由 unidepth 提供的目标深度估计数据以辅助姿态判断。", "最终判定依赖于 MLLM 对上述视觉证据的综合推理。"], "limitations": "仅能检测单帧图像中呈现的摔倒姿态，无法区分摔倒的具体原因或后续状态，且依赖于检测工具对人体目标的准确识别。"}
- 工具链：`groundingdino -> yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/fall_68edd8ec2f06.json`；`scripts/fall_68edd8ec2f06.py`

### fall_image_baseline

- ID：`fall_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 fall 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/fall_96c9e72153f7.json`；`scripts/fall_96c9e72153f7.py`

### fall_detection_image

- ID：`fall_c6c5bc199599`
- 选择条件：基于单张静态图像输入，利用开放词汇目标检测（GroundingDINO）定位人员，结合深度估计（UniDepth）获取空间信息，并通过多模态大语言模型（MLLM）综合视觉证据判定是否发生人员摔倒（fall）异常事件。
- 不选择：视频流、连续帧序列或实时流媒体输入（仅支持单张静态图像）; 非视觉模态输入（如纯文本、音频）; 非人员主体的摔倒检测（如物体倾倒、动物跌倒）; 需要调用 embeddingTool 或纯文本语义分析的场景; 非 'fall' 类别的异常事件（如打架、奔跑等）。
- 执行边界：{"event_type": "fall", "media_type": "image", "subject_constraint": "人员", "evidence_requirements": ["通过 groundingdino 检测到的人员目标（建议置信度阈值 >= 0.3）", "需包含 unidepth 生成的深度信息以辅助空间姿态判断", "最终判定由 MLLM 基于上述视觉证据执行"], "output_format": "binary (是/否)", "constraints": ["严格限定为人员摔倒事件", "禁止泛化为其他异常类型"]}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/fall_c6c5bc199599.json`；`scripts/fall_c6c5bc199599.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
