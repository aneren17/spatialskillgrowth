# 全部工具与中间结果

本文从“一个工具的输出怎样交给下一个工具”开始，然后逐一介绍当前注册的 12 个工具。

## 1. 工具不直接把原始响应交给 Skill

Skill 通过 `runtime.call(...)` 调工具。`ToolRuntime` 会把不同服务的字符串或 JSON 统一为：

```python
{
    "ok": True,
    "status": "success",
    "tool": "groundingdino",
    "output_type": "pixel_detections",
    "output_types": ["pixel_detections"],
    "content": "工具的文本响应",
    "data": {
        "detections": [
            {
                "class_name": "banner",
                "bbox": [120, 80, 460, 260],
                "score": 0.91,
            }
        ],
        "detections_json": "{\"detections\": [...]}",
        "image_refs": ["http://.../result.jpg"],
        "image": "http://.../result.jpg",
        "bbox_format": "xyxy_pixel",
    },
    "raw": "原始响应",
    "error": "",
}
```

失败时 `ok=False`，`status` 可能是 `error`、`empty`、`invalid` 或 `skipped`。对检测工具来说，
“没有检测框”会被归一为 `empty` 失败，而不是成功的空数组。

读值时使用 `runtime.value`：

```python
boxes = runtime.value(detect, "detections", [])
images = runtime.value(crop, "image_refs", [])
text = runtime.value(ocr, "content", "")
```

`runtime.value` 先查顶层，再查 `data`，避免脚本了解每个字段的内部位置。

## 2. `call`、`require`、`value`、`finish` 分别做什么

### `runtime.call`

```python
detect = runtime.call(
    "groundingdino",
    {
        "query": "banner",
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "box_threshold": 0.35,
        "text_threshold": 0.25,
    },
    step_id="detect",
    purpose="定位横幅。",
    depends_on=[],
)
```

它会：

1. 检查工具是否出现在当前 Workflow 的步骤白名单中；
2. 调用工具并统一返回格式；
3. 以 `step_id` 保存结果；
4. 把参数、结果、用途和依赖写入本次执行轨迹。

它不会自动判断业务结果是否正确。`purpose` 只是轨迹说明；`depends_on` 表示图上的逻辑依赖，也不会在
Python 脚本中自动停止或跳过下一步。实际控制流仍由 `solve` 中的 `require` 或 `if` 决定。

### `runtime.require`

```python
runtime.require(detect, "detect")
```

它只检查 `detect["ok"]`。成功就继续；失败就抛出异常并让当前 Workflow 失败。它不会重试、不会检查
检测类别是否符合题意，也不是 `required_tools` 的别名。

```python
# crop 没有检测框就无法工作，因此 detect 是必需步骤
runtime.require(detect, "detect")

# OCR 只是辅助证据，失败后仍允许看原图，因此不 require
if ocr.get("ok"):
    ocr_text = runtime.value(ocr, "content", "")
```

### `runtime.value`

```python
boxes = runtime.value(detect, "detections", [])
```

它只负责取字段，不判断字段含义，也不把失败结果变成成功结果。

### `runtime.finish`

```python
return runtime.finish(review)
```

它从字典的 `content`/`answer` 或给定文本中提取最终短答案。它不调用模型、不做证据验收、不保存 Workflow，
也不会自动合并多个工具。异常检测脚本必须把真正含有“是/否”结论的 MLLM 结果交给它：

```python
return runtime.finish(review)  # review 是 MLLM 的异常判断
```

下面两种写法没有业务意义：

```python
return runtime.finish(detect)  # 检测框不是异常结论
return runtime.finish(crop)    # 图片地址不是异常结论
```

## 3. Runtime 提供的媒体和证据方法

| 方法 | 返回内容 |
|---|---|
| `runtime.media_path()` | 原始媒体路径；视频任务返回原视频 |
| `runtime.image_path()` | 当前代表图片；视频开始时是中间抽样帧，逐帧工具执行后会变成最佳帧 |
| `runtime.filename(path)` | 指定路径的文件名；不传参数时使用当前代表图片 |
| `runtime.evidence_text()` | 已执行步骤的 `content/error` 合并文本，只保留末尾 6000 字符 |
| `runtime.evidence_image()` | 最近一个结果的第一张 `data.image`；没有结果图时返回当前代表图片 |
| `runtime.render(value)` | 解析 `$question`、`$evidence`、`$step...` 等模板引用 |

常见 contract 模板与 Python 写法对应如下：

| contract 中的值 | `solve` 中的写法 |
|---|---|
| `$media` | `runtime.media_path()` |
| `$image` | `runtime.image_path()` |
| `$filename` | `runtime.filename()` |
| `$media_filename` | `runtime.filename(runtime.media_path())` |
| `$question` | `question` |
| `$evidence` | `runtime.evidence_text()` |
| `$evidence_image` | `runtime.evidence_image()` |
| `$slot.event_type` | `event_type` |
| `$step.detect.detections` | `runtime.value(detect, "detections", [])` |
| `$step.crop.images` | `runtime.value(crop, "image_refs", [])` |
| `$step.crop.image` | `runtime.value(crop, "image", "")` |
| `$frames` | `image_paths` |

精确的 `$step.detect.detections` 会得到 Python 列表；如果把它嵌入一段长字符串，Runtime 会把列表转成
JSON 文本。

## 4. 视频抽样帧的自动 fan-out

下列七个单图工具收到当前抽样图片路径时，如果任务有多张视频抽样帧，Runtime 会自动在全部帧上
并行执行：

```text
embeddingTool
groundingdino
yoloTool
paddleHeadDetTool
paddlePedriderDetTool
paddleOcrTool
sam3
```

Runtime 从成功结果中选择一帧，排序依据依次是：embedding 是否判断异常、检测框数量、最高置信度、是否有结果图、
文本长度、较早帧。对非 embedding 工具，第一项始终为假，不改变原排序。
选中后 `runtime.image_path()` 会切换到该帧。因此下面的 crop 会使用与检测框对应的同一张帧(这里的逻辑我还没改好，理论上要选最优的一个bbox框，这还有问题)：

```python
detect = runtime.call(
    "groundingdino",
    {"query": "banner", "file": runtime.image_path(), "filename": runtime.filename()},
    step_id="detect",
)
runtime.require(detect, "detect")

crop = runtime.call(
    "crop_detections",
    {
        "file": runtime.image_path(),
        "detections": runtime.value(detect, "detections", []),
        "folder": "spatialskillgrowth_crops",
    },
    step_id="crop",
    depends_on=["detect"],
)
```

`crop_detections`、`picRelativeCut`、`unidepth` 和 `MLLM` 不会自动 fan-out。不要把 `image_paths`
列表直接传给这些工具的单图参数。

## 5. 12 个工具速查

| 工具注册名 | 主要输入 | 统一输出 | 主要用途 |
|---|---|---|---|
| `embeddingTool` | 图片或原始视频、精确 `event_type` | `decision/is_anomaly/threshold` | 图片证据或独立视频异常通道 |
| `MLLM` | 一张图、问题 | `content` | 视觉理解和最终“是/否” |
| `yoloTool` | 图片、阈值 | `detections` | COCO 80 类目标检测 |
| `paddleHeadDetTool` | 图片 | `detections` | 人头检测 |
| `paddlePedriderDetTool` | 图片 | `detections` | 行人、骑行者、车辆检测 |
| `sam3` | 图片、短英文目标、阈值 | `detections` + `image_refs` | 目标分割及框 |
| `groundingdino` | 图片、英文开放词汇目标 | `detections` + 可能的结果图 | 开放词汇定位 |
| `unidepth` | 图片、检测框 | 带深度的 `detections` | 目标度量深度 |
| `paddleOcrTool` | 图片 | `content` | 文字识别 |
| `crop_detections` | 图片、像素框 | `image_refs` | 每个框分别裁剪 |
| `picRelativeCut` | 图片、检测框 | `image_refs` | 保留相对空间关系的裁剪 |
| `python_code_sandbox` | Python 代码字符串 | `content` | 规则计算 |

## 6. 每个工具的参数和限制

### 6.1 `embeddingTool`

```python
embedding = runtime.call(
    "embeddingTool",
    {
        "file_path": runtime.image_path(),
        "event_type": event_type,
    },
    step_id="embedding",
)
```

- 接受本地图片或原始视频；
- `event_type` 必须是 `tools/basicTools/embeddingTool.py` 中注册的精确英文 ID；
- 成功后可读取 `decision`、`is_anomaly`、`threshold`；
- 探索只使用图片能力，Workflow 参数应声明 `file_path: "$image"`；
- 原始视频能力由框架独立建立的 embedding 基线工作流使用，其参数是 `file_path: "$media"`。

图片 embedding 对多个视频抽样帧会按帧并行调用；确定性选择时优先保留判断为“是”的成功帧，再按通用帧证据规则打破平局。

### 6.2 `MLLM`

```python
image = runtime.evidence_image()
review = runtime.call(
    "MLLM",
    {
        "file": image,
        "filename": runtime.filename(image),
        "query": question + "\n工具证据：\n" + runtime.evidence_text(),
        "tool": "qwen36Tool",
    },
    step_id="review",
)
```

`file` 每次只接受一张本地图片、URL 或 Base64；不能传视频或图片列表。`content` 是模型文本。若它负责
最终判断，提示中应明确要求只输出“是”或“否”，最后 `return runtime.finish(review)`。

### 6.3 `yoloTool`

```python
yolo = runtime.call(
    "yoloTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "threshold": 0.5,
    },
    step_id="yolo",
)
```

只能检测 COCO 预训练的 80 类常见物体。`threshold` 越高结果越少。它不适合 `banner`、“安全带”等
不在 COCO 类别表中的目标。

### 6.4 `paddleHeadDetTool`

```python
heads = runtime.call(
    "paddleHeadDetTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "tool": "paddleHeadDetTool",
    },
    step_id="heads",
)
```

只检测人头，`tool` 必须写 `paddleHeadDetTool`。不要用于检测整个人、车辆或文字。

### 6.5 `paddlePedriderDetTool`

```python
traffic = runtime.call(
    "paddlePedriderDetTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "tool": "paddlePedriderDetTool",
    },
    step_id="traffic",
)
```

用于汽车、公交车、卡车、自行车、三轮车和行人。`tool` 必须写注册名本身。

### 6.6 `sam3`

```python
segment = runtime.call(
    "sam3",
    {
        "query": "red car",
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "threshold": 0.6,
        "tool": "sam3Tool",
    },
    step_id="segment",
)
```

- `query` 必须是 1～3 个英文单词，中文或长句在 Runtime 参数检查阶段失败；
- `threshold` 必须在 0～1；具体物体通常用 0.6～0.8，抽象目标可从 0.5 尝试；
- 当前契约同时产出分割结果图和像素检测框，所以可继续交给 crop，也可把分割图交给 MLLM。

### 6.7 `groundingdino`

```python
detect = runtime.call(
    "groundingdino",
    {
        "query": "safety harness",
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "box_threshold": 0.35,
        "text_threshold": 0.25,
    },
    step_id="detect",
)
```

`query` 使用英文类别、英文指代表达，或 JSON 字符串列表，例如 `["person", "car"]`。输出框是
`[xmin, ymin, xmax, ymax]` 像素坐标。

### 6.8 `unidepth`

```python
depth = runtime.call(
    "unidepth",
    {
        "detections": runtime.value(detect, "detections", []),
        "file": runtime.image_path(),
        "filename": runtime.filename(),
    },
    step_id="depth",
    depends_on=["detect"],
)
```

必须有非空检测框。Runtime 会把统一的 `class_name/bbox/score` 自动转换为接口需要的
`cls/box/score` JSON。结果中的 detection 会包含后端返回的深度信息。

### 6.9 `paddleOcrTool`

```python
ocr = runtime.call(
    "paddleOcrTool",
    {"file": runtime.image_path(), "filename": runtime.filename()},
    step_id="ocr",
)
```

当前包装器优先返回后端 `content` 文本，因此主要通过 `runtime.value(ocr, "content", "")` 使用；不要
假设它一定提供可供 crop 使用的文字框。

### 6.10 `crop_detections`

```python
crop = runtime.call(
    "crop_detections",
    {
        "file": runtime.image_path(),
        "detections": runtime.value(detect, "detections", []),
        "folder": "spatialskillgrowth_crops",
        "score": "0.5",
        "className": "banner",
    },
    step_id="crop",
    depends_on=["detect"],
)
```

输入是像素框。Skill 可以直接传 Python detection 列表，Runtime 会转成后端需要的 JSON 字符串。
`className` 为空表示不按类别过滤；`score` 会过滤低分框。输出：

```python
all_crops = runtime.value(crop, "image_refs", [])  # 全部裁剪图
first_crop = runtime.value(crop, "image", "")     # 永远是第一张
```

### 6.11 `picRelativeCut`

参数与 `crop_detections` 相同：

```python
relative = runtime.call(
    "picRelativeCut",
    {
        "file": runtime.image_path(),
        "detections": runtime.value(detect, "detections", []),
        "folder": "spatialskillgrowth_relative_crops",
        "score": "0.5",
        "className": "",
    },
    step_id="relative",
    depends_on=["detect"],
)
```

后端需要 0～1 相对坐标；如果输入是像素框，Runtime 会读取本地图片宽高并自动归一化。若图片不是可读取的
本地文件，自动归一化会失败。

### 6.12 `python_code_sandbox`

```python
boxes = runtime.value(detect, "detections", [])
code = "detections = " + str(boxes) + "\nprint(len(detections))"
count = runtime.call(
    "python_code_sandbox",
    {"code": code},
    step_id="count",
    depends_on=["detect"],
)
```

代码必须用 `print()` 输出，执行超时为 10 秒，stdout 进入 `content`。这是一个独立子进程工具，与承载
`solve` 的受限 Python Skill 环境不是同一个沙箱。它允许的模块以
`tools/basicTools/pythonSandboxTool.py` 中的 `SAFE_MODULES` 为准。当前白名单包含 `os` 和 `pickle`，
因此不能把它视为强安全隔离边界，只应运行受信任代码。

## 7. 检测框如何交给 crop

最短可执行链如下：

```python
detect = runtime.call(
    "groundingdino",
    {
        "query": "banner",
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "box_threshold": 0.35,
        "text_threshold": 0.25,
    },
    step_id="detect",
)
runtime.require(detect, "detect")

boxes = runtime.value(detect, "detections", [])
crop = runtime.call(
    "crop_detections",
    {
        "file": runtime.image_path(),
        "detections": boxes,
        "folder": "spatialskillgrowth_crops",
        "score": "0.5",
        "className": "banner",
    },
    step_id="crop",
    depends_on=["detect"],
)
runtime.require(crop, "crop")
```

不需要手工 `json.dumps`，也不要把 `detect["content"]` 当成检测框传递。

## 8. crop 有多张图时，MLLM 到底看哪张

当前行为必须明确：

- `runtime.value(crop, "image_refs", [])` 返回全部裁剪图；
- `runtime.value(crop, "image", "")` 只返回第一张；
- crop 是最近结果时，`runtime.evidence_image()` 也只返回第一张；
- `MLLM.file` 一次只接受一张图；
- Runtime 当前没有“从多个 crop 中自动选择最佳图片”的逻辑。

### 推荐方式：先把框筛成一个，再 crop

例如选择置信度最高的框。受限 Skill 禁止 `lambda`，可以直接循环：

```python
boxes = runtime.value(detect, "detections", [])
runtime.require(detect, "detect")

best = boxes[0]
for item in boxes[1:]:
    item_score = float(item.get("score", item.get("confidence", 0.0)))
    best_score = float(best.get("score", best.get("confidence", 0.0)))
    if item_score > best_score:
        best = item

crop = runtime.call(
    "crop_detections",
    {
        "file": runtime.image_path(),
        "detections": [best],
        "folder": "spatialskillgrowth_crops",
        "score": "0.0",
        "className": "",
    },
    step_id="crop",
    depends_on=["detect"],
)
runtime.require(crop, "crop")

crop_images = runtime.value(crop, "image_refs", [])
selected_image = crop_images[0]
review = runtime.call(
    "MLLM",
    {
        "file": selected_image,
        "filename": runtime.filename(selected_image),
        "query": question + "\n" + runtime.evidence_text(),
        "tool": "qwen36Tool",
    },
    step_id="review",
    depends_on=["crop"],
)
runtime.require(review, "review")
return runtime.finish(review)
```

也可以先按 `class_name` 过滤，再按分数或框面积选择。这比“默认拿第一张”更能表达业务规则。

### 必须逐张看时

在 `WORKFLOW_CONTRACT["steps"]` 中提前声明固定的 `review_0`、`review_1` 等 MLLM step，再在脚本中
分别调用。不要在循环中构造动态 `step_id`；人工校验器要求 `runtime.call` 的 `step_id` 是静态字符串，
且必须与 contract 的 step 集合完全一致。图片数量没有固定上限时，当前框架缺少自然的动态多图 MLLM
契约，应先扩展 Runtime/工具接口，而不是把列表塞进单图 `file` 参数。

## 9. 常见错误

| 现象 | 原因 | 正确处理 |
|---|---|---|
| crop 报需要非空检测框 | 传了检测器文本或检测为空 | 先 `require(detect)`，再取 `detections` |
| MLLM 只看了一张 crop | `evidence_image()` 和 `data.image` 本来就取第一张 | 先筛框，或声明多个固定 MLLM step |
| 视频工具只处理了中间帧 | 手工传了非抽样帧路径，未触发 fan-out | 图片工具使用 `runtime.image_path()` |
| embedding 调用了错误媒体 | 图片 Workflow 使用了 `$media` | 图片能力传 `runtime.image_path()` / `$image`；只有独立视频基线使用 `$media` |
| `depends_on` 后仍执行了失败步骤 | 它只描述依赖，不控制 Python | 使用 `runtime.require` 或显式 `if` |
| `finish` 返回图片地址/检测 JSON | 传入的不是最终判断 | 让 MLLM 形成“是/否”，再 finish |
