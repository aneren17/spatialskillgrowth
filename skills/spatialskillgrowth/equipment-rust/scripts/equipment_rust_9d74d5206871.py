"""Executable SpatialSkillGrowth Skill: equipment_rust_detector."""

WORKFLOW_ID = 'equipment_rust_9d74d5206871'
PROBLEM_CLASS = 'equipment_rust'
WORKFLOW_GRAPH_SHA256 = '7c6995285adc8a868fc4006d67edb2367f1a8a5ec99e4909e6c390f9cd4ea156'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'equipment_rust_9d74d5206871', 'name': 'equipment_rust_detector', 'problem_class': 'equipment_rust', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于多模态大模型（MLLM）分析输入图像，检测是否存在设备生锈（equipment_rust）异常。该工作流通过视觉证据识别金属表面的氧化腐蚀特征，适用于工业设备、管道、结构件等场景的表面状态评估。', 'exclusions': '非图像类型的媒体输入（如视频、音频、纯文本）; 图像中未包含任何可识别的设备或金属结构主体; 需要精确量化锈蚀面积百分比或化学成分的定量分析任务; 涉及动态过程（如实时锈蚀生成监控）的连续视频流分析', 'capability_boundary': '{"supported_media": ["image"], "required_evidence": ["金属表面呈现红褐色或橙黄色氧化层", "表面出现剥落、起泡或粗糙不平的腐蚀纹理", "原有金属光泽消失并伴随颜色异常"], "decision_scope": "仅判断是否存在设备生锈异常（是/否），不提供锈蚀等级评分或修复建议"}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 equipment_rust 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 equipment_rust 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 equipment_rust 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 equipment_rust 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 equipment_rust 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
