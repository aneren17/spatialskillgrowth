---
name: banner
description: "检测视频或图像中是否出现违规横幅，并输出 embeddingTool 的异常判断和判定阈值；当任务给定精确 event_type `banner`，或要求识别违规横幅、横幅异常时使用。"
---

# 违规横幅检测

## 执行流程

1. 保持调用方给出的精确 `event_type=banner`，不要重新分类。
2. 始终先用 `embeddingTool` 处理原始视频或图像，取得“是/否”和 `threshold`。
3. 对图片或视频代表帧按需执行 OCR 和 MLLM，补充可见文字与视觉证据。
4. 辅助工具失败时保留 embedding 结论，不要把 OCR 文本、检测框 JSON 或文件地址当成最终答案。
5. 最终只输出“是”或“否”，并在结构化结果中保留 `event_type`、`is_anomaly`、`threshold`。

## 人工脚本

- 优先使用 `scripts/banner-human-review-v1.py` 作为人工审阅的稳定路线。
- 运行或修改脚本前阅读项目级 `docs/spatialskillgrowth-skill-authoring.md`。
- 修改后必须运行 `scripts.validate_spatialskillgrowth_skill`；验证失败时不得发布。
- 机器契约和工作流历史位于 `references/`，按需读取，不要手工复制到本文。

## 能力边界

- 只处理 `banner`，不扩展到旗帜、广告牌倒塌或其他事件类别。
- OCR 与 MLLM 只提供补充证据；embedding 返回失败、类别不一致或缺少阈值时不得接受结果。
- 当前样本数量有限，人工脚本不能替代不同场景正负样本的后续验证。
