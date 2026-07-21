---
name: climbing-disconnection
description: "检测输入视频或图像中是否发生“攀爬脱网”异常事件。"
---

# 攀爬脱网

## Skill 作用

检测输入视频或图像中是否发生“攀爬脱网”异常事件。

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

### climbing_disconnection_detector

- ID：`climbing_disconnection_cfde2056e5e9`
- 选择条件：针对静态图像输入，检测是否发生'攀爬脱网'异常事件。工作流首先利用 paddleHeadDetTool 定位可见人头，随后结合多模态大模型（MLLM）分析人头与防护网/围栏的空间关系及攀爬姿态，以判定是否存在脱离防护结构的异常行为。
- 不选择：非图像类型的媒体输入（如视频流、纯文本描述）。; 图像中未检测到任何可见人头，或人头被严重遮挡导致无法判断其与防护设施的空间关系。; 场景中没有防护网、围栏或类似攀爬防护结构。; 需要实时视频流分析或时序行为追踪的场景（本工作流仅支持单帧静态图像分析）。; 涉及其他类型异常事件（如入侵、跌倒、打架等）的检测需求。
- 执行边界：{"supported_event_type": "climbing_disconnection", "required_evidence": ["可见的人头检测框（由 paddleHeadDetTool 提供）。", "人头与防护设施（如网、围栏）的相对位置及交互状态（由 MLLM 基于图像像素和检测框推理）。", "攀爬姿态或脱离防护结构的视觉特征。"], "input_constraints": {"media_type": "image", "prohibited_tools": ["embeddingTool"]}, "output_format": "布尔值（是/否），表示是否检测到攀爬脱网异常。"}
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/climbing_disconnection_cfde2056e5e9.json`；`scripts/climbing_disconnection_cfde2056e5e9.py`

### climbing_disconnection_detector

- ID：`climbing_disconnection_d8a9b55f4b0d`
- 选择条件：基于多模态大语言模型（MLLM）分析输入图像，检测是否存在‘攀爬脱网’异常事件。该工作流通过视觉证据判断目标主体是否出现攀爬过程中脱离防护网或安全约束的状态，适用于静态图像场景下的特定安全违规检测。
- 不选择：不适用于视频流或动态序列分析，仅处理单张静态图像。; 不适用于非攀爬类异常（如跌倒、入侵、火灾等），仅针对攀爬行为中的脱网状态。; 不适用于无清晰视觉证据或图像质量严重受损导致无法识别主体与防护网关系的场景。; 不执行目标物体名称的泛化抽象，因工具图未提供可替换目标的运行时槽位，检测器严格限定于‘攀爬脱网’这一具体事件类型。
- 执行边界：{"required_evidence": ["图像中必须包含可识别的攀爬主体（如人员）与防护网结构。", "必须存在主体与防护网空间关系异常的视觉特征（如主体悬空、脱离网面接触点）。", "MLLM 需基于上述视觉证据输出明确的是/否判断，不得依赖外部文本或嵌入向量工具。"], "tool_constraints": ["禁止调用 embeddingTool，所有视觉分析必须通过图像工具与多模态模型完成。", "工具图固定为单步 MLLM 推理，无前置预处理或后处理步骤。"], "output_format": "仅返回‘是’或‘否’作为最终判断结果。"}
- 工具链：`MLLM`
- 资源：`references/workflows/climbing_disconnection_d8a9b55f4b0d.json`；`scripts/climbing_disconnection_d8a9b55f4b0d.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
