"""Executable SpatialSkillGrowth Skill: ebike_reverse_detector."""

WORKFLOW_ID = 'ebike_reverse_583e438d5c97'
PROBLEM_CLASS = 'ebike_reverse'
WORKFLOW_GRAPH_SHA256 = '8358445078ce102566b304fb1d5c99ba525980a1ea92fc3142244c5505c2cde3'
DECLARED_TOOLS = ('groundingdino', 'crop_detections', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'ebike_reverse_583e438d5c97', 'name': 'ebike_reverse_detector', 'problem_class': 'ebike_reverse', 'required_slots': [], 'required_tools': ['groundingdino', 'crop_detections', 'MLLM'], 'description': '基于图像输入，利用 GroundingDINO 进行开放词汇目标检测并裁剪区域，结合多模态大模型（MLLM）分析视觉证据，以判定是否存在非机动车（如电动车）逆行异常事件。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本描述）; 需要调用 embeddingTool 进行特征嵌入的场景; 其他类型的交通异常事件（如闯红灯、违停等），本工作流仅针对 ebike_reverse 类别; 图像中未包含非机动车或道路方向信息，导致无法判断逆行逻辑的场景', 'capability_boundary': '{"required_event_type": "ebike_reverse", "required_media_type": "image", "detection_threshold": 0.3, "evidence_source": "visual_crops_and_groundingdino_detections", "decision_model": "MLLM", "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'ebike_reverse', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'crop_detections', 'args': {'file': '$image', 'detections': '$step.groundingdino_0.detections_json', 'folder': 'spatialskillgrowth', 'score': '0.5', 'className': ''}, 'param_atoms': [{'tool_name': 'crop_detections', 'axis': 'operation', 'value': 'insert_after_detection', 'kind': 'structural', 'description': '裁剪已检测区域。', 'args': {}}], 'purpose': '裁剪已检测区域。', 'step_id': 'crop_detections_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 ebike_reverse 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}], 'purpose': '依据图像证据判断 ebike_reverse 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'crop_detections_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'ebike_reverse', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 裁剪已检测区域。
    crop_detections_0_result = runtime.call(
        'crop_detections',
        {'file': runtime.image_path(), 'detections': runtime.value(groundingdino_0_result, 'detections_json'), 'folder': 'spatialskillgrowth', 'score': '0.5', 'className': ''},
        step_id='crop_detections_0',
        purpose='裁剪已检测区域。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(crop_detections_0_result, 'crop_detections_0')

    # 依据图像证据判断 ebike_reverse 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 ebike_reverse 分析完整图像，并同时遵守以下推理和证据要求：给出明确视觉线索。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 ebike_reverse 异常事件。',
        depends_on=['groundingdino_0', 'crop_detections_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
