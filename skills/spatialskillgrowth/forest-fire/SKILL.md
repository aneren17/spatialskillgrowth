---
name: forest-fire
description: "检测输入视频或图像中是否发生“森林火灾”异常事件。"
---

# 森林火灾

## Skill 作用

检测输入视频或图像中是否发生“森林火灾”异常事件。

## 工作流选择

- 探索阶段只处理图片；`embeddingTool` 可按图片工具参与，但图片基线仍为单步 MLLM。
- 图片及视频抽样帧使用同一套图片工作流，可组合 embeddingTool、MLLM 或其他图像工具。
- 冻结视频推理默认根据本 `SKILL.md` 和当前抽样帧选择 Top-K（默认 2 条）工作流。
- 推理并行执行原视频 `embeddingTool` 和选中的图片工作流；全工作流模式执行全部结构合格路线。
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

### forest_fire_detector

- ID：`forest_fire_2c91fe8e39d2`
- 选择条件：基于单张输入图像（或视频的关键帧），利用多模态大语言模型（MLLM）分析视觉特征，检测是否存在森林火灾异常事件。专注于通过图像证据识别火灾相关的视觉信号（如烟雾、明火、焦痕等），并输出二元判断结果。
- 不选择：不支持视频流、音频或非图像类型的媒体输入（仅支持单图或视频关键帧）。; 不执行火灾原因分析、火势蔓延预测或损失评估。; 不处理非森林环境（如城市建筑火灾、工业火灾）的检测，除非视觉特征与森林火灾高度相似且无其他上下文排除。; 禁止使用 embeddingTool 进行图像嵌入处理。
- 执行边界：{"event_type": "forest_fire", "media_type": "image", "required_evidence": "视觉证据（如烟雾、火焰、燃烧痕迹）", "output_format": "binary (是/否)"}
- 工具链：`MLLM`
- 资源：`references/workflows/forest_fire_2c91fe8e39d2.json`；`scripts/forest_fire_2c91fe8e39d2.py`

### forest_fire_detection

- ID：`forest_fire_a3655cdae210`
- 选择条件：基于图像输入检测森林火灾异常事件。工作流程利用 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，结合 UniDepth 估计目标深度信息，并通过 Python 代码沙箱计算结构化证据摘要，最终由多模态大语言模型综合视觉证据判断是否发生森林火灾。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他类型的异常事件检测（仅限 forest_fire）; 需要重新分类或改写事件类别的任务
- 执行边界：{"event_type": "forest_fire", "media_type": "image", "detection_threshold": 0.3, "required_evidence": ["groundingdino 检测结果", "unidepth 深度估计", "python_code_sandbox 结构化摘要"], "output_format": "binary_yes_no"}
- 工具链：`groundingdino -> python_code_sandbox -> unidepth -> MLLM`
- 资源：`references/workflows/forest_fire_a3655cdae210.json`；`scripts/forest_fire_a3655cdae210.py`

### forest_fire_detector

- ID：`forest_fire_c2d955795bcc`
- 选择条件：基于视觉证据的森林火灾异常检测工作流。该流程首先使用 GroundingDINO 以 0.3 的开放词汇检测阈值定位潜在火源或烟雾目标，随后通过代码沙箱计算结构化证据摘要，最后结合多模态大语言模型（MLLM）综合图像特征与量化证据，判定输入图像中是否发生森林火灾事件。
- 不选择：非图像类型的输入数据（如纯文本、音频或视频流），本工作流仅支持静态图像分析。; 需要调用 embeddingTool 进行特征提取的场景，本工作流严格禁止使用 embeddingTool。; 非森林火灾类别的异常检测任务，本工作流专用于 event_type 为 'forest_fire' 的场景，不泛化至其他火灾类型或自然灾害。; 要求输出概率分数、置信度区间或详细自然语言解释的场景，本工作流仅输出二分类结果（是/否）。
- 执行边界：{"input_media_type": "image", "target_event_type": "forest_fire", "detection_method": "visual_grounding_and_multimodal_reasoning", "evidence_requirements": "必须包含基于 GroundingDINO 的视觉定位证据及代码沙箱生成的结构化摘要", "output_format": "binary_classification_yes_no"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/forest_fire_c2d955795bcc.json`；`scripts/forest_fire_c2d955795bcc.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
