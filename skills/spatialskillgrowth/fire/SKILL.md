---
name: fire
description: "检测输入视频或图像中是否发生“起火”异常事件。"
---

# 起火

## Skill 作用

检测输入视频或图像中是否发生“起火”异常事件。

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

### fire_detection_workflow

- ID：`fire_38a6e4d538da`
- 选择条件：基于视觉证据的起火异常检测工作流。通过 GroundingDINO 进行开放词汇目标检测，结合 Python 代码沙箱计算结构化证据摘要，最终由多模态大语言模型（MLLM）综合判断图像中是否存在起火事件。
- 不选择：非图像类型的媒体输入（如纯文本、音频或视频流）; 需要调用 embeddingTool 的场景; 非 'fire' 类型的异常事件检测任务; 需要重新分类或改写异常类别的场景
- 执行边界：支持事件类型: fire; 支持媒体类型: image; 检测方法: 视觉目标检测与多模态推理; 所需工具: groundingdino, python_code_sandbox, MLLM; 输出格式: binary (是/否)
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/fire_38a6e4d538da.json`；`scripts/fire_38a6e4d538da.py`

### fire_detection_workflow

- ID：`fire_428af33cad44`
- 选择条件：基于 YOLO 目标检测与多模态大语言模型（MLLM）的图像起火异常检测工作流。使用 0.3 阈值识别潜在异常，结合视觉证据判断是否发生广义起火事件。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）；需要调用 embeddingTool 进行特征提取的场景；要求对异常事件进行重新分类或泛化到其他火灾子类别（如电气火灾、森林火灾等具体细分）的场景；需要输出详细推理过程、置信度分数或除“是/否”以外格式的最终判断。
- 执行边界：{"input_media": "image", "event_type": "fire", "detection_threshold": 0.3, "required_tools": ["yoloTool", "MLLM"], "output_format": "binary_yes_no"}
- 工具链：`yoloTool -> MLLM`
- 资源：`references/workflows/fire_428af33cad44.json`；`scripts/fire_428af33cad44.py`

### fire_image_baseline

- ID：`fire_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 fire 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/fire_96c9e72153f7.json`；`scripts/fire_96c9e72153f7.py`

### fire_detection_image

- ID：`fire_ea9123696534`
- 选择条件：基于多模态大模型（MLLM）和结构化证据分析，检测输入图像中是否存在“起火”异常事件。工作流首先通过代码沙箱计算视觉证据摘要，随后由 MLLM 依据图像特征进行最终判断。
- 不选择：禁止使用 embeddingTool 处理图像输入。; 仅适用于静态图像输入，不支持视频流或音频数据。; 仅检测“起火”这一特定异常类别，不泛化至烟雾、爆炸或其他火灾相关现象，除非证据明确指向明火。; 不适用于需要实时低延迟响应的场景，因涉及代码执行与多模态推理。
- 执行边界：{"input_media": "image", "event_type": "fire", "evidence_requirement": "必须包含通过 python_code_sandbox 生成的结构化视觉证据摘要，以及 MLLM 基于图像像素特征对明火存在的直接判定。", "output_format": "布尔值（是/否）"}
- 工具链：`python_code_sandbox -> MLLM`
- 资源：`references/workflows/fire_ea9123696534.json`；`scripts/fire_ea9123696534.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
