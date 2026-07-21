"""Banner 定位和裁剪辅助检测的人工脚本示例。"""

WORKFLOW_ID = "banner-crop-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = (
    "groundingdino",
    "crop_detections",
    "MLLM",
)
WORKFLOW_CONTRACT = {
    "workflow_id": WORKFLOW_ID,
    "name": "banner_crop_example",
    "problem_class": PROBLEM_CLASS,
    "required_slots": ["event_type"],
    "required_tools": list(DECLARED_TOOLS),
    "description": "适合横幅在整图中较小的画面；先定位横幅，再裁剪目标区域供 MLLM 查看。",
    "exclusions": "不适用于 banner 以外类别；目标没有清晰外观或定位器无法返回框时不适合裁剪路线。",
    "capability_boundary": (
        "不调用 embeddingTool；GroundingDINO、crop 和 MLLM 必须依次成功，最终判断来自 MLLM。"
    ),
    "steps": [
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
            "purpose": "定位画面中的横幅。",
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
            "purpose": "裁剪检测到的横幅区域。",
        },
        {
            "tool_name": "MLLM",
            "args": {
                "file": "$step.crop.image",
                "filename": "$filename",
                "query": "$question\n$evidence",
                "tool": "qwen36Tool",
            },
            "step_id": "review",
            "depends_on": ["crop"],
            "purpose": "查看裁剪后的横幅区域并形成是或否判断。",
        },
    ],
}


def solve(runtime, question, image_paths, *, event_type=""):
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
        purpose="定位画面中的横幅。",
        depends_on=[],
    )
    runtime.require(detect, "detect")

    crop = runtime.call(
        "crop_detections",
        {
            "file": runtime.image_path(),
            "detections": runtime.value(detect, "detections", []),
            "folder": "",
            "score": "0.5",
            "className": "banner",
        },
        step_id="crop",
        purpose="裁剪检测到的横幅区域。",
        depends_on=["detect"],
    )
    runtime.require(crop, "crop")

    evidence_image = runtime.evidence_image()
    review = runtime.call(
        "MLLM",
        {
            "file": evidence_image,
            "filename": runtime.filename(evidence_image),
            "query": question + "\n" + runtime.evidence_text(),
            "tool": "qwen36Tool",
        },
        step_id="review",
        purpose="查看裁剪后的横幅区域并形成是或否判断。",
        depends_on=["crop"],
    )
    runtime.require(review, "review")

    return runtime.finish(review)
