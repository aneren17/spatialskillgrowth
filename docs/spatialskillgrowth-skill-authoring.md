# SpatialSkillGrowth 人工 Skill 编写说明

人工编写只需要完成两件事：

1. 修改当前类别的 `SKILL.md`；
2. 编写 `scripts/<WORKFLOW_ID>.py`，并通过确定性 mock 验证。

验证器不会调用真实工具、读取真实图片或视频、执行效果评测、生成 Workflow JSON、复制文件或修改索引。
mock 通过后，是否长期保存、保存到哪个 Skill 或白板目录，由负责人手动决定。

`skills/spatialskillgrowth_whiteboard/` 仍是构建脚本生成的标准空模板。验证器不会修改它；如果人工决定把
脚本复制进去，需要自行承担下次重建 whiteboard 时被覆盖的风险。

## 1. 需要阅读的文件

1. 本文：最短人工编写流程；
2. [09-tool-cookbook.md](nodes-spatialskillgrowth/09-tool-cookbook.md)：12 个工具的全部
   `runtime.call` 示例；
3. [10-runtime-and-contract-tutorial.md](nodes-spatialskillgrowth/10-runtime-and-contract-tutorial.md)：
   Runtime 和 `WORKFLOW_CONTRACT` 的逐项解释；
4. [12-manual-workflow-tutorial.md](nodes-spatialskillgrowth/12-manual-workflow-tutorial.md)：从空脚本开始的
   连续教程。

可直接参考：

- `skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py`
- `skills/spatialskillgrowth/banner/scripts/banner-crop-example.py`

## 2. 标准目录

```text
skill-name/
├── SKILL.md
├── scripts/
│   └── <WORKFLOW_ID>.py
└── references/
    ├── skill.json
    └── workflows/
```

人工日常只修改 `SKILL.md` 和 `scripts/*.py`。`references/` 可以保留模板或已经存在的运行快照，但 mock
验证不会读取旧 Workflow JSON 来覆盖脚本中的 `WORKFLOW_CONTRACT`，也不会向其中写入内容。

## 3. `SKILL.md`

frontmatter 只能包含 `name` 和 `description`：

```markdown
---
name: banner
description: "检测输入视频或图像中是否发生违规横幅异常事件。"
---
```

正文是该类别下所有工作流的简明使用说明书，不写接口元数据、显示名称、工具调用参数或某一张样本
的答案。只保留四部分：

1. `Skill 作用`：一句话说明检测什么异常；
2. `工作流选择`：说明不同画面和证据条件下选择哪类路线；
3. `可选工作流`：由 Repository 自动生成每条正式工作流的选择条件；
4. `资源`：列出 Workflow JSON、Python 脚本和 Skill 索引的位置。

event type、别名、工具模板和通用证据要求保存在 `references/skill.json`，不在 `SKILL.md` 重复。

Retriever 会读取 run 内 active Skill 的正文，结合当前抽帧和候选 Workflow JSON 进行 Top-K 排序。
下面的标记区由 Repository 自动维护，不要手工删除标记：

```markdown
<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->
## 可选工作流

这里会生成每条工作流的选择条件、不选择条件、执行边界、工具链和资源路径。
<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->
```

人工可以修改标记区外的类别说明和选择原则。探索保存、晋升或更新工作流时，只替换标记区。

## 4. 最小脚本

```python
WORKFLOW_ID = "banner-minimal-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool",)
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_minimal_example",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "直接使用 embeddingTool 判断 banner。",
    "exclusions": "不适用于 banner 以外类别。",
    "capability_boundary": (
        "必须取得 embeddingTool 的是或否和 threshold；"
        "工具失败时本路线直接失败，没有备用判断。"
    ),
    "steps": [
        {
            "tool_name": "embeddingTool",
            "args": {
                "file_path": "$media",
                "event_type": "$slot.event_type",
            },
            "step_id": "embedding",
            "depends_on": [],
            "purpose": "取得异常判断和阈值。",
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
        purpose="取得异常判断和阈值。",
        depends_on=[],
    )
    runtime.require(embedding, "embedding")
    return runtime.finish(embedding)
```

必须满足：

```text
脚本文件名 = WORKFLOW_ID + ".py"

DECLARED_TOOLS
    = WORKFLOW_CONTRACT["required_tools"]
    = WORKFLOW_CONTRACT["steps"] 中的工具集合
    = solve 中 runtime.call 的工具集合
```

`solve` 的前三个参数固定为 `runtime, question, image_paths`。`required_slots` 中的每个名字还必须作为
`solve` 参数出现。

## 5. `runtime.call`

```python
result = runtime.call(
    "paddleOcrTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
    },
    step_id="ocr",
    purpose="读取画面文字。",
    depends_on=[],
)
```

五部分分别表示：

| 部分 | 真正作用 |
|---|---|
| `"paddleOcrTool"` | 精确工具注册名；不一致时直接拒绝 |
| 参数字典 | 真正传给工具的参数 |
| `step_id` | 当前 Workflow 内的步骤名；必须和 contract 一致 |
| `purpose` | 写入轨迹，帮助人理解为什么调用；不改变工具结果 |
| `depends_on` | 记录逻辑依赖；不会自动替你写 `if` 或停止执行 |

返回值统一为：

```json
{
  "ok": true,
  "status": "success",
  "tool": "paddleOcrTool",
  "content": "识别到的文字",
  "data": {
    "detections": [],
    "image_refs": [],
    "image": ""
  },
  "error": ""
}
```

读取结构化值使用：

```python
text = runtime.value(result, "content", "")
boxes = runtime.value(result, "detections", [])
images = runtime.value(result, "image_refs", [])
```

## 6. `runtime.require` 到底做什么

```python
runtime.require(result, "detect")
```

它只做一件事：检查 `result["ok"]`。

- 为 `true`：什么也不返回，继续执行；
- 为 `false`：抛出带 `step_id` 的错误，当前 Workflow 立即失败；
- 它不会重试工具；
- 它不会检查检测框是否符合业务含义；
- 它不会判断最终答案是否正确；
- 它和 `required_tools` 不是同一概念。`required_tools` 是工具白名单，`require` 是运行时失败策略。

必须依赖上一步结果时使用：

```python
detect = runtime.call(...)
runtime.require(detect, "detect")
boxes = runtime.value(detect, "detections", [])
```

有备用路线时不要使用：

```python
ocr = runtime.call(...)
if ocr.get("ok"):
    text = runtime.value(ocr, "content", "")
```

## 7. `runtime.finish` 到底做什么

```python
return runtime.finish(embedding)
```

它只把一个工具结果或文本提取成最终短答案，最常见结果是“是”或“否”。

它不会：

- 调用任何工具或模型；
- 检查前面步骤是否成功；
- 执行证据验收；
- 生成或修改 threshold；
- 自动保存 Workflow；
- 结束整个 Agent，只是给当前 `solve` 生成返回值。

因此应把真正包含结论的结果传给它：

```python
return runtime.finish(embedding)
```

不要把 OCR 文本、检测框 JSON 或裁剪图片地址传给它：

```python
return runtime.finish(ocr)   # 错误：OCR 不是异常判断
return runtime.finish(crop)  # 错误：crop 返回图片，不是是或否
```

mock 验证会要求最终结果必须恰好是“是”或“否”。

## 8. `evidence_image` 和多张图片

`runtime.evidence_image()` 的返回值永远是一张图片路径。它从最近的工具结果向前查找：

1. 最近一次结果中的第一张 `data.image`；
2. 如果没有结果图，返回当前代表帧。

这样设计是因为当前 `MLLM` 的 `file` 参数只接受一张图片。

多图来源要分开处理：

### 视频抽样帧

`image_paths` 是全部抽样帧。GroundingDINO、YOLO、OCR、Paddle 检测器和 SAM3 会由 Runtime 自动在多帧
上执行，并选出证据较好的一帧。通常不需要自己循环。

### crop 返回多张图

```python
crop_images = runtime.value(crop, "image_refs", [])
first_crop = crop_images[0] if crop_images else runtime.evidence_image()
```

当前 MLLM 不接受图片列表，所以有三种做法：

1. 通常直接使用 `runtime.evidence_image()` 选中的第一张；
2. 按业务规则从 `image_refs` 中选一张；
3. 确实要逐张查看时，在 contract 中声明多个固定 MLLM step，再分别调用。不要把列表直接传给
   `file`，也不要动态生成 contract 中不存在的 `step_id`。

## 9. `capability_boundary` 怎么写

它不是“这个模型大概能做什么”的宣传语，而是当前 Workflow 的运行边界。必须回答四个具体问题：

1. 哪一步必须成功？
2. 它必须产出什么字段？
3. 哪些步骤允许失败？
4. 失败后是降级、跳过，还是整条 Workflow 失败？

不合格：

```text
能力有限，只适用于 banner。
```

合格的 OCR 路线：

```text
embeddingTool 必须成功并返回是或否和 threshold；OCR、MLLM 是可选证据，
文字不可见或辅助工具失败时仍返回 embeddingTool 的判断。
```

合格的 crop 路线：

```text
embeddingTool 必须成功；GroundingDINO 必须返回非空检测框后才能调用 crop。
没有框、裁剪失败或 MLLM 失败时停止辅助链，最终返回 embeddingTool 的判断。
```

`description` 回答“什么时候值得选这条路线”，`exclusions` 回答“什么情况下不要选”，
`capability_boundary` 回答“选中以后，哪些结果是继续执行的必要条件”。

## 10. 12 个工具速查

| 工具 | 主要输入 | 主要输出 | 常见下游 |
|---|---|---|---|
| `embeddingTool` | 原视频/原图、event_type | 是/否、threshold | 最终答案 |
| `MLLM` | 一张图片、query | 文本回答 | `finish` 或辅助说明 |
| `paddleOcrTool` | 图片 | OCR 文本 | MLLM |
| `groundingdino` | 图片、英文目标 | 像素检测框、结果图 | crop、relative crop、depth |
| `yoloTool` | 图片、阈值 | COCO 检测框、结果图 | crop、relative crop、depth |
| `paddleHeadDetTool` | 图片 | 人头框 | 计数、crop |
| `paddlePedriderDetTool` | 图片 | 行人/骑行者/车辆框 | crop、布局分析 |
| `sam3` | 图片、1～3 个英文词 | 分割图、检测框 | crop、MLLM |
| `crop_detections` | 图片、像素框 | 一张或多张裁剪图 | OCR、MLLM |
| `picRelativeCut` | 图片、检测框 | 保持相对关系的裁剪图 | MLLM |
| `unidepth` | 图片、检测框 | 目标深度 | sandbox、MLLM |
| `python_code_sandbox` | Python 代码字符串 | stdout/计算结果 | MLLM 或规则判断 |

每个工具的完整参数和可复制 `runtime.call` 代码见
[09-tool-cookbook.md](nodes-spatialskillgrowth/09-tool-cookbook.md)。

## 11. 只运行 mock 验证

OCR 示例：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

crop 示例：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-crop-example.py
```

验证内容只有：

```text
标准目录和 SKILL.md frontmatter
    -> Python AST 安全限制
    -> WORKFLOW_CONTRACT 与脚本调用一致
    -> 确定性 mock 工具执行 solve
    -> 最终返回值是“是”或“否”
```

通过报告：

```json
{
  "valid": true,
  "checks": {
    "standard_skill_layout": true,
    "safe_python_ast": true,
    "script_contract": true,
    "mock_execution": true
  },
  "errors": []
}
```

没有 `--media`、`--event-type`、`--real-tools`、`--install` 或 `--force`。验证器不会永久保存任何内容。

mock 通过只说明脚本结构和控制流能运行，不说明真实工具可用，也不说明异常检测效果正确。
