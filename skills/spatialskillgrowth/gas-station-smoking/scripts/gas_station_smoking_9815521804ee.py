"""Executable SpatialSkillGrowth Skill: gas_station_smoking_detector."""

WORKFLOW_ID = 'gas_station_smoking_9815521804ee'
PROBLEM_CLASS = 'gas_station_smoking'
WORKFLOW_GRAPH_SHA256 = '36b42f5bdd0021bf6fc21256bfb1a78d2e75476ae7c33c45f0aec8c582d331aa'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'gas_station_smoking_9815521804ee', 'name': 'gas_station_smoking_detector', 'problem_class': 'gas_station_smoking', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于图像输入，利用多模态大模型检测是否存在‘加油站抽烟’异常事件。该工作流通过视觉证据分析，判断场景中是否出现人员在加油站区域内吸烟的行为。', 'exclusions': '非图像类型的媒体输入（如视频、音频或文本描述）; 非加油站场景的图像（如普通街道、室内办公室等，除非明确包含加油站设施）; 未涉及吸烟行为的图像（即使场景为加油站）; 模糊或无法识别关键视觉元素（如人物、香烟、加油站标识）的图像', 'capability_boundary': '{"supported_media": ["image"], "event_type": "gas_station_smoking", "evidence_requirements": ["图像中需清晰呈现加油站环境特征（如加油机、油站标识等）", "图像中需存在人物进行吸烟动作的视觉证据（如手持香烟、烟雾、点火动作等）", "吸烟行为与加油站场景需在同一画面中关联"], "limitations": ["仅支持静态图像分析，不支持动态视频流或实时监测", "依赖多模态模型对吸烟行为和加油站场景的识别准确率，极端光照、遮挡或低分辨率可能影响判断", "不区分吸烟者身份或具体违规程度，仅输出是否存在该异常事件"]}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 gas_station_smoking 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 gas_station_smoking 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 gas_station_smoking 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 gas_station_smoking 分析局部区域，并同时遵守以下推理和证据要求：分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 gas_station_smoking 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
