"""Executable SpatialSkillGrowth Skill: breaking_through_toll_booths_detector."""

WORKFLOW_ID = 'breaking_through_toll_booths_9f74d96f04bd'
PROBLEM_CLASS = 'breaking_through_toll_booths'
WORKFLOW_GRAPH_SHA256 = '222d0190c83429e62299353bc0a1ad645d412ba25e2f67f7f538f5fca22a2bb3'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'unidepth', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'breaking_through_toll_booths_9f74d96f04bd', 'name': 'breaking_through_toll_booths_detector', 'problem_class': 'breaking_through_toll_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'unidepth', 'python_code_sandbox', 'MLLM'], 'description': '检测输入图像中是否发生车辆或行人强行通过收费站闸机（闯收费站）的异常事件。该工作流利用 OCR 识别收费站标识文字，结合 YOLO 目标检测定位车辆或行人，并通过深度估计与结构化证据计算，由多模态大模型综合判断是否存在违规闯卡行为。', 'exclusions': '非收费站场景（如普通道路、停车场入口无闸机设施）; 图像中未出现收费站闸机、栏杆或相关标识文字; 目标物体未处于通过或试图通过闸机的动态过程中; 图像质量过低导致无法识别关键视觉证据（如文字模糊、目标遮挡严重）; 非图像类型的媒体输入', 'capability_boundary': '{"required_evidence": ["OCR 识别到的收费站相关文字（如‘收费站’、‘ETC’、‘缴费’等）", "YOLO 检测到的车辆或行人目标及其边界框", "基于 YOLO 结果的深度估计信息，用于判断目标与闸机的空间关系", "结构化证据摘要，整合位置、深度与文本信息"], "tool_constraints": ["必须使用 paddleOcrTool 读取可见文字", "必须使用 yoloTool 进行目标检测（阈值 0.5）", "必须使用 unidepth 估计检测目标深度", "必须使用 python_code_sandbox 计算结构化证据摘要", "最终判断由 MLLM 基于上述所有工具输出完成", "禁止对图像输入调用 embeddingTool"], "event_type": "breaking_through_toll_booths", "media_type": "image"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.yolotool_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 breaking_through_toll_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0', 'unidepth_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 使用 0.5 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.5},
        step_id='yolotool_0',
        purpose='使用 0.5 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(yolotool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['yolotool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.yolotool_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['yolotool_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 breaking_through_toll_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 breaking_through_toll_booths 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0', 'unidepth_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
