---
name: foreign-objects-on-transmission-lines
description: "检测输入视频或图像中是否发生“输电线路异物”异常事件。"
---

# 输电线路异物

## Skill 作用

检测输入视频或图像中是否发生“输电线路异物”异常事件。

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

### foreign_objects_on_transmission_lines

- ID：`foreign_objects_on_transmission_lines_31a8b0597407`
- 选择条件：基于图像输入，利用开放词汇目标检测（GroundingDINO）定位潜在异物，并结合多模态大模型（MLLM）分析视觉证据，判断输电线路是否存在异物附着异常。
- 不选择：非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非输电线路场景（如配电线路、通信光缆等，除非工具图槽位明确支持泛化）; 未包含 groundingdino 和 MLLM 工具依赖的运行环境
- 执行边界：{"event_type": "foreign_objects_on_transmission_lines", "media_type": "image", "detection_threshold": 0.3, "evidence_requirement": "必须通过 groundingdino 检测到的目标框及 MLLM 对图像内容的语义分析作为判断依据", "output_format": "二元分类（是/否）"}
- 工具链：`groundingdino -> MLLM`
- 资源：`references/workflows/foreign_objects_on_transmission_lines_31a8b0597407.json`；`scripts/foreign_objects_on_transmission_lines_31a8b0597407.py`

### foreign_objects_on_transmission_lines

- ID：`foreign_objects_on_transmission_lines_96c9e72153f7`
- 选择条件：基于多模态大模型（MLLM）对输入图像（含视频代表帧）进行视觉分析，检测输电线路本体是否存在异物附着或悬挂异常（如风筝、塑料布等），并基于视觉证据判断是否发生该异常事件。
- 不选择：非图像类型的媒体输入（如纯文本、音频或原始视频时序流）; 未包含输电线路主体的图像场景; 需要调用 embeddingTool 的场景; 非输电线路异物类别的异常检测任务（如断线、塔材缺失等）; 缺乏明确视觉证据支持的模糊场景; 需要输出详细分析报告而非二分类结果的任务
- 执行边界：输入媒体仅限图像；目标事件类型严格限定为输电线路异物检测；输出格式为二分类结果；必须通过图像工具和多模态模型收集可复用的视觉证据以支持判断；仅使用 MLLM 工具，禁止使用 embeddingTool。
- 工具链：`MLLM`
- 资源：`references/workflows/foreign_objects_on_transmission_lines_96c9e72153f7.json`；`scripts/foreign_objects_on_transmission_lines_96c9e72153f7.py`

### foreign_objects_on_transmission_lines_detector

- ID：`foreign_objects_on_transmission_lines_ad5cbcebbbeb`
- 选择条件：检测输电线路图像中是否存在悬挂、缠绕或附着在导线、绝缘子串或杆塔结构上的非标准异物（如塑料薄膜、风筝线、树枝、鸟巢等）。该工作流首先通过代码沙箱提取图像中的结构化视觉特征摘要，随后利用多模态大模型结合这些证据，严格判定是否发生‘输电线路异物’异常事件。
- 不选择：非图像格式的输入数据（如纯文本、音频或视频流）。; 未包含输电线路核心组件（导线、绝缘子、杆塔）的图像。; 需要识别异物具体材质、品牌或来源的任务。; 需要评估异物对电网安全具体风险等级或量化影响的任务。; 其他类型的电力设施异常（如绝缘子破损、金具锈蚀、导线断股等，除非明确归类为异物附着）。
- 执行边界：{"input_constraints": {"media_type": "image", "format_requirements": "支持常见图像格式（如JPEG, PNG），需清晰展示输电线路局部或整体视图。"}, "detection_scope": {"target_objects": "输电线路上的非预期附着物或悬挂物。", "excluded_objects": "输电线路的标准组成部分（如防震锤、间隔棒、标准绝缘子串等，除非其状态异常且被归类为异物干扰）。"}, "output_format": {"type": "binary", "values": ["是", "否"]}, "tool_dependencies": ["python_code_sandbox: 用于生成图像的结构化证据摘要。", "MLLM: 用于基于视觉证据进行最终异常判定。"]}
- 工具链：`python_code_sandbox -> MLLM`
- 资源：`references/workflows/foreign_objects_on_transmission_lines_ad5cbcebbbeb.json`；`scripts/foreign_objects_on_transmission_lines_ad5cbcebbbeb.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
