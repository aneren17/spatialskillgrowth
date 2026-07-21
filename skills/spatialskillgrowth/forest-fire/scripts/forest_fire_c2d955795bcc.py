"""Executable SpatialSkillGrowth Skill: forest_fire_detector."""

WORKFLOW_ID = 'forest_fire_c2d955795bcc'
PROBLEM_CLASS = 'forest_fire'
WORKFLOW_GRAPH_SHA256 = 'b6815fe6d32ef8952f29549308a863fc6c62a710a4623b788771bc5c7b4a799f'
DECLARED_TOOLS = ('groundingdino', 'python_code_sandbox', 'MLLM')
WORKFLOW_CONTRACT = {'workflow_id': 'forest_fire_c2d955795bcc', 'name': 'forest_fire_detector', 'problem_class': 'forest_fire', 'required_slots': [], 'required_tools': ['groundingdino', 'python_code_sandbox', 'MLLM'], 'description': '基于视觉证据的森林火灾异常检测工作流。该流程首先使用 GroundingDINO 以 0.3 的开放词汇检测阈值定位潜在火源或烟雾目标，随后通过代码沙箱计算结构化证据摘要，最后结合多模态大语言模型（MLLM）综合图像特征与量化证据，判定输入图像中是否发生森林火灾事件。', 'exclusions': "非图像类型的输入数据（如纯文本、音频或视频流），本工作流仅支持静态图像分析。; 需要调用 embeddingTool 进行特征提取的场景，本工作流严格禁止使用 embeddingTool。; 非森林火灾类别的异常检测任务，本工作流专用于 event_type 为 'forest_fire' 的场景，不泛化至其他火灾类型或自然灾害。; 要求输出概率分数、置信度区间或详细自然语言解释的场景，本工作流仅输出二分类结果（是/否）。", 'capability_boundary': '{"input_media_type": "image", "target_event_type": "forest_fire", "detection_method": "visual_grounding_and_multimodal_reasoning", "evidence_requirements": "必须包含基于 GroundingDINO 的视觉定位证据及代码沙箱生成的结构化摘要", "output_format": "binary_classification_yes_no"}', 'steps': [{'tool_name': 'groundingdino', 'args': {'query': 'forest_fire', 'file': '$image', 'filename': '$filename', 'box_threshold': 0.3, 'text_threshold': 0.25}, 'param_atoms': [{'tool_name': 'groundingdino', 'axis': 'box_threshold', 'value': 'low', 'kind': 'numerical', 'description': '使用 0.3 开放词汇检测阈值。', 'args': {}}], 'purpose': '使用 0.3 开放词汇检测阈值。', 'step_id': 'groundingdino_0', 'depends_on': []}, {'tool_name': 'python_code_sandbox', 'args': {'code': 'import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n'}, 'param_atoms': [{'tool_name': 'python_code_sandbox', 'axis': 'operation', 'value': 'append_verification', 'kind': 'structural', 'description': '计算结构化证据摘要。', 'args': {}}], 'purpose': '计算结构化证据摘要。', 'step_id': 'python_code_sandbox_0', 'depends_on': ['groundingdino_0']}, {'tool_name': 'MLLM', 'args': {'file': '$evidence_image', 'filename': '$filename', 'query': '请针对 forest_fire 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question', 'tool': 'qwen36Tool'}, 'param_atoms': [{'tool_name': 'MLLM', 'axis': 'evidence_focus', 'value': 'explicit_visual_cues', 'kind': 'world_model', 'description': '给出明确视觉线索。', 'args': {}}, {'tool_name': 'MLLM', 'axis': 'scope', 'value': 'local_regions', 'kind': 'world_model', 'description': '分析已定位的局部区域。', 'args': {}}], 'purpose': '依据图像证据判断 forest_fire 异常事件。', 'step_id': 'mllm_0', 'depends_on': ['groundingdino_0', 'python_code_sandbox_0']}]}


def solve(
    runtime,
    question,
    image_paths,
):

    # 使用 0.3 开放词汇检测阈值。
    groundingdino_0_result = runtime.call(
        'groundingdino',
        {'query': 'forest_fire', 'file': runtime.image_path(), 'filename': runtime.filename(), 'box_threshold': 0.3, 'text_threshold': 0.25},
        step_id='groundingdino_0',
        purpose='使用 0.3 开放词汇检测阈值。',
        depends_on=[],
    )
    runtime.require(groundingdino_0_result, 'groundingdino_0')

    # 计算结构化证据摘要。
    python_code_sandbox_0_result = runtime.call(
        'python_code_sandbox',
        {'code': runtime.render('import json\n\ndetections = json.loads(r\'\'\'$step.groundingdino_0.detections_json\'\'\').get("detections", [])\nsummary = []\nfor item in detections:\n    box = item.get("bbox", [])\n    if len(box) != 4:\n        continue\n    width = max(0.0, float(box[2]) - float(box[0]))\n    height = max(0.0, float(box[3]) - float(box[1]))\n    summary.append({\n        "class_name": item.get("class_name", ""),\n        "score": item.get("score", 0.0),\n        "area": width * height,\n        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],\n    })\nprint(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))\n')},
        step_id='python_code_sandbox_0',
        purpose='计算结构化证据摘要。',
        depends_on=['groundingdino_0'],
    )
    runtime.require(python_code_sandbox_0_result, 'python_code_sandbox_0')

    # 依据图像证据判断 forest_fire 异常事件。
    mllm_0_result = runtime.call(
        'MLLM',
        {'file': runtime.evidence_image(), 'filename': runtime.filename(), 'query': runtime.render('请针对 forest_fire 分析局部区域，并同时遵守以下推理和证据要求：给出明确视觉线索。; 分析已定位的局部区域。。如已有工具证据，必须优先使用。只输出最终答案。证据：$evidence\n问题：$question'), 'tool': 'qwen36Tool'},
        step_id='mllm_0',
        purpose='依据图像证据判断 forest_fire 异常事件。',
        depends_on=['groundingdino_0', 'python_code_sandbox_0'],
    )
    runtime.require(mllm_0_result, 'mllm_0')

    return runtime.finish(mllm_0_result)
