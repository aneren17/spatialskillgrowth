---
name: billboard-fell
description: "检测输入视频或图像中是否发生“广告牌倒塌”异常事件。"
---

# 广告牌倒塌

## Skill 作用

检测输入视频或图像中是否发生“广告牌倒塌”异常事件。

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

### billboard_fell_detector

- ID：`billboard_fell_45c056ca779c`
- 选择条件：检测输入静态图像中是否发生广告牌倒塌异常事件。通过 groundingdino 定位广告牌目标，利用 unidepth 估计其深度信息以分析空间姿态，最后由多模态大模型综合视觉与深度证据判断是否存在倒塌状态。
- 不选择：非静态图像输入（如视频流、实时动态监测）; 未包含广告牌或类似大型户外广告结构的场景; 需要调用 embeddingTool 进行特征提取的任务; 其他类型的异常事件检测（如火灾、交通事故、其他结构倒塌或物体坠落等）; groundingdino 检测失败导致无法获取目标实例的场景
- 执行边界：基于开放词汇检测定位目标，结合深度估计分析空间结构与姿态，最终由多模态模型判定倒塌状态；仅支持静态图像输入，输出为二元判定结果，严格限定于广告牌倒塌事件。
- 工具链：`groundingdino -> unidepth -> MLLM`
- 资源：`references/workflows/billboard_fell_45c056ca779c.json`；`scripts/billboard_fell_45c056ca779c.py`

### billboard_fell_image_baseline

- ID：`billboard_fell_96c9e72153f7`
- 选择条件：使用单张图片或视频代表帧判断 billboard_fell 异常事件。
- 不选择：不处理原始视频时序，只依据当前图片证据。
- 执行边界：必须取得 MLLM 基于可见画面的明确判断。
- 工具链：`MLLM`
- 资源：`references/workflows/billboard_fell_96c9e72153f7.json`；`scripts/billboard_fell_96c9e72153f7.py`

<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
