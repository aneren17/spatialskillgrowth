"""Executable SpatialSkillGrowth Skill: tree_fallen_detector."""

WORKFLOW_ID = 'tree_fallen_cda35fb4d7a4'
PROBLEM_CLASS = 'tree_fallen'
WORKFLOW_GRAPH_SHA256 = 'e1af5f9101511ba72e8b74c3ac1247414d87b9c7932a3193541f7aa4e11d6e84'
DECLARED_TOOLS = ('yoloTool', 'groundingdino', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'tree_fallen_cda35fb4d7a4', 'name': 'tree_fallen_detector', 'problem_class': 'tree_fallen', 'required_slots': [], 'required_tools': ['yoloTool', 'groundingdino', 'unidepth', 'MLLM'], 'description': '针对静态图像输入，检测是否存在树木倒伏或倒塌的异常事件。该工作流结合目标检测（YOLO、GroundingDINO）与深度估计（UniDepth）提取视觉证据，并由多模态大语言模型进行最终判定。', 'exclusions': '非图像类型的媒体输入; 非树木倒伏类别的其他异常事件检测; 需要调用 embeddingTool 的场景', 'capability_boundary': '{"required_evidence": ["基于 YOLO 和 GroundingDINO 的目标检测结果", "基于 UniDepth 的目标深度估计信息"], "supported_media": ["image"], "event_type": "tree_fallen", "limitation_note": "仅适用于图像模态下的树木倒伏检测，不泛化至其他异常类别或非图像输入"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'groundingdino', 'args': {'query': "使用提示词 'fallen tree, downed tree' 检测图像中是否存在倒伏的树木主体，以弥补当前仅有人物检测结果的不足", 'file': '$image', 'filename': '$filename', 'box_threshold': 0.5, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.5 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.groundingdino_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 tree_fallen 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 tree_fallen 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'groundingdino_0', 'unidepth_0']}]}


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

    # 使用 0.5 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': "使用提示词 'fallen tree, downed tree' 检测图像中是否存在倒伏的树木主体，以弥补当前仅有人物检测结果的不足", 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.5, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.5 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 tree_fallen 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 tree_fallen 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 tree_fallen 异常事件。',
        depends_on=['yolotool_0', 'groundingdino_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
