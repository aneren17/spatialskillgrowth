"""Executable SpatialSkillGrowth Skill: emergency_lane_occupancy_detector."""

WORKFLOW_ID = 'emergency_lane_occupancy_2fff1b65dc02'
PROBLEM_CLASS = 'emergency_lane_occupancy'
WORKFLOW_GRAPH_SHA256 = 'd6959949ee81d4dfe7f9322b6e66c00123e97ec7ecaa68628b31272f1697c5e2'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'emergency_lane_occupancy_2fff1b65dc02', 'name': 'emergency_lane_occupancy_detector', 'problem_class': 'emergency_lane_occupancy', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于图像输入，利用目标检测模型（YoloTool）提取视觉特征，并结合多模态大语言模型（MLLM）进行语义推理，以判定是否存在‘占用应急车道’的异常事件。该工作流严格限定于静态图像分析，通过检测车辆与车道线的空间关系来收集证据，最终输出二值化的异常判断结果。', 'exclusions': '视频流、音频或其他非图像类型的媒体输入; 需要调用 embeddingTool 进行向量检索的场景; 其他类型的交通异常事件（如逆行、超速、事故等），本工作流仅针对应急车道占用; 缺乏清晰车道线或应急车道标识的图像场景，可能导致检测器失效', 'capability_boundary': '{"supported_event_type": "emergency_lane_occupancy", "supported_media_type": "image", "detection_method": "视觉证据收集（YoloTool 目标检测 + MLLM 语义判断）", "output_format": "binary (是/否)", "constraints": ["必须保留 event_type 为 emergency_lane_occupancy", "禁止泛化至其他异常类别", "禁止修改或覆盖人工维护的 SKILL.md 与 scripts/*.py 文件"]}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 emergency_lane_occupancy 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 emergency_lane_occupancy 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 emergency_lane_occupancy 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 emergency_lane_occupancy 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 emergency_lane_occupancy 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
