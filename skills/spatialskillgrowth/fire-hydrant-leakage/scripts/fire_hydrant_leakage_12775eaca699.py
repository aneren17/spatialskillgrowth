"""Executable SpatialSkillGrowth Skill: fire_hydrant_leakage_detector."""

WORKFLOW_ID = 'fire_hydrant_leakage_12775eaca699'
PROBLEM_CLASS = 'fire_hydrant_leakage'
WORKFLOW_GRAPH_SHA256 = '04455678aa340417ba081dc78a8c00cf16ac3f097b5f875820e5c76ddeeee36b'
DECLARED_TOOLS = ('MLLM',)
WORKFLOW_CONTRACT = {'workflow_id': 'fire_hydrant_leakage_12775eaca699', 'name': 'fire_hydrant_leakage_detector', 'problem_class': 'fire_hydrant_leakage', 'required_slots': [], 'required_tools': ['MLLM'], 'description': '基于图像输入，利用多模态大语言模型分析视觉特征，检测消防栓是否存在泄漏异常。该工作流通过识别消防栓本体及其周围的水迹、水流或湿润痕迹，判断是否发生泄漏事件。', 'exclusions': '非图像类型的媒体输入（如纯文本、音频）; 图像中未包含消防栓主体或消防栓被严重遮挡无法辨识; 图像分辨率过低导致无法分辨细微水迹或泄漏特征; 非消防栓相关的水体场景（如自然水域、非消防用途的管道泄漏）', 'capability_boundary': '{"event_type": "fire_hydrant_leakage", "media_type": "image", "required_evidence": ["清晰可见的消防栓本体", "消防栓接口、阀门或本体周围存在明显的水迹、水流或湿润区域"], "tool_constraints": ["禁止使用 embeddingTool 处理图像输入", "必须使用 MLLM 工具进行视觉证据收集与推理"]}', 'steps': [{'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 fire_hydrant_leakage 异常事件。', 'step_id': 'mllm_0', 'depends_on': []}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 依据图像证据判断 fire_hydrant_leakage 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 fire_hydrant_leakage 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 fire_hydrant_leakage 异常事件。',
        depends_on=[],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
