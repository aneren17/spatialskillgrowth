---
name: without-wearing-a-mask
description: "检测输入视频或图像中是否发生“未戴口罩”异常事件。"
---

# 未戴口罩

## Skill 作用

检测输入视频或图像中是否发生“未戴口罩”异常事件。

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

### without_wearing_a_mask

- ID：`without_wearing_a_mask_69c595d96158`
- 选择条件：基于图像输入，通过检测可见人头并结合多模态视觉证据，判断场景中是否存在人员未佩戴口罩的异常事件。
- 不选择：非图像类型的媒体输入; 图像中未检测到可见人头的场景; 涉及面部遮挡物（如围巾、口罩）但非标准医用或防护口罩的模糊边界情况，需依赖多模态模型对视觉证据的明确判定
- 执行边界：{"event_type": "without_wearing_a_mask", "media_type": "image", "required_evidence": ["通过 paddleHeadDetTool 检测到的可见人头区域", "多模态大语言模型（MLLM）基于人头区域视觉特征对是否佩戴口罩的判定结果"], "constraints": ["禁止使用 embeddingTool 处理图像输入", "最终输出必须为二值判断（是/否）", "检测范围仅限于工具图定义的可见人头区域，不泛化至全身或其他身体部位"]}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/without_wearing_a_mask_69c595d96158.json`；`scripts/without_wearing_a_mask_69c595d96158.py`

### without_wearing_a_mask_detector

- ID：`without_wearing_a_mask_96c9e72153f7`
- 选择条件：基于多模态大语言模型（MLLM）分析输入图像，检测是否存在人员未佩戴口罩的异常行为。适用于需要验证合规性口罩佩戴情况的静态图像场景。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）；图像中未包含清晰可见的人脸区域，或人脸被严重遮挡、模糊导致无法识别面部特征；需要实时流式处理或动态行为分析的场景；涉及其他类型异常事件（如未穿安全帽、违规操作等）的检测任务。
- 执行边界：仅支持单帧图像分析，不支持跨帧时序推理；检测精度依赖于图像中面部的清晰度和分辨率；不包含对口罩佩戴规范性（如是否遮住口鼻）的细粒度合规性评分，仅判断是否佩戴；必须取得MLLM基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/without_wearing_a_mask_96c9e72153f7.json`；`scripts/without_wearing_a_mask_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
