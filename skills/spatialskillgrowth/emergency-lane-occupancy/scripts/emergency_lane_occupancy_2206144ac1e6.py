"""Executable SpatialSkillGrowth Skill: emergency_lane_occupancy_detector."""

WORKFLOW_ID = 'emergency_lane_occupancy_2206144ac1e6'
PROBLEM_CLASS = 'emergency_lane_occupancy'
WORKFLOW_GRAPH_SHA256 = 'cbcacdf90d19b2d21a99a85139081fd0eb38d199cf984a74abb6857b34cc7681'
DECLARED_TOOLS = ('yoloTool', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'emergency_lane_occupancy_2206144ac1e6', 'name': 'emergency_lane_occupancy_detector', 'problem_class': 'emergency_lane_occupancy', 'required_slots': [], 'required_tools': ['yoloTool', 'python_code_sandbox', 'MLLM'], 'description': '本工作流用于检测输入图像中是否存在车辆占用应急车道的异常行为。流程首先利用目标检测模型（yoloTool）识别图像中的车辆及道路标线，随后通过代码沙箱（python_code_sandbox）计算车辆与应急车道边界的结构化空间关系证据，最后由多模态大模型（MLLM）综合视觉特征与空间证据，判定是否发生占用应急车道事件。', 'exclusions': '不包含视频流或序列帧分析，仅处理单张静态图像输入。; 不检测非车辆物体（如行人、动物、掉落物）占用应急车道的情况，检测器限制为仅针对车辆目标。; 不处理模糊、严重遮挡或无法清晰辨识应急车道标线的低质量图像。; 不涉及对占用时长的统计或历史轨迹回溯，仅基于当前帧进行瞬时状态判定。', 'capability_boundary': '{"event_type": "emergency_lane_occupancy", "media_type": "image", "required_evidence": ["车辆目标的边界框坐标", "应急车道边界的几何定义或检测结果", "车辆与应急车道区域的空间重叠度或距离指标"], "output_format": "binary_classification", "allowed_tools": ["yoloTool", "python_code_sandbox", "MLLM"]}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.yolotool_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 emergency_lane_occupancy 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 emergency_lane_occupancy 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

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

    # 依据图像证据判断 emergency_lane_occupancy 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 emergency_lane_occupancy 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 emergency_lane_occupancy 异常事件。',
        depends_on=['yolotool_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
