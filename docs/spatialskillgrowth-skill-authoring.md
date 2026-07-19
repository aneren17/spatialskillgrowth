# SpatialSkillGrowth 人工 Skill 编写说明

> `skills/spatialskillgrowth_whiteboard/` 是可重复生成的标准模板，禁止人工修改。本文所有人工工作都在
> `skills/spatialskillgrowth/` 下进行；重建 whiteboard 不会同步或保存人工改动。

第一次写脚本前，建议先读：

1. `docs/nodes-spatialskillgrowth/10-runtime-and-contract-tutorial.md`：逐项解释 runtime 和 contract；
2. `docs/nodes-spatialskillgrowth/09-tool-cookbook.md`：12 个工具的实际参数和组合代码；
3. `docs/nodes-spatialskillgrowth/11-exploration-skill-source.md`：探索从哪里复制 Skill。

## 1. 你的工作范围

人工维护只需要关注两个入口：

1. `SKILL.md`：说明这个 Skill 何时使用、执行原则和能力边界；
2. `scripts/<WORKFLOW_ID>.py`：实现一个可执行工作流。

验证程序会根据脚本中的 `WORKFLOW_CONTRACT` 生成
`references/workflows/<WORKFLOW_ID>.json`。不要直接维护根目录 `skill.json` 或 `workflows/`；标准
Skill 根目录只允许：

```text
skill-name/
├── SKILL.md
├── scripts/
└── references/
    ├── skill.json
    └── workflows/
```

## 2. 编写 SKILL.md

文件必须以如下 frontmatter 开始，并且只能包含 `name`、`description`：

```markdown
---
name: banner
description: "检测视频或图像中的违规横幅；当任务 event_type 为 banner 时使用。"
---
```

规则：

- `name` 必须与目录名一致，只使用小写字母、数字和连字符；
- `description` 同时说明能力和触发条件；
- 正文写执行顺序、失败降级、证据要求和能力边界；
- 主线多模态检索器会把同类别的 `SKILL.md` 作为一次公共指引读取，再结合每条工作流契约排序；
- 不把某个样本答案、任务 ID、评测切分或服务地址写进 Skill；
- 详细机器契约放在 `references/`，不要复制到正文；
- 框架更新工作流时不会覆盖已有 `SKILL.md`。

## 3. 编写脚本

脚本不能导入模块、读写文件、访问私有属性或使用 `eval/exec`。所有工具只能通过 `runtime.call` 调用。

最小模板：

```python
WORKFLOW_ID = "banner-human-review-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool",)
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_human_review",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "使用人工审阅的稳定流程检测 banner。",
    "exclusions": "不适用于其他 event_type。",
    "capability_boundary": "必须获得 embeddingTool 的判断和阈值。",
    "steps": [
        {
            "tool_name": "embeddingTool",
            "args": {
                "file_path": "$media",
                "event_type": "$slot.event_type",
            },
            "step_id": "embedding",
            "depends_on": [],
            "purpose": "检测 banner。",
        }
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
    embedding = runtime.call(
        "embeddingTool",
        {
            "file_path": runtime.media_path(),
            "event_type": event_type,
        },
        step_id="embedding",
        purpose="检测 banner。",
        depends_on=[],
    )
    runtime.require(embedding, "embedding")
    return runtime.finish(embedding)
```

必须遵守：

- 文件名必须是 `<WORKFLOW_ID>.py`；
- 必须声明 `WORKFLOW_ID`、`PROBLEM_CLASS`、`DECLARED_TOOLS`、`WORKFLOW_CONTRACT`；
- `solve` 前三个参数固定为 `runtime, question, image_paths`；
- `required_slots` 中的槽位必须作为 `solve` 的关键字参数；
- 每个 `runtime.call` 的工具和 `step_id` 必须出现在 `WORKFLOW_CONTRACT.steps`；
- `DECLARED_TOOLS`、`required_tools`、实际调用工具三者必须一致；
- 异常检测脚本必须调用 `embeddingTool`，并使用精确 `event_type`；
- 返回值必须经过 `runtime.finish(...)` 收口为“是”或“否”；
- 辅助工具失败时是否终止由脚本明确决定，不要无意间把 OCR 文本、检测框 JSON 或裁剪地址当最终答案。

## 4. Runtime API

本节只作为速查表。每个内部属性、方法返回值和完整调用过程见
`docs/nodes-spatialskillgrowth/10-runtime-and-contract-tutorial.md`。

| API | 用途 |
|---|---|
| `runtime.media_path()` | 原始视频或图像；embedding 使用它 |
| `runtime.image_path()` | 当前代表帧；图像工具使用它 |
| `runtime.filename()` | 当前代表帧文件名 |
| `runtime.call(...)` | 调用白名单工具并记录轨迹 |
| `runtime.require(result, step_id)` | 工具失败时立即抛出带步骤名的错误 |
| `runtime.value(result, field)` | 读取工具结构化字段 |
| `runtime.evidence_text()` | 汇总此前工具证据 |
| `runtime.evidence_image()` | 取得当前最佳证据图 |
| `runtime.render(value)` | 展开 `$question/$evidence/$slot.*` 等运行时引用 |
| `runtime.finish(value)` | 规范化最终答案 |

图像检测工具在视频任务中会自动对抽样帧并行执行，并把后续依赖步骤绑定到证据最好的一帧。脚本不要
自行读取或切分视频。

## 5. 验证和安装

先用 mock 工具验证目录、AST、契约、工具白名单、执行路径和异常证据：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-human-review-v1.py \
  --media test/banner.jpg \
  --event-type banner
```

验证通过并确认要发布时增加 `--install`：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script /path/to/banner-human-review-v1.py \
  --media test/banner.jpg \
  --event-type banner \
  --install
```

`--install` 会复制脚本并生成 `references/workflows/*.json`。目标脚本已存在时不会静默覆盖；人工确认
后才能增加 `--force`。

安装成功后，人工工作流会以 `mutation_mode=manual` 进入 active。它与自动生成工作流使用相同的：

- problem class、槽位、工具和答案类型硬过滤；
- retriever 排序与 top-k 执行；
- Python Skill 运行时与工具轨迹；
- embedding 异常契约和证据门。

框架不会因为脚本来自人工而额外加分，也不会因为来自自动生成而优先。人工 Skill 的优势来自更准确的
适用边界和流程设计，不是一个隐藏优先级。后续指标更新会保留脚本、`SKILL.md` 和 `authorship=human`。

最后可以增加 `--real-tools` 调用真实服务。建议按顺序执行：

1. mock 验证；
2. 一张已知图片的真实工具验证；
3. 一段短视频验证；
4. 检查 `conversation.md` 中的工具参数、失败降级和最终答案；
5. 再交给正式推理 run 使用。

## 6. 常见报错

| 报错 | 修复方法 |
|---|---|
| `Unsupported Python construct` | 删除 import、文件操作、异步或其他受限语法 |
| `WORKFLOW_ID ... expected ...` | 统一文件名、常量和 contract 中的 ID |
| `called undeclared tool` | 把工具同时加入 DECLARED_TOOLS、required_tools 和 steps |
| `step_id ... 不一致` | 统一 runtime.call 与 contract 的 step_id |
| `requires non-empty detection boxes` | 确保裁剪/深度步骤读取正确的检测结果 |
| `未返回可识别的异常判断` | 最终必须保留 embedding 的“是/否”和 threshold |
| `证据验收失败` | 查看报告中的 observations、failed_step_ids 和 traceback |

验证器返回非零退出码表示不能发布；完整 JSON 的 `errors` 是首先需要处理的反馈，`execution` 中保留
执行步骤和工具返回，Python 运行错误还会包含脚本路径与 traceback。不要只修改
`references/workflows/*.json` 来绕过失败，因为验证器会比较它和脚本内的 `WORKFLOW_CONTRACT`。
