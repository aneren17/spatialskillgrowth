---
name: cold-flame
description: "检测输入视频或图像中是否发生“冷焰火检测”异常事件。"
---

# 冷焰火检测

## Skill 作用

检测输入视频或图像中是否发生“冷焰火检测”异常事件。

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

### cold_flame_detector

- ID：`cold_flame_8525e5d8e629`
- 选择条件：基于视觉证据检测图像中是否存在冷焰火（cold_flame）异常事件。工作流首先使用 GroundingDINO 以 0.3 的开放词汇检测阈值定位潜在目标，随后利用多模态大语言模型（MLLM）结合图像上下文进行最终判定。该流程专用于静态图像输入，旨在通过可复用的视觉证据链确认冷焰火的存在与否。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 的场景; 其他类型的火焰或燃烧事件（非冷焰火类别）; 动态实时流媒体检测场景
- 执行边界：{"input_media": "image", "event_type": "cold_flame", "detection_threshold": 0.3, "evidence_chain": ["groundingdino_object_localization", "mllm_contextual_reasoning"], "output_format": "binary_yes_no"}
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/cold_flame_8525e5d8e629.json`；`scripts/cold_flame_8525e5d8e629.py`

### cold_flame_detector

- ID：`cold_flame_874ea29c1e51`
- 选择条件：基于单张静态图像输入，利用多模态大模型（MLLM）分析视觉特征（如微弱光点、无明火特征等），检测是否存在冷焰火（cold_flame）异常事件，并输出二分类判断结果。
- 不选择：禁止使用 embeddingTool 处理图像输入；不适用于视频流、音频或纯文本描述；不适用于其他类型的火焰异常（如明火、爆炸火焰）或非冷焰火相关视觉异常；若图像质量严重受损导致无法识别基本视觉特征，则不适用；不包含对异常事件的原因分析、修复建议或历史趋势评估。
- 执行边界：{"input_modality": "image", "event_type": "cold_flame", "evidence_source": "visual_features_via_mllm", "output_format": "binary_classification", "tool_constraints": "仅允许使用 MLLM 工具进行图像分析和判断，不得引入外部知识库或额外推理步骤。"}
- 工具链：`MLLM`
- 资源：`references/workflows/cold_flame_874ea29c1e51.json`；`scripts/cold_flame_874ea29c1e51.py`

### cold_flame_image_baseline

- ID：`cold_flame_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 cold_flame 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/cold_flame_96c9e72153f7.json`；`scripts/cold_flame_96c9e72153f7.py`

### cold_flame_detector

- ID：`cold_flame_f6f8ce21d2a1`
- 选择条件：针对图像输入，通过开放词汇检测定位潜在目标，结合深度估计分析空间结构，并利用多模态大模型综合视觉证据，判断是否存在冷焰火（cold_flame）异常事件。
- 不选择：非图像类型的媒体输入（如视频、音频、纯文本）。; 需要调用 embeddingTool 进行语义嵌入处理的场景。; 其他非 cold_flame 类别的异常事件检测。; 无法提供清晰视觉特征以支持深度估计或目标定位的极度模糊或遮挡图像。
- 执行边界：{"input_media_type": "image", "target_event_type": "cold_flame", "detection_logic": "基于 groundingdino 目标定位与 unidepth 深度信息，由 MLLM 进行最终异常判定", "output_format": "binary_yes_no"}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/cold_flame_f6f8ce21d2a1.json`；`scripts/cold_flame_f6f8ce21d2a1.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
