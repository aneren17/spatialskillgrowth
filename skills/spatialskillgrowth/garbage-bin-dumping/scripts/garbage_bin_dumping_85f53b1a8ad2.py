"""Executable SpatialSkillGrowth Skill: garbage_bin_dumping_detector."""

WORKFLOW_ID = 'garbage_bin_dumping_85f53b1a8ad2'
PROBLEM_CLASS = 'garbage_bin_dumping'
WORKFLOW_GRAPH_SHA256 = '0127f0b66d50ba557041b8e19864b9fb3b376d1f9352ec56d7f42c99f0eda5ed'
DECLARED_TOOLS = ('groundingdino', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'garbage_bin_dumping_85f53b1a8ad2', 'name': 'garbage_bin_dumping_detector', 'problem_class': 'garbage_bin_dumping', 'required_slots': [], 'required_tools': ['groundingdino', 'python_code_sandbox', 'MLLM'], 'description': '基于 GroundingDINO 开放词汇检测与多模态大模型推理，识别图像中是否发生垃圾桶倾倒异常事件。通过设定 0.3 的检测阈值定位目标物体，结合结构化证据摘要进行最终判定。', 'exclusions': "非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征提取的场景; 非 'garbage_bin_dumping' 类别的其他异常事件检测任务; 未提供明确视觉证据或图像质量严重受损导致无法识别垃圾桶形态的场景", 'capability_boundary': '{"required_event_type": "garbage_bin_dumping", "supported_media_type": "image", "detection_method": "GroundingDINO (threshold 0.3) + Python Code Sandbox + MLLM", "output_format": "Binary (Yes/No)", "object_scope": "仅限于图像中可被识别为垃圾桶及其倾倒状态的视觉实例，不包含其他无关物体或抽象概念"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'garbage_bin_dumping', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 garbage_bin_dumping 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'garbage_bin_dumping', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
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

    # 依据图像证据判断 garbage_bin_dumping 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 garbage_bin_dumping 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 garbage_bin_dumping 异常事件。',
        depends_on=['groundingdino_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
