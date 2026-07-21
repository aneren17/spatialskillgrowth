"""Executable SpatialSkillGrowth Skill: occluded_license_plate_detector."""

WORKFLOW_ID = 'occluded_license_plate_3e48518cbbb4'
PROBLEM_CLASS = 'occluded_license_plate'
WORKFLOW_GRAPH_SHA256 = '3690413b29f4a9246ff606e4594267d22c7a3cd296e6415ed2710a25a67e41f3'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'occluded_license_plate_3e48518cbbb4', 'name': 'occluded_license_plate_detector', 'problem_class': 'occluded_license_plate', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '检测输入图像中是否存在车牌遮挡异常。该工作流首先通过 OCR 工具提取图像中的可见文字信息，随后结合多模态大语言模型分析视觉证据，判断车牌是否被物理遮挡、污损或故意遮蔽，导致无法完整识别。', 'exclusions': '非图像类型的媒体输入（如视频流、音频或纯文本）; 图像中未包含车辆或车牌区域; 车牌清晰可见且无任何遮挡、污损或变形; 因光照不足、运动模糊或分辨率过低导致车牌完全不可见（此类属于图像质量问题，而非遮挡异常）; 使用 embedding 工具进行特征提取的场景', 'capability_boundary': '{"required_slots": {"event_type": "occluded_license_plate", "media_type": "image"}, "evidence_requirements": ["必须包含通过 paddleOcrTool 提取的可见文字证据", "必须包含 MLLM 基于图像视觉特征对遮挡状态的定性判断"], "limitations": ["仅适用于静态图像输入", "无法区分遮挡意图（故意遮挡 vs 无意遮挡），仅检测遮挡事实", "依赖 OCR 工具对可见部分的识别能力，若车牌完全不可见则无法通过文字证据辅助判断"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 occluded_license_plate 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 occluded_license_plate 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 读取可见文字。
    paddleocrtool_0_result = runtime.call(
        'paddleOcrTool',
        {'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='paddleocrtool_0',
        purpose='读取可见文字。',
        depends_on=[],
    )
    runtime.require(paddleocrtool_0_result, 'paddleocrtool_0')

    # 依据图像证据判断 occluded_license_plate 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 occluded_license_plate 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 occluded_license_plate 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
