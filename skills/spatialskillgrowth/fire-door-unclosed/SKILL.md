---
name: fire-door-unclosed
description: "检测输入视频或图像中是否发生“消防门未关闭”异常事件。"
---

# 消防门未关闭

## Skill 作用

检测输入视频或图像中是否发生“消防门未关闭”异常事件。

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

### fire_door_unclosed_detector

- ID：`fire_door_unclosed_1c1aea5e038d`
- 选择条件：基于视觉证据检测消防门是否处于未关闭状态。工作流程首先使用开放词汇检测模型（GroundingDINO）定位消防门及其状态特征，随后结合多模态大语言模型（MLLM）分析图像上下文，综合判断是否存在消防门未关闭的异常事件。
- 不选择：非图像类型的媒体输入; 图像中未包含消防门主体或其状态无法被视觉证据明确识别的场景; 需要调用 embeddingTool 进行特征提取的任务; 涉及其他类型异常事件（如火灾、入侵等）的检测需求
- 执行边界：{"event_type": "fire_door_unclosed", "media_type": "image", "required_evidence": ["通过 GroundingDINO 检测到的消防门实例及其边界框", "多模态模型基于视觉上下文对门状态（开启/关闭）的语义判断"], "constraints": ["仅支持静态图像输入", "检测阈值固定为 0.5", "最终输出仅为二元判断（是/否）", "不执行物体名称的运行时替换，严格限定于消防门类别"]}
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/fire_door_unclosed_1c1aea5e038d.json`；`scripts/fire_door_unclosed_1c1aea5e038d.py`

### fire_door_unclosed_detector

- ID：`fire_door_unclosed_74b0c3f20721`
- 选择条件：基于 YOLO 目标检测与多模态大语言模型（MLLM）的视觉分析工作流，用于检测输入图像中是否存在消防门未关闭的异常状态。该工作流首先利用 YOLO 工具以 0.5 的置信度阈值提取关键视觉特征，随后由 MLLM 结合图像证据进行语义推理，最终判定是否发生消防门未关闭事件。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征嵌入的场景; 非 fire_door_unclosed 类别的其他异常事件检测任务; 缺乏清晰消防门视觉特征或图像质量过低导致无法识别门体状态的场景
- 执行边界：仅支持对静态图像进行 fire_door_unclosed 异常事件的二元判定（是/否）。检测逻辑严格依赖于 YOLO 工具在 0.5 阈值下的检测结果以及 MLLM 对视觉证据的语义分析，不包含对门体机械故障原因的分析或对其他类型安全门（如普通防火门、逃生门）的通用未关闭检测能力，除非明确指定为 fire_door_unclosed 事件类型。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/fire_door_unclosed_74b0c3f20721.json`；`scripts/fire_door_unclosed_74b0c3f20721.py`

### fire_door_unclosed_image_baseline

- ID：`fire_door_unclosed_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 fire_door_unclosed 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/fire_door_unclosed_96c9e72153f7.json`；`scripts/fire_door_unclosed_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
