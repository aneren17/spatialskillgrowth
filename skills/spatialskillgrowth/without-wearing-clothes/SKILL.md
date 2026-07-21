---
name: without-wearing-clothes
description: "检测输入视频或图像中是否发生“未穿防护服”异常事件。"
---

# 未穿防护服

## Skill 作用

检测输入视频或图像中是否发生“未穿防护服”异常事件。

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

### without_wearing_clothes

- ID：`without_wearing_clothes_198c1989b348`
- 选择条件：基于静态图像输入，利用多模态大模型（MLLM）分析视觉特征，检测场景中人员是否完全未穿着规定防护服（如防尘服、无菌服等），并输出二分类判断结果。
- 不选择：非图像类型的媒体输入（如视频流、音频）；需要调用 embeddingTool 的场景；防护服穿戴不规范（如穿戴错误但已穿戴）的情况；模糊不清导致无法辨识衣着状态的图像；其他类型的异常检测任务（如未戴安全帽等）。
- 执行边界：仅支持对静态图像进行视觉分析，通过多模态模型识别衣着特征以判定是否违反防护服穿戴规范（完全未穿戴），不生成中间嵌入向量，不执行代码脚本，不进行人工规则硬编码匹配，不处理事件重分类或类别改写。
- 工具链：`MLLM`
- 资源：`references/workflows/without_wearing_clothes_198c1989b348.json`；`scripts/without_wearing_clothes_198c1989b348.py`

### without_wearing_clothes_detector

- ID：`without_wearing_clothes_74b0c3f20721`
- 选择条件：针对输入图像执行未穿防护服异常检测。工作流首先利用 YOLO 工具以 0.5 的置信度阈值提取视觉特征，随后结合多模态大语言模型分析图像证据，最终判定是否存在未穿防护服行为。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本）; 需要调用 embeddingTool 进行向量检索的场景; 其他类型的异常事件检测（仅限 without_wearing_clothes 类别）
- 执行边界：仅支持静态图像输入；依赖 YOLO 工具（阈值固定为 0.5）进行初步特征提取，并由 MLLM 进行最终语义判断；输出结果严格限制为二元判定（是/否）
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/without_wearing_clothes_74b0c3f20721.json`；`scripts/without_wearing_clothes_74b0c3f20721.py`

### without_wearing_clothes_image_baseline

- ID：`without_wearing_clothes_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 without_wearing_clothes 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/without_wearing_clothes_96c9e72153f7.json`；`scripts/without_wearing_clothes_96c9e72153f7.py`

### without_wearing_clothes_detector

- ID：`without_wearing_clothes_d3df6fb17d3e`
- 选择条件：检测输入图像中是否存在人员未穿防护服的异常事件。工作流首先通过 paddleHeadDetTool 定位可见人头，随后利用多模态大语言模型（MLLM）结合视觉证据判断该区域是否满足未穿防护服的特征条件。
- 不选择：非图像类型的媒体输入; 图像中未检测到可见人头的场景; 需要调用 embeddingTool 的场景; 非 without_wearing_clothes 类别的异常检测任务
- 执行边界：{"input_media": "image", "event_type": "without_wearing_clothes", "required_evidence": ["paddleHeadDetTool 检测到的人头边界框", "MLLM 基于人头区域视觉特征对防护服穿戴状态的判定"], "constraints": ["禁止使用 embeddingTool", "必须依赖工具图定义的步骤顺序执行", "仅针对已确定的 without_wearing_clothes 类别进行二元判断"]}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/without_wearing_clothes_d3df6fb17d3e.json`；`scripts/without_wearing_clothes_d3df6fb17d3e.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
