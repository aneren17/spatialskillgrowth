"""Executable SpatialSkillGrowth Skill: fight_detection_workflow."""

WORKFLOW_ID = 'fight_d0dd12ac36b0'
PROBLEM_CLASS = 'fight'
WORKFLOW_GRAPH_SHA256 = '7d3c748d908b9013ca9ba9febfef4f2b6215cf459e2a7305a66bac1d7e203e35'
DECLARED_TOOLS = ('paddleHeadDetTool', 'yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fight_d0dd12ac36b0', 'name': 'fight_detection_workflow', 'problem_class': 'fight', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'yoloTool', 'MLLM'], 'description': '基于多模态视觉证据检测图像中是否发生打架斗殴事件。工作流首先通过 paddleHeadDetTool 检测可见人头以确认人员存在，同时利用 yoloTool（阈值 0.5）识别潜在的攻击性动作或物体交互。随后，MLLM 综合人头检测结果与 YOLO 提取的视觉特征，依据打架斗殴的视觉表现（如肢体冲突、攻击姿态）进行最终判定。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 未检测到可见人头且缺乏明确肢体冲突视觉证据的场景; 需要调用 embeddingTool 进行语义嵌入处理的场景; 非打架斗殴类别的异常事件（如跌倒、火灾、盗窃等）', 'capability_boundary': '{"supported_media": "image", "event_type": "fight", "required_evidence": ["paddleHeadDetTool 检测到的人头实例", "yoloTool 在 0.5 阈值下检测到的目标或动作特征"], "decision_logic": "MLLM 基于上述工具输出的视觉证据进行二分类判断（是/否）"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fight 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 fight 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0', 'yolotool_0']}]}


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

    # 依据图像证据判断 fight 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fight 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fight 异常事件。',
        depends_on=['paddleheaddettool_0', 'yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
