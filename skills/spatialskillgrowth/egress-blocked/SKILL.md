---
name: egress-blocked
description: "检测输入视频或图像中是否发生“安全出口遮挡”异常事件。"
---

# 安全出口遮挡

## Skill 作用

检测输入视频或图像中是否发生“安全出口遮挡”异常事件。

## 工作流选择

- 探索阶段只处理图片；`embeddingTool` 可按图片工具参与，但图片基线仍为单步 MLLM。
- 图片及视频抽样帧使用同一套图片工作流，可组合 embeddingTool、MLLM 或其他图像工具。
- 冻结视频推理默认根据本 `SKILL.md` 和当前抽样帧选择 Top-K（默认 2 条）工作流。
- 推理并行执行原视频 `embeddingTool` 和选中的图片工作流；全工作流模式执行全部结构合格路线。
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

### egress_blocked_detector

- ID：`egress_blocked_5edebbe1dfe0`
- 选择条件：针对静态图像输入，检测安全出口是否被物体遮挡或堵塞。通过 GroundingDINO 定位潜在障碍物，结合 PaddleOCR 提取出口标识等文字信息，由多模态大模型综合视觉与文本证据判定异常。
- 不选择：非图像类型的媒体输入；动态视频流或实时视频帧序列；需要调用 embeddingTool 的场景；非 'egress_blocked' 类别的其他异常检测任务；未包含可见出口标识或相关遮挡物的场景
- 执行边界：仅适用于检测图像中安全出口被物理遮挡或堵塞的情况。依赖 GroundingDINO 检测到的物体边界框及置信度（阈值 >= 0.3）和 PaddleOCR 提取的场景文字内容作为必要证据。严禁使用 embeddingTool。不处理其他类型的设施故障或安全违规。
- 工具链：`groundingdino -> paddleOcrTool -> MLLM`
- 资源：`references/workflows/egress_blocked_5edebbe1dfe0.json`；`scripts/egress_blocked_5edebbe1dfe0.py`

### egress_blocked_detector

- ID：`egress_blocked_661077834e2a`
- 选择条件：基于多模态视觉证据检测图像中的安全出口遮挡异常。通过开放词汇检测定位潜在障碍物，结合OCR识别出口标识文字，并利用深度估计分析空间遮挡关系，最终由多模态大模型综合判断是否发生出口堵塞。
- 不选择：非图像类型的媒体输入; 未包含安全出口或疏散通道场景的图像; 无法通过视觉手段识别出口标识或障碍物深度的模糊图像
- 执行边界：{"required_evidence": ["通过 groundingdino 检测到的潜在障碍物边界框", "通过 paddleocr 识别的出口相关文字信息", "通过 unidepth 估计的障碍物与出口区域的深度关系"], "detection_scope": "仅针对已确定类别为 egress_blocked 的安全出口遮挡事件进行检测，不扩展至其他类型的异常事件", "input_constraint": "仅支持图像输入，禁止调用 embedding 工具"}
- 工具链：`groundingdino -> paddleOcrTool -> unidepth -> MLLM`
- 资源：`references/workflows/egress_blocked_661077834e2a.json`；`scripts/egress_blocked_661077834e2a.py`

### egress_blocked_detector

- ID：`egress_blocked_8fb801c3fd73`
- 选择条件：针对静态图像输入，通过光学字符识别（OCR）提取场景中的可见文字信息，并结合多模态大语言模型（MLLM）进行视觉语义分析，以检测是否存在‘安全出口遮挡’（egress_blocked）异常事件。该工作流专注于验证安全出口通道是否被物理障碍物堵塞或标识被遮挡，确保证据链包含视觉特征与文本信息的综合判断。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本日志）。; 需要动态时序分析的场景，本工作流仅处理单帧静态图像。; 其他类型的异常事件（如火灾、入侵、设备故障等），本检测器仅针对 egress_blocked 类别。; 无法通过 OCR 或视觉模型识别的极端低质量、模糊或完全黑暗图像。
- 执行边界：{"required_inputs": ["image"], "required_evidence": ["paddleOcrTool 提取的可见文字内容", "MLLM 基于图像视觉特征及 OCR 结果的综合判断"], "tool_constraints": ["禁止调用 embeddingTool。", "必须使用 paddleOcrTool 进行文字读取。", "必须使用 MLLM 进行最终异常判定。"], "event_type": "egress_blocked"}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/egress_blocked_8fb801c3fd73.json`；`scripts/egress_blocked_8fb801c3fd73.py`

### egress_blocked_vision_detector

- ID：`egress_blocked_96c9e72153f7`
- 选择条件：基于图像输入（包括视频的关键帧），利用多模态大语言模型（MLLM）检测安全出口是否被遮挡。通过视觉证据分析，判断具有安全出口标识或功能的通道区域是否被物体堵塞，从而确认 egress_blocked 异常。
- 不选择：禁止调用 embeddingTool 处理图像输入; 仅适用于图像媒体类型（含视频提取的单帧），不支持原始视频时序分析或纯文本输入; 不处理非安全出口区域的普通物体遮挡，仅针对具有安全出口标识或功能的通道区域; 不进行事件分类，仅验证已确定的 egress_blocked 类别。
- 执行边界：必须使用 MLLM 工具基于可见画面进行最终判断; 依赖图像工具获取视觉证据，禁止使用嵌入模型; 需要安全出口标识或通道区域的视觉可见性以及遮挡物体对通行能力阻碍程度的证据; 输出为二元判断（是/否）。
- 工具链：`MLLM`
- 资源：`references/workflows/egress_blocked_96c9e72153f7.json`；`scripts/egress_blocked_96c9e72153f7.py`

### egress_blocked_detector

- ID：`egress_blocked_bf89f2a3b4ab`
- 选择条件：基于多模态视觉证据检测安全出口遮挡异常。工作流首先通过 OCR 识别场景中的文字标识以确认出口属性，利用开放词汇检测模型（阈值 0.3）定位潜在遮挡物，并结合深度估计分析空间关系，最终由多模态大模型综合判断是否存在 egress_blocked 事件。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 egress_blocked 类别的异常检测任务; 无法通过视觉证据直接判断遮挡关系的抽象场景
- 执行边界：仅支持针对 egress_blocked 事件的图像检测，依赖 paddleOcrTool、groundingdino、unidepth 和 MLLM 的协同推理，不泛化至其他异常类别或非视觉模态。
- 工具链：`paddleOcrTool -> groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/egress_blocked_bf89f2a3b4ab.json`；`scripts/egress_blocked_bf89f2a3b4ab.py`

### egress_blocked_detector

- ID：`egress_blocked_ca7dd3800fd8`
- 选择条件：针对图像输入，利用目标检测工具（yoloTool）结合多模态大模型（MLLM）进行视觉证据收集与分析，专门用于判定是否存在安全出口被遮挡或堵塞的异常事件。
- 不选择：禁止对图像输入调用 embeddingTool; 不适用于非图像类型的媒体数据; 不处理非 egress_blocked 类别的异常事件; 不进行事件类别的重新分类或改写
- 执行边界：仅支持基于图像视觉证据的 egress_blocked 事件检测，依赖 yoloTool 进行初步特征提取及 MLLM 进行最终逻辑判断，输出结果为二值化的存在性判定。
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/egress_blocked_ca7dd3800fd8.json`；`scripts/egress_blocked_ca7dd3800fd8.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
