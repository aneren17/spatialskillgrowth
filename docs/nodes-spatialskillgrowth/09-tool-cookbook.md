# 12 个工具逐一使用教程

本文面向只了解基本 Python 函数调用的读者。这里的“工具调用”不是直接请求 HTTP，而是在 Skill 的
`solve` 函数中调用 `runtime.call(...)`。Runtime 会负责服务调用、错误捕获、返回格式统一和视频逐帧。

当前实际注册目录是 `tools/basicTools`，共 12 个工具。已经移除的 Web、ASR、PDF 工具不在本文中。

## 先看懂一次最小调用

```python
result = runtime.call(
    "paddleOcrTool",                 # 工具注册名，必须精确一致
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
    },                               # 传给工具的参数字典
    step_id="read-text",             # 当前 Workflow 内唯一的步骤 ID
    purpose="读取画面文字。",          # 写入轨迹，便于人工排错
    depends_on=[],                    # 此步骤不依赖前一步
)
runtime.require(result, "read-text") # 工具失败就停止当前 Workflow
```

Runtime 返回的不是 OCR 原始字符串，而是统一字典：

```json
{
  "ok": true,
  "status": "success",
  "tool": "paddleOcrTool",
  "output_type": "text_regions",
  "content": "原始工具文本",
  "data": {
    "detections": [],
    "image_refs": [],
    "image": ""
  },
  "error": ""
}
```

读取字段时优先使用 `runtime.value(result, "字段", 默认值)`，不要自己猜字段位于顶层还是 `data`。

`runtime.call` 只负责“调用并记录”。`depends_on` 只写入轨迹，不会自动判断前一步是否成功；需要停止时
显式调用 `runtime.require`，允许降级时使用 `if result.get("ok")`。

## 1. `embeddingTool`：视频异常检测主判断

用途：输入一段原始视频以及已经确定的精确 `event_type`，返回“是/否”和判定阈值。该接口的图片
输入会系统性返回无异常，因此图片和视频抽样帧禁止调用。

参数：

| 参数 | 类型 | 示例 | 注意 |
|---|---|---|---|
| `file_path` | str | `test/banner.mp4` | 必须是本地存在的原始视频 |
| `event_type` | str | `banner` | 必须是 55 类英文 ID，不能写“横幅异常” |

Skill 调用：

```python
embedding = runtime.call(
    "embeddingTool",
    {
        "file_path": runtime.media_path(),
        "event_type": event_type,
    },
    step_id="embedding",
    purpose="判断指定异常是否发生并取得阈值。",
    depends_on=[],
)
runtime.require(embedding, "embedding")
```

原始返回可能是 `是 (判定阈值: 0.66)`；统一后可读取：

```python
decision = runtime.value(embedding, "decision")      # "是"
is_anomaly = runtime.value(embedding, "is_anomaly")  # True
threshold = runtime.value(embedding, "threshold")    # 0.66
```

视频 embedding 证据门要求最终答案与它一致。图片/抽样帧 Skill 使用独立的视觉证据契约，不要求
threshold。视频任务中 embedding 自动使用 `runtime.media_path()` 的原视频，不会被抽样帧替换；
运行时会拒绝任何图片后缀。

## 2. `MLLM`：对图像和已有证据做自然语言判断

参数：

| 参数 | 示例 | 说明 |
|---|---|---|
| `file` | `runtime.evidence_image()` | 本地图片、URL 或 Base64；不能传视频 |
| `filename` | `runtime.filename()` | 服务端使用的文件名 |
| `query` | `question` | 问题或证据审阅要求 |
| `tool` | `qwen36Tool` | 当前多模态模型标识 |

```python
evidence_image = runtime.evidence_image()
review = runtime.call(
    "MLLM",
    {
        "file": evidence_image,
        "filename": runtime.filename(evidence_image),
        "query": "请结合已有定位和文字证据检查画面，但不要替代 embedding 结论。\n"
                 + runtime.evidence_text(),
        "tool": "qwen36Tool",
    },
    step_id="visual-review",
    purpose="补充视觉解释。",
    depends_on=["embedding"],
)
```

`content` 是模型文本。异常 Skill 通常不对 MLLM 使用 `runtime.require`，这样模型服务失败时仍能返回
embedding 主结论。

当前 MLLM 一次只接收一张图。`runtime.evidence_image()` 也只返回一张；如果 crop 返回多张图，使用
`runtime.value(crop, "image_refs", [])` 取得列表，再按规则选择一张。视频抽样帧由 Runtime 自动分发给
支持逐帧的图片工具，不要把图片列表直接传给 MLLM 的 `file`。

## 3. `paddleOcrTool`：读取图片文字

参数只有 `file` 和 `filename`：

```python
ocr = runtime.call(
    "paddleOcrTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
    },
    step_id="ocr",
    purpose="读取横幅、车牌、仪表等可见文字。",
    depends_on=[],
)
ocr_text = runtime.value(ocr, "content", "")
```

适合横幅、车牌、仪表读数、告示牌。它只能读取文字，不能独立判断“人员摔倒”或“建筑坍塌”。视频输入
会自动在抽样帧上并行 OCR，并选出信息最丰富的代表帧。

## 4. `groundingdino`：开放词汇目标检测

它适合 YOLO 类别表之外的目标，例如 `banner`、`manhole cover`、`safety harness`。

| 参数 | 示例 | 说明 |
|---|---|---|
| `query` | `red banner` | 英文类别、短语或 JSON 字符串列表 |
| `file` | `runtime.image_path()` | 图片通道 |
| `filename` | `runtime.filename()` | 文件名 |
| `box_threshold` | `0.35` | 框置信度阈值 |
| `text_threshold` | `0.25` | 文本匹配阈值 |

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
    step_id="locate-banner",
    purpose="定位横幅区域。",
    depends_on=[],
)
runtime.require(detect, "locate-banner")
detections = runtime.value(detect, "detections", [])
```

统一 detection 项类似：

```json
{"class_name": "banner", "bbox": [120, 80, 620, 300], "score": 0.88}
```

## 5. `yoloTool`：COCO 80 类通用检测

适合 person、car、bus、bicycle、traffic light、chair、bottle 等固定常见物体。

```python
yolo = runtime.call(
    "yoloTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "threshold": 0.5,
    },
    step_id="detect-common-objects",
    purpose="检测人车等 COCO 常见目标。",
    depends_on=[],
)
```

它没有 query 参数，会返回画面中所有达到阈值的 COCO 类别。不要用它找 `banner`、安全带、井盖等不在
COCO 类别表中的目标；这些应使用 GroundingDINO 或 SAM3。

## 6. `paddleHeadDetTool`：只检测人头

```python
heads = runtime.call(
    "paddleHeadDetTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "tool": "paddleHeadDetTool",
    },
    step_id="detect-heads",
    purpose="定位可见人头，用于人数或佩戴状态辅助判断。",
    depends_on=[],
)
```

它是闭集工具，只能找人头，不要用它找车辆、文字或动物。当前 `TaskPlanner` 没有默认排除该工具，但
只有事件逻辑确实需要人头定位时才应加入 Workflow；注册可用不代表它适合所有异常类别。

## 7. `paddlePedriderDetTool`：行人、骑行者和车辆

```python
traffic_subjects = runtime.call(
    "paddlePedriderDetTool",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "tool": "paddlePedriderDetTool",
    },
    step_id="detect-traffic-subjects",
    purpose="定位行人、骑行者和车辆。",
    depends_on=[],
)
```

适合非机动车逆行、车辆违停、交通事故等辅助定位。它同样是闭集工具，不能检测横幅、井盖或火焰。

当前 `TaskPlanner` 没有默认排除该工具。是否加入 Workflow 仍应由异常事件的证据需求决定，不应仅因为
工具已经注册就调用。

## 8. `sam3`：短英文提示分割和边界框

| 参数 | 示例 | 限制 |
|---|---|---|
| `query` | `red banner` | 必须 1～3 个英文单词，中文和句子会在 Runtime 被拒绝 |
| `file` | 图片路径 | 不支持视频 |
| `filename` | 文件名 | 必填 |
| `threshold` | `0.6` | 0～1；具体目标常用 0.6～0.8 |
| `tool` | `sam3Tool` | 固定服务标识 |

```python
mask = runtime.call(
    "sam3",
    {
        "query": "red banner",
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "threshold": 0.6,
        "tool": "sam3Tool",
    },
    step_id="segment-banner",
    purpose="取得横幅掩码、结果图和像素边界框。",
    depends_on=[],
)
runtime.require(mask, "segment-banner")
mask_image = runtime.value(mask, "image")
mask_boxes = runtime.value(mask, "detections", [])
```

SAM3 同时生产 `segmentation_image` 和 `pixel_detections`，因此后面既能交给 MLLM 看掩码图，也能把框
传给裁剪或深度工具。

## 9. `crop_detections`：按像素框分别裁剪

它不能单独使用，前面必须有 GroundingDINO、YOLO、Paddle detector 或 SAM3 产生检测框。

```python
crop = runtime.call(
    "crop_detections",
    {
        "file": runtime.image_path(),
        "detections": runtime.value(detect, "detections", []),
        "folder": "",
        "score": "0.5",
        "className": "banner",
    },
    step_id="crop-banner",
    purpose="裁剪检测到的横幅区域。",
    depends_on=["locate-banner"],
)
runtime.require(crop, "crop-banner")
crop_image = runtime.value(crop, "image")
```

脚本可以传 detection list，Runtime 会转成工具要求的 JSON 字符串。若框为空，会在请求服务前报
`requires non-empty detection boxes`。

## 10. `picRelativeCut`：保留多个框相对关系的裁剪

适合比较“人是否跨过护栏”“车辆与停止线的位置”等需要整体布局的情况。

```python
relative = runtime.call(
    "picRelativeCut",
    {
        "file": runtime.image_path(),
        "detections": runtime.value(detect, "detections", []),
        "folder": "",
        "score": "0.5",
        "className": "",
    },
    step_id="preserve-layout",
    purpose="保留目标间相对空间关系。",
    depends_on=["detect-common-objects"],
)
```

底层工具要求 0～1 归一化框；如果上游返回像素框，Runtime 会读取本地图片宽高自动归一化。没有本地
图片或图片尺寸无效时会明确失败。

## 11. `unidepth`：对已定位目标估计米制深度

它也必须接检测框：

```python
depth = runtime.call(
    "unidepth",
    {
        "file": runtime.image_path(),
        "filename": runtime.filename(),
        "detections": runtime.value(detect, "detections", []),
    },
    step_id="estimate-depth",
    purpose="估计已定位目标的中位深度。",
    depends_on=["locate-targets"],
)
runtime.require(depth, "estimate-depth")
depth_items = runtime.value(depth, "detections", [])
```

Runtime 会把统一 detection 转成 UniDepth 要求的 `cls/box/score` JSON 字符串。它不能从整张图自动决定
要测哪个目标。

## 12. `python_code_sandbox`：确定性计算

这是当前注册表中的第 12 个工具，只接收 `code`：

```python
detections = runtime.value(detect, "detections", [])
code = (
    "detections = " + str(detections) + "\n"
    "print(len(detections))\n"
)
calculation = runtime.call(
    "python_code_sandbox",
    {"code": code},
    step_id="count-detections",
    purpose="确定性计算检测框数量。",
    depends_on=["locate-targets"],
)
runtime.require(calculation, "count-detections")
```

Skill 本身禁止 import，但传给 sandbox 的代码字符串运行在另一套受限环境，可使用其白名单模块。代码
必须 `print()` 输出结果。异常检测中它只能做辅助计算，最终仍需要 embedding 判断和阈值。

## 常用组合 1：OCR + MLLM

适合 banner、车牌、仪表异常等文字能够支持最终判断的图片或视频抽样帧：

```text
paddleOcrTool（代表帧，文字）
        -> MLLM（代表帧 + 累积证据，最终判断）
最终返回 MLLM
```

这正是 `skills/spatialskillgrowth/banner/scripts/banner-ocr-example.py` 的路线。

## 常用组合 2：Embedding + GroundingDINO + Crop + OCR

适合整张图文字太小，必须先定位再 OCR：

```python
detect = runtime.call(
    "groundingdino",
    {"query": "banner", "file": runtime.image_path(),
     "filename": runtime.filename(), "box_threshold": 0.35,
     "text_threshold": 0.25},
    step_id="detect", purpose="定位横幅。", depends_on=[],
)
runtime.require(detect, "detect")

crop = runtime.call(
    "crop_detections",
    {"file": runtime.image_path(),
     "detections": runtime.value(detect, "detections", []),
     "folder": "", "score": "0.5", "className": "banner"},
    step_id="crop", purpose="裁剪横幅。", depends_on=["detect"],
)
runtime.require(crop, "crop")

ocr = runtime.call(
    "paddleOcrTool",
    {"file": runtime.value(crop, "image"),
     "filename": runtime.filename(runtime.value(crop, "image"))},
    step_id="ocr", purpose="读取裁剪区域文字。", depends_on=["crop"],
)
```

注意：还应在完整脚本开头调用 embedding，结尾返回 embedding。若 detect/crop 是可选证据，就不要对其
调用 `require`，而应在 `if detect.get("ok"):` 中降级。

同一组合在 `WORKFLOW_CONTRACT["steps"]` 中应写成：

```python
[
    {
        "tool_name": "embeddingTool",
        "args": {"file_path": "$media", "event_type": "$slot.event_type"},
        "step_id": "embedding",
        "depends_on": [],
        "purpose": "取得异常主判断和阈值。",
    },
    {
        "tool_name": "groundingdino",
        "args": {
            "query": "banner",
            "file": "$image",
            "filename": "$filename",
            "box_threshold": 0.35,
            "text_threshold": 0.25,
        },
        "step_id": "detect",
        "depends_on": [],
        "purpose": "定位横幅。",
    },
    {
        "tool_name": "crop_detections",
        "args": {
            "file": "$image",
            "detections": "$step.detect.detections",
            "folder": "",
            "score": "0.5",
            "className": "banner",
        },
        "step_id": "crop",
        "depends_on": ["detect"],
        "purpose": "裁剪横幅区域。",
    },
    {
        "tool_name": "paddleOcrTool",
        "args": {
            "file": "$step.crop.image",
            "filename": "$filename",
        },
        "step_id": "ocr",
        "depends_on": ["crop"],
        "purpose": "读取裁剪区域文字。",
    },
]
```

`$step.detect.detections` 表示读取 detect 统一结果的 `data.detections`；`$step.crop.image` 表示读取裁剪
工具返回的第一张证据图。contract 用引用描述连接，solve 用 `runtime.value` 实现同一连接。两边 step ID
必须一致。

## 常用组合 3：检测 + 相对布局 + MLLM

适合跨护栏、越黄线、逆行、违停：

```text
yolo / paddlePedrider / GroundingDINO
        -> picRelativeCut
        -> MLLM 检查目标间相对位置并形成结论
```

检测器选哪个取决于目标：COCO 常见物体用 YOLO；交通主体用 Pedrider；开放类别用 GroundingDINO。

## 常用组合 4：检测 + UniDepth + 计算

适合需要距离辅助证据的场景：

```text
GroundingDINO/SAM3 产生 pixel_detections
        -> UniDepth 为每个框补深度
        -> python_code_sandbox 做比较或过滤
        -> MLLM 结合图像解释
```

视频推理的 embedding 在 Skill 工作流之外并行执行，最终与 MLLM 判断取 OR。

不能写成 `UniDepth -> GroundingDINO`，因为 UniDepth 的输入依赖检测框。`tool_contracts.py` 和验证器会
阻止这种生产者/消费者顺序错误。

## 如何决定是否 `runtime.require`

| 情况 | 建议 |
|---|---|
| 后续步骤必须依赖该框/裁剪 | require，否则后续参数没有意义 |
| OCR/MLLM 产生当前工作流最终判断 | require |
| 检测器在当前事件经常找不到目标 | 用 `if result.get("ok")` 分支，不要强制终止 |

工具“调用成功”不等于“真实检测正确”。人工验证器只用 mock 检查这些调用能否连通，不会调用真实服务、
读取 ground truth 或评估效果。
