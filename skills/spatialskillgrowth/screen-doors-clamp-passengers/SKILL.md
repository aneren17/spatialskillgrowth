---
name: screen-doors-clamp-passengers
description: "检测输入视频或图像中是否发生“屏蔽门夹人”异常事件。"
---

# 屏蔽门夹人

## Skill 作用

检测输入视频或图像中是否发生“屏蔽门夹人”异常事件。

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

### screen_doors_clamp_passengers_detector

- ID：`screen_doors_clamp_passengers_2ebebd3e0e79`
- 选择条件：基于图像输入，通过人头检测、深度估计及多模态大模型推理，检测地铁站台屏蔽门是否发生夹人异常事件。
- 不选择：非图像类型的媒体输入; 非屏蔽门夹人（screen_doors_clamp_passengers）类别的其他异常事件; 需要调用 embeddingTool 的场景
- 执行边界：{"required_inputs": ["包含站台屏蔽门区域的图像"], "evidence_requirements": ["必须检测到可见人头（paddleHeadDetTool）", "必须获取检测目标的深度信息（unidepth）", "必须通过多模态模型（MLLM）综合视觉证据进行最终判断"], "output_format": "布尔值（是/否）"}
- 工具链：`paddleHeadDetTool -> unidepth -> MLLM`
- 资源：`references/workflows/screen_doors_clamp_passengers_2ebebd3e0e79.json`；`scripts/screen_doors_clamp_passengers_2ebebd3e0e79.py`

### screen_doors_clamp_passengers_image_baseline

- ID：`screen_doors_clamp_passengers_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 screen_doors_clamp_passengers 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/screen_doors_clamp_passengers_96c9e72153f7.json`；`scripts/screen_doors_clamp_passengers_96c9e72153f7.py`

### screen_doors_clamp_passengers_detector

- ID：`screen_doors_clamp_passengers_b9e829d1798b`
- 选择条件：基于图像输入，通过人头检测与多模态大模型推理，判断屏蔽门与乘客之间是否存在夹持异常。
- 不选择：非图像类型的媒体输入; 未包含屏蔽门或乘客场景的图像; 图像中无人头检测结果的场景; 需要调用 embeddingTool 的场景; 其他类型的异常事件检测
- 执行边界：仅针对 event_type 为 'screen_doors_clamp_passengers' 且 media_type 为 'image' 的场景，依赖 paddleHeadDetTool 提供的人头检测证据及 MLLM 的视觉推理能力，不泛化至其他异常类别或非图像模态。
- 工具链：`paddleHeadDetTool -> MLLM`
- 资源：`references/workflows/screen_doors_clamp_passengers_b9e829d1798b.json`；`scripts/screen_doors_clamp_passengers_b9e829d1798b.py`

### screen_doors_clamp_passengers_detector

- ID：`screen_doors_clamp_passengers_f0c329f7e2a1`
- 选择条件：基于视觉证据检测屏蔽门夹人异常事件。工作流首先利用开放词汇检测工具（GroundingDINO）在图像中定位与屏蔽门及乘客相关的视觉目标，随后通过多模态大语言模型（MLLM）结合检测证据进行综合研判，以确认是否发生屏蔽门夹人事件。
- 不选择：非图像类型的媒体输入; 非屏蔽门夹人（screen_doors_clamp_passengers）类别的异常检测任务; 需要调用 embeddingTool 的场景
- 执行边界：仅适用于图像模态下的屏蔽门夹人事件检测。检测能力依赖于 GroundingDINO 的开放词汇定位精度及 MLLM 的视觉推理能力，不包含对视频流、音频或其他类型异常事件的检测支持。
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/screen_doors_clamp_passengers_f0c329f7e2a1.json`；`scripts/screen_doors_clamp_passengers_f0c329f7e2a1.py`

### screen_doors_clamp_passengers_detector

- ID：`screen_doors_clamp_passengers_f9bb0f23e3a4`
- 选择条件：基于静态图像输入，利用人头检测、行人检测及深度估计工具提取视觉证据，并通过多模态大模型判断屏蔽门与乘客之间是否存在物理夹持异常。该工作流专门针对屏蔽门夹人场景，依赖图像中可检测的人体部位与门体结构的相对位置及深度关系进行判定。
- 不选择：非图像类型的媒体输入（如视频流、纯文本描述）; 非屏蔽门夹人类别的其他异常事件（如列车故障、火灾、打架斗殴等）; 图像中无可见乘客或屏蔽门结构，导致无法建立空间关系证据的场景; 需要时序动态分析才能判定的夹人过程（本工作流仅支持单帧静态判断）
- 执行边界：{"required_evidence": ["可见的人头或行人检测框", "屏蔽门与检测目标之间的深度估计值", "多模态模型对‘夹持’状态的语义确认"], "tool_constraints": ["必须使用 paddleHeadDetTool 检测人头", "必须使用 paddlePedriderDetTool 检测交通参与者", "必须使用 unidepth 估计目标深度", "必须使用 MLLM 进行最终逻辑判断", "禁止调用 embeddingTool"], "generalization_scope": "仅适用于已确认为 screen_doors_clamp_passengers 类别的图像检测任务，不泛化至其他类型的门体或物体夹持事件"}
- 工具链：`paddleHeadDetTool -> paddlePedriderDetTool -> unidepth -> MLLM`
- 资源：`references/workflows/screen_doors_clamp_passengers_f9bb0f23e3a4.json`；`scripts/screen_doors_clamp_passengers_f9bb0f23e3a4.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
