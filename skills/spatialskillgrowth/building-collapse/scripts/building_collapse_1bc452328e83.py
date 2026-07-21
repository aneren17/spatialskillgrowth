"""Executable SpatialSkillGrowth Skill: building_collapse_detector."""

WORKFLOW_ID = 'building_collapse_1bc452328e83'
PROBLEM_CLASS = 'building_collapse'
WORKFLOW_GRAPH_SHA256 = 'ccd8aab423a1c118477d6d08fd5352fd5c6ba376f4761a7c50b62024c70390d9'
DECLARED_TOOLS = ('yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'building_collapse_1bc452328e83', 'name': 'building_collapse_detector', 'problem_class': 'building_collapse', 'required_slots': [], 'required_tools': ['yoloTool', 'unidepth', 'MLLM'], 'description': '针对静态图像输入，通过目标检测（yoloTool）与深度估计（unidepth）结合多模态大模型（MLLM）分析，检测是否存在建筑坍塌（building_collapse）异常事件。该工作流依赖于视觉证据中的结构破坏特征与空间深度信息，适用于需要精确判定建筑物是否发生倒塌场景的自动化检测任务。', 'exclusions': '非图像类媒体输入（如视频流、音频、纯文本描述）。; 未包含建筑物或结构物的场景（如自然景观、室内无结构背景）。; 需要实时视频流分析或连续帧时序推理的任务。; 依赖 Embedding 工具进行特征提取的场景。; 非 building_collapse 类别的其他异常事件（如火灾、洪水、交通事故等）。', 'capability_boundary': '{"required_event_type": "building_collapse", "required_media_type": "image", "tool_dependencies": ["yoloTool", "unidepth", "MLLM"], "evidence_requirements": ["目标检测结果（阈值 0.5）", "检测目标的深度估计信息", "多模态模型对视觉证据的综合判断"], "output_format": "binary (是/否)"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 building_collapse 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 building_collapse 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'unidepth_0']}]}


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

    # 依据图像证据判断 building_collapse 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 building_collapse 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 building_collapse 异常事件。',
        depends_on=['yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
