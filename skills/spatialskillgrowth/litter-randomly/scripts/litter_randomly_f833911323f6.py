"""Executable SpatialSkillGrowth Skill: litter_randomly_detector."""

WORKFLOW_ID = 'litter_randomly_f833911323f6'
PROBLEM_CLASS = 'litter_randomly'
WORKFLOW_GRAPH_SHA256 = '771d6f0d5df1b54927e00565ce99cb89d8c1c08d01d6959c0dbf0c0ba7909527'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'litter_randomly_f833911323f6', 'name': 'litter_randomly_detector', 'problem_class': 'litter_randomly', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '检测输入图像中是否发生‘随地乱扔垃圾’异常事件。工作流首先使用 YOLO 工具以 0.5 的置信度阈值识别潜在目标，随后结合多模态大语言模型（MLLM）分析视觉证据，综合判断是否存在该特定异常行为。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 其他类型的异常事件检测（仅限 litter_randomly）', 'capability_boundary': '{"event_type": "litter_randomly", "media_type": "image", "detection_logic": "基于 YOLO 目标检测（阈值 0.5）与 MLLM 语义判断的联合推理", "output_format": "二元判断（是/否）"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 litter_randomly 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'whole_image', 'kind': 'world_model', 'description': '分析完整图像。', 'args': {}}], 'purpose': '依据图像证据判断 litter_randomly 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 litter_randomly 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 litter_randomly 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析完整图像。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 litter_randomly 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
