---
name: flag
description: "检测输入视频或图像中是否发生“旗帜检测”异常事件。"
---

# 旗帜检测

## Skill 作用

检测输入视频或图像中是否发生“旗帜检测”异常事件。

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

### flag_detection_workflow

- ID：`flag_96c9e72153f7`
- 选择条件：针对图像输入（包括单张图片或视频关键帧），利用多模态大模型（MLLM）分析视觉证据，以检测是否存在旗帜相关的异常事件。适用于需要确认画面中是否包含特定旗帜形态或异常旗帜展示的场景，输出最终的二值判断。
- 不选择：非图像类型的媒体输入（如纯文本、音频或未转为关键帧的原始视频流）; 需要调用 embeddingTool 进行向量检索或语义嵌入的场景; 涉及其他非旗帜类异常事件（如火灾、入侵等）的检测任务; 需要输出详细分类置信度、中间推理步骤或处理原始视频时序信息的场景
- 执行边界：输入媒体类型限制为图像（含视频关键帧）; 事件类型限定为旗帜异常; 必须依赖 MLLLM 工具; 禁止使用 embeddingTool; 输出格式为二值判断（是/否）; 依据来源为可见画面的视觉特征
- 工具链：`MLLM`
- 资源：`references/workflows/flag_96c9e72153f7.json`；`scripts/flag_96c9e72153f7.py`

### flag_detection_workflow

- ID：`flag_e92162514a45`
- 选择条件：本工作流用于检测输入图像中是否存在旗帜（flag）异常事件。流程首先使用 GroundingDINO 工具以 0.5 的开放词汇检测阈值识别图像中的旗帜目标，随后将检测到的视觉证据传递给多模态大语言模型（MLLM），由其依据图像内容判断是否发生旗帜异常事件。
- 不选择：禁止对图像输入调用 embeddingTool; 不适用于非图像类型的媒体输入; 不适用于非旗帜（flag）类别的异常检测任务
- 执行边界：{"event_type": "flag", "media_type": "image", "detection_threshold": 0.5, "required_tools": ["groundingdino", "MLLM"], "evidence_source": "visual_grounding_and_multimodal_analysis"}
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/flag_e92162514a45.json`；`scripts/flag_e92162514a45.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
