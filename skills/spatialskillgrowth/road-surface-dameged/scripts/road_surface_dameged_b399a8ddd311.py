"""Executable SpatialSkillGrowth Skill: road_surface_dameged_detector."""

WORKFLOW_ID = 'road_surface_dameged_b399a8ddd311'
PROBLEM_CLASS = 'road_surface_dameged'
WORKFLOW_GRAPH_SHA256 = '53b010f07f1b13e91d98a7479701bc6189a389487b3480cf0846cbd8e1b292a6'
DECLARED_TOOLS = ('yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'road_surface_dameged_b399a8ddd311', 'name': 'road_surface_dameged_detector', 'problem_class': 'road_surface_dameged', 'required_slots': [], 'required_tools': ['yoloTool', 'unidepth', 'MLLM'], 'description': '基于YOLO目标检测、UniDepth深度估计及多模态大语言模型（MLLM）的联合推理工作流，用于在图像输入中检测路面破损异常。该流程首先利用YOLO以0.3阈值识别潜在破损区域，随后通过UniDepth获取空间深度信息，最后由MLLM综合视觉特征与深度证据判定是否发生road_surface_dameged事件。', 'exclusions': '非图像类型的媒体输入; 需要调用embeddingTool的场景; 非road_surface_dameged类别的异常检测任务; 缺乏YOLO检测目标或无法进行深度估计的图像场景', 'capability_boundary': '仅支持静态图像输入下的road_surface_dameged事件检测，依赖yoloTool进行初步定位、unidepth进行深度辅助以及MLLM进行最终语义判断，不包含视频流处理或实时动态检测能力。', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.3}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 检测阈值。', 'args': {}}], 'purpose': '使用 0.3 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 road_surface_dameged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 road_surface_dameged 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'unidepth_0']}]}


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

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(yolotool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['yolotool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 road_surface_dameged 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 road_surface_dameged 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 road_surface_dameged 异常事件。',
        depends_on=['yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
