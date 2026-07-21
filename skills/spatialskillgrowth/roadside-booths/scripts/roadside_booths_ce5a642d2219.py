"""Executable SpatialSkillGrowth Skill: roadside_booths_detector."""

WORKFLOW_ID = 'roadside_booths_ce5a642d2219'
PROBLEM_CLASS = 'roadside_booths'
WORKFLOW_GRAPH_SHA256 = '5e7547d1c3b29eab7d19937825981901313917bf6aa8066041a3647a90aca59a'
DECLARED_TOOLS = ('paddleOcrTool', 'yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'roadside_booths_ce5a642d2219', 'name': 'roadside_booths_detector', 'problem_class': 'roadside_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'yoloTool', 'unidepth', 'MLLM'], 'description': '基于多模态视觉证据检测图像中是否存在占道经营（roadside_booths）异常事件。通过目标检测识别潜在摊位结构，利用深度估计分析其空间位置关系，并结合OCR提取的文字信息，综合判断是否构成占道经营。', 'exclusions': '非图像类型的输入数据; 需要调用embeddingTool的场景; 非roadside_booths类别的其他异常事件检测; 缺乏可见文字或目标结构导致无法获取必要视觉证据的场景', 'capability_boundary': '仅适用于静态图像输入，依赖yoloTool进行目标检测（阈值0.5）、unidepth进行深度估计以及paddleOcrTool进行文字识别，最终由多模态大模型依据上述视觉证据判断是否存在占道经营行为。', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 roadside_booths 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 roadside_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'yolotool_0', 'unidepth_0']}]}


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

    # 依据图像证据判断 roadside_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 roadside_booths 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 roadside_booths 异常事件。',
        depends_on=['paddleocrtool_0', 'yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
