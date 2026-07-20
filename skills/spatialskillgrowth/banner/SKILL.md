---
name: banner
description: "检测输入视频或图像中是否发生“违规横幅检测”异常事件。"
---

# 违规横幅检测

## Skill 作用

检测输入视频或图像中是否发生“违规横幅检测”异常事件。

## 工作流选择

- 横幅文字清晰、需要核对文字内容时，选择 OCR 辅助工作流。
- 横幅目标较小、整图难以辨认时，选择“定位 -> 裁剪 -> MLLM”工作流。
- 定位工具不能稳定返回检测框时，不选择依赖裁剪的工作流。
- 辅助路线不适用于 `flag`、`billboard_fell` 等其他异常类别。

<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

当前没有可检索工作流。
<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->

## 资源

- `references/workflows/*.json`：工作流详细机器契约。
- `scripts/*.py`：工作流执行脚本。
- `references/skill.json`：Skill 和工作流索引。
- `scripts/banner-ocr-example.py`：OCR 辅助路线的人工 mock 示例。
- `scripts/banner-crop-example.py`：定位和裁剪路线的人工 mock 示例。
