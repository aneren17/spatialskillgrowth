---
name: fire-hydrant-leakage
description: "检测输入视频或图像中是否发生“消防栓泄漏”异常事件。"
---

# 消防栓泄漏

## Skill 作用

检测输入视频或图像中是否发生“消防栓泄漏”异常事件。

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

### fire_hydrant_leakage_detector

- ID：`fire_hydrant_leakage_06ff05f588ac`
- 选择条件：针对输入图像执行消防栓泄漏异常检测。工作流首先利用 GroundingDINO 以 0.3 的开放词汇检测阈值定位消防栓目标，随后通过 UniDepth 估计目标的深度信息以辅助空间理解，最后结合多模态大语言模型（MLLM）分析视觉证据，判断是否存在消防栓泄漏现象。
- 不选择：非图像类型的媒体输入（如视频、音频或纯文本）; 需要调用 embeddingTool 进行特征嵌入的场景; 非 fire_hydrant_leakage 类别的其他异常事件检测; 需要重新分类或改写事件类别的任务
- 执行边界：{"required_tools": ["groundingdino", "unidepth", "MLLM"], "input_modality": "image", "event_type": "fire_hydrant_leakage", "detection_threshold": 0.3, "output_format": "binary (是/否)", "constraints": ["禁止使用 embeddingTool", "必须保留 fire_hydrant_leakage 事件类型不变", "仅基于视觉证据进行判断"]}
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/fire_hydrant_leakage_06ff05f588ac.json`；`scripts/fire_hydrant_leakage_06ff05f588ac.py`

### fire_hydrant_leakage_detector

- ID：`fire_hydrant_leakage_0e1ee6980e3f`
- 选择条件：基于 GroundingDINO 开放词汇检测与多模态大模型（MLLM）推理的消防栓泄漏异常检测工作流。该工作流通过 0.3 的检测阈值定位消防栓实例，结合 Python 代码沙箱计算结构化视觉证据摘要，最终由 MLLM 依据图像特征判断是否存在泄漏现象。仅适用于静态图像输入，禁止使用嵌入工具。
- 不选择：非图像类型的媒体输入（如视频、音频、纯文本）。; 未包含消防栓实体的场景（如普通管道泄漏、非消防水利设施）。; 需要动态时序分析或连续监控的场景。; 依赖 embeddingTool 进行特征提取的流程。; 非 fire_hydrant_leakage 类别的其他异常事件检测任务。
- 执行边界：{"supported_event_type": "fire_hydrant_leakage", "supported_media_type": "image", "detection_method": "GroundingDINO (threshold=0.3) + MLLM reasoning", "evidence_requirement": "必须提供包含消防栓的图像，并生成结构化证据摘要以支持 MLLM 判断。", "output_format": "Binary classification (Yes/No)"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/fire_hydrant_leakage_0e1ee6980e3f.json`；`scripts/fire_hydrant_leakage_0e1ee6980e3f.py`

### fire_hydrant_leakage_detector

- ID：`fire_hydrant_leakage_12775eaca699`
- 选择条件：基于图像输入，利用多模态大语言模型分析视觉特征，检测消防栓是否存在泄漏异常。通过识别消防栓本体及其周围的水迹、水流或湿润痕迹，判断是否发生泄漏事件。仅处理单张图像或视频帧，不处理原始视频时序。
- 不选择：非图像类型的媒体输入（如纯文本、音频、原始视频流）; 图像中未包含消防栓主体或消防栓被严重遮挡无法辨识; 图像分辨率过低导致无法分辨细微水迹或泄漏特征; 非消防栓相关的水体场景（如自然水域、非消防用途的管道泄漏）
- 执行边界：{"event_type": "fire_hydrant_leakage", "media_type": "image", "required_evidence": ["清晰可见的消防栓本体", "消防栓接口、阀门或本体周围存在明显的水迹、水流或湿润区域"], "tool_constraints": ["禁止使用 embeddingTool 处理图像输入", "必须使用 MLLM 工具进行视觉证据收集与推理", "仅基于单帧图像证据进行判断，不进行视频时序分析"]}
- 工具链：`MLLM`
- 资源：`references/workflows/fire_hydrant_leakage_12775eaca699.json`；`scripts/fire_hydrant_leakage_12775eaca699.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
