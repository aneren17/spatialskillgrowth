"""Banner 定位和裁剪辅助检测的人工脚本示例。"""

WORKFLOW_ID = "banner-crop-example"
PROBLEM_CLASS = "banner"
DECLARED_TOOLS = (
    "embeddingTool",
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
        "embeddingTool 必须成功；GroundingDINO 必须先返回检测框，crop 才能执行。"
        "定位、裁剪或 MLLM 任一步失败时停止辅助链，最终仍返回 embeddingTool 的判断。"
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
            "purpose": "取得 banner 主判断和阈值。",
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
            "depends_on": ["embedding", "crop"],
            "purpose": "查看裁剪后的横幅区域。",
        },
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
        purpose="取得 banner 主判断和阈值。",
        depends_on=[],
    )
    runtime.require(embedding, "embedding")

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

    if detect.get("ok"):
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
        if crop.get("ok"):
            evidence_image = runtime.evidence_image()
            runtime.call(
                "MLLM",
                {
                    "file": evidence_image,
                    "filename": runtime.filename(evidence_image),
                    "query": question + "\n" + runtime.evidence_text(),
                    "tool": "qwen36Tool",
                },
                step_id="review",
                purpose="查看裁剪后的横幅区域。",
                depends_on=["embedding", "crop"],
            )

    return runtime.finish(embedding)
