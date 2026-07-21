"""Executable SpatialSkillGrowth Skill: tree_fallen_detector."""

WORKFLOW_ID = 'tree_fallen_5b4213dceb8e'
PROBLEM_CLASS = 'tree_fallen'
WORKFLOW_GRAPH_SHA256 = '44eeaf722128707f8bb9f6a46811f394669ab0ecf46660e7fd567a6fa93847c4'
DECLARED_TOOLS = ('yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'tree_fallen_5b4213dceb8e', 'name': 'tree_fallen_detector', 'problem_class': 'tree_fallen', 'required_slots': [], 'required_tools': ['yoloTool', 'unidepth', 'MLLM'], 'description': '基于图像输入检测树木倒伏异常事件。工作流首先利用 YOLO 工具以 0.5 的置信度阈值检测潜在目标，随后通过 UniDepth 估计检测目标的深度信息，最后结合多模态大语言模型（MLLM）综合视觉证据判断是否发生树木倒伏。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非 tree_fallen 类别的异常事件检测; 未提供有效图像数据的请求', 'capability_boundary': '{"input_media": "image", "event_type": "tree_fallen", "detection_logic": "依赖 YOLO 目标检测、UniDepth 深度估计及 MLLM 语义推理的串联工作流", "output_format": "布尔值（是/否）"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 tree_fallen 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 tree_fallen 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'unidepth_0']}]}


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

    # 依据图像证据判断 tree_fallen 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 tree_fallen 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 tree_fallen 异常事件。',
        depends_on=['yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
