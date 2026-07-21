"""Executable SpatialSkillGrowth Skill: fight_detection_workflow."""

WORKFLOW_ID = 'fight_513cb2fe7351'
PROBLEM_CLASS = 'fight'
WORKFLOW_GRAPH_SHA256 = 'afcf904e6cbc53058174fd305271ef1be22f9d209b5372b5a02c2a8fb261d432'
DECLARED_TOOLS = ('paddleHeadDetTool', 'yoloTool', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fight_513cb2fe7351', 'name': 'fight_detection_workflow', 'problem_class': 'fight', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'yoloTool', 'python_code_sandbox', 'MLLM'], 'description': '基于图像输入检测‘打架斗殴’（fight）异常事件。工作流通过 paddleHeadDetTool 检测可见人头以评估人员密度，结合 yoloTool（阈值 0.5）识别潜在冲突行为或物体，利用 python_code_sandbox 计算结构化证据摘要，最终由多模态大模型（MLLM）综合视觉证据判断是否发生打架事件。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非‘打架斗殴’类别的其他异常事件检测; 需要重新分类或改写 event_type 的场景', 'capability_boundary': "仅适用于 event_type 为 'fight' 且 media_type 为 'image' 的检测任务。检测器依赖于可见人头的存在及 YOLO 检测到的特定行为特征，若图像中缺乏可检测的人头或关键行为特征导致证据不足，可能无法准确判定。", 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.yolotool_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fight 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 fight 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0', 'yolotool_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.yolotool_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['yolotool_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 fight 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fight 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fight 异常事件。',
        depends_on=['paddleheaddettool_0', 'yolotool_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
