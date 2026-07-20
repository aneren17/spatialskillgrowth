# 证据和人工 Skill 验证

`AnomalyEvidenceValidator.validate(event_type, question, answer, result, media_paths)` 检查：单媒体、执行成功、
实际调用 embedding、类别一致、有布尔判断、最终答案一致、阈值为数值。任何一项失败都拒绝候选。

已删除“无证据”“纯语义”“数值题”等验证策略。

`validate_human_skill` 只检查标准目录、frontmatter、安全 AST、脚本常量、`solve` 签名、脚本工具调用与
`WORKFLOW_CONTRACT` 一致性，最后用确定性 mock 执行一次并确认返回“是”或“否”。它不会进入异常证据
门、调用真实工具或写入 Skill 文件。

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

框架没有 Omni3D 评测适配器。批量结果统一写 `per_task.jsonl`、`per_task.csv` 和 `metrics/summary.json`。
