"""Executable SpatialSkillGrowth Skill: traffic_accident_detector."""

WORKFLOW_ID = 'traffic_accident_34f138c7ac64'
PROBLEM_CLASS = 'traffic_accident'
WORKFLOW_GRAPH_SHA256 = 'aa14b2a29fe617eb1da361b8bae34ad5aa253a5c2d237c7f1ad49b08fe019cc0'
DECLARED_TOOLS = ('yoloTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'traffic_accident_34f138c7ac64', 'name': 'traffic_accident_detector', 'problem_class': 'traffic_accident', 'required_slots': [], 'required_tools': ['yoloTool', 'MLLM'], 'description': '基于 YOLO 目标检测（阈值 0.5）与多模态大模型推理，分析输入图像中是否存在交通事故异常事件。该工作流通过视觉证据收集与语义判断，确认场景中是否包含符合交通事故定义的视觉特征。', 'exclusions': '非图像类型的媒体输入; 需要调用 embeddingTool 的嵌入向量分析任务; 非交通事故类别的其他异常事件检测; 未提供有效图像数据或图像内容完全无法解析的情况', 'capability_boundary': '{"event_type": "traffic_accident", "media_type": "image", "required_evidence": ["YOLO 检测到的相关目标实体（置信度 >= 0.5）", "多模态模型基于图像内容对事故状态的语义判断"], "limitations": "仅适用于静态图像分析，不包含视频时序分析或音频证据处理；检测范围严格限定于交通事故，不泛化至其他交通违规或非交通类事故。"}', 'steps': [{'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 traffic_accident 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['yolotool_0']}]}


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

    # 依据图像证据判断 traffic_accident 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 traffic_accident 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 traffic_accident 异常事件。',
        depends_on=['yolotool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
