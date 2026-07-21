---
name: tree-fallen
description: "检测输入视频或图像中是否发生“树木倒伏”异常事件。"
---

# 树木倒伏

## Skill 作用

检测输入视频或图像中是否发生“树木倒伏”异常事件。

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

### tree_fallen_detector

- ID：`tree_fallen_5b4213dceb8e`
- 选择条件：基于图像输入检测树木倒伏异常事件。工作流首先利用 YOLO 工具检测潜在目标，随后通过 UniDepth 估计检测目标的深度信息，最后结合多模态大语言模型（MLLM）综合视觉证据与深度线索判断是否发生树木倒伏。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 tree_fallen 类别的异常事件检测; 未提供有效图像数据的请求
- 执行边界：{"input_media": "image", "event_type": "tree_fallen", "detection_logic": "依赖 YOLO 目标检测、UniDepth 深度估计及 MLLM 语义推理的串联工作流", "output_format": "布尔值（是/否）", "detection_scope": "仅针对图像中已检测到的树木对象进行倒伏状态判断，不泛化至其他植被或物体倒塌事件"}
- 工具链：`yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/tree_fallen_5b4213dceb8e.json`；`scripts/tree_fallen_5b4213dceb8e.py`

### tree_fallen_image_baseline

- ID：`tree_fallen_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 tree_fallen 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/tree_fallen_96c9e72153f7.json`；`scripts/tree_fallen_96c9e72153f7.py`

### tree_fallen_detector

- ID：`tree_fallen_cda35fb4d7a4`
- 选择条件：针对静态图像输入，检测是否存在树木倒伏或倒塌的异常事件。该工作流结合目标检测（YOLO、GroundingDINO）与深度估计（UniDepth）提取视觉证据，并由多模态大语言模型进行最终判定。
- 不选择：非图像类型的媒体输入; 非树木倒伏类别的其他异常事件检测; 需要调用 embeddingTool 的场景
- 执行边界：{"required_evidence": ["基于 YOLO 和 GroundingDINO 的目标检测结果", "基于 UniDepth 的目标深度估计信息"], "supported_media": ["image"], "event_type": "tree_fallen", "limitation_note": "仅适用于图像模态下的树木倒伏检测，不泛化至其他异常类别或非图像输入"}
- 工具链：`yoloTool -> groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/tree_fallen_cda35fb4d7a4.json`；`scripts/tree_fallen_cda35fb4d7a4.py`

### tree_fallen_detector

- ID：`tree_fallen_dcb94e4f472f`
- 选择条件：基于图像输入，利用开放词汇目标检测与深度估计技术，验证是否存在‘树木倒伏’异常事件。该工作流首先通过 groundingdino 定位树木目标，随后使用 unidepth 评估其空间深度信息，最后结合多模态大模型综合视觉证据进行判定。
- 不选择：非图像类型的媒体输入（如视频流、纯文本描述）; 需要调用 embeddingTool 进行语义嵌入的场景; 非‘树木倒伏’类别的其他异常事件（如火灾、积水、车辆故障等）; 未提供原始图像像素数据的场景
- 执行边界：{"required_evidence": ["通过 groundingdino 检测到的树木目标及其边界框", "通过 unidepth 生成的对应目标深度图或深度估计值", "多模态模型基于上述视觉特征输出的逻辑判断依据"], "constraints": ["仅针对 event_type 为 'tree_fallen' 的场景生效", "必须保留 groundingdino 的 0.3 检测阈值设定", "不得抽象或替换‘树木’这一具体检测对象，因为工具图中无通用物体槽位", "最终输出必须为二分类结果（是/否），不包含概率值或置信度分数"]}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/tree_fallen_dcb94e4f472f.json`；`scripts/tree_fallen_dcb94e4f472f.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
