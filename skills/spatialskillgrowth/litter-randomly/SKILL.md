---
name: litter-randomly
description: "检测输入视频或图像中是否发生“随地乱扔垃圾”异常事件。"
---

# 随地乱扔垃圾

## Skill 作用

检测输入视频或图像中是否发生“随地乱扔垃圾”异常事件。

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

### litter_randomly_detector

- ID：`litter_randomly_96c9e72153f7`
- 选择条件：基于静态图像输入，利用多模态大语言模型（MLLM）分析视觉证据，检测是否存在‘随地乱扔垃圾’异常事件。专注于识别非指定丢弃点处的垃圾遗留行为，通过图像特征直接判断事件发生与否，不涉及文本嵌入或外部知识检索。
- 不选择：禁止使用 embeddingTool 处理图像输入；不适用于视频流、音频或纯文本输入，仅支持静态图像；不处理垃圾清理、分类、回收或放置在指定垃圾桶/合法堆放点的正常行为场景；不泛化至其他类型的公共秩序违规或异常事件（如打架、喧哗、火灾、入侵等）；不依赖人工标注的 benchmark 数据或奖励机制；不输出详细分类概率或中间推理步骤。
- 执行边界：事件类型限定为‘随地乱扔垃圾’；输入模态限定为静态图像；要求视觉图像中显示物体被随意丢弃在非垃圾收集设施处；输出格式为二元布尔判断（是/否）；工具约束为仅使用 MLLM 工具进行端到端视觉分析与判断，禁止使用 embeddingTool。
- 工具链：`MLLM`
- 资源：`references/workflows/litter_randomly_96c9e72153f7.json`；`scripts/litter_randomly_96c9e72153f7.py`

### litter_randomly_detector

- ID：`litter_randomly_f833911323f6`
- 选择条件：检测输入图像中是否发生‘随地乱扔垃圾’异常事件。工作流首先使用 YOLO 工具以 0.5 的置信度阈值识别潜在目标，随后结合多模态大语言模型（MLLM）分析视觉证据，综合判断是否存在该特定异常行为。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他类型的异常事件检测（仅限 litter_randomly）
- 执行边界：{"event_type": "litter_randomly", "media_type": "image", "detection_logic": "基于 YOLO 目标检测（阈值 0.5）与 MLLM 语义判断的联合推理", "output_format": "二元判断（是/否）"}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/litter_randomly_f833911323f6.json`；`scripts/litter_randomly_f833911323f6.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
