---
name: without-wearing-a-helmet
description: "检测输入视频或图像中是否发生“未戴安全帽”异常事件。"
---

# 未戴安全帽

## Skill 作用

检测输入视频或图像中是否发生“未戴安全帽”异常事件。

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

### without_wearing_a_helmet_detector

- ID：`without_wearing_a_helmet_96c9e72153f7`
- 选择条件：检测输入图像中是否存在人员未佩戴安全帽的异常事件。通过多模态大语言模型分析图像视觉特征，识别目标人物头部区域是否缺失标准安全防护装备，从而判定是否发生 'without_wearing_a_helmet' 事件。仅处理静态图像或视频单帧，不处理原始视频时序。
- 不选择：非图像类型的媒体输入; 图像中未包含任何人员主体; 图像质量严重受损导致无法清晰辨识头部区域或佩戴状态; 非安全帽类其他头部装饰或防护具的检测（仅限标准安全帽）; 不处理原始视频时序，只依据当前图片证据。
- 执行边界：仅针对 'without_wearing_a_helmet' 这一特定异常类型进行二分类判断（是/否），不扩展至其他类型的安全违规检测，也不提供安全帽佩戴规范性（如系带是否扣好）的细粒度评估。必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/without_wearing_a_helmet_96c9e72153f7.json`；`scripts/without_wearing_a_helmet_96c9e72153f7.py`

### without_wearing_a_helmet_detector

- ID：`without_wearing_a_helmet_fe2744c48473`
- 选择条件：检测输入图像中是否存在人员未佩戴安全帽的异常事件。工作流首先通过目标检测工具定位可见的人头区域，随后利用多模态大语言模型结合视觉证据，判断该人员是否未佩戴符合安全规范的头盔。
- 不选择：输入媒体类型非图像（如视频流、音频或纯文本）；图像中未检测到任何可见的人头目标或人头区域被严重遮挡导致无法辨识头部特征；人员佩戴了非标准防护装备但视觉上符合头盔形态（需依赖模型对‘安全帽’定义的泛化理解）；涉及其他类型安全违规（如未穿反光衣、未系安全带等）的检测任务；需要调用 embeddingTool 进行语义嵌入的场景。
- 执行边界：{"event_type": "without_wearing_a_helmet", "media_type": "image", "required_evidence": ["paddleHeadDetTool 检测到的人头边界框坐标及置信度", "MLLM 基于人头区域图像内容对佩戴状态的语义判断"], "tool_constraints": ["禁止对图像输入调用 embeddingTool", "必须依赖 paddleHeadDetTool 的输出作为 MLLM 的视觉证据来源"], "output_format": "binary_yes_no"}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/without_wearing_a_helmet_fe2744c48473.json`；`scripts/without_wearing_a_helmet_fe2744c48473.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
