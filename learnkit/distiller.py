"""Task H7 — Harden Distiller (Contrastive failures, trace records).

Schema validation, TraceRecord emission, and contrastive failure extraction.
"""

import json
from typing import List, Optional, Tuple

import dspy

from .logging import get_logger
from .schemas.fact import FactRecord
from .schemas.failure import FailureRecord
from .schemas.skill import SkillRecord
from .schemas.trace import TraceRecord
from .trajectory import Trajectory

logger = get_logger("distiller")

DISTILL_PROMPT = """
You are reading an AI agent's execution trace to extract reusable knowledge.

TASK: {task}
DOMAINS: {domains}
QUALITY SCORE: {quality}/5

REASONING TRACE:
{reasoning}

EXECUTION STEPS:
{steps}

FINAL OUTPUT:
{output}

Extract reusable knowledge. Respond with JSON only:
{{
  "skill": {{
    "pattern_name": "short reusable label for this approach (3-6 words, no task-specific identifiers)",
    "steps": ["step 1", "step 2"],
    "tools_used": ["tool_name"],
    "constraints": ["constraint"],
    "failure_modes": ["what almost went wrong"]
  }},
  "facts": [
    {{"statement": "...", "source": "from trace"}}
  ],
  "failures": [
    {{"description": "...", "what_to_avoid": "..."}}
  ]
}}

If no reusable skill can be extracted (task was one-off), set skill to null.
Focus on the APPROACH, not the specific content. The skill must generalize.
"""

# Procedure reflection (Hermes-style accumulating skill body) — used by the
# agent path (`@lk.agent_learn`) to author the durable natural-language
# "playbook" that sits alongside the captured tool procedure. Each successful
# run adds class-level knowledge (good sources/inputs, selection criteria,
# output conventions) and pitfalls; these are merged + deduped across runs so
# the skill body grows smarter over repeated exposures, not just cheaper.
REFLECT_PROMPT = """
You are reviewing an AI agent's SUCCESSFUL execution trace to capture the durable
know-how that would make the next attempt at this CLASS of task better.

TASK: {task}
DOMAINS: {domains}
TOOLS USED (in order): {tools}

REASONING TRACE:
{reasoning}

EXECUTION STEPS:
{steps}

FINAL OUTPUT:
{output}

Write a PLAYBOOK: short, reusable, class-level knowledge a future agent should
know BEFORE starting a task like this. Respond with JSON only:
{{
  "playbook": [
    "where to look / which sources or inputs are worth using",
    "how to decide what matters / selection criteria",
    "output or formatting conventions that worked"
  ],
  "pitfalls": [
    "a concrete trap to avoid next time"
  ]
}}

Rules:
- Each bullet is ONE short, durable, reusable insight (<= 25 words).
- Prefer concrete, domain-specific knowledge over generic advice: a narrow rule
  that names a real failure mechanism with an executable fix is worth far more
  than polished general best-practice. Aim each bullet at one of:
    * FAILURE MECHANISM - the specific reason agents fail here and its causal
      chain (e.g. "the orders API caps results at 100; later pages are silently
      dropped"), NOT "handle errors carefully".
    * ACTIONABLE STEP - a concrete procedure referencing real tools/objects
      (e.g. "after a refund, re-query the order to confirm status == refunded"),
      NOT "decompose into smaller steps".
    * HIGH-RISK ACTION TO AVOID - a specific pattern that looks right but
      reliably fails, with the reason (e.g. "never issue a refund before
      verifying the order exists; the tool errors on unknown ids").
- Capture knowledge that GENERALIZES to the whole class of task, not this one
  instance's specific values, names, or numbers.
- Do NOT write generic platitudes ("be systematic", "verify results", "be
  careful"): they read plausible but do not improve outcomes and are discarded.
- Do NOT capture: environment/setup failures (missing binary, not installed,
  bad credentials), negative claims that a tool "doesn't work", transient errors
  that resolved on retry, or one-off task narration. These harden into bad rules.
- If there is genuinely no durable knowledge to capture, return empty lists.
"""

# ReasoningBank (ICLR 2026) Finding 4 — dual-pass contrastive failure extraction.
# "ReasoningBank explicitly extracts 'preventative lessons' from failures in a
# dual-prompt extraction step."
# Used by distill_failure() when quality_score < quality_threshold.
FAILURE_CONTRASTIVE_PROMPT = """
You are analyzing a failed AI agent execution to extract a preventative lesson.

TASK: {task}
DOMAINS: {domains}
QUALITY SCORE: {quality}/5 (below passing threshold)

FAILED OUTPUT:
{output}

EXECUTION STEPS:
{steps}

Extract a concise preventative lesson. Respond with JSON only:
{{
  "lesson_title": "one-line title for this failure pattern",
  "root_cause": "why the agent failed on this task",
  "corrective_strategy": "what a successful agent should do instead",
  "trigger_pattern": "describe the task pattern that triggers this failure",
  "what_to_avoid": "specific action or reasoning the agent must NOT repeat"
}}

Be specific and actionable. The lesson must generalize to similar future tasks.
"""


def robust_json_loads(text: str) -> dict:
    """Safely loads JSON from string, falling back to json_repair if available."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import json_repair
            res = json_repair.loads(text)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        return json.loads(text.replace("'", '"'))


def _extract_json_block(raw: str) -> str:
    """Strip surrounding markdown code fences from an LLM JSON response."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and (lines[0].startswith("```json") or lines[0] == "```"):
            cleaned = "\n".join(lines[1:-1])
    return cleaned.strip()


# ── Untrusted distiller-output validation boundary ────────────────────────────
# Adapted from Graphify's validate_semantic_fragment pattern: distilled records
# come straight from an LLM and become *persistent* memory, so a runaway or
# adversarial model must not be able to pollute the store with oversized or
# malformed payloads. These bounds are deliberately generous for real traces but
# hard-cap pathological output before it is ever written.
MAX_DISTILL_PAYLOAD_BYTES = 256 * 1024
MAX_DISTILL_FACTS = 20
MAX_DISTILL_FAILURES = 20
MAX_DISTILL_LIST_ITEMS = 50
MAX_DISTILL_FIELD_CHARS = 2000


def _clamp_str(value: object, limit: int = MAX_DISTILL_FIELD_CHARS) -> str:
    """Coerce to a stripped string capped at ``limit`` characters."""
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    return value.strip()[:limit]


def _clamp_str_list(
    value: object,
    max_items: int = MAX_DISTILL_LIST_ITEMS,
    limit: int = MAX_DISTILL_FIELD_CHARS,
) -> list[str]:
    """Coerce to a list of non-empty stripped strings, capped at ``max_items``."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = _clamp_str(item, limit)
        if s:
            out.append(s)
        if len(out) >= max_items:
            break
    return out


def sanitize_distilled_payload(data: object) -> tuple[dict | None, list[str]]:
    """Validate and defensively clamp an untrusted distiller JSON payload.

    Returns ``(sanitized, errors)``. ``sanitized`` is ``None`` only when the
    payload is fundamentally untrustworthy (not an object, not serializable, or
    larger than ``MAX_DISTILL_PAYLOAD_BYTES``) — those are dropped wholesale.
    Otherwise it is a bounded copy containing only the known schema keys, with
    over-long strings truncated and over-long lists capped. ``errors`` lists the
    clamping actions taken (empty when the payload passed through unchanged).
    """
    if not isinstance(data, dict):
        return None, ["payload is not a JSON object"]
    try:
        size = len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return None, ["payload is not JSON-serializable"]
    if size > MAX_DISTILL_PAYLOAD_BYTES:
        return None, [f"payload is {size} bytes; max is {MAX_DISTILL_PAYLOAD_BYTES}"]

    errors: list[str] = []
    clean: dict = {"skill": None, "facts": [], "failures": []}

    skill = data.get("skill")
    if isinstance(skill, dict):
        clean_skill: dict = {}
        pattern = _clamp_str(skill.get("pattern_name"), 120)
        if pattern:
            clean_skill["pattern_name"] = pattern
        raw_steps = skill.get("steps")
        if isinstance(raw_steps, list) and len(raw_steps) > MAX_DISTILL_LIST_ITEMS:
            errors.append("skill.steps truncated")
        clean_skill["steps"] = _clamp_str_list(raw_steps)
        clean_skill["tools_used"] = _clamp_str_list(skill.get("tools_used"))
        clean_skill["constraints"] = _clamp_str_list(skill.get("constraints"))
        clean_skill["failure_modes"] = _clamp_str_list(skill.get("failure_modes"))
        clean["skill"] = clean_skill
    elif skill is not None:
        errors.append("skill is not an object; dropped")

    facts = data.get("facts")
    if isinstance(facts, list):
        if len(facts) > MAX_DISTILL_FACTS:
            errors.append("facts list truncated")
        for f in facts[:MAX_DISTILL_FACTS]:
            if not isinstance(f, dict):
                continue
            statement = _clamp_str(f.get("statement"))
            if not statement:
                continue
            clean["facts"].append(
                {
                    "statement": statement,
                    "source": _clamp_str(f.get("source"), 200) or "agent trace",
                }
            )
    elif facts is not None:
        errors.append("facts is not a list; dropped")

    failures = data.get("failures")
    if isinstance(failures, list):
        if len(failures) > MAX_DISTILL_FAILURES:
            errors.append("failures list truncated")
        for f in failures[:MAX_DISTILL_FAILURES]:
            if not isinstance(f, dict):
                continue
            clean["failures"].append(
                {
                    "description": _clamp_str(f.get("description")),
                    "what_to_avoid": _clamp_str(f.get("what_to_avoid")),
                }
            )
    elif failures is not None:
        errors.append("failures is not a list; dropped")

    return clean, errors


class MemoryDistiller:
    """
    Converts successful execution traces into typed memory records.
    """

    def __init__(self, lm=None):
        import os
        if lm is None:
            model = os.environ.get("LEARNKIT_DISTILLER_MODEL")
            if not model:
                if os.environ.get("ANTHROPIC_API_KEY"):
                    model = "anthropic/claude-haiku-4-5-20251001"
                elif os.environ.get("GEMINI_API_KEY"):
                    model = "gemini/gemini-2.5-flash"
                else:
                    model = "anthropic/claude-haiku-4-5-20251001"
            self.lm = dspy.LM(model)
        else:
            self.lm = dspy.LM(lm) if isinstance(lm, str) else lm

    def distill(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float,
    ) -> Tuple[
        Optional[SkillRecord],
        List[FactRecord],
        List[FailureRecord],
        Optional[TraceRecord],
    ]:
        """
        Distill trajectory into Skill, Fact, Failure, and Trace records.

        Returns (None, [], [], None) with a warning when quality_score is below
        threshold. Callers should call distill_failure() separately for low-quality
        traces to extract a contrastive FailureRecord.
        """
        if quality_score < 3.5:
            logger.warning(
                "Distillation skipped — quality below threshold",
                extra={
                    "event": "distill_quality_gate",
                    "quality_score": quality_score,
                    "threshold": 3.5,
                },
            )
            return None, [], [], None

        # Flatten trajectory for the prompt
        reasoning_steps = []
        execution_steps = []
        final_output = ""

        for step in trajectory.steps:
            if step.reasoning:
                reasoning_steps.append(step.reasoning)
            if step.role == "assistant":
                execution_steps.append(f"Agent: {step.content[:300]}")
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        prompt = DISTILL_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            quality=quality_score,
            reasoning="\n".join(reasoning_steps) or "No reasoning trace captured",
            steps="\n".join(execution_steps),
            output=final_output[:500],
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
        except Exception as e:
            logger.warning(
                "Distillation model call failed",
                extra={"event": "distill_model_fail", "error": str(e)},
            )
            # Safe degradation: don't pollute memory, return empty tuple
            return None, [], [], None

        # Basic json extraction
        cleaned = _extract_json_block(raw)

        try:
            data = robust_json_loads(cleaned)
        except Exception as e:
            logger.warning(
                "Distillation JSON parsing failed, returning empty records",
                extra={
                    "event": "distillation_parse_fail",
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            data = {"skill": None, "facts": [], "failures": []}

        if not isinstance(data, dict):
            logger.warning(
                "Distillation output is not a JSON object, returning empty records"
            )
            data = {"skill": None, "facts": [], "failures": []}

        # Bound + sanitize the untrusted LLM payload before it becomes memory.
        cleaned_data, payload_errors = sanitize_distilled_payload(data)
        if cleaned_data is None:
            logger.warning(
                "Distilled payload rejected by validator, returning empty records",
                extra={
                    "event": "distill_payload_rejected",
                    "reason": payload_errors[0] if payload_errors else "invalid",
                },
            )
            return None, [], [], None
        if payload_errors:
            logger.info(
                "Distilled payload sanitized before storage",
                extra={"event": "distill_payload_sanitized", "actions": payload_errors[:5]},
            )
        data = cleaned_data

        # Build records
        skill = None
        skill_data = data.get("skill")
        if isinstance(skill_data, dict):
            steps = skill_data.get("steps")
            has_steps = isinstance(steps, list) and any(
                isinstance(s, str) and s.strip() for s in steps
            )
            if not has_steps:
                logger.info(
                    "Skill skipped — no non-empty steps",
                    extra={"event": "distill_skill_empty"},
                )
            else:
                # Use a generalized pattern label as task_type rather than the
                # raw task prefix. Storing trajectory.task[:80] turned every
                # skill into a BM25 magnet for its originating task, so skills
                # only ever matched the exact task that produced them. A short
                # pattern name keeps the record retrievable for *similar* tasks.
                pattern_name = (skill_data.get("pattern_name") or "").strip()
                skill_task_type = (
                    pattern_name[:80]
                    if pattern_name
                    else f"{next(iter(domain_vector), 'general')}_skill"
                )
                try:
                    skill = SkillRecord(
                        domains=domain_vector,
                        task_type=skill_task_type,
                        content=skill_data,
                        confidence=0.75,  # above CONFIDENCE_FLOOR + distilled-failure default (0.7)
                        status="quarantine",  # 24h quarantine before becoming active
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to validate skill schema", extra={"error": str(e)}
                    )

        facts = []
        for f in data.get("facts", []):
            if isinstance(f, dict) and "statement" in f:
                try:
                    facts.append(
                        FactRecord(
                            domains=domain_vector,
                            content={
                                "statement": f["statement"],
                                "source": f.get("source", "agent trace"),
                            },
                            status="quarantine",
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to validate fact schema", extra={"error": str(e)}
                    )

        # Failure records activate IMMEDIATELY — no quarantine
        failures = []
        for f in data.get("failures", []):
            if isinstance(f, dict):
                try:
                    failures.append(
                        FailureRecord(
                            domains=domain_vector,
                            content={
                                "description": f.get("description", ""),
                                "what_to_avoid": f.get("what_to_avoid", ""),
                            },
                            status="active",  # immediately active
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to validate failure schema", extra={"error": str(e)}
                    )

        # TraceRecord emission (active immediately)
        trace_steps = []
        for step in trajectory.steps:
            trace_steps.append(
                {
                    "step": step.step,
                    "role": step.role,
                    "content": step.content,
                    "tool_name": step.tool_name,
                    "tool_input": step.tool_input,
                    "reasoning": step.reasoning,
                    "timestamp": step.timestamp,
                }
            )

        try:
            trace_record = TraceRecord(
                domains=domain_vector,
                task_type=trajectory.task[:80],
                content={
                    "trajectory_id": trajectory.id,
                    "task": trajectory.task,
                    "summary": f"Distilled trace of {trajectory.task} with quality {quality_score}",
                    "steps": trace_steps,
                },
                status="active",
            )
        except Exception as e:
            logger.warning(
                "Failed to validate trace record schema", extra={"error": str(e)}
            )
            trace_record = None

        return skill, facts, failures, trace_record

    def reflect_procedure(
        self,
        trajectory: Trajectory,
        tool_sequence: list[str],
        domain_vector: dict[str, float],
    ) -> dict:
        """Reflect on a successful agent run and author a *playbook* — the durable
        natural-language knowledge that makes the agent better at this CLASS of
        task next time (Hermes-style accumulating skill body).

        Returns ``{"playbook": [...], "pitfalls": [...]}``. Both lists hold short,
        reusable, class-level insights — NOT one-off narration. Safe-degrades to
        ``{}`` on any model/parse failure so reflection never blocks storage.
        """
        reasoning_steps = []
        execution_steps = []
        final_output = ""
        for step in trajectory.steps:
            if step.reasoning:
                reasoning_steps.append(step.reasoning)
            if step.role == "assistant":
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        prompt = REFLECT_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            tools=list(tool_sequence or []),
            reasoning="\n".join(reasoning_steps) or "No reasoning trace captured",
            steps="\n".join(execution_steps) or "No tool steps captured",
            output=final_output[:500],
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
            data = robust_json_loads(_extract_json_block(raw))
        except Exception as e:
            logger.warning(
                "Procedure reflection failed; storing procedure without playbook",
                extra={"event": "reflect_fail", "error_type": type(e).__name__},
            )
            return {}

        if not isinstance(data, dict):
            return {}

        def _bullets(value):
            if not isinstance(value, list):
                return []
            out = []
            for item in value[:MAX_DISTILL_LIST_ITEMS]:
                clean = _clamp_str(item, 280)
                if clean:
                    out.append(clean)
            return out

        return {
            "playbook": _bullets(data.get("playbook")),
            "pitfalls": _bullets(data.get("pitfalls")),
        }

    def distill_failure(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float,
    ) -> Optional[FailureRecord]:
        """Contrastive failure extraction (ReasoningBank dual-pass pattern).

        Called when a trace fails the quality gate (score < threshold). Extracts
        a preventative lesson — root cause, corrective strategy, and trigger pattern
        — and returns an immediately-active FailureRecord. This record is retrieved
        on similar future tasks, blocking the agent from repeating the same mistake.

        Returns None on model call failure or JSON parse failure (safe degradation).
        """
        execution_steps = []
        final_output = ""
        for step in trajectory.steps:
            if step.role == "assistant":
                execution_steps.append(f"Agent: {step.content[:300]}")
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        prompt = FAILURE_CONTRASTIVE_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            quality=quality_score,
            output=final_output[:500],
            steps="\n".join(execution_steps),
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
        except Exception as e:
            logger.warning(
                "Contrastive failure model call failed",
                extra={"event": "distill_failure_model_fail", "error": str(e)},
            )
            return None

        cleaned = _extract_json_block(raw)

        try:
            data = robust_json_loads(cleaned)
        except Exception as e:
            logger.warning(
                "Contrastive failure JSON parsing failed",
                extra={"event": "distill_failure_parse_fail", "error_type": type(e).__name__},
            )
            return None

        if not isinstance(data, dict):
            return None

        # Bound the untrusted payload before constructing a persistent record.
        try:
            payload_size = len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError):
            return None
        if payload_size > MAX_DISTILL_PAYLOAD_BYTES:
            logger.warning(
                "Contrastive failure payload too large; rejected",
                extra={"event": "distill_failure_payload_rejected", "bytes": payload_size},
            )
            return None

        try:
            lesson_title = _clamp_str(data.get("lesson_title"))
            failure_label = lesson_title[:80] if lesson_title else "failure_pattern"
            failure = FailureRecord(
                domains=domain_vector,
                task_type=failure_label,
                content={
                    "description": lesson_title,
                    "root_cause": _clamp_str(data.get("root_cause")),
                    "corrective_strategy": _clamp_str(data.get("corrective_strategy")),
                    "trigger_pattern": _clamp_str(data.get("trigger_pattern")),
                    "what_to_avoid": _clamp_str(data.get("what_to_avoid")),
                },
                status="active",  # immediately active — no quarantine for failures
                confidence=0.7,   # start at 0.7 so it clears the CONFIDENCE_FLOOR
            )
            logger.warning(
                "Contrastive failure record created from low-quality trace",
                extra={"event": "distill_failure_created", "task_type": failure.task_type},
            )
            return failure
        except Exception as e:
            logger.warning(
                "Failed to construct FailureRecord from contrastive extraction",
                extra={"error": str(e)},
            )
            return None
