---
name: firelane-occupied
description: "检测输入视频或图像中是否发生“占用消防通道”异常事件。"
---

# 占用消防通道

## Skill 作用

检测输入视频或图像中是否发生“占用消防通道”异常事件。

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

### firelane_occupied_detector

- ID：`firelane_occupied_61ab37812c63`
- 选择条件：检测静态图像中是否存在占用消防通道的异常事件。通过OCR识别标识文字、检测交通参与者及通用物体，结合深度估计分析空间占用，由多模态大模型综合判断是否构成占用。
- 不选择：非图像输入；无消防通道场景或标识的图像；需视频时序分析、动态行为判断、外部知识库、实时数据或特征提取的任务；非此类异常检测任务。
- 执行边界：仅支持静态图像分析，输出二元占用结果。依赖固定工具链获取文字、物体检测及深度证据，不支持视频分析、动态阈值调整、身份识别、法律判定或时长统计。
- 工具链：`paddleOcrTool -> paddlePedriderDetTool -> yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/firelane_occupied_61ab37812c63.json`；`scripts/firelane_occupied_61ab37812c63.py`

### firelane_occupied_image_baseline

- ID：`firelane_occupied_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 firelane_occupied 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/firelane_occupied_96c9e72153f7.json`；`scripts/firelane_occupied_96c9e72153f7.py`

### firelane_occupied_detector

- ID：`firelane_occupied_af8ef8146a45`
- 选择条件：基于静态图像输入，利用OCR识别场景文字、检测交通参与者（行人/骑行者）及通用目标检测（YOLO）收集视觉证据，通过多模态大模型综合判断是否存在车辆或杂物违规占用消防通道的异常事件。
- 不选择：非图像类型的媒体输入；需要语义嵌入分析或向量检索的场景；非消防通道占用类的其他异常事件检测；缺乏可见文字、交通参与者或可检测物体，或因黑屏、极端模糊导致无法提取有效视觉证据的场景。
- 执行边界：仅支持图像输入；必须使用paddleOcrTool、paddlePedriderDetTool和yoloTool（阈值0.5）提取证据，并由MLLM进行最终逻辑判断；禁止调用embeddingTool；固定事件类型为firelane_occupied；最终输出仅限'是'或'否'。
- 工具链：`paddleOcrTool -> paddlePedriderDetTool -> yoloTool -> MLLM`
- 资源：`references/workflows/firelane_occupied_af8ef8146a45.json`；`scripts/firelane_occupied_af8ef8146a45.py`

### firelane_occupied_detector

- ID：`firelane_occupied_c473dd4021b2`
- 选择条件：检测输入图像中是否存在占用消防通道的异常事件。通过OCR提取场景文字标识，结合目标检测识别交通参与者或障碍物，最终由多模态大模型综合视觉与文本证据进行判断。
- 不选择：非图像类型的媒体输入; 需要调用 embedding 工具的场景; 非 firelane_occupied 类别的异常检测任务; 无法通过 OCR 或目标检测获取有效证据的模糊、遮挡严重或极度缺乏清晰视觉证据的图像
- 执行边界：严格限定于 firelane_occupied 事件类型；依赖 paddleOcrTool 识别可见文字信息（如消防标识）及 paddlePedriderDetTool 检测交通参与者/障碍物位置与类型；由 MLLM 依据上述证据输出布尔值结论；不泛化至其他占用类或火灾类异常。
- 工具链：`paddleOcrTool -> paddlePedriderDetTool -> MLLM`
- 资源：`references/workflows/firelane_occupied_c473dd4021b2.json`；`scripts/firelane_occupied_c473dd4021b2.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
