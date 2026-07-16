"""SpatialSkillGrowth 的全部 LLM 提示词。业务模块不得内嵌提示词正文。"""

FREE_REACT_SYSTEM_PROMPT = """You are a multimodal visual reasoning agent. Solve the current
question with the available tools. Use the smallest evidence chain that can answer the question,
do not repeat an uninformative call, and stop as soon as the answer is supported. If a tool fails,
switch to a relevant alternative. When ready, return JSON only as {"answer": "the requested final
answer"}. Do not put reasoning or units outside the answer field."""

REACT_FINALIZATION_PROMPT = """The tool-use budget is exhausted. Do not request another tool.
Using only the question and observations already present in this conversation, return the best
supported final answer now. Return JSON only as {"answer": "the requested final answer"}."""

FINAL_ANSWER_NORMALIZATION_PROMPT = """Normalize a visual agent's raw response into the exact
answer requested by the question. This is formatting only: preserve the response's intended answer,
do not solve the problem again, do not add a value that the response did not assert, and do not use
the image. Return JSON only as {{"answer": "normalized answer"}}.

Expected answer type: {answer_type}
Question: {question}
Raw response: {raw_answer}
"""

WORKFLOW_NORMALIZED_QUERY_PROMPT = (
    "Answer using explicit visual evidence. Return only the final answer: $question"
)
WORKFLOW_DEFAULT_ANSWER_PROMPT = (
    "Use explicit {role} evidence to answer the question. "
    "Return only the final answer: $question"
)
WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT = (
    "Analyze {scope} for {problem_class}. Apply these reasoning and evidence requirements together: "
    "{requirements}. Use the collected evidence below when available. Return only the final answer. "
    "Evidence: $evidence\nQuestion: $question"
)
WORKFLOW_FINAL_ANSWER_PROMPT = (
    "Use the collected tool evidence below together with the image to answer the question. "
    "Do not guess from unsupported assumptions. Return only the final answer. "
    "Evidence:\n$evidence\nQuestion: $question"
)

PROBLEM_CLASSIFIER_PROMPT = """Classify the multimodal Omni3D question into exactly one supplied
problem class. Judge the operation required to answer, not shared words, objects, answer choices,
or dataset frequency. Return JSON only: {{\"problem_class\": \"exact supplied name\", \"reason\":
\"brief reason\"}}.

Problem classes:
{class_definitions}

Question:
{question}
"""

SLOT_EXTRACTION_PROMPT = """Extract reusable runtime bindings from the multimodal question and
image. target_a and target_b must be short English referring expressions. sam_query_a and
sam_query_b must each be a concise 1-3 word English object label suitable for SAM3; never use a
sentence or Chinese. Do not solve the question. Return JSON only with target_a, target_b,
sam_query_a, sam_query_b, reference_frame, reference_entity, reference_value, reference_unit,
measurement_dimension, operation.

Problem class: {problem_class}
Question: {question}
"""

FLAT_WORKFLOW_RETRIEVAL_PROMPT = """Rank reusable workflows for the current multimodal problem.
All candidates already passed structured compatibility checks and belong to the same problem class.
Judge natural-language applicability, exclusions, capability boundary, current image evidence needs,
runtime slots, and the workflow tool graph. Do not select by workflow ID, wording overlap, object-name
overlap, or answer options. Prefer relevance, evidence suitability, and validated history. Use
complexity and tool cost only to break a tie; neither short nor complex workflows receive a prior.
Return at most {top_k} exact workflow IDs, or reject all when none is likely to help.

Return JSON only:
{{
  "action": "select|reject_all",
  "ranked_workflow_ids": ["exact workflow id"],
  "reason": "brief semantic and evidence-based reason"
}}

Problem class: {problem_class}
Answer type: {answer_type}
Runtime slots: {slot_bindings}
Question: {question}
Candidates: {candidates}
"""

WORKFLOW_TREE_RETRIEVAL_PROMPT = """Select one reusable workflow by traversing the supplied
workflow tree. Match the current problem semantics and runtime slots to each route's natural-language
applicability. Children are refinements of their parent; select a child only when its refinement is
needed. Do not select by shared answer-option words or opaque workflow IDs. Historical counts are
only a tie-breaker between semantically suitable routes.

Return JSON only:
{{
  "workflow_path": ["root workflow id", "optional child id"],
  "workflow_id": "final selected workflow id",
  "reason": "brief applicability reason"
}}

Problem class: {problem_class}
Runtime slots: {slot_bindings}
Question: {question}
Workflow tree: {workflow_tree}
"""

SUCCESS_ENHANCEMENT_DIRECTION_PROMPT = """Direct mutations that enhance a workflow which already
answered the exploration task correctly. The goal is broader robustness, complementary evidence,
or a useful new capability boundary without damaging the validated route. You must not receive or
infer the ground-truth answer. Select directions only from the supplied ParamType atom IDs. Do not
invent tools, placements, scores, or final answers.

Return JSON only:
{{
  "objective": "brief enhancement objective",
  "preferred_atom_ids": ["exact atom id"],
  "avoid_atom_ids": ["exact atom id"],
  "tool_hints": {{"exact tool": "short runtime target hint"}},
  "diagnosis": "why this direction complements the successful evidence"
}}

Problem class: {problem_class}
Question: {question}
Runtime slots: {slot_bindings}
Successful workflow and observations: {workflow_context}
Allowed ParamType atoms: {param_atoms}
"""

FAILURE_REPAIR_DIRECTION_PROMPT = """Diagnose why the workflow failed on this exploration example
and direct mutations that repair the missing evidence. The ground-truth answer is diagnostic-only:
never copy it, a derived value, or an answer-specific clue into tool hints, workflow arguments,
applicability text, names, or reusable artifacts. Select directions only from the supplied ParamType
atom IDs. Do not invent tools, placements, or scores.

Return JSON only:
{{
  "objective": "brief repair objective",
  "preferred_atom_ids": ["exact atom id"],
  "avoid_atom_ids": ["exact atom id"],
  "tool_hints": {{"exact tool": "short runtime target hint"}},
  "diagnosis": "evidence-level failure diagnosis"
}}

Problem class: {problem_class}
Question: {question}
Incorrect prediction: {prediction}
Ground-truth answer for diagnosis only: {groundtruth}
Runtime slots: {slot_bindings}
Failed workflow and observations: {workflow_context}
Allowed ParamType atoms: {param_atoms}
"""

MUTATION_DIRECTION_RETRY_PROMPT = """The previous mutation direction did not select any valid
ParamType atom. Choose one to three exact IDs from the supplied list that best implement the stated
objective and evidence diagnosis. Do not invent or rewrite IDs. Return the complete direction JSON
only, using objective, preferred_atom_ids, avoid_atom_ids, tool_hints, and diagnosis.

Mutation mode: {mode}
Previous direction: {direction}
Allowed tools: {allowed_tools}
Allowed ParamType atom IDs: {allowed_atom_ids}
"""

GROUNDTRUTH_SAFE_DIRECTION_PROMPT = """Rewrite a failure-repair mutation direction into a reusable,
answer-independent evidence diagnosis. The ground truth may be used only to understand what failed.
Remove every exact, partial, rounded, transformed, or indirectly revealing answer clue from all text.
Preserve the intended repair and select only exact supplied ParamType atom IDs and tool names. Return
the complete direction JSON only, using objective, preferred_atom_ids, avoid_atom_ids, tool_hints,
and diagnosis. Do not return the ground truth or explain the rewrite.

Ground truth for sanitization only: {groundtruth}
Candidate direction: {direction}
Allowed tools: {allowed_tools}
Allowed ParamType atom IDs: {allowed_atom_ids}
"""

APPLICABILITY_GENERALIZATION_PROMPT = """Write reusable natural-language applicability for one
ground-truth-validated workflow. Generalize the operation and evidence condition; never include a
task ID, final answer, concrete scene anecdote, benchmark split, reward, or implementation history.
Keep the supplied tool graph unchanged. Do not broaden a specific operation into the whole problem
class. Preserve the operation and attribute family required by the question. Object names may be
abstracted only when the tool graph contains runtime slots that replace them; when no such target
slot exists, state the detector/target limitation explicitly in applicability or exclusions. Runtime
required slots are derived from graph references and must not be inferred from language. Return JSON
only with name, description, exclusions, and capability_boundary.

Problem class: {problem_class}
Question: {question}
Runtime slots: {slot_bindings}
Mutation mode: {mutation_mode}
Tool graph: {tool_graph}
"""

APPLICABILITY_COMPATIBILITY_PROMPT = """Decide whether two structurally compatible workflows have
the same reusable natural-language applicability. Structure was checked separately; now judge only
semantic applicability, exclusions, and capability boundaries. Never use keyword overlap or object
name overlap as evidence. Merge only when one generalized route can honestly represent both.

Return JSON only:
{{
  "action": "merge|separate",
  "reason": "brief semantic reason",
  "generalized_name": "name when merging",
  "generalized_description": "shared applicability when merging",
  "generalized_exclusions": "shared exclusions when merging",
  "generalized_capability_boundary": "shared boundary when merging"
}}

Left workflow: {left}
Right workflow: {right}
"""

SEMANTIC_EVIDENCE_VALIDATION_PROMPT = """Judge whether the workflow observations provide enough
task-relevant evidence to accept the candidate answer. Do not judge by fluency or format alone. Check
that the required objects, relation or attribute were actually observed and that failed tool calls do
not break the evidence chain. For a numerical answer, require observations to expose the relevant
detected instances, measurements, reference values, or intermediate operands and a derivation that
supports the exact candidate number. A bare number or an MLLM assertion without observable numerical
provenance is insufficient. Return JSON only: {{\"accepted\": true|false, \"reason\": \"brief
evidence reason\"}}.

Problem class: {problem_class}
Answer type: {answer_type}
Question: {question}
Candidate answer: {answer}
Observations: {observations}
"""
