# Runtime 与 `WORKFLOW_CONTRACT` 从零解释

本文假设读者会写普通 Python 函数，但不了解本框架。先记住一句话：

> `WORKFLOW_CONTRACT` 告诉框架“这条路线适不适合当前任务、会调用哪些工具”；`solve` 才是实际执行
> 代码；`runtime` 是 solve 唯一可以用来访问工具、媒体和历史证据的对象。

## 1. 框架怎样调用 `solve`

假设脚本定义：

```python
def solve(runtime, question, image_paths, *, event_type=""):
    ...
```

`PythonSkillExecutor` 实际做的事情可以简化为：

```python
context = SkillExecutionContext(
    tool_runtime=真实工具注册表,
    workflow=当前 WorkflowSpec,
    question=当前中文问题,
    image_paths=图片或抽样帧列表,
    slot_bindings={"event_type": "banner"},
    media_path=原始视频或图片,
)

solve(
    runtime=context,
    question=当前中文问题,
    image_paths=图片或抽样帧列表,
    event_type="banner",
)
```

实习生不创建 runtime，也不传这些参数。框架会根据 contract 的 required slots 和 Planner 的槽位自动
注入。

外层 `PythonSkillExecutor` 还有一个公开实现属性 `tool_runtime`，保存底层 `ToolRuntime`。它由
`ExperimentFactory` 创建，实习生脚本拿到的是 `SkillExecutionContext`，不应绕过 context 直接访问该
属性。

## 2. Runtime 内部属性逐个解释

这些属性以下划线开头，Skill 脚本禁止直接访问；这里解释它们是为了理解公开方法为什么这样工作。

| 内部属性 | banner 图片例子 | 用途 |
|---|---|---|
| `_tool_runtime` | 含 12 个工具的 `ToolRuntime` | 真正执行 `tool.invoke` 并统一返回格式 |
| `_workflow` | `banner-human-review-v1` 的 WorkflowSpec | 决定允许调用哪些工具、最终记录哪个 workflow ID |
| `_question` | “请检测……banner……” | `render("$question")` 和 MLLM query 的来源 |
| `_image_paths` | `[".../banner.jpg"]` | 图片输入；视频时是按时间排序的抽样帧列表 |
| `_media_path` | `.../banner.jpg` 或原始 `.mp4` | embedding 专用原媒体通道 |
| `_selected_image_path` | 当前代表帧 | OCR、检测器、MLLM 默认看的图片 |
| `_slots` | `{"event_type": "banner", ...}` | 展开 `$slot.event_type` 等运行时参数 |
| `_allowed_tools` | `{embeddingTool, paddleOcrTool, MLLM}` | 阻止脚本调用 contract 未声明工具 |
| `_observations` | 按调用顺序保存的工具轨迹列表 | evidence validator、conversation、`evidence_text()` 使用 |
| `_results` | `{step_id: 统一结果}` | 展开 `$step.embedding.threshold` |
| `_previous` | 最近一次成功工具的 `content` | 展开 `$previous` |

视频时 `_selected_image_path` 初始取抽样帧中间一张。若某图片工具对全部帧并行执行，Runtime 会根据
检测数量、最大置信度、是否有结果图和文本长度选出更好的帧，并更新该属性。

## 3. Runtime 公开方法逐个解释

### `runtime.call(...)`

```python
result = runtime.call(
    tool_name="embeddingTool",
    args={"file_path": runtime.media_path(), "event_type": event_type},
    step_id="embedding",
    purpose="取得异常判断和阈值。",
    depends_on=[],
)
```

参数含义：

- `tool_name`：必须同时出现在 `DECLARED_TOOLS`、contract `required_tools` 和某个 step 中；
- `args`：实际传给工具的参数。embedding 的 file path 会被强制改成原媒体；
- `step_id`：本 Workflow 唯一键，结果会存入 `_results[step_id]`；
- `purpose`：只用于轨迹说明，不改变工具行为；
- `depends_on`：写入轨迹表达逻辑依赖。Python 脚本仍按代码顺序执行，必须配合 `require` 或 `if` 自己
  处理依赖失败。

返回值永远是统一字典，不会直接抛出服务异常：

```json
{
  "ok": false,
  "status": "error",
  "tool": "groundingdino",
  "content": "",
  "data": {},
  "error": "ConnectionError: ..."
}
```

只有调用未声明工具等脚本契约错误才会由 Runtime 抛异常。

### `runtime.require(result, step_id)`

```python
runtime.require(embedding, "embedding")
```

若 `result["ok"]` 为 false，立即抛 `SkillStepExecutionError`，当前 Workflow 失败。适合主判断或后续必须
依赖的检测框。不适合可有可无的 OCR/MLLM。

### `runtime.value(result, field, default="")`

```python
boxes = runtime.value(detect, "detections", [])
threshold = runtime.value(embedding, "threshold", None)
raw_text = runtime.value(ocr, "content", "")
```

先找结果顶层字段，再找 `result["data"]`。这样脚本不需要知道 `content` 在顶层、`detections` 在 data。

### `runtime.media_path()`

返回唯一原媒体。图片任务是原图，视频任务是 `.mp4`。主要给 embedding：

```python
{"file_path": runtime.media_path()}
```

### `runtime.image_path()`

返回当前代表图片。图片任务是原图；视频任务是当前选中的抽样帧。给 OCR、YOLO、SAM3、GroundingDINO
等图片工具。

### `runtime.filename(image_path="")`

返回 basename：

```python
runtime.filename()                         # frame_003_0003500ms.jpg
runtime.filename(runtime.media_path())    # input.mp4
runtime.filename(crop_image)              # crop_0.jpg
```

### `runtime.evidence_text()`

把之前 observations 压成一段文本，例如：

```text
embedding [success]:
是 (判定阈值: 0.66)

ocr [success]:
施工区域 严禁入内
```

可以传给 MLLM，但注意文本可能较长，框架默认保留末尾约 6000 字符。

### `runtime.evidence_image()`

从最近工具结果倒序找 `data.image`，优先返回裁剪图、相对裁剪图、SAM 掩码图或检测结果图；都没有时
返回当前代表帧。

### `runtime.render(value)`

递归展开 contract 风格引用：

| 输入 | 运行时结果 |
|---|---|
| `$media` | 原视频/原图路径 |
| `$image` | 当前代表帧 |
| `$frames` | 全部抽样帧列表 |
| `$filename` | 代表帧文件名 |
| `$question` | 当前问题 |
| `$previous` | 上一次成功工具文本 |
| `$evidence` | 累积证据文本 |
| `$evidence_image` | 当前最佳证据图 |
| `$slot.event_type` | `banner` |
| `$step.embedding.threshold` | `0.66` |

普通脚本优先使用明确方法；只有字符串里混合多个引用时才需要 render：

```python
query = runtime.render("类别=$slot.event_type；证据如下：$evidence")
```

### `runtime.finish(value)`

把工具结果或文本收口成最终答案：

```python
return runtime.finish(embedding)                 # "是"
return runtime.finish("Final answer: 否")        # "否"
return runtime.finish({"answer": "是"})         # "是"
```

它只提取答案，不会自动补 threshold。threshold 保留在 observations，最后由
`extract_anomaly_result` 加入执行结果。

### `runtime.result(...)`

这是 Executor 内部在 solve 结束后调用的方法，实习生通常不直接调用。它生成：

```json
{
  "success": true,
  "final_answer": "是",
  "observations": [],
  "used_tools": ["embeddingTool"],
  "valid_step_ids": ["embedding"],
  "failed_step_ids": [],
  "error": "",
  "script_path": ".../script.py",
  "script_traceback": "",
  "workflow_id": "banner-human-review-v1",
  "execution_backend": "python_skill",
  "event_type": "banner",
  "is_anomaly": true,
  "threshold": 0.66
}
```

## 4. 脚本顶部四个常量

```python
WORKFLOW_ID = "banner-human-review-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool", "paddleOcrTool", "MLLM")
WORKFLOW_CONTRACT = {...}
```

| 常量 | 意义 |
|---|---|
| `WORKFLOW_ID` | 路线唯一 ID；必须等于文件名，不要用中文或空格 |
| `PROBLEM_CLASS` | 精确异常类别 ID；必须与 Skill 目录对应，例如 `fire_door_unclosed` 对应目录 `fire-door-unclosed` |
| `DECLARED_TOOLS` | 该脚本允许调用的全部工具，不能少写也不能多写 |
| `WORKFLOW_CONTRACT` | Retriever、验证器和 Repository 使用的机器契约 |

Exporter 生成脚本还会包含 `WORKFLOW_GRAPH_SHA256`，用于记录生成时工具图哈希；人工新脚本不是必需。

## 5. `WORKFLOW_CONTRACT` 顶层属性逐个解释

完整形状：

```python
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_human_review",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合什么情况，以及大致怎么做。",
    "exclusions": "明确不适合什么情况。",
    "capability_boundary": "成功所需证据和失败降级边界。",
    "steps": [],
}
```

### `workflow_id`

必须与 `WORKFLOW_ID` 和脚本文件名一致。作用是 Repository 查 JSON/Python、Retriever 返回候选 ID、轨迹
标记执行路线。

### `name`

给人看的短名称，不是唯一 ID。建议小写下划线，例如 `banner_text_assisted_review`。修改它不会改变文件
路径，但会影响 Retriever 看到的候选描述。

### `problem_class`

精确后端类别。Retriever 第一层只读取同 class 的 Workflow，不能写中文别名。

### `required_slots`

执行前必须有值的运行时变量。异常 Skill 通常是 `["event_type"]`。每个 required slot 还必须出现在
solve 的关键字参数中：

```python
def solve(runtime, question, image_paths, *, event_type=""):
```

若写 `required_slots=["target"]` 但 solve 没有 `target` 参数，验证失败。

### `required_tools`

运行前必须注册的工具集合。它必须与 `DECLARED_TOOLS` 和 steps 中工具集合完全相同。若某工具只是可选
调用，它仍需声明，因为 Runtime 白名单在脚本执行前确定。

### `description`

回答“什么任务适合这条路线”。应该写证据和流程，不要写某个样本答案。例如：

```text
适合画面中的横幅文字可能影响判断，需要 embedding 主判断并用 OCR 补充可审计文字证据的 banner 任务。
```

### `exclusions`

回答“即使类别相同，什么情况也不适合”。例如：

```text
不适用于 banner 以外类别；不适用于完全不可见文字且必须依赖 OCR 才能工作的场景。
```

### `capability_boundary`

回答“这条路线成功依赖什么，失败时如何降级”。例如：

```text
embedding 必须成功并返回阈值；OCR 和 MLLM 失败时可降级，不能反转 embedding 结论。
```

这三个自然语言字段会被主线多模态 Retriever 使用；不要只写“用于 banner”，否则多条 banner 路线之间
无法区分。

### `steps`

声明工具 DAG。它不是可执行代码替代品，而是用于：

- 判断 required tools 是否可用；
- 判断工具输入输出能否衔接；
- Retriever 查看证据链；
- 合并器比较两条路线结构；
- 验证实际脚本没有调用未声明工具。

## 6. 每个 step 属性逐个解释

```python
{
    "tool_name": "embeddingTool",
    "args": {
        "file_path": "$media",
        "event_type": "$slot.event_type",
    },
    "step_id": "embedding",
    "depends_on": [],
    "purpose": "取得异常判断和阈值。",
    "param_atoms": [],
}
```

| 属性 | 意义 |
|---|---|
| `tool_name` | 精确注册名，必须出现在 required/declared tools |
| `args` | 机器可读参数模板，使用 `$media/$image/$slot.*` 等引用 |
| `step_id` | Workflow 内唯一 ID；实际 `runtime.call` 必须使用同一个 ID |
| `depends_on` | DAG 的前置 step ID；不能引用不存在或后面的步骤 |
| `purpose` | 说明为什么调用，进入 Retriever 和 conversation |
| `param_atoms` | 自动探索使用的参数原子记录；人工脚本通常省略或为空 |

contract 的 `args` 与 solve 的实际参数必须表达同一件事：

```python
# contract
{"file_path": "$media", "event_type": "$slot.event_type"}

# solve
{"file_path": runtime.media_path(), "event_type": event_type}
```

## 7. 一份可直接理解的完整脚本

```python
WORKFLOW_ID = "banner-simple-human-v1"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("embeddingTool", "paddleOcrTool")
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_simple_human",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "用 embedding 判断 banner，并用 OCR 补充可见文字。",
    "exclusions": "不适用于 banner 以外类别。",
    "capability_boundary": "embedding 必须成功；OCR 可以失败并降级。",
    "steps": [
        {
            "tool_name": "embeddingTool",
            "args": {"file_path": "$media", "event_type": "$slot.event_type"},
            "step_id": "embedding",
            "depends_on": [],
            "purpose": "取得主判断和阈值。",
        },
        {
            "tool_name": "paddleOcrTool",
            "args": {"file": "$image", "filename": "$filename"},
            "step_id": "ocr",
            "depends_on": [],
            "purpose": "读取可见文字。",
        },
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
    embedding = runtime.call(
        "embeddingTool",
        {"file_path": runtime.media_path(), "event_type": event_type},
        step_id="embedding",
        purpose="取得主判断和阈值。",
        depends_on=[],
    )
    runtime.require(embedding, "embedding")

    runtime.call(
        "paddleOcrTool",
        {"file": runtime.image_path(), "filename": runtime.filename()},
        step_id="ocr",
        purpose="读取可见文字。",
        depends_on=[],
    )

    return runtime.finish(embedding)
```

这里 OCR 的结果没有参与最终答案，这是有意的：它进入 observations 和 conversation，供人工审计或后续
MLLM 使用，但异常结论仍来自 embedding。

## 8. 常见理解错误

| 错误理解 | 实际情况 |
|---|---|
| contract 写了 step，工具就会自动执行 | 不会，实际执行只看 solve |
| solve 调一个新工具，不改 contract 也可以 | 不可以，Runtime 和验证器会拒绝 |
| `depends_on` 会自动跳过失败步骤 | Python 脚本不会；要用 require 或 if |
| `runtime.image_path()` 对视频返回视频 | 不会，返回代表帧；视频用 media_path |
| OCR/MLLM 可以替代 embedding 阈值 | 不可以，异常 evidence contract 会拒绝 |
| description 越长越好 | 不对，应明确适用条件和证据差异，避免样本细节 |
| `runtime.finish` 会执行证据验收 | 不会；它只抽答案，证据验收在脚本结束后发生 |
