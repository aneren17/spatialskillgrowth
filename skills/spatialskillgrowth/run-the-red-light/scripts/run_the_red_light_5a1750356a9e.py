"""Executable SpatialSkillGrowth Skill: run_the_red_light."""

WORKFLOW_ID = 'run_the_red_light_5a1750356a9e'
PROBLEM_CLASS = 'run_the_red_light'
WORKFLOW_GRAPH_SHA256 = '7fa81f60835936d65a81b83335db27906dbde6ba3d3c29e200ab347678426d96'
DECLARED_TOOLS = ('paddleOcrTool', 'paddlePedriderDetTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'run_the_red_light_5a1750356a9e', 'name': 'run_the_red_light', 'problem_class': 'run_the_red_light', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'paddlePedriderDetTool', 'MLLM'], 'description': '检测输入图像中是否存在车辆或行人闯红灯的异常行为。该工作流通过OCR识别交通标志文字、检测交通参与者，并结合多模态大模型分析视觉证据，判断是否发生闯红灯事件。', 'exclusions': '非图像类型的媒体输入; 无法清晰识别交通信号灯状态或车辆/行人位置的模糊图像; 非交通场景的图像; 需要视频时序分析而非单帧图像判断的场景', 'capability_boundary': '{"event_type": "run_the_red_light", "media_type": "image", "required_evidence": ["交通信号灯状态（红色）", "交通参与者（车辆或行人）位置", "停止线或路口位置关系"], "tools": ["paddleOcrTool", "paddlePedriderDetTool", "MLLM"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 run_the_red_light 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 run_the_red_light 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0', 'paddlepedriderdettool_0']}]}


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

    # 依据图像证据判断 run_the_red_light 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 run_the_red_light 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 run_the_red_light 异常事件。',
        depends_on=['paddleocrtool_0', 'paddlepedriderdettool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
