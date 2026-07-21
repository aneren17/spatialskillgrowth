---
name: kitchen-infested-with-rats
description: "检测输入视频或图像中是否发生“厨房出现老鼠”异常事件。"
---

# 厨房出现老鼠

## Skill 作用

检测输入视频或图像中是否发生“厨房出现老鼠”异常事件。

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

### kitchen_infested_with_rats

- ID：`kitchen_infested_with_rats_14a547780a36`
- 选择条件：基于图像输入，利用开放词汇检测器（GroundingDINO）定位目标，并结合多模态大语言模型（MLLM）进行视觉证据推理，以判定厨房环境中是否存在老鼠异常事件。
- 不选择：非厨房场景（如卧室、办公室、户外等）；非老鼠类动物（如猫、狗、昆虫等其他害虫）；非图像类型的媒体输入；需要调用 embeddingTool 的场景；需要高精度物种分类或数量统计的场景
- 执行边界：仅限厨房环境内的老鼠存在性二元判断（Yes/No）。依赖 GroundingDINO 检测（阈值0.3）和 MLLM 视觉推理确认。不涉及其他异常类别、复杂行为分析、非厨房场景或非图像媒体。禁止使用 embeddingTool。
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/kitchen_infested_with_rats_14a547780a36.json`；`scripts/kitchen_infested_with_rats_14a547780a36.py`

### kitchen_infested_with_rats_image_baseline

- ID：`kitchen_infested_with_rats_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 kitchen_infested_with_rats 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/kitchen_infested_with_rats_96c9e72153f7.json`；`scripts/kitchen_infested_with_rats_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
