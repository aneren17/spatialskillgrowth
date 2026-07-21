"""Executable SpatialSkillGrowth Skill: foreign_objects_on_transmission_lines_detector."""

WORKFLOW_ID = 'foreign_objects_on_transmission_lines_ad5cbcebbbeb'
PROBLEM_CLASS = 'foreign_objects_on_transmission_lines'
WORKFLOW_GRAPH_SHA256 = 'f3499fb657dd3b222095020414c9762389602dde0cebf2b509f343c706bcdd91'
DECLARED_TOOLS = ('python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'foreign_objects_on_transmission_lines_ad5cbcebbbeb', 'name': 'foreign_objects_on_transmission_lines_detector', 'problem_class': 'foreign_objects_on_transmission_lines', 'required_slots': [], 'required_tools': ['python_code_sandbox', 'MLLM'], 'description': '检测输电线路图像中是否存在悬挂、缠绕或附着在导线、绝缘子串或杆塔结构上的非标准异物（如塑料薄膜、风筝线、树枝、鸟巢等）。该工作流首先通过代码沙箱提取图像中的结构化视觉特征摘要，随后利用多模态大模型结合这些证据，严格判定是否发生‘输电线路异物’异常事件。', 'exclusions': '非图像格式的输入数据（如纯文本、音频或视频流）。; 未包含输电线路核心组件（导线、绝缘子、杆塔）的图像。; 需要识别异物具体材质、品牌或来源的任务。; 需要评估异物对电网安全具体风险等级或量化影响的任务。; 其他类型的电力设施异常（如绝缘子破损、金具锈蚀、导线断股等，除非明确归类为异物附着）。', 'capability_boundary': '{"input_constraints": {"media_type": "image", "format_requirements": "支持常见图像格式（如JPEG, PNG），需清晰展示输电线路局部或整体视图。"}, "detection_scope": {"target_objects": "输电线路上的非预期附着物或悬挂物。", "excluded_objects": "输电线路的标准组成部分（如防震锤、间隔棒、标准绝缘子串等，除非其状态异常且被归类为异物干扰）。"}, "output_format": {"type": "binary", "values": ["是", "否"]}, "tool_dependencies": ["python_code_sandbox: 用于生成图像的结构化证据摘要。", "MLLM: 用于基于视觉证据进行最终异常判定。"]}', 'steps': [{'tool_name': 'python_code_sandbox', 'args': {'code': ''}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': []}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 foreign_objects_on_transmission_lines 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': ''},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=[],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 foreign_objects_on_transmission_lines 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 foreign_objects_on_transmission_lines 异常事件。',
        depends_on=['python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
