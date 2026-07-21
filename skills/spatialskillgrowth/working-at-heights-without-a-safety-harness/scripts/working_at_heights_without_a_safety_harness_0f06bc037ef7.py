"""Executable SpatialSkillGrowth Skill: working_at_heights_without_a_safety_harness_detector."""

WORKFLOW_ID = 'working_at_heights_without_a_safety_harness_0f06bc037ef7'
PROBLEM_CLASS = 'working_at_heights_without_a_safety_harness'
WORKFLOW_GRAPH_SHA256 = '16584540f0cf4cd4c76214567e20bdf986c6539a56d5087194e45c0e5f42e557'
DECLARED_TOOLS = ('yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'working_at_heights_without_a_safety_harness_0f06bc037ef7', 'name': 'working_at_heights_without_a_safety_harness_detector', 'problem_class': 'working_at_heights_without_a_safety_harness', 'required_slots': [], 'required_tools': ['yoloTool', 'unidepth', 'MLLM'], 'description': '基于YOLO目标检测、UniDepth深度估计及多模态大模型（MLLM）的视觉证据链，检测输入图像中是否存在人员处于高空作业状态但未佩戴安全带的异常事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用embeddingTool进行语义嵌入的场景; 非高空作业场景（如地面作业、室内低处作业）; 已正确佩戴安全带的高空作业场景; 无法通过YOLO检测出人员或安全装备的极端遮挡或模糊图像; 涉及其他类型异常事件（如火灾、入侵、设备故障等）的检测需求', 'capability_boundary': '{"required_event_type": "working_at_heights_without_a_safety_harness", "required_media_type": "image", "detection_logic": "通过YOLO检测人员及潜在安全装备，结合UniDepth估算相对高度以确认‘高空’属性，最终由MLLM综合视觉证据判断是否缺失安全带", "abstractable_entities": "无（工具图中无通用物体槽位，检测器严格限定于‘人员’与‘安全带’相关视觉特征）", "output_format": "二元分类（是/否）"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 working_at_heights_without_a_safety_harness 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'unidepth_0']}]}


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

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(yolotool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['yolotool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 working_at_heights_without_a_safety_harness 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。',
        depends_on=['yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
