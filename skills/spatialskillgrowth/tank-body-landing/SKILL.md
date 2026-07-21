---
name: tank-body-landing
description: "检测输入视频或图像中是否发生“罐体落地”异常事件。"
---

# 罐体落地

## Skill 作用

检测输入视频或图像中是否发生“罐体落地”异常事件。

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

### tank_body_landing_image_baseline

- ID：`tank_body_landing_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 tank_body_landing 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/tank_body_landing_96c9e72153f7.json`；`scripts/tank_body_landing_96c9e72153f7.py`

### tank_body_landing_detector

- ID：`tank_body_landing_a798073ef370`
- 选择条件：基于单帧静态图像，利用 GroundingDINO 定位罐体并结合 UniDepth 深度估计，由多模态大模型综合视觉证据判断是否发生罐体落地异常。
- 不选择：非图像媒体输入（如视频流、实时序列）；未包含罐体目标的场景；非落地类的罐体异常（如倾斜、泄漏、爆炸、碰撞）；其他物体（如车辆、人员）的落地或碰撞事件；需要调用 embeddingTool 的任务；依赖外部文本或历史上下文的场景。
- 执行边界：仅支持对静态图像中已检测到的罐体目标进行落地状态的二元判定（是/否）；严格依赖 groundingdino、unidepth 和 MLLM 工具链；不泛化至其他物体或异常类型；输出基于单帧视觉证据，不涉及时序分析。
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/tank_body_landing_a798073ef370.json`；`scripts/tank_body_landing_a798073ef370.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
