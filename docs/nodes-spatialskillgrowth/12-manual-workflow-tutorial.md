# 手工编写一条异常检测工作流

本文以 `banner` 为例。人工编写的完成标准只有：

1. `SKILL.md` 符合标准格式；
2. Python 脚本通过确定性 mock 验证。

不要求实习生调用真实工具、准备真实媒体、验证检测效果、生成 Workflow JSON、更新索引或安装工作流。
mock 通过后，由负责人手动复制需要长期保留的 `SKILL.md` 和脚本。

下面含 `embeddingTool` 的示例全部是视频专用路线。图片路线必须删除 embedding 步骤，以 MLLM 或
其他图像工具处理原图；视频抽样帧也不能传给 embedding。

## 1. 人工负责哪些文件

```text
skills/spatialskillgrowth/banner/
├── SKILL.md
├── scripts/
│   ├── banner-ocr-example.py
│   └── banner-crop-example.py
└── references/
    ├── skill.json
    └── workflows/
```

人工主要修改：

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 说明整个异常类别共同遵守的规则 |
| `scripts/<WORKFLOW_ID>.py` | 定义一条具体工具调用路线 |

`references/` 可以保留标准模板或运行快照。mock 验证器不会生成、覆盖或安装其中的文件。

`skills/spatialskillgrowth_whiteboard/` 是构建脚本产生的标准模板。验证器不会修改它。若负责人决定把人工
结果复制到某个长期白板，需要手动操作，并注意标准 whiteboard 被重建时会整体覆盖。

## 2. 先决定工具路线

写代码前回答四个问题：

1. 哪个工具产生最后的“是/否”？
2. 哪些工具只补充证据？
3. 哪一步失败后，后面已经没有执行意义？
4. 可选工具失败时返回什么？

OCR 示例：

```text
图片/视频抽样帧
    -> paddleOcrTool -----------> 可见文字
    -> MLLM --------------------> 最终“是/否”
```

crop 示例：

```text
图片/视频抽样帧
    -> groundingdino -> crop_detections
                         -> MLLM -------------> 最终“是/否”
```

这两条示例路线都不调用 embedding，最终答案来自 MLLM。视频推理时框架会把它们应用到抽样帧，
并与原视频 embedding 并行执行，最后按 OR 规则汇总。

## 3. 编写 `SKILL.md`

frontmatter 只能包含 `name` 和 `description`：

```markdown
---
name: banner
description: "检测视频中的违规横幅；当 event_type 为 banner 时使用。"
---
```

`name` 必须与目录名一致。正文至少说明：

- 精确 `event_type`；
- 主判断工具和输出格式；
- 相近但不属于当前 Skill 的类别；
- OCR、crop 等路线适合什么画面；
- 工具失败时如何降级。

不要把某个样本的正确答案、接口地址或评测任务 ID 写入 Skill。

## 4. 脚本顶部四个对象

```python
WORKFLOW_ID = "banner-ocr-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = ("paddleOcrTool", "MLLM")
WORKFLOW_CONTRACT = {...}
```

### `WORKFLOW_ID`

当前路线的唯一 ID。必须满足：

```text
脚本文件名 = WORKFLOW_ID + ".py"
```

### `PROBLEM_CLASS`

后端精确英文事件类别。消防门未关闭写 `fire_door_unclosed`，不能写中文。

目录名使用连字符：

```text
fire_door_unclosed -> fire-door-unclosed/
```

### `DECLARED_TOOLS`

脚本可能调用的全部工具白名单。它必须与以下两处完全一致：

- `WORKFLOW_CONTRACT["required_tools"]`
- `WORKFLOW_CONTRACT["steps"]` 中出现的工具集合

### `WORKFLOW_CONTRACT`

它告诉框架“这条路线适合什么任务、需要哪些工具、步骤如何连接”。`solve` 才是真正执行代码。

## 5. `WORKFLOW_CONTRACT` 顶层字段

```python
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_ocr_example",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合横幅文字清晰可见的画面。",
    "exclusions": "不适用于 banner 以外类别；文字不可见时 OCR 无收益。",
    "capability_boundary": (
        "不调用 embeddingTool；OCR 和 MLLM 必须成功，最终判断来自 MLLM。"
    ),
    "steps": [],
}
```

| 字段 | 应写内容 |
|---|---|
| `workflow_id` | 与脚本文件名、`WORKFLOW_ID` 相同 |
| `name` | 给人看的短名称，不作为文件名 |
| `problem_class` | 精确英文 event_type |
| `required_slots` | 执行时注入的变量，通常是 `event_type` |
| `required_tools` | 当前脚本可调用的全部工具 |
| `description` | 什么时候值得选这条路线 |
| `exclusions` | 哪些画面或类别不要选 |
| `capability_boundary` | 必须成功的步骤、必要输出和失败处理 |
| `steps` | 工具步骤、参数和依赖关系 |

### `capability_boundary` 不要写抽象话

错误：

```text
能力有限，适合 banner。
```

OCR 路线的具体写法：

```text
不调用 embeddingTool；OCR 与 MLLM 必须成功，最终判断来自 MLLM。
```

crop 路线的具体写法：

```text
不调用 embeddingTool；GroundingDINO 必须返回检测框，crop 与 MLLM 必须成功，
最终判断来自 MLLM。
```

## 6. step 字段

```python
{
    "tool_name": "paddleOcrTool",
    "args": {
        "file": "$image",
        "filename": "$filename",
    },
    "step_id": "ocr",
    "depends_on": [],
    "purpose": "读取横幅文字。",
}
```

| 字段 | 实际意义 |
|---|---|
| `tool_name` | 精确工具注册名，区分大小写 |
| `args` | 机器可读参数模板 |
| `step_id` | 当前 Workflow 内的唯一步骤名 |
| `depends_on` | 逻辑上依赖的前置 step |
| `purpose` | 为什么调用，供轨迹和人阅读 |

`depends_on` 不会自动改变 Python 执行顺序，也不会自动检查上游是否成功。真正的执行和降级逻辑仍写在
`solve` 中。

常见引用：

| contract 引用 | solve 中对应值 |
|---|---|
| `$media` | `runtime.media_path()` |
| `$image` | `runtime.image_path()` |
| `$filename` | `runtime.filename()` |
| `$question` | `question` |
| `$evidence` | `runtime.evidence_text()` |
| `$evidence_image` | `runtime.evidence_image()` |
| `$slot.event_type` | `event_type` |
| `$step.detect.detections` | `runtime.value(detect, "detections", [])` |
| `$step.crop.image` | `runtime.value(crop, "image", "")` |

## 7. `solve` 参数

```python
def solve(runtime, question, image_paths, *, event_type=""):
```

前三个参数固定：

| 参数 | 内容 |
|---|---|
| `runtime` | 工具、媒体、前序结果和轨迹接口 |
| `question` | 当前中文异常检测问题 |
| `image_paths` | 图片任务的一张图，或视频的多张抽样帧 |
| `event_type` | Planner 注入的精确异常类别 |

脚本不能 `import`，不能读写文件，也不能直接请求工具 HTTP 服务。

## 8. `runtime.call`

```python
ocr = runtime.call(
    "paddleOcrTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
    },
    step_id="ocr",
    purpose="读取横幅文字。",
    depends_on=[],
)
```

返回值永远是统一字典：

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

读取字段：

```python
text = runtime.value(ocr, "content", "")
boxes = runtime.value(detect, "detections", [])
images = runtime.value(crop, "image_refs", [])
```

12 个工具的参数和完整 `runtime.call` 示例见
[09-tool-cookbook.md](09-tool-cookbook.md)。

## 9. `runtime.require`

```python
runtime.require(embedding, "embedding")
```

它只检查 `embedding["ok"]`：

- 成功：继续下一行；
- 失败：抛错并终止当前 Workflow。

它不会重试、不会判断内容是否正确、不会检查 threshold，也不等于 contract 的 `required_tools`。

没有主结论就不能继续时使用：

```python
runtime.require(embedding, "embedding")
```

OCR 只是补充证据时不要使用：

```python
ocr = runtime.call(...)
if ocr.get("ok"):
    text = runtime.value(ocr, "content", "")
```

检测框是 crop 的必要输入时，可以选择：

```python
# 没有框就让整条 Workflow 失败
runtime.require(detect, "detect")
```

或者：

```python
# 没有框就跳过辅助链
if detect.get("ok"):
    crop = runtime.call(...)
```

## 10. `runtime.finish`

```python
return runtime.finish(embedding)
```

它只从指定结果或文本中提取最终短答案。它不会调用模型、不会执行证据验证、不会生成 threshold、不会保存
Workflow，也不会自动决定哪个工具更可信。

应该传入真正包含异常结论的结果：

```python
return runtime.finish(embedding)
```

不要传：

```python
return runtime.finish(ocr)   # OCR 文本不是异常判断
return runtime.finish(crop)  # crop 图片地址不是异常判断
```

mock 验证要求最终值必须恰好是“是”或“否”。

## 11. 一张证据图和多张图片

### `runtime.evidence_image()`

它永远返回一张图片路径：

1. 优先使用最近工具结果中的第一张 `data.image`；
2. 没有结果图时返回当前代表帧。

当前 MLLM 的 `file` 只接受一张图，所以不能把列表直接传给它。

### 视频多帧

`image_paths` 保存全部抽样帧。GroundingDINO、YOLO、OCR、Paddle 检测器和 SAM3 会自动在多帧上执行并
选择证据较好的一帧。脚本通常只需要：

```python
runtime.image_path()
```

不要自己切视频或循环请求这些工具。

### crop 多图

```python
crop_images = runtime.value(crop, "image_refs", [])
selected = crop_images[0] if crop_images else runtime.evidence_image()
```

如果确实需要逐张调用 MLLM，应在 contract 中提前声明多个固定 MLLM step。不能动态生成 contract 中没有的
`step_id`。

## 12. OCR 示例的关键逻辑

完整文件：

```text
skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

核心控制流：

```python
ocr = runtime.call(
    "paddleOcrTool",
    ...,
    step_id="ocr",
)
runtime.require(ocr, "ocr")

review = runtime.call(
    "MLLM",
    {
        "file": runtime.evidence_image(),
        "query": question + "\n" + runtime.evidence_text(),
        ...
    },
    step_id="review",
)
runtime.require(review, "review")

return runtime.finish(review)
```

OCR 和 MLLM 都是必要步骤；任一步失败时整条工作流失败。

## 13. crop 示例的关键逻辑

完整文件：

```text
skills/spatialskillgrowth/banner/scripts/banner-crop-example.py
```

核心控制流：

```python
detect = runtime.call("groundingdino", ...)
runtime.require(detect, "detect")
crop = runtime.call("crop_detections", ...)
runtime.require(crop, "crop")
review = runtime.call("MLLM", ...)
runtime.require(review, "review")

return runtime.finish(review)
```

这条路线没有 embedding 兜底，因此 detect、crop 和 MLLM 都必须成功。

## 14. 运行 mock 验证

OCR：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py
```

crop：

```bash
python -m scripts.validate_spatialskillgrowth_skill \
  --skill-dir skills/spatialskillgrowth/banner \
  --script skills/spatialskillgrowth/banner/scripts/banner-crop-example.py
```

验证顺序：

```text
目录和 SKILL.md
    -> Python AST
    -> WORKFLOW_CONTRACT
    -> 工具集合与 step_id
    -> mock 工具执行 solve
    -> 最终返回“是”或“否”
```

成功报告：

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

验证命令没有：

- `--media`
- `--event-type`
- `--real-tools`
- `--install`
- `--force`

验证器不读取真实媒体、不调用真实服务、不评价准确率，也不修改任何 Skill 文件。

## 15. mock 通过以后

mock 通过后，验证器不会自动安装。负责人按需要手动复制：

```text
SKILL.md
scripts/<WORKFLOW_ID>.py
```

复制目标由当前团队流程决定。若复制到自动生成的 whiteboard，后续重建会覆盖人工文件；若复制到正式运行
Skill，还需要由运行侧自己的加载流程处理机器索引。人工验证器不负责这些永久化步骤。

## 16. 常见报错

| 报错 | 原因 | 修改方式 |
|---|---|---|
| 文件名必须等于 `WORKFLOW_ID` | 文件名和顶部常量不同 | 同时改文件名和常量 |
| `PROBLEM_CLASS` 与目录不匹配 | event_type 和连字符目录不对应 | 检查 underscore 到 hyphen |
| `DECLARED_TOOLS` 不一致 | 四处工具集合不同 | 对照 declared、required、steps、call |
| `step_id` 不一致 | contract 和 solve 名字不同 | 使用同一 step ID |
| `called undeclared tool` | 调用了白名单外工具 | 加入 contract 或删除调用 |
| `Unsupported Python construct` | 使用 import、class、lambda、async 等 | 改成普通同步 Python |
| `Step ... failed` | 对失败 mock 调用了 require | 检查参数和依赖 |
| `requires non-empty detection boxes` | crop/depth 没拿到上游框 | 传入 `runtime.value(detect, "detections", [])` |
| mock 必须返回“是”或“否” | finish 的对象不是异常结论 | 返回 `runtime.finish(embedding)` |

## 17. 提交前检查

```text
[ ] 只修改 SKILL.md 和 scripts/*.py
[ ] frontmatter 只有 name、description
[ ] 文件名等于 WORKFLOW_ID + ".py"
[ ] PROBLEM_CLASS 是精确英文 event_type
[ ] DECLARED_TOOLS、required_tools、steps、runtime.call 一致
[ ] contract 与 solve 的 step_id 一致
[ ] depends_on 指向已经定义的步骤
[ ] capability_boundary 写清必须结果和失败处理
[ ] embedding 使用 runtime.media_path() 和 event_type
[ ] 图片工具使用 runtime.image_path() 或 runtime.evidence_image()
[ ] 必需步骤才使用 require
[ ] finish 接收真正的异常判断结果
[ ] mock_execution 通过
[ ] 没有运行真实工具或安装命令
```
