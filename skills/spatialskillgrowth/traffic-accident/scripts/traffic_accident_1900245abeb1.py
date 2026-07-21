"""Executable SpatialSkillGrowth Skill: traffic_accident_detector."""

WORKFLOW_ID = 'traffic_accident_1900245abeb1'
PROBLEM_CLASS = 'traffic_accident'
WORKFLOW_GRAPH_SHA256 = '7802d3f0818fd97ecd7ceb4117aa2e50afb60219fbf3905ef8aa2da86a51085b'
DECLARED_TOOLS = ('yoloTool', 'paddlePedriderDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'traffic_accident_1900245abeb1', 'name': 'traffic_accident_detector', 'problem_class': 'traffic_accident', 'required_slots': [], 'required_tools': ['yoloTool', 'paddlePedriderDetTool', 'MLLM'], 'description': '基于图像输入，利用 YOLO 目标检测与行人/骑行者专用检测器提取视觉证据，结合多模态大模型判断是否发生交通事故。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的场景; 非交通事故类别的异常事件检测; 未包含交通参与者或车辆相关视觉元素的场景', 'capability_boundary': '{"required_tools": ["yoloTool", "paddlePedriderDetTool", "MLLM"], "event_type": "traffic_accident", "media_type": "image", "evidence_requirements": "必须通过 yoloTool 和 paddlePedriderDetTool 获取结构化检测框及类别信息，并作为 MLLM 判断的依据", "limitations": "仅适用于静态图像分析，不支持视频流或实时动态检测；检测精度受限于底层视觉模型对遮挡、低光照等复杂环境的鲁棒性"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 traffic_accident 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0', 'paddlepedriderdettool_0']}]}


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

    # 检测交通参与者。
    paddlepedriderdettool_0_result = runtime.call(
        'paddlePedriderDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddlePedriderDetTool'},
        step_id='paddlepedriderdettool_0',
        purpose='检测交通参与者。',
        depends_on=[],
    )
    runtime.require(paddlepedriderdettool_0_result, 'paddlepedriderdettool_0')

    # 依据图像证据判断 traffic_accident 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 traffic_accident 异常事件。',
        depends_on=['yolotool_0', 'paddlepedriderdettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
