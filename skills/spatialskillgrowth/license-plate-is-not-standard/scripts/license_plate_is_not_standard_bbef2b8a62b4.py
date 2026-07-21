"""Executable SpatialSkillGrowth Skill: license_plate_is_not_standard."""

WORKFLOW_ID = 'license_plate_is_not_standard_bbef2b8a62b4'
PROBLEM_CLASS = 'license_plate_is_not_standard'
WORKFLOW_GRAPH_SHA256 = '83102d1f96af0dc122c2de5ab68356977562a9b0f7192dea259eebe4320ca9cd'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'license_plate_is_not_standard_bbef2b8a62b4', 'name': 'license_plate_is_not_standard', 'problem_class': 'license_plate_is_not_standard', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '检测输入图像中车辆车牌是否存在不规范情况（如模糊、遮挡、污损、角度严重倾斜或字符缺失等），依据视觉证据判断是否构成 license_plate_is_not_standard 异常事件。', 'exclusions': '非图像类型的媒体输入; 图像中未包含车辆或车牌区域; 需要调用 embeddingTool 进行特征提取的场景; 涉及其他类型异常（如违章停车、超速等）的检测任务', 'capability_boundary': '{"required_event_type": "license_plate_is_not_standard", "required_media_type": "image", "allowed_tools": ["MLLM"], "forbidden_tools": ["embeddingTool"], "evidence_requirement": "必须基于图像中的视觉特征（如车牌清晰度、完整性、规范性）提供判断依据"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 license_plate_is_not_standard 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 license_plate_is_not_standard 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 license_plate_is_not_standard 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 license_plate_is_not_standard 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 license_plate_is_not_standard 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
