"""Executable SpatialSkillGrowth Skill: pipeline_leak_detector."""

WORKFLOW_ID = 'pipeline_leak_1dbd8d95a7a7'
PROBLEM_CLASS = 'pipeline_leak'
WORKFLOW_GRAPH_SHA256 = '744496eb29ea7d9892f384a5e681bee8ea3edc0447d60c0c179d089d148fda09'
DECLARED_TOOLS = ('groundingdino', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'pipeline_leak_1dbd8d95a7a7', 'name': 'pipeline_leak_detector', 'problem_class': 'pipeline_leak', 'required_slots': [], 'required_tools': ['groundingdino', 'python_code_sandbox', 'MLLM'], 'description': '基于视觉证据的管道泄漏异常检测工作流。该流程通过 GroundingDINO 以 0.3 阈值进行开放词汇目标检测，结合 Python 代码沙箱计算结构化证据摘要，最终由多模态大语言模型（MLLM）综合判断图像中是否存在管道泄漏。仅适用于图像输入，禁止使用嵌入工具。', 'exclusions': '非图像类型的媒体输入（如纯文本、音频或视频流）; 需要调用 embeddingTool 的场景; 非 pipeline_leak 类别的异常检测任务; 需要动态调整 GroundingDINO 检测阈值的场景', 'capability_boundary': '{"input_media": "image", "event_type": "pipeline_leak", "detection_threshold": 0.3, "required_tools": ["groundingdino", "python_code_sandbox", "MLLM"], "prohibited_tools": ["embeddingTool"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'pipeline_leak', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 pipeline_leak 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'pipeline_leak', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 pipeline_leak 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 pipeline_leak 异常事件。',
        depends_on=['groundingdino_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
