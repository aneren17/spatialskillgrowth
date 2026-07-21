---
name: banner
description: "检测输入视频或图像中是否发生“违规横幅检测”异常事件。"
---

# 违规横幅检测

## Skill 作用

检测输入视频或图像中是否发生“违规横幅检测”异常事件。

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

### banner_detection_workflow

- ID：`banner_97c96483c376`
- 选择条件：基于OCR文本提取与多模态视觉分析，检测图像中是否存在违规横幅。该工作流首先通过OCR工具读取图像中的可见文字，随后结合图像视觉特征与文本内容，由多模态大模型判断是否构成违规横幅异常。
- 不选择：非图像类型的媒体输入（如纯文本、音频、视频流）；需要调用embeddingTool进行语义嵌入的场景；非违规横幅类别的其他异常检测任务（如水印、Logo侵权等）；图像中无可见文字且视觉特征不足以支撑横幅判断的模糊场景。
- 执行边界：{"input_media_type": "image", "required_evidence": ["OCR提取的可见文字内容", "图像整体视觉布局与横幅形态特征"], "tool_constraints": ["禁止使用embeddingTool", "必须使用paddleOcrTool进行文字读取", "必须使用MLLM进行最终异常判定"], "event_type": "banner", "output_format": "binary_yes_no"}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/banner_97c96483c376.json`；`scripts/banner_97c96483c376.py`

### banner_detection_workflow

- ID：`banner_f043712d5540`
- 选择条件：基于视觉证据的违规横幅检测工作流。通过 PaddleOCR 提取图像中的可见文字，结合 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，最后由多模态大模型综合文字与视觉定位证据，判断是否存在 banner 类型的异常事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 banner 类别的异常检测任务; 不包含可见文字或横幅实体的纯背景图像
- 执行边界：{"event_type": "banner", "media_type": "image", "required_evidence": ["paddleOcrTool 输出的可见文字内容", "groundingdino 输出的目标检测结果（阈值 0.3）"], "decision_model": "MLLM", "output_format": "binary (是/否)", "constraint": "仅基于提供的视觉与文本证据判断是否存在违规横幅，不泛化至其他异常类别"}
- 工具链：`paddleOcrTool -> groundingdino -> MLLM`
- 资源：`references/workflows/banner_f043712d5540.json`；`scripts/banner_f043712d5540.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
