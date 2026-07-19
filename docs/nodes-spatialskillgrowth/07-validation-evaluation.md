# 证据和人工 Skill 验证

`AnomalyEvidenceValidator.validate(event_type, question, answer, result, media_paths)` 检查：单媒体、执行成功、
实际调用 embedding、类别一致、有布尔判断、最终答案一致、阈值为数值。任何一项失败都拒绝候选。

已删除“无证据”“纯语义”“数值题”等验证策略。

`validate_human_skill` 检查标准目录、frontmatter、安全 AST、脚本常量、`solve` 签名、脚本工具调用与 JSON
图一致性，最后用模拟工具真实执行一次并经过同一个异常证据门。

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-human-review-v1.py \
  --media benchmark/anomaly/banner_demo/images/banner_00_00252ms.jpg \
  --event-type banner
```

框架没有 Omni3D 评测适配器。批量结果统一写 `per_task.jsonl`、`per_task.csv` 和 `metrics/summary.json`。
