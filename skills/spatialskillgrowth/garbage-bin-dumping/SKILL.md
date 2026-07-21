---
name: garbage-bin-dumping
description: "检测输入视频或图像中是否发生“垃圾桶倾倒”异常事件。"
---

# 垃圾桶倾倒

## Skill 作用

检测输入视频或图像中是否发生“垃圾桶倾倒”异常事件。

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

### garbage_bin_dumping_detector

- ID：`garbage_bin_dumping_06c81c66a38f`
- 选择条件：基于单张输入图像，利用多模态大模型（MLLM）分析视觉特征，检测是否存在垃圾桶倾倒（garbage_bin_dumping）异常事件。专注于识别垃圾桶本体发生倾覆、侧翻或内容物散落等特定物理状态，需收集确凿的视觉证据以支持最终的二元判断。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）；图像中未包含垃圾桶主体，或垃圾桶处于正常直立、静止状态；缺乏清晰视觉证据导致无法判断垃圾桶状态的情况；涉及其他类型异常事件（如火灾、入侵、打架等）的检测任务；需要调用 embeddingTool 进行特征提取的场景；需要输出详细报告、置信度分数或多分类标签的场景，仅限输出‘是’或‘否’。
- 执行边界：输入媒体：单张图像；目标事件：垃圾桶倾倒；证据要求：必须通过 MLLM 直接分析图像像素信息，确认识别到垃圾桶及其倾倒状态（如倾斜角度异常、位置偏移或垃圾溢出），不得依赖外部元数据或历史上下文；输出格式：二分类（是/否）；允许工具：MLLM；禁止工具：embeddingTool。
- 工具链：`MLLM`
- 资源：`references/workflows/garbage_bin_dumping_06c81c66a38f.json`；`scripts/garbage_bin_dumping_06c81c66a38f.py`

### garbage_bin_dumping_detector

- ID：`garbage_bin_dumping_85f53b1a8ad2`
- 选择条件：基于 GroundingDINO 开放词汇检测与多模态大模型推理，识别图像中是否发生垃圾桶倾倒异常事件。通过设定 0.3 的检测阈值定位目标物体，结合结构化证据摘要进行最终判定。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征提取的场景; 非 'garbage_bin_dumping' 类别的其他异常事件检测任务; 未提供明确视觉证据或图像质量严重受损导致无法识别垃圾桶形态的场景
- 执行边界：{"required_event_type": "garbage_bin_dumping", "supported_media_type": "image", "detection_method": "GroundingDINO (threshold 0.3) + Python Code Sandbox + MLLM", "output_format": "Binary (Yes/No)", "object_scope": "仅限于图像中可被识别为垃圾桶及其倾倒状态的视觉实例，不包含其他无关物体或抽象概念"}
- 工具链：`groundingdino -> python_code_sandbox -> MLLM`
- 资源：`references/workflows/garbage_bin_dumping_85f53b1a8ad2.json`；`scripts/garbage_bin_dumping_85f53b1a8ad2.py`

### garbage_bin_dumping_detector

- ID：`garbage_bin_dumping_fd657a72e118`
- 选择条件：检测输入图像中是否发生垃圾桶倾倒异常事件。通过 GroundingDINO 定位垃圾桶及潜在倾倒物，结合 UniDepth 分析空间深度关系，最终由多模态大模型依据视觉证据判定是否存在倾倒行为。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 garbage_bin_dumping 类别的其他异常事件; 无法通过开放词汇检测定位垃圾桶或相关物体的场景
- 执行边界：仅针对图像输入执行垃圾桶倾倒检测，依赖 GroundingDINO 的开放词汇检测能力与 UniDepth 的深度估计，最终由 MLLM 进行语义判断。不处理视频流、音频或非视觉模态数据。
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/garbage_bin_dumping_fd657a72e118.json`；`scripts/garbage_bin_dumping_fd657a72e118.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
