---
name: pipeline-leak
description: "检测输入视频或图像中是否发生“管道泄漏”异常事件。"
---

# 管道泄漏

## Skill 作用

检测输入视频或图像中是否发生“管道泄漏”异常事件。

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

### pipeline_leak_detector

- ID：`pipeline_leak_1dbd8d95a7a7`
- 选择条件：基于视觉证据的管道泄漏异常检测工作流。该流程通过 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，结合 Python 代码沙箱计算结构化证据摘要，最终由多模态大语言模型（MLLM）综合判断图像中是否存在管道泄漏。仅适用于图像输入，禁止使用嵌入工具。
- 不选择：非图像类型的媒体输入（如纯文本、音频或视频流）; 需要调用 embeddingTool 的场景; 非 pipeline_leak 类别的异常检测任务; 需要动态调整 GroundingDINO 检测阈值的场景
- 执行边界：{"input_media": "image", "event_type": "pipeline_leak", "detection_threshold": 0.3, "required_tools": ["groundingdino", "python_code_sandbox", "MLLM"], "prohibited_tools": ["embeddingTool"], "output_format": "binary_yes_no"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/pipeline_leak_1dbd8d95a7a7.json`；`scripts/pipeline_leak_1dbd8d95a7a7.py`

### pipeline_leak_detector

- ID：`pipeline_leak_ad1b245c64fb`
- 选择条件：基于图像输入，利用 GroundingDINO 进行开放词汇目标检测，结合代码沙箱计算结构化证据，最终通过多模态大语言模型判断是否发生管道泄漏异常。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 pipeline_leak 类别的异常检测任务; 未提供原始图像数据的请求
- 执行边界：{"required_evidence": ["GroundingDINO 检测到的管道或泄漏相关视觉对象", "代码沙箱生成的结构化证据摘要"], "detection_logic": "依据视觉证据判断是否存在管道泄漏，输出二值结论", "constraints": "严格限制在 pipeline_leak 事件类型，不泛化至其他泄漏或管道故障类别"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/pipeline_leak_ad1b245c64fb.json`；`scripts/pipeline_leak_ad1b245c64fb.py`

### pipeline_leak_visual_detector

- ID：`pipeline_leak_d1f7dfcf6135`
- 选择条件：基于多模态大语言模型（MLLM）对输入图像或视频代表帧进行视觉分析，通过识别液体喷涌、积水痕迹、管道破损或湿痕等视觉证据，判断是否存在管道泄漏异常。
- 不选择：非图像类型的媒体输入（如音频、纯文本）; 需要调用 embeddingTool 进行特征提取的场景; 非管道泄漏类别的异常检测（如火灾、入侵、设备故障等）; 缺乏清晰视觉证据导致无法判断泄漏状态的模糊图像; 不处理原始视频时序分析，仅依据当前帧图像证据。
- 执行边界：支持事件类型：pipeline_leak; 支持媒体类型：image/video_frame; 必需工具：MLLM; 证据要求：必须存在指向管道泄漏的视觉特征（如水流、湿痕、破损点）; 判断依据严格限制于当前图像内容，不依赖外部上下文、历史数据或视频时序信息。
- 工具链：`MLLM`
- 资源：`references/workflows/pipeline_leak_d1f7dfcf6135.json`；`scripts/pipeline_leak_d1f7dfcf6135.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
