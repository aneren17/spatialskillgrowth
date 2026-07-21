"""Executable SpatialSkillGrowth Skill: screen_doors_clamp_passengers_detector."""

WORKFLOW_ID = 'screen_doors_clamp_passengers_f9bb0f23e3a4'
PROBLEM_CLASS = 'screen_doors_clamp_passengers'
WORKFLOW_GRAPH_SHA256 = '36af9fc722fd89451811d7bd1690b791add8b3f1c6d5f8980ee7976d913ef33c'
DECLARED_TOOLS = ('paddleHeadDetTool', 'paddlePedriderDetTool', 'unidepth', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'screen_doors_clamp_passengers_f9bb0f23e3a4', 'name': 'screen_doors_clamp_passengers_detector', 'problem_class': 'screen_doors_clamp_passengers', 'required_slots': [], 'required_tools': ['paddleHeadDetTool', 'paddlePedriderDetTool', 'unidepth', 'MLLM'], 'description': '基于静态图像输入，利用人头检测、行人检测及深度估计工具提取视觉证据，并通过多模态大模型判断屏蔽门与乘客之间是否存在物理夹持异常。该工作流专门针对屏蔽门夹人场景，依赖图像中可检测的人体部位与门体结构的相对位置及深度关系进行判定。', 'exclusions': '非图像类型的媒体输入（如视频流、纯文本描述）; 非屏蔽门夹人类别的其他异常事件（如列车故障、火灾、打架斗殴等）; 图像中无可见乘客或屏蔽门结构，导致无法建立空间关系证据的场景; 需要时序动态分析才能判定的夹人过程（本工作流仅支持单帧静态判断）', 'capability_boundary': '{"required_evidence": ["可见的人头或行人检测框", "屏蔽门与检测目标之间的深度估计值", "多模态模型对‘夹持’状态的语义确认"], "tool_constraints": ["必须使用 paddleHeadDetTool 检测人头", "必须使用 paddlePedriderDetTool 检测交通参与者", "必须使用 unidepth 估计目标深度", "必须使用 MLLM 进行最终逻辑判断", "禁止调用 embeddingTool"], "generalization_scope": "仅适用于已确认为 screen_doors_clamp_passengers 类别的图像检测任务，不泛化至其他类型的门体或物体夹持事件"}', 'steps': [{'tool_name': 'paddleHeadDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddleHeadDetTool'}, 'param_atoms': [{'tool_name': 'paddleHeadDetTool', 'axis': 'target', 'value': 'head', 'kind': 'fixed', 'description': '检测可见人头。', 'args': {}}], 'purpose': '检测可见人头。', 'step_id': 'paddleheaddettool_0', 'depends_on': []}, {'tool_name': 'paddlePedriderDetTool', 'args': {'file': '$image', 'filename': '$filename', 'tool': 'paddlePedriderDetTool'}, 'param_atoms': [{'tool_name': 'paddlePedriderDetTool', 'axis': 'target', 'value': 'traffic_subject', 'kind': 'fixed', 'description': '检测交通参与者。', 'args': {}}], 'purpose': '检测交通参与者。', 'step_id': 'paddlepedriderdettool_0', 'depends_on': []}, {'tool_name': 'unidepth', 'args': {'detections': '$step.paddlepedriderdettool_0.detections_json', 'file': '$image', 'filename': '$filename'}, 'param_atoms': [{'tool_name': 'unidepth', 'axis': 'evidence_role', 'value': 'metric_depth', 'kind': 'fixed', 'description': '估计检测目标深度。', 'args': {}}], 'purpose': '估计检测目标深度。', 'step_id': 'unidepth_0', 'depends_on': ['paddlepedriderdettool_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 screen_doors_clamp_passengers 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['paddleheaddettool_0', 'paddlepedriderdettool_0', 'unidepth_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 检测可见人头。
    paddleheaddettool_0_result = runtime.call(
        'paddleHeadDetTool',
        {'file': runtime.image_path(), 'filename': runtime.filename(), 'tool': 'paddleHeadDetTool'},
        step_id='paddleheaddettool_0',
        purpose='检测可见人头。',
        depends_on=[],
    )
    runtime.require(paddleheaddettool_0_result, 'paddleheaddettool_0')

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

    # 依据图像证据判断 screen_doors_clamp_passengers 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 screen_doors_clamp_passengers 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 screen_doors_clamp_passengers 异常事件。',
        depends_on=['paddleheaddettool_0', 'paddlepedriderdettool_0', 'unidepth_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
