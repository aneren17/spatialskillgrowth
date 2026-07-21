"""Executable SpatialSkillGrowth Skill: fall_detection_workflow."""

WORKFLOW_ID = 'fall_68edd8ec2f06'
PROBLEM_CLASS = 'fall'
WORKFLOW_GRAPH_SHA256 = 'c28a1166d92a56d3dad6d0f3cc650bb734777b04b3bb5656419b362423e6b988'
DECLARED_TOOLS = ('groundingdino', 'yoloTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'fall_68edd8ec2f06', 'name': 'fall_detection_workflow', 'problem_class': 'fall', 'required_slots': [], 'required_tools': ['groundingdino', 'yoloTool', 'unidepth', 'MLLM'], 'description': '基于多模态视觉证据的静态图像人员摔倒检测工作流。该流程通过 GroundingDINO 进行开放词汇目标定位，结合 YOLO 进行高精度目标检测，并利用 UniDepth 估计目标深度信息，最终由多模态大语言模型综合几何与空间证据判断是否发生摔倒事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）。; 场景中不存在人类主体的情况。; 图像质量严重受损导致无法提取有效视觉特征（如极度模糊、过曝或完全遮挡）。; 需要时间序列分析才能判定的动态跌倒过程（本工作流仅适用于单帧静态图像分析）。', 'capability_boundary': '{"supported_event_type": "fall", "supported_media_type": "image", "evidence_requirements": ["必须包含由 groundingdino 和 yolotool 提供的人体目标边界框。", "必须包含由 unidepth 提供的目标深度估计数据以辅助姿态判断。", "最终判定依赖于 MLLM 对上述视觉证据的综合推理。"], "limitations": "仅能检测单帧图像中呈现的摔倒姿态，无法区分摔倒的具体原因或后续状态，且依赖于检测工具对人体目标的准确识别。"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'fall', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'yoloTool', 'args': {'file': '$image', 'filename': '$filename', 'threshold': 0.5}, 'param_atoms': [{'tool_name': 'yoloTool', 'axis': 'threshold', 'value': 'medium', 'kind': 'numerical', 'description': '使用 0.5 检测阈值。', 'args': {}}], 'purpose': '使用 0.5 检测阈值。', 'step_id': 'yolotool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.yolotool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['yolotool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 fall 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'yolotool_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'fall', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

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

    # 依据图像证据判断 fall 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fall 异常事件。',
        depends_on=['groundingdino_0', 'yolotool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
