"""Executable SpatialSkillGrowth Skill: breaking_through_toll_booths_detector."""

WORKFLOW_ID = 'breaking_through_toll_booths_53481044122a'
PROBLEM_CLASS = 'breaking_through_toll_booths'
WORKFLOW_GRAPH_SHA256 = '6126f01948eab955afe3f6ef59b65a119ac934b2f04b22a3d2cdabeb45db8986'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'breaking_through_toll_booths_53481044122a', 'name': 'breaking_through_toll_booths_detector', 'problem_class': 'breaking_through_toll_booths', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '检测输入图像中是否发生车辆或物体强行通过收费站（闯收费站）的异常事件。该工作流通过OCR提取现场可见文字信息，并结合多模态大模型对图像中的车辆行为、收费站物理状态及通行合规性进行综合视觉证据分析，以判断是否存在违规闯卡行为。', 'exclusions': '非收费站场景（如普通道路、停车场入口、高速匝道等无收费设施区域）; 图像质量严重受损导致无法识别车辆位置或收费站结构的情况; 仅包含静态收费站设施而无车辆或移动物体的图像; 需要视频时序分析才能判断的连续闯卡行为（本工作流仅支持单帧图像分析）', 'capability_boundary': '{"event_type": "breaking_through_toll_booths", "required_evidence": ["收费站物理设施（栏杆、亭子、标识等）的视觉存在", "车辆或移动物体与收费站设施的相对位置关系", "OCR识别出的收费站相关文字信息（如站名、通道状态等）", "车辆是否处于非正常通行状态（如栏杆未升起时通过、撞击设施等）"], "limitations": ["仅支持单张静态图像分析，不支持视频流或时序数据", "依赖图像中收费站标识和车辆特征的清晰可见性", "无法判断驾驶员身份或主观意图，仅基于视觉行为判定"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 breaking_through_toll_booths 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 breaking_through_toll_booths 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 breaking_through_toll_booths 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 breaking_through_toll_booths 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
