---
name: breaking-through-toll-booths
description: "检测输入视频或图像中是否发生“闯收费站”异常事件。"
---

# 闯收费站

## Skill 作用

检测输入视频或图像中是否发生“闯收费站”异常事件。

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

### breaking_through_toll_booths_detector

- ID：`breaking_through_toll_booths_53481044122a`
- 选择条件：检测输入图像中是否发生车辆或物体强行通过收费站（闯收费站）的异常事件。该工作流通过OCR提取现场可见文字信息，并结合多模态大模型对图像中的车辆行为、收费站物理状态及通行合规性进行综合视觉证据分析，以判断是否存在违规闯卡行为。
- 不选择：非收费站场景（如普通道路、停车场入口、高速匝道等无收费设施区域）; 图像质量严重受损导致无法识别车辆位置或收费站结构的情况; 仅包含静态收费站设施而无车辆或移动物体的图像; 需要视频时序分析才能判断的连续闯卡行为（本工作流仅支持单帧图像分析）
- 执行边界：{"event_type": "breaking_through_toll_booths", "required_evidence": ["收费站物理设施（栏杆、亭子、标识等）的视觉存在", "车辆或移动物体与收费站设施的相对位置关系", "OCR识别出的收费站相关文字信息（如站名、通道状态等）", "车辆是否处于非正常通行状态（如栏杆未升起时通过、撞击设施等）"], "limitations": ["仅支持单张静态图像分析，不支持视频流或时序数据", "依赖图像中收费站标识和车辆特征的清晰可见性", "无法判断驾驶员身份或主观意图，仅基于视觉行为判定"]}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/breaking_through_toll_booths_53481044122a.json`；`scripts/breaking_through_toll_booths_53481044122a.py`

### breaking_through_toll_booths_detector

- ID：`breaking_through_toll_booths_5a401c0b68f1`
- 选择条件：基于多模态视觉证据检测图像中是否发生‘闯收费站’异常事件。通过 OCR 提取收费站标识文字、YOLO 检测车辆与收费站结构的空间关系，结合多模态大模型综合判断车辆是否存在强行通过收费站而未正常缴费或通行的行为。
- 不选择：非收费站场景（如普通道路、停车场入口、高速公路主线）; 无清晰收费站结构或标识的模糊图像; 车辆正常排队缴费或已通过ETC通道的场景; 非图像模态输入（如视频帧序列、音频、纯文本描述）; 无法识别关键视觉元素（如车辆、收费站栏杆、收费亭）的图像
- 执行边界：{"required_evidence": ["OCR 识别出的收费站相关文字（如‘收费站’、‘缴费’、‘ETC’等）", "YOLO 检测到的车辆与收费站物理结构（如栏杆、收费亭、道闸）的空间位置关系", "多模态模型对车辆行为与收费站状态的综合语义判断"], "detection_scope": "仅限静态图像中单一时间点的闯收费站行为检测", "tool_dependency": "必须依赖 paddleOcrTool 和 yoloTool 的输出作为 MLLM 的输入证据", "output_format": "布尔值（是/否），表示是否检测到闯收费站异常事件"}
- 工具链：`paddleOcrTool -> yoloTool -> MLLM`
- 资源：`references/workflows/breaking_through_toll_booths_5a401c0b68f1.json`；`scripts/breaking_through_toll_booths_5a401c0b68f1.py`

### breaking_through_toll_booths_image_baseline

- ID：`breaking_through_toll_booths_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 breaking_through_toll_booths 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/breaking_through_toll_booths_96c9e72153f7.json`；`scripts/breaking_through_toll_booths_96c9e72153f7.py`

### breaking_through_toll_booths_detector

- ID：`breaking_through_toll_booths_9f74d96f04bd`
- 选择条件：检测输入图像中是否发生车辆或行人强行通过收费站闸机（闯收费站）的异常事件。该工作流利用 OCR 识别收费站标识文字，结合 YOLO 目标检测定位车辆或行人，并通过深度估计与结构化证据计算，由多模态大模型综合判断是否存在违规闯卡行为。
- 不选择：非收费站场景（如普通道路、停车场入口无闸机设施）; 图像中未出现收费站闸机、栏杆或相关标识文字; 目标物体未处于通过或试图通过闸机的动态过程中; 图像质量过低导致无法识别关键视觉证据（如文字模糊、目标遮挡严重）; 非图像类型的媒体输入
- 执行边界：{"required_evidence": ["OCR 识别到的收费站相关文字（如‘收费站’、‘ETC’、‘缴费’等）", "YOLO 检测到的车辆或行人目标及其边界框", "基于 YOLO 结果的深度估计信息，用于判断目标与闸机的空间关系", "结构化证据摘要，整合位置、深度与文本信息"], "tool_constraints": ["必须使用 paddleOcrTool 读取可见文字", "必须使用 yoloTool 进行目标检测（阈值 0.5）", "必须使用 unidepth 估计检测目标深度", "必须使用 python_code_sandbox 计算结构化证据摘要", "最终判断由 MLLM 基于上述所有工具输出完成", "禁止对图像输入调用 embeddingTool"], "event_type": "breaking_through_toll_booths", "media_type": "image"}
- 工具链：`paddleOcrTool -> yoloTool -> unidepth -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/breaking_through_toll_booths_9f74d96f04bd.json`；`scripts/breaking_through_toll_booths_9f74d96f04bd.py`

### breaking_through_toll_booths_detector

- ID：`breaking_through_toll_booths_e7ed2b3b5674`
- 选择条件：检测输入图像中是否发生车辆或物体强行通过收费站（Toll Booth）的异常事件。该工作流通过 OCR 识别收费站标识文字、YOLO 检测车辆及收费站结构、UniDepth 估计空间深度关系，结合多模态大模型综合判断是否存在‘闯收费站’行为。
- 不选择：非收费站场景（如普通路口、停车场入口、无收费设施的通道）; 车辆正常排队缴费或通过已抬起栏杆的收费站; 图像中未包含收费站关键结构（栏杆、亭子、标识牌）或车辆; 模糊、遮挡严重导致无法识别收费站状态或车辆行为的图像; 非图像媒体类型（本工作流仅支持 image 类型输入）
- 执行边界：{"required_evidence": ["OCR 识别到收费站相关文字（如‘收费’、‘ETC’、‘收费站’等）", "YOLO 检测到车辆与收费站栏杆/亭子的空间共存", "UniDepth 估计显示车辆处于栏杆未抬起或应停止区域", "多模态模型确认车辆行为符合‘强行通过’而非正常通行"], "tool_constraints": ["paddleOcrTool 必须成功读取收费站标识文字", "yoloTool 必须使用 0.5 检测阈值定位车辆与收费站结构", "unidepth 必须基于 yoloTool 输出估计目标深度", "MLLM 必须综合上述三项证据进行最终判断"], "event_type_lock": "breaking_through_toll_booths", "media_type_lock": "image"}
- 工具链：`paddleOcrTool -> yoloTool -> unidepth -> MLLM`
- 资源：`references/workflows/breaking_through_toll_booths_e7ed2b3b5674.json`；`scripts/breaking_through_toll_booths_e7ed2b3b5674.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
