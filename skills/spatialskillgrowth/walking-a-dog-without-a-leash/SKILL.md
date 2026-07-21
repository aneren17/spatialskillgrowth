---
name: walking-a-dog-without-a-leash
description: "检测输入视频或图像中是否发生“遛狗未牵绳”异常事件。"
---

# 遛狗未牵绳

## Skill 作用

检测输入视频或图像中是否发生“遛狗未牵绳”异常事件。

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

### walking_a_dog_without_a_leash_detector

- ID：`walking_a_dog_without_a_leash_7bf76f25c40f`
- 选择条件：基于 YOLO 目标检测与多模态大模型（MLLM）的图像分析工作流，专门用于检测输入图像中是否存在‘遛狗未牵绳’的异常行为。该流程首先通过 YOLO 工具以 0.5 的置信度阈值识别图像中的关键主体（如人、狗、牵引绳等），随后利用 MLLM 结合视觉证据进行语义推理，判断是否满足‘人在遛狗’且‘未使用牵引绳’的条件。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 进行向量检索或嵌入生成的任务; 涉及其他类型异常事件（如打架、盗窃、火灾等）的检测需求; 需要修改或覆盖人工维护的 SKILL.md 与 scripts/*.py 文件的场景; 图像中主体模糊、遮挡严重导致无法明确判断人与狗关系及牵引绳状态的情况
- 执行边界：{"input_constraints": "仅接受静态图像输入，禁止使用 embeddingTool", "detection_scope": "严格限定于 event_type 为 'walking_a_dog_without_a_leash' 的场景，不泛化至其他遛狗相关行为（如牵绳遛狗、狗绳断裂等）或其他异常类别", "evidence_requirements": "必须包含 YOLO 检测到的实体边界框及 MLLM 基于视觉证据的逻辑判断结果", "output_format": "最终判断结果仅限‘是’或‘否’"}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/walking_a_dog_without_a_leash_7bf76f25c40f.json`；`scripts/walking_a_dog_without_a_leash_7bf76f25c40f.py`

### walking_a_dog_without_a_leash_image_baseline

- ID：`walking_a_dog_without_a_leash_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 walking_a_dog_without_a_leash 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/walking_a_dog_without_a_leash_96c9e72153f7.json`；`scripts/walking_a_dog_without_a_leash_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
