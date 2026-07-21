"""Executable SpatialSkillGrowth Skill: platform_yellowline_detector."""

WORKFLOW_ID = 'platform_yellowline_a1314fd8a363'
PROBLEM_CLASS = 'platform_yellowline'
WORKFLOW_GRAPH_SHA256 = '237915482796a5b3e026d287ea7aa75dabd008cb7da0d722bff0bf6822576d65'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'platform_yellowline_a1314fd8a363', 'name': 'platform_yellowline_detector', 'problem_class': 'platform_yellowline', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测与多模态大语言模型（MLLM）的视觉证据链，检测图像中是否存在人员或物体越过站台安全黄线的异常行为。', 'exclusions': '非站台场景（如普通道路、室内走廊无黄线区域）; 未包含清晰站台黄线视觉特征的低分辨率或模糊图像; 非图像类型的媒体输入', 'capability_boundary': '{"event_type": "platform_yellowline", "media_type": "image", "detection_logic": "通过 yoloTool 定位关键视觉元素，结合 MLLM 分析空间位置关系以判定是否越线", "evidence_requirement": "必须包含站台黄线及潜在越线主体的视觉证据"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 platform_yellowline 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 platform_yellowline 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 platform_yellowline 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 platform_yellowline 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 platform_yellowline 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
