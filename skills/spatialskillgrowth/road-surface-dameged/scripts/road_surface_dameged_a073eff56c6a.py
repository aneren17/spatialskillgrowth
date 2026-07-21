"""Executable SpatialSkillGrowth Skill: road_surface_dameged_detector."""

WORKFLOW_ID = 'road_surface_dameged_a073eff56c6a'
PROBLEM_CLASS = 'road_surface_dameged'
WORKFLOW_GRAPH_SHA256 = '3fb354314e1497fd364f182458ba2dd99d5f83f6aee21679db5499540b5556d1'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'road_surface_dameged_a073eff56c6a', 'name': 'road_surface_dameged_detector', 'problem_class': 'road_surface_dameged', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '检测输入图像中是否存在路面破损（road_surface_dameged）异常事件。该工作流首先使用 YOLO 工具以 0.3 的置信度阈值进行目标检测，随后结合多模态大语言模型（MLLM）依据视觉证据进行最终判定。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他非路面破损类的异常事件检测', 'capability_boundary': '{"supported_media": ["image"], "event_type": "road_surface_dameged", "detection_method": "yolo_tool_with_mllm_verification", "yolo_threshold": 0.3}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.3}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 检测阈值。', 'args': {}}], 'purpose': '使用 0.3 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 road_surface_dameged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 road_surface_dameged 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 检测阈值。
    yolotool_0_result = runtime.call(
        'yoloTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'threshold': 0.3},
        step_id='yolotool_0',
        purpose='使用 0.3 检测阈值。',
        depends_on=[],
    )
    runtime.require(yolotool_0_result, 'yolotool_0')

    # 依据图像证据判断 road_surface_dameged 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 road_surface_dameged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 road_surface_dameged 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
