"""Executable SpatialSkillGrowth Skill: run_the_red_light."""

WORKFLOW_ID = 'run_the_red_light_ed990c3cbf1e'
PROBLEM_CLASS = 'run_the_red_light'
WORKFLOW_GRAPH_SHA256 = 'd1c776b1c35a9994b56ad9eee47c9ab654f9f1285370ffda94e1c082e83ee9d9'
DECLARED_TOOLS = ('paddleOcrTool', 'paddlePedriderDetTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'run_the_red_light_ed990c3cbf1e', 'name': 'run_the_red_light', 'problem_class': 'run_the_red_light', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'paddlePedriderDetTool', 'unidepth', 'MLLM'], 'description': '检测输入图像中是否存在交通参与者（如行人、骑行者）在交通信号灯显示红灯时，违规通过路口或停止线的行为。工作流通过OCR识别交通标志文字、检测交通参与者位置及深度，并结合多模态大模型综合判断是否构成闯红灯异常。', 'exclusions': '非交通路口场景（如小区内部道路、无信号灯路段）; 图像中未包含可见的交通信号灯或交通参与者; 信号灯状态模糊不清或无法通过OCR/视觉证据明确判定为红灯; 交通参与者未处于通过路口或越过停止线的动作状态; 非图像类型的媒体输入', 'capability_boundary': '{"event_type": "run_the_red_light", "media_type": "image", "required_evidence": ["交通信号灯显示为红色的视觉证据或OCR识别结果", "交通参与者（行人或骑行者）的检测框及位置信息", "交通参与者相对于停止线或路口的深度/位置关系证据"], "output_format": "binary_yes_no"}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.paddlepedriderdettool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['paddlepedriderdettool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 run_the_red_light 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 run_the_red_light 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'paddlepedriderdettool_0', 'unidepth_0']}]}


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

    # 检测交通参与者。
    paddlepedriderdettool_0_result = runtime.call(
        'paddlePedriderDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddlePedriderDetTool'},
        step_id='paddlepedriderdettool_0',
        purpose='检测交通参与者。',
        depends_on=[],
    )
    runtime.require(paddlepedriderdettool_0_result, 'paddlepedriderdettool_0')

    # 估计检测目标深度。
    unidepth_0_result = runtime.call(
        'unidepth',
        {'detections': runtime.value(paddlepedriderdettool_0_result, 'detections_json'), 'file': runtime.image_path(), 'filename': runtime.filename()},
        step_id='unidepth_0',
        purpose='估计检测目标深度。',
        depends_on=['paddlepedriderdettool_0'],
    )
    runtime.require(unidepth_0_result, 'unidepth_0')

    # 依据图像证据判断 run_the_red_light 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 run_the_red_light 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 run_the_red_light 异常事件。',
        depends_on=['paddleocrtool_0', 'paddlepedriderdettool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
