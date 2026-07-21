---
name: fight
description: "检测输入视频或图像中是否发生“打架斗殴”异常事件。"
---

# 打架斗殴

## Skill 作用

检测输入视频或图像中是否发生“打架斗殴”异常事件。

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

### fight_detection_image

- ID：`fight_0bebbe640bf1`
- 选择条件：基于静态图像输入，通过结合人头检测、通用目标检测及深度估计的多模态证据，判断场景中是否存在‘打架斗殴’异常事件。该工作流利用 PaddleHeadDetTool 定位人头，YoloTool 识别潜在冲突目标，Unidepth 评估空间深度关系，最终由多模态大模型综合视觉证据进行判定。
- 不选择：非图像类型的媒体输入（如视频流、音频），需使用其他适配的工作流。; 图像中完全无法检测到人头或关键目标，导致缺乏基础视觉证据的场景。; 需要语义嵌入分析（embedding）的场景，本工作流禁止调用 embeddingTool。; 非‘打架斗殴’类别的其他异常事件检测，本工作流严格限定于 event_type 为 'fight' 的场景。
- 执行边界：仅适用于静态图像输入下的打架斗殴事件检测。检测能力依赖于工具链中人头检测、目标检测（阈值0.5）及深度估计的准确性。最终判断严格基于多模态模型对视觉证据的综合分析，输出结果为二元判定（是/否）。
- 工具链：`paddleHeadDetTool -> yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/fight_0bebbe640bf1.json`；`scripts/fight_0bebbe640bf1.py`

### fight_detection_workflow

- ID：`fight_513cb2fe7351`
- 选择条件：基于图像输入检测‘打架斗殴’（fight）异常事件。工作流通过 paddleHeadDetTool 检测可见人头以评估人员密度，结合 yoloTool（阈值 0.5）识别潜在冲突行为或物体，利用 python_code_sandbox 计算结构化证据摘要，最终由多模态大模型（MLLM）综合视觉证据判断是否发生打架事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非‘打架斗殴’类别的其他异常事件检测; 需要重新分类或改写 event_type 的场景
- 执行边界：仅适用于 event_type 为 'fight' 且 media_type 为 'image' 的检测任务。检测器依赖于可见人头的存在及 YOLO 检测到的特定行为特征，若图像中缺乏可检测的人头或关键行为特征导致证据不足，可能无法准确判定。
- 工具链：`paddleHeadDetTool -> yoloTool -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/fight_513cb2fe7351.json`；`scripts/fight_513cb2fe7351.py`

### fight_image_baseline

- ID：`fight_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 fight 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/fight_96c9e72153f7.json`；`scripts/fight_96c9e72153f7.py`

### fight_detection_workflow

- ID：`fight_d0dd12ac36b0`
- 选择条件：基于多模态视觉证据检测图像中是否发生打架斗殴事件。工作流首先通过 paddleHeadDetTool 检测可见人头以确认人员存在，同时利用 yoloTool（阈值 0.5）识别潜在的攻击性动作或物体交互。随后，MLLM 综合人头检测结果与 YOLO 提取的视觉特征，依据打架斗殴的视觉表现（如肢体冲突、攻击姿态）进行最终判定。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 未检测到可见人头且缺乏明确肢体冲突视觉证据的场景; 需要调用 embeddingTool 进行语义嵌入处理的场景; 非打架斗殴类别的异常事件（如跌倒、火灾、盗窃等）
- 执行边界：{"supported_media": "image", "event_type": "fight", "required_evidence": ["paddleHeadDetTool 检测到的人头实例", "yoloTool 在 0.5 阈值下检测到的目标或动作特征"], "decision_logic": "MLLM 基于上述工具输出的视觉证据进行二分类判断（是/否）"}
- 工具链：`paddleHeadDetTool -> yoloTool -> MLLM`
- 资源：`references/workflows/fight_d0dd12ac36b0.json`；`scripts/fight_d0dd12ac36b0.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
