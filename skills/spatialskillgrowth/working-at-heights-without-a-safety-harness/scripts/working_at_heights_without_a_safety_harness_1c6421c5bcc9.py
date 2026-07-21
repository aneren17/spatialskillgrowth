"""Executable SpatialSkillGrowth Skill: working_at_heights_without_a_safety_harness_detector."""

WORKFLOW_ID = 'working_at_heights_without_a_safety_harness_1c6421c5bcc9'
PROBLEM_CLASS = 'working_at_heights_without_a_safety_harness'
WORKFLOW_GRAPH_SHA256 = 'c6219ac131e9063a3a9f0bbffbac3983a07321a04da36c6187f472c883f66250'
DECLARED_TOOLS = ('yoloTool', 'paddleHeadDetTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'working_at_heights_without_a_safety_harness_1c6421c5bcc9', 'name': 'working_at_heights_without_a_safety_harness_detector', 'problem_class': 'working_at_heights_without_a_safety_harness', 'required_slots': [], 'required_tools': ['yoloTool', 'paddleHeadDetTool', 'unidepth', 'MLLM'], 'description': '基于图像输入，利用目标检测（YOLO）、人头检测（PaddleHeadDet）及深度估计（UniDepth）工具收集视觉证据，并通过多模态大模型（MLLM）综合判断是否存在‘高空作业未系安全带’异常事件。该工作流严格限定于检测人员在进行高空作业时未正确佩戴或连接安全带的违规行为，依赖于对人员位置、高度及安全带状态的视觉证据链。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 不涉及人员高空作业的场景（如地面作业、室内低处活动）; 无法通过视觉证据明确判断安全带佩戴状态或作业高度的模糊场景; 需要调用 embeddingTool 进行语义嵌入的场景（本工作流禁止使用）; 其他类型的异常事件检测（如火灾、入侵、设备故障等）', 'capability_boundary': '{"event_type": "working_at_heights_without_a_safety_harness", "required_evidence": ["通过 YOLO 工具检测到的相关物体或人员轮廓", "通过 PaddleHeadDet 工具检测到的可见人头位置", "通过 UniDepth 工具估计的深度信息以辅助判断作业高度", "MLLM 基于上述视觉证据对安全带佩戴状态的最终判定"], "limitations": ["仅支持静态图像输入，不支持实时视频流分析", "依赖检测工具对人员和头部的识别精度，遮挡严重可能导致漏检", "深度估计可能存在误差，影响对‘高空’定义的精确判断", "无法检测非视觉可辨的安全带类型或隐蔽式安全带"]}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.paddleheaddettool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['paddleheaddettool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 working_at_heights_without_a_safety_harness 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'paddleheaddettool_0', 'unidepth_0']}]}


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

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(paddleheaddettool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['paddleheaddettool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 working_at_heights_without_a_safety_harness 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 working_at_heights_without_a_safety_harness 异常事件。',
        depends_on=['yolotool_0', 'paddleheaddettool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
