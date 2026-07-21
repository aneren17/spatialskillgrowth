---
name: instrument-operation
description: "检测输入视频或图像中是否发生“是否操作仪器”异常事件。"
---

# 是否操作仪器

## Skill 作用

检测输入视频或图像中是否发生“是否操作仪器”异常事件。

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

### instrument_operation_detector

- ID：`instrument_operation_1bd3fad70aa2`
- 选择条件：检测输入图像中是否发生“是否操作仪器”异常事件。该工作流首先利用 paddleHeadDetTool 检测可见人头以提供上下文证据，随后通过多模态大语言模型（MLLM）结合图像内容判断是否存在仪器操作行为。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 不包含可见人头或无法通过视觉证据判断仪器操作状态的模糊场景
- 执行边界：{"required_slots": {"event_type": "instrument_operation", "media_type": "image"}, "tool_constraints": ["必须使用 paddleHeadDetTool 进行人头检测", "必须使用 MLLM 进行最终判断", "禁止使用 embeddingTool"], "output_format": "仅返回“是”或“否”"}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/instrument_operation_1bd3fad70aa2.json`；`scripts/instrument_operation_1bd3fad70aa2.py`

### instrument_operation_detector

- ID：`instrument_operation_884b9b12288c`
- 选择条件：基于视觉证据检测图像中是否发生仪器操作异常事件。工作流通过 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，利用 Python 代码沙箱计算结构化证据摘要，最终由多模态大语言模型（MLLM）综合视觉证据判断是否存在仪器操作行为。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 instrument_operation 类别的异常检测任务; 需要重新分类或改写事件类别的场景
- 执行边界：{"event_type": "instrument_operation", "media_type": "image", "detection_method": "groundingdino_with_0.3_threshold", "evidence_processing": "python_code_sandbox_structured_summary", "decision_maker": "mllm_visual_evidence_based", "output_format": "binary_yes_no"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/instrument_operation_884b9b12288c.json`；`scripts/instrument_operation_884b9b12288c.py`

### instrument_operation_detector

- ID：`instrument_operation_f06dd7f53eb7`
- 选择条件：基于多模态大语言模型（MLLM）分析输入图像，检测是否存在针对仪器的操作行为。通过视觉证据判断是否发生仪器操作异常事件，输出二元判断结果。
- 不选择：非图像类型的媒体输入; 涉及非仪器对象的操作场景; 需要调用 embeddingTool 的文本或向量嵌入任务; 不处理原始视频时序，仅依据当前图片证据
- 执行边界：supported_event_type: instrument_operation; supported_media_type: image; required_evidence: 图像中可见的仪器操作行为视觉特征; output_format: 布尔值（是/否）; tool_dependency: MLLM
- 工具链：`MLLM`
- 资源：`references/workflows/instrument_operation_f06dd7f53eb7.json`；`scripts/instrument_operation_f06dd7f53eb7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
