"""Executable SpatialSkillGrowth Skill: fight_detection_image."""

WORKFLOW_ID = 'fight_0bebbe640bf1'
PROBLEM_CLASS = 'fight'
WORKFLOW_GRAPH_SHA256 = '1fbf11be95cf4683cdd6d11e1cd7d0b1e312a1c8a1e7448e3d7ea443b39d27be'
DECLARED_TOOLS = ('paddleHeadDetTool', 'yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fight_0bebbe640bf1', 'name': 'fight_detection_image', 'problem_class': 'fight', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'yoloTool', 'unidepth', 'MLLM'], 'description': '基于静态图像输入，通过结合人头检测、通用目标检测及深度估计的多模态证据，判断场景中是否存在‘打架斗殴’异常事件。该工作流利用 PaddleHeadDetTool 定位人头，YoloTool 识别潜在冲突目标，Unidepth 评估空间深度关系，最终由多模态大模型综合视觉证据进行判定。', 'exclusions': "非图像类型的媒体输入（如视频流、音频），需使用其他适配的工作流。; 图像中完全无法检测到人头或关键目标，导致缺乏基础视觉证据的场景。; 需要语义嵌入分析（embedding）的场景，本工作流禁止调用 embeddingTool。; 非‘打架斗殴’类别的其他异常事件检测，本工作流严格限定于 event_type 为 'fight' 的场景。", 'capability_boundary': '仅适用于静态图像输入下的打架斗殴事件检测。检测能力依赖于工具链中人头检测、目标检测（阈值0.5）及深度估计的准确性。最终判断严格基于多模态模型对视觉证据的综合分析，输出结果为二元判定（是/否）。', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fight 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 fight 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0', 'yolotool_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

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

    # 依据图像证据判断 fight 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fight 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fight 异常事件。',
        depends_on=['paddleheaddettool_0', 'yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
