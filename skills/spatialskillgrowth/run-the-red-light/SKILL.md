---
name: run-the-red-light
description: "检测输入视频或图像中是否发生“闯红灯”异常事件。"
---

# 闯红灯

## Skill 作用

检测输入视频或图像中是否发生“闯红灯”异常事件。

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

### run_the_red_light

- ID：`run_the_red_light_5a1750356a9e`
- 选择条件：检测输入图像中是否存在车辆或行人闯红灯的异常行为。该工作流通过OCR识别交通标志文字、检测交通参与者，并结合多模态大模型分析视觉证据，判断是否发生闯红灯事件。
- 不选择：非图像类型的媒体输入; 无法清晰识别交通信号灯状态或车辆/行人位置的模糊图像; 非交通场景的图像; 需要视频时序分析而非单帧图像判断的场景
- 执行边界：{"event_type": "run_the_red_light", "media_type": "image", "required_evidence": ["交通信号灯状态（红色）", "交通参与者（车辆或行人）位置", "停止线或路口位置关系"], "tools": ["paddleOcrTool", "paddlePedriderDetTool", "MLLM"]}
- 工具链：`paddleOcrTool -> paddlePedriderDetTool -> MLLM`
- 资源：`references/workflows/run_the_red_light_5a1750356a9e.json`；`scripts/run_the_red_light_5a1750356a9e.py`

### run_the_red_light_image_baseline

- ID：`run_the_red_light_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 run_the_red_light 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/run_the_red_light_96c9e72153f7.json`；`scripts/run_the_red_light_96c9e72153f7.py`

### run_the_red_light

- ID：`run_the_red_light_dedd1e22d850`
- 选择条件：基于图像输入，通过光学字符识别提取可见文字证据，并结合多模态大模型分析视觉特征，检测是否存在闯红灯异常事件。
- 不选择：非图像类型的媒体输入; 未包含交通信号灯或车辆相关视觉信息的场景; 需要调用 embeddingTool 的处理流程
- 执行边界：{"event_type": "run_the_red_light", "media_type": "image", "required_evidence": ["paddleOcrTool 提取的可见文字", "MLLM 基于图像证据的分析结果"]}
- 工具链：`paddleOcrTool -> MLLM`
- 资源：`references/workflows/run_the_red_light_dedd1e22d850.json`；`scripts/run_the_red_light_dedd1e22d850.py`

### run_the_red_light

- ID：`run_the_red_light_ed990c3cbf1e`
- 选择条件：检测输入图像中是否存在车辆或交通参与者在红灯亮起时越过停止线或进入路口的闯红灯行为。
- 不选择：非图像类型的媒体输入（如视频流、音频或纯文本描述）；无法识别交通信号灯状态、缺乏清晰视觉特征或关键交通参与者被严重遮挡的场景；非闯红灯类别的其他交通异常事件；需要时序逻辑分析以判断信号相位变化的复杂动态场景（单帧无法确定）。
- 执行边界：依赖 paddleOcrTool 读取可见文字/信号灯状态、paddlePedriderDetTool 检测交通参与者位置、unidepth 估计检测目标深度，最终由 MLLM 依据上述视觉证据判断是否发生 run_the_red_light 异常事件。必须严格依赖工具图定义步骤，禁止调用 embeddingTool，最终判断仅基于视觉证据输出是或否。
- 工具链：`paddleOcrTool -> paddlePedriderDetTool -> unidepth -> MLLM`
- 资源：`references/workflows/run_the_red_light_ed990c3cbf1e.json`；`scripts/run_the_red_light_ed990c3cbf1e.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
