"""Executable SpatialSkillGrowth Skill: run_the_red_light."""

WORKFLOW_ID = 'run_the_red_light_dedd1e22d850'
PROBLEM_CLASS = 'run_the_red_light'
WORKFLOW_GRAPH_SHA256 = '7e5fdecf0a394e88ab936c59399d72d2d69c1740830eac494863e91240964ba7'
DECLARED_TOOLS = ('paddleOcrTool', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'run_the_red_light_dedd1e22d850', 'name': 'run_the_red_light', 'problem_class': 'run_the_red_light', 'required_slots': [], 'required_tools': ['paddleOcrTool', 'MLLM'], 'description': '基于图像输入，通过光学字符识别提取可见文字证据，并结合多模态大模型分析视觉特征，检测是否存在闯红灯异常事件。', 'exclusions': '非图像类型的媒体输入; 未包含交通信号灯或车辆相关视觉信息的场景; 需要调用 embeddingTool 的处理流程', 'capability_boundary': '{"event_type": "run_the_red_light", "media_type": "image", "required_evidence": ["paddleOcrTool 提取的可见文字", "MLLM 基于图像证据的分析结果"]}', 'steps': [{'tool_name': 'paddleOcrTool', 'args': {'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'paddleOcrTool', 'axis': 'evidence_role', 'value': 'text_reading', 'kind': 'fixed', 'description': '读取可见文字。', 'args': {}}], 'purpose': '读取可见文字。', 'step_id': 'paddleocrtool_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [], 'purpose': '依据图像证据判断 run_the_red_light 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleocrtool_0']}]}


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

    # 依据图像证据判断 run_the_red_light 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请结合下方工具证据与输入图像回答问题，不要基于缺少证据的假设猜测。只输出最终答案。\n证据：\n$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 run_the_red_light 异常事件。',
        depends_on=['paddleocrtool_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
