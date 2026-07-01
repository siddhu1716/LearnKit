import atexit
import functools
import hashlib
import os
import sys
import threading
import time
import uuid
import weakref
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from .attribution import build_attribution
from .backends.registry import get_backend
from .classifier import classify_task
from .composer import compose_context
from .consolidation import consolidate_skills
from .distiller import MemoryDistiller
from .errors import PostProcessError
from .evaluator import Evaluator
from .inference_mode import determine_inference_mode
from .logging import get_logger
from .memory_quality import apply_retrieval_feedback, decide_storage, reinforce_existing, update_utility
from .observability import estimate_run_telemetry, resolve_models
from .procedural import (
    extract_procedure,
    match_kind,
    procedure_fingerprint,
    signature_coverage,
    signature_fingerprint,
)
from .procedure_evolution import (
    demote_procedure,
    find_family_procedure,
    reinforce_or_refine,
)
from .playbook import merge_insights
from .retriever import SemanticRetriever
from .router import MemoryRouter
from .schemas.base import MemoryScope
from .tool_tracker import ToolTracker
from .trajectory import Trajectory

logger = get_logger("core")


def _skill_fingerprint(skill) -> str:
    """Compute a stable fingerprint for a SkillRecord.

    Procedural skills (agent path) fingerprint on their captured tool-call
    sequence — two trajectories that invoke the same tools in the same order are
    the same procedure. Declarative skills (model path) fall back to the AWM +
    Voyager step-sequence hash. Steps are normalized (lowercased, stripped)
    before hashing so minor wording variations don't bypass dedup.
    """
    tool_sequence = skill.content.get("tool_sequence")
    if tool_sequence:
        return procedure_fingerprint(tool_sequence)
    steps = skill.content.get("steps", [])
    normalized = "|".join(s.strip().lower() for s in steps if isinstance(s, str))
    return hashlib.sha256(normalized.encode()).hexdigest()


class LearnKit:
    def __init__(
        self,
        memory_backend: str = "sqlite",
        evaluation: str = "llm_judge",
        scope: MemoryScope = "team",
        capture_reasoning: bool = True,  # ReaComp: mandatory CoT capture
        quality_threshold: float = 3.5,
        classifier: Optional[Callable] = None,
        evaluator: Optional[Evaluator] = None,
        distiller: Optional[MemoryDistiller] = None,
        embedder: Optional[Callable] = None,
        background_postprocess: bool = True,
        max_workers: int = 4,
        auto_promote: bool = False,
        diversity_lambda: float = 0.7,
        procedure_match_threshold: float = 0.7,
        reflect_procedures: bool = False,
        retrieval_fusion: str = "weighted",
        relevance_floor: Optional[float] = None,
        utility_floor: Optional[float] = None,
        max_tracked_runs: int = 256,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        record_ttl: bool = True,
        **backend_kwargs,
    ):
        self.backend = get_backend(memory_backend, **backend_kwargs)
        self.router = MemoryRouter(
            max_records=8, max_tokens=1200, diversity_lambda=diversity_lambda
        )
        self.retriever = SemanticRetriever(
            backend=self.backend,
            embedder=embedder,
            fusion_strategy=retrieval_fusion,
            relevance_floor=relevance_floor,
            utility_floor=utility_floor,
        )
        self.classifier = classifier or classify_task
        self.evaluator = evaluator or Evaluator()
        self.distiller = distiller or MemoryDistiller(quality_threshold=quality_threshold)
        # If a pre-built distiller was injected, keep its own threshold in sync
        # with ours so the success-gate and distill-gate never diverge.
        if not hasattr(self.distiller, "quality_threshold") or self.distiller.quality_threshold != quality_threshold:
            try:
                self.distiller.quality_threshold = float(quality_threshold)
            except Exception:
                pass
        self.scope = scope
        self.capture_reasoning = capture_reasoning
        self.quality_threshold = quality_threshold
        self.evaluation_mode = evaluation
        self.background_postprocess = background_postprocess
        # Stable agent identity for run telemetry / dashboard tracing. The id is
        # what the UI traces; the name is an optional human-friendly label. When
        # no id is given we generate a stable per-instance one so every run is
        # still attributable to *some* agent.
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.agent_name = agent_name or self.agent_id
        # When False, distilled records are stored with no TTL (expires_at=None)
        # so user-run memory persists until explicitly deleted. Implemented as a
        # process-level flag honored by MemoryRecord at creation time; default
        # True preserves the published SDK TTL/decay behavior.
        self.record_ttl = record_ttl
        if not record_ttl:
            os.environ["LEARNKIT_PERSIST_FOREVER"] = "1"

        # When True, distilled skill/fact/strategy/etc. records skip the 24h
        # quarantine window and are stored as `active` so they're retrievable
        # on the next task. Use for benchmark/online-learning scenarios.
        self.auto_promote = auto_promote

        # Agent path: minimum coverage of a stored procedure's task skeleton by
        # the current task before it is eligible for replay (AP5 signature gate).
        self.procedure_match_threshold = procedure_match_threshold
        # Agent path: when True, a successful run also reflects on the trace to
        # author/accumulate a natural-language *playbook* (Hermes-style growing
        # skill body) alongside the captured procedure. Opt-in (LLM call).
        self.reflect_procedures = reflect_procedures
        # Concurrency safety: bounded trajectory registry + worker pool.
        # The registries are capped (LRU by insertion order) so a long-lived
        # process that prepares runs but never reads old ones back cannot grow
        # them without bound. The most recent runs stay available for
        # last_trajectory / get_trajectory; a run can also be dropped eagerly
        # via discard_run (e.g. when an adapter's framework crashes mid-run).
        self._max_tracked_runs = max(1, max_tracked_runs)
        self._trajectories: "OrderedDict[str, Trajectory]" = OrderedDict()
        self._attributions: "OrderedDict[str, dict]" = OrderedDict()
        self._trajectory_lock = threading.Lock()
        self._last_run_id: Optional[str] = None
        self._last_records: list = []
        # When True, the per-record utility EMA is NOT updated from the internal
        # LLM judge during post-processing; instead a caller supplies a trusted
        # external outcome via ``apply_external_outcome`` (e.g. a test/grader
        # result). Confidence still tracks the judge. This separates "the judge
        # liked the answer" (confidence) from "injecting this actually improved
        # the real outcome" (utility), which is what the utility gate needs.
        self.utility_external = os.environ.get(
            "LEARNKIT_UTILITY_EXTERNAL", ""
        ).lower() in ("1", "true", "yes")
        self._worker_pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="LearnKitWorker"
        )
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Drain in-flight post-processing futures before interpreter exit so
        # background evaluator/distiller calls do not try to schedule new
        # sub-tasks against an already-closed pool (which surfaced as the
        # "cannot schedule new futures after shutdown" warning on every
        # quick_start exit before this).
        self_ref = weakref.ref(self)

        def _atexit_shutdown() -> None:
            inst = self_ref()
            if inst is not None:
                inst.shutdown(wait=True)

        atexit.register(_atexit_shutdown)

    @property
    def last_trajectory(self) -> Optional[Trajectory]:
        """Backward compatibility for tests. Returns the most recently prepared trajectory."""
        with self._trajectory_lock:
            if self._last_run_id and self._last_run_id in self._trajectories:
                return self._trajectories[self._last_run_id]
        return None

    def get_trajectory(self, run_id: str) -> Optional[Trajectory]:
        """Thread-safe access to a specific run's trajectory."""
        with self._trajectory_lock:
            return self._trajectories.get(run_id)

    def _trim_registries_locked(self) -> None:
        """Evict oldest tracked runs beyond ``_max_tracked_runs``.

        Must be called while holding ``_trajectory_lock``. Bounds the
        trajectory/attribution registries so a long-lived process cannot leak
        them; the newest runs (including ``_last_run_id``) are always retained.
        """
        while len(self._trajectories) > self._max_tracked_runs:
            old_id, _ = self._trajectories.popitem(last=False)
            self._attributions.pop(old_id, None)
        while len(self._attributions) > self._max_tracked_runs:
            self._attributions.popitem(last=False)

    def discard_run(self, run: dict) -> None:
        """Drop a prepared run's tracked state without learning from it.

        Use when a run is abandoned (e.g. the wrapped framework raised before a
        final answer was produced) so its trajectory/attribution are released
        immediately instead of lingering until evicted by the size cap. Safe to
        call more than once.
        """
        traj = run.get("trajectory") if isinstance(run, dict) else None
        run_id = getattr(traj, "id", None)
        if run_id is None:
            return
        with self._trajectory_lock:
            self._trajectories.pop(run_id, None)
            self._attributions.pop(run_id, None)
            if self._last_run_id == run_id:
                self._last_run_id = None

    @property
    def last_attribution(self) -> Optional[dict]:
        """Attribution dict for the most recent prepared run, if any."""
        with self._trajectory_lock:
            if self._last_run_id and self._last_run_id in self._attributions:
                return self._attributions[self._last_run_id]
        return None

    def apply_external_outcome(
        self, eval_score: float, records: Optional[list] = None
    ) -> int:
        """Feed a trusted external outcome into the utility EMA of retrieved records.

        Use this when a real, objective outcome signal is available (unit tests
        passing, a deterministic grader, an explicit user accept/reject) instead
        of relying on the model's own LLM judge — which cannot always see the
        harm a needless injection causes. Updates the per-record utility that the
        retriever's utility gate reads, without touching confidence.

        Returns the number of records updated. Defaults to the records retrieved
        on the most recent run.
        """
        recs = records if records is not None else list(self._last_records)
        seen: set[str] = set()
        n = 0
        for record in recs:
            rid = getattr(record, "id", None)
            if rid is None or rid in seen:
                continue
            seen.add(rid)
            try:
                update_utility(
                    self.backend, record, eval_score, self.quality_threshold
                )
                n += 1
            except Exception as e:
                logger.warning(
                    "External utility update failed",
                    extra={
                        "event": "external_utility_update_fail",
                        "record_id": rid,
                        "error_type": type(e).__name__,
                    },
                )
        return n

    def get_attribution(self, run_id: str) -> Optional[dict]:
        """Thread-safe access to a specific run's retrieval attribution."""
        with self._trajectory_lock:
            return self._attributions.get(run_id)

    def _maybe_promote(self, record):
        """If auto_promote is enabled, store distilled records as `active` so
        they're retrievable on the next task instead of waiting out the 24h
        quarantine window. Failures already arrive as `active` and are untouched.
        """
        if self.auto_promote and record is not None and record.status == "quarantine":
            record.status = "active"
        return record

    def _select_procedure(self, records, task: Optional[str] = None):
        """Pick the best learned procedure to replay for this run, if any.

        Records are already ranked by the retriever/router, so the first
        procedural skill that survived the gates is the best candidate. When a
        ``task`` is supplied, a task-signature gate (AP5) rejects a procedure
        whose stored skeleton is not sufficiently present in the current task —
        this stops the agent replaying the wrong proven sequence just because the
        retriever ranked it highly. Returns ``(procedure_steps, source_id)`` or
        ``(None, None)``.
        """
        for r in records or []:
            if getattr(r, "type", None) != "skill" or not r.content.get("procedure"):
                continue
            if task is not None:
                stored_sig = r.content.get("task_signature") or []
                if signature_coverage(stored_sig, task) < self.procedure_match_threshold:
                    logger.info(
                        "Procedure rejected by signature gate",
                        extra={
                            "event": "procedure_signature_reject",
                            "record_id": r.id,
                            "stored_signature": stored_sig,
                        },
                    )
                    continue
            return r.content["procedure"], r.id
        return None, None

    def _match_procedure(self, records, task: str):
        """Like :meth:`_select_procedure` but also classifies the match strength.

        Returns ``(kind, procedure_steps, source_id)`` where ``kind`` is
        ``"exact"`` (same task — safe to hard-replay with no LLM), ``"sibling"``
        (same family, different slot values — needs argument adaptation, better
        used as guidance), or ``None`` (no usable procedure).
        """
        for r in records or []:
            if getattr(r, "type", None) != "skill" or not r.content.get("procedure"):
                continue
            kind = match_kind(
                r.content.get("task_signature") or [],
                r.content.get("task_tokens") or [],
                task,
                threshold=self.procedure_match_threshold,
            )
            if kind is None:
                continue
            return kind, r.content["procedure"], r.id
        return None, None, None

    def _attach_procedure(self, skill, traj, domain_vector, score):
        """Capture the executed tool-call sequence onto a procedural skill.

        Agent path only. If ``traj`` has tool steps, attach the captured
        ``procedure`` / ``tool_sequence`` to the distilled skill so it is stored
        as a Hermes-style procedure rather than prose. If the prose distiller
        returned no skill but a real tool workflow ran, build a minimal
        procedural skill directly so the procedure is not lost.
        """
        captured = extract_procedure(traj)
        if captured is None:
            return skill  # no tool calls — model path, nothing to attach

        if skill is None:
            from .schemas.skill import SkillRecord

            skill = SkillRecord(
                domains=domain_vector,
                task_type=traj.task[:80],
                content={
                    "steps": [],
                    "tools_used": [],
                    "constraints": [],
                    "failure_modes": [],
                },
            )

        skill.content["procedure"] = captured["procedure"]
        skill.content["tool_sequence"] = captured["tool_sequence"]
        skill.content["task_signature"] = captured["task_signature"]
        skill.content["task_tokens"] = captured["task_tokens"]
        skill.content.setdefault("trigger", f"Tasks like: {traj.task[:120]}")
        # Keep tools_used aligned with the captured sequence (deduped, ordered).
        seen: set[str] = set()
        tools_used = []
        for t in captured["tool_sequence"]:
            if t not in seen:
                seen.add(t)
                tools_used.append(t)
        skill.content["tools_used"] = tools_used
        logger.info(
            "Captured procedural skill from tool trajectory",
            extra={
                "event": "procedure_captured",
                "tool_calls": captured["call_count"],
                "tool_sequence": captured["tool_sequence"],
            },
        )
        return skill

    def _consolidate_procedure(self, skill, score: float) -> str:
        """Store or evolve a procedural skill within its task-signature family.

        If no family procedure exists yet, store this one as the family seed.
        Otherwise reinforce the existing record (and refine it to a shorter path
        if this run found one) instead of inserting a near-duplicate. This is the
        institutional-knowledge mechanism: one durable, improving procedure per
        task family rather than a pile of one-off captures.

        Returns ``"stored"``, ``"reinforced"``, or ``"refined"``.
        """
        sig_fp = signature_fingerprint(skill.content.get("task_signature") or [])
        skill.content["_signature_fp"] = sig_fp
        existing = find_family_procedure(self.backend, sig_fp, self.scope)
        if existing is None:
            skill.content.setdefault("success_count", 1)
            skill.content["_fingerprint"] = _skill_fingerprint(skill)
            skill.content["_quality_score"] = score
            self._maybe_promote(skill)
            self.backend.add(skill)
            logger.info(
                "Stored new family procedure",
                extra={"event": "procedure_family_seed", "signature_fp": sig_fp[:16]},
            )
            return "stored"
        return reinforce_or_refine(self.backend, existing, skill.content, score)

    def _reflect_playbook(self, skill, traj, domain_vector) -> None:
        """Author the natural-language playbook for a procedural skill (opt-in).

        Runs a single reflection LLM call to capture durable, class-level
        knowledge (good sources, selection criteria, output conventions) and
        pitfalls, and attaches them to ``skill.content``. The accumulation across
        runs happens later in :func:`reinforce_or_refine`; here we only produce
        this run's contribution. Best-effort: any failure leaves the procedure
        stored without a playbook rather than blocking it.
        """
        if not self.reflect_procedures:
            return
        reflect = getattr(self.distiller, "reflect_procedure", None)
        if not callable(reflect):
            return
        try:
            result = reflect(
                trajectory=traj,
                tool_sequence=skill.content.get("tool_sequence") or [],
                domain_vector=domain_vector,
            )
        except Exception as e:
            logger.warning(
                "Playbook reflection raised; storing procedure without playbook",
                extra={"event": "reflect_error", "error_type": type(e).__name__},
            )
            return
        if not isinstance(result, dict):
            return
        playbook = merge_insights(skill.content.get("playbook"), result.get("playbook"))
        pitfalls = merge_insights(skill.content.get("pitfalls"), result.get("pitfalls"))
        if playbook:
            skill.content["playbook"] = playbook
        if pitfalls:
            skill.content["pitfalls"] = pitfalls
        if playbook or pitfalls:
            logger.info(
                "Authored procedure playbook",
                extra={
                    "event": "playbook_authored",
                    "playbook_items": len(playbook),
                    "pitfall_items": len(pitfalls),
                },
            )

    def export_skill_library(self, path) -> int:
        """Write the learned procedural skills to an on-disk Hermes-style library.

        Each procedure becomes ``<path>/<name>/SKILL.md`` (YAML frontmatter +
        procedure body). This is the durable institutional-knowledge artifact:
        a growing, human-readable library that survives the process and can be
        reviewed, versioned, or shared. Returns the number of skills written.
        """
        from pathlib import Path
        import re

        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)
        records = self.backend.list_by_scope(self.scope, limit=1000)
        written = 0
        for r in records:
            if getattr(r, "type", None) != "skill" or not r.content.get("procedure"):
                continue
            raw = (r.task_type or "skill") + "-" + r.id[:8]
            name = re.sub(r"[^a-z0-9._-]+", "-", raw.lower()).strip("-") or r.id[:8]
            skill_dir = out / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(r.to_skill_md(), encoding="utf-8")
            written += 1
        logger.info(
            "Exported procedural skill library",
            extra={"event": "skill_library_export", "count": written, "path": str(out)},
        )
        return written

    def shutdown(self, wait: bool = True) -> None:
        """Drain the post-processing worker pool. Safe to call multiple times."""
        with self._shutdown_lock:
            if self._is_shutdown:
                return
            self._is_shutdown = True
            self._worker_pool.shutdown(wait=wait)

    def learn(self, domain: Optional[str] = None, task_type: Optional[str] = None):
        """Model path — wrap a single-turn agent function with the LearnKit loop.

        The wrapped function is treated as a black box: ``task`` in, answer string
        out. Retrieved memory is injected as text via the ``_learnkit_context``
        keyword, and only the final answer is judged and distilled. Use this for
        models / single-shot generations that do not expose their tool calls.
        """

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(task: str, *args, **kwargs) -> str:
                run = self.prepare_run(task)
                run["learning_mode"] = "learn"

                # Inject context into kwargs or modify the call
                enriched_kwargs = {**kwargs, "_learnkit_context": run["context"]}
                try:
                    result = fn(task, *args, **enriched_kwargs)
                except Exception as e:
                    # Capture failure if the agent crashes
                    logger.warning(
                        "Agent execution failed",
                        extra={"event": "agent_crash", "error_type": type(e).__name__},
                    )
                    raise e

                return self.finalize_run(run, result)

            return wrapper

        return decorator

    # Backward-compatible alias. Existing call sites use ``@memory.agent(...)``.
    agent = learn

    def agent_learn(
        self, domain: Optional[str] = None, task_type: Optional[str] = None
    ):
        """Agent path (Hermes-style) — wrap a tool-using agent and learn its
        *procedure*, not just its final answer.

        A :class:`~learnkit.tool_tracker.ToolTracker` is injected via the
        ``_learnkit_tools`` keyword. The agent reports each tool call through it
        (``tracker.record(...)`` or ``tracker.wrap(tool_fn)``), which records the
        tool steps on the run's trajectory. On a successful run those steps are
        distilled into a reusable procedural skill, and ``tracker.call_count``
        exposes the tool-calls-per-task metric.

        The wrapped function receives ``_learnkit_context`` (text memory) and
        ``_learnkit_tools`` (the tracker). It still returns the final answer
        string.
        """

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(task: str, *args, **kwargs) -> str:
                run = self.prepare_run(task)
                run["learning_mode"] = "agent_learn"
                tracker = self.arm_tool_tracker(run)

                enriched_kwargs = {
                    **kwargs,
                    "_learnkit_context": run["context"],
                    "_learnkit_tools": tracker,
                }
                try:
                    result = fn(task, *args, **enriched_kwargs)
                except Exception as e:
                    logger.warning(
                        "Agent execution failed",
                        extra={"event": "agent_crash", "error_type": type(e).__name__},
                    )
                    raise e

                run["tool_calls"] = tracker.call_count
                # Tool-success gate: gate storage/reinforcement on the real
                # outcome (tools succeeded) rather than the harm-blind LLM judge.
                run["outcome_score"] = tracker.outcome_score()
                return self.finalize_run(run, result)

            return wrapper

        return decorator

    def prepare_run(self, task: str) -> dict:
        try:
            classification = self.classifier(task)
            domain_vector = classification.domains
        except Exception as e:
            logger.warning(
                "Classification failed, falling back to empty domains",
                extra={"event": "classifier_fallback", "error_type": type(e).__name__},
            )
            from .classifier import ClassificationOutput

            classification = ClassificationOutput(
                task_type="unknown", domains={}, complexity="medium"
            )
            domain_vector = {}

        try:
            records = self.retriever.retrieve(
                task=task,
                domain_vector=domain_vector,
                scope=self.scope,
                router=self.router,
            )
        except Exception as e:
            logger.warning(
                "Retrieval failed, returning empty context",
                extra={"event": "retrieval_fallback", "error_type": type(e).__name__},
            )
            records = []

        mode = determine_inference_mode(records)
        context_block = compose_context(records, task, mode)
        attribution = build_attribution(records, context_block)

        traj = Trajectory(task=task)
        traj.add_step("user", task)

        with self._trajectory_lock:
            self._trajectories[traj.id] = traj
            self._attributions[traj.id] = attribution
            self._last_run_id = traj.id
            self._last_records = records
            self._trim_registries_locked()

        return {
            "classification": classification,
            "domain_vector": domain_vector,
            "records": records,
            "mode": mode,
            "context": context_block,
            "attribution": attribution,
            "trajectory": traj,
            "_t_start": time.perf_counter(),
        }

    def arm_tool_tracker(self, run: dict) -> ToolTracker:
        """Attach a :class:`ToolTracker` to a prepared run and wire procedure
        replay, mirroring what :meth:`agent_learn` does internally.

        Adapters use this so any framework integration gets the procedural
        (tool-capture + replay) learning path for free. Returns the tracker;
        the caller must set ``run["tool_calls"]`` and ``run["outcome_score"]``
        from it before calling :meth:`finalize_run` to engage the tool-success
        gate.
        """
        tracker = ToolTracker(run["trajectory"])
        task = run["trajectory"].task
        # Adapters that arm a tracker directly are on the agent (tool-using)
        # path; tag the run so its telemetry is attributed to agent_learn.
        run.setdefault("learning_mode", "agent_learn")
        # Replay: if a previously-learned procedure matches this task, attach it
        # so the agent can follow the proven tool sequence instead of
        # re-deriving it (Hermes / AWM step-reduction).
        proc, source_id = self._select_procedure(run["records"], task=task)
        if proc:
            kind, _, _ = self._match_procedure(run["records"], task)
            tracker.set_plan(proc, source_id=source_id, kind=kind)
            # Remember which stored procedure we replayed so the outcome can
            # reinforce it (success) or demote it (failure).
            run["replayed_source_id"] = source_id
        return tracker

    def finalize_run(self, run: dict, response: str) -> str:
        traj = run["trajectory"]
        traj.add_step("assistant", response)

        classification = run.get("classification")
        t_start = run.get("_t_start")
        latency_ms = None
        if t_start is not None:
            latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        run_meta = {
            "tool_calls": int(run.get("tool_calls", 0) or 0),
            "learning_mode": run.get("learning_mode"),
            "record_ids": [
                getattr(r, "id", None) for r in run.get("records", []) if getattr(r, "id", None)
            ],
            "task_type": getattr(classification, "task_type", None),
            "latency_ms": latency_ms,
            "task_chars": len(run.get("trajectory").task or ""),
            "context_chars": len(run.get("context") or ""),
            "response_chars": len(response or ""),
        }

        self._post_process(
            traj,
            run["domain_vector"],
            run.get("records", []),
            override_score=run.get("outcome_score"),
            replayed_source_id=run.get("replayed_source_id"),
            run_meta=run_meta,
        )
        return response

    def _post_process(
        self,
        traj: Trajectory,
        domain_vector: dict,
        retrieved_records=None,
        override_score: Optional[float] = None,
        replayed_source_id: Optional[str] = None,
        run_meta: Optional[dict] = None,
    ):
        if not self.background_postprocess:
            self._post_process_now(
                traj, domain_vector, retrieved_records or [], override_score,
                replayed_source_id, run_meta,
            )
            return
        self._post_process_async(
            traj, domain_vector, retrieved_records or [], override_score,
            replayed_source_id, run_meta,
        )

    def _post_process_async(
        self,
        traj: Trajectory,
        domain_vector: dict,
        retrieved_records: list,
        override_score: Optional[float] = None,
        replayed_source_id: Optional[str] = None,
        run_meta: Optional[dict] = None,
    ) -> None:
        """
        Quality gate + distillation. Runs after response returned to user.
        Uses a bounded thread pool to avoid unbound thread growth and logs exceptions.
        Falls back to sync if the pool has been drained (e.g. after shutdown).
        """
        if self._is_shutdown:
            self._post_process_now(traj, domain_vector, retrieved_records, override_score,
                                   replayed_source_id, run_meta)
            return
        future = self._worker_pool.submit(
            self._post_process_now, traj, domain_vector, retrieved_records, override_score,
            replayed_source_id, run_meta,
        )

        # Add a done callback to catch and log silent failures in the thread
        def _handle_result(fut):
            try:
                fut.result()
            except Exception as e:
                logger.error(
                    "Background post-processing failed",
                    extra={
                        "event": "post_process_crash",
                        "error_type": type(e).__name__,
                    },
                )

        future.add_done_callback(_handle_result)

    def _post_process_now(
        self,
        traj: Trajectory,
        domain_vector: dict,
        retrieved_records: list | None = None,
        override_score: Optional[float] = None,
        replayed_source_id: Optional[str] = None,
        run_meta: Optional[dict] = None,
    ) -> None:
        # Interpreter is shutting down — dspy/litellm's own thread pool may already
        # be torn down (their atexit runs first since they're imported lazily on
        # the first LM call). Calling the judge here would fail with "cannot
        # schedule new futures after interpreter shutdown", which the evaluator
        # then catches and returns score=2.0, which then causes us to write a
        # synthetic FailureRecord for a run that was actually successful.
        # Skip post-processing entirely in this case.
        if sys.is_finalizing():
            logger.info(
                "Skipping post-processing during interpreter finalization",
                extra={"event": "post_process_skip_finalizing", "task": traj.task[:80]},
            )
            return
        try:
            # Agent path supplies a trusted outcome (tool success); model path
            # falls back to the LLM judge. Gating on a real outcome signal is the
            # core fix for the judge's harm-blindness on its own output.
            if override_score is not None:
                score = float(override_score)
                logger.info(
                    "Using external outcome score (tool-success gate)",
                    extra={"event": "outcome_gate_external", "score": score},
                )
            else:
                eval_result = self.evaluator.evaluate_with_llm_judge(
                    task=traj.task, response=traj.steps[-1].content if traj.steps else ""
                )
                score = eval_result.score
            traj.quality_score = score
            traj.outcome = (
                "success" if score >= self.quality_threshold else "failure"
            )
            self._reinforce_or_demote_retrieved(
                retrieved_records or [], score
            )

            if score >= self.quality_threshold:
                skill, facts, failures, trace_record = self.distiller.distill(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=score,
                )
                # Agent path (@lk.agent_learn): capture the executed tool-call
                # sequence and store it as a procedural skill. If the prose
                # distiller abstained (one-off task) but the agent still ran a
                # real tool workflow that succeeded, build a procedural skill
                # from the captured calls so the procedure is not lost.
                skill = self._attach_procedure(
                    skill, traj, domain_vector, score
                )
                if skill and skill.content.get("procedure"):
                    # Agent path: evolve the task-signature *family*. All siblings
                    # reinforce one durable procedure (institutional knowledge),
                    # the shortest successful path wins (refinement), and dupes
                    # never accumulate.
                    skill.scope = self.scope
                    # Author the natural-language playbook (opt-in) so the skill
                    # body grows smarter over repeats, not just cheaper to replay.
                    self._reflect_playbook(skill, traj, domain_vector)
                    self._consolidate_procedure(skill, score)
                elif skill:
                    skill.scope = self.scope
                    # AWM + Voyager pattern: skip if a near-duplicate skill already exists
                    # (same step-sequence fingerprint). Reinforce the existing record instead.
                    fp = _skill_fingerprint(skill)
                    storage_decision = decide_storage(
                        skill, self.backend, self.scope, task_text=traj.task
                    )
                    existing_fp = self.backend.search(
                        query=f"fingerprint:{fp}",
                        domain=None,
                        scope=self.scope,
                        limit=1,
                    )
                    dup = next(
                        (r for r in existing_fp if r.content.get("_fingerprint") == fp),
                        None,
                    )
                    if dup:
                        new_conf = min(0.95, dup.confidence + 0.02)
                        self.backend.update_confidence(dup.id, new_conf)
                        logger.info(
                            "Skill dedup: reinforced existing record instead of inserting duplicate",
                            extra={"event": "skill_dedup", "fingerprint": fp[:16]},
                        )
                    elif storage_decision.duplicate:
                        reinforce_existing(self.backend, storage_decision.duplicate)
                        logger.info(
                            "Skill dedup: reinforced near-duplicate record",
                            extra={
                                "event": "skill_dedup_near",
                                "record_id": storage_decision.duplicate.id,
                            },
                        )
                    elif not storage_decision.should_store:
                        logger.info(
                            "Skill storage skipped by quality gate",
                            extra={
                                "event": "skill_store_skip",
                                "reason": storage_decision.reason,
                            },
                        )
                    else:
                        skill.content["_fingerprint"] = fp
                        skill.content["_quality_score"] = score
                        self._maybe_promote(skill)
                        self.backend.add(skill)
                for fact in facts:
                    fact.scope = self.scope
                    storage_decision = decide_storage(
                        fact, self.backend, self.scope, task_text=traj.task
                    )
                    if storage_decision.duplicate:
                        reinforce_existing(self.backend, storage_decision.duplicate, delta=0.01)
                    elif storage_decision.should_store:
                        self._maybe_promote(fact)
                        self.backend.add(fact)
                for failure in failures:
                    failure.scope = self.scope
                    self._add_failure_deduped(failure)
                if trace_record:
                    trace_record.scope = self.scope
                    self._maybe_promote(trace_record)
                    self.backend.add(trace_record)
            else:
                # Low quality — run contrastive failure extraction (ReasoningBank dual-pass).
                # distill_failure() makes a targeted LLM call to extract root_cause,
                # corrective_strategy, and trigger_pattern from the failed trace.
                # Falls back to a minimal generic FailureRecord if extraction fails.
                from .schemas.failure import FailureRecord

                # Agent path self-healing: if this failed run replayed a stored
                # procedure, demote it. Repeated failures quarantine the procedure
                # so the agent stops trusting it and re-learns the task.
                if replayed_source_id:
                    rec = self.backend.read(replayed_source_id)
                    if rec is not None:
                        demote_procedure(self.backend, rec)

                failure = self.distiller.distill_failure(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=score,
                )
                if failure is None:
                    # Safe fallback: at minimum record that this task/approach failed
                    failure = FailureRecord(
                        domains=domain_vector,
                        content={
                            "description": f"Failed task: {traj.task[:100]}",
                            "what_to_avoid": "Approach used in this trace",
                        },
                        status="active",
                    )
                failure.scope = self.scope
                self._add_failure_deduped(failure)
        except Exception as e:
            raise PostProcessError(f"Post-processing failed: {e}") from e
        finally:
            # Persist run telemetry regardless of distillation outcome so the
            # dashboard can trace the agent and chart its learning. Best-effort:
            # a telemetry write must never break the learning loop.
            try:
                self._persist_run(traj, domain_vector, retrieved_records or [],
                                   replayed_source_id, run_meta)
            except Exception as e:  # pragma: no cover - telemetry is non-critical
                logger.warning(
                    "Run telemetry persist failed",
                    extra={"event": "run_persist_fail", "error_type": type(e).__name__},
                )

    def _persist_run(
        self,
        traj: Trajectory,
        domain_vector: dict,
        retrieved_records: list,
        replayed_source_id: Optional[str],
        run_meta: Optional[dict],
    ) -> None:
        """Write a single finalized run to the backend's runs table.

        Computes "calls reduced" against the cold (non-replayed) baseline for the
        task family, so the dashboard can show how replay shrinks tool calls over
        time. No-op on backends without a runs store (BaseBackend default).
        """
        meta = run_meta or {}
        tool_calls = int(meta.get("tool_calls", 0) or 0)

        # Family key: prefer the captured task-signature (agent path, same key as
        # procedure consolidation), else fall back to the classified task type so
        # model-path runs still group into a family.
        captured = extract_procedure(traj)
        if captured and captured.get("task_signature"):
            signature_fp = signature_fingerprint(captured["task_signature"])
        else:
            base = (meta.get("task_type") or "general").strip().lower()
            signature_fp = hashlib.sha256(base.encode()).hexdigest()

        replayed = bool(replayed_source_id)
        baseline = self.backend.family_baseline(signature_fp)
        calls_reduced = 0.0
        if baseline is not None and tool_calls > 0:
            calls_reduced = max(0.0, baseline - tool_calls)

        # Learning path for this run: prefer the explicit tag set by the
        # learn / agent_learn decorators; fall back to tool evidence so
        # adapter-driven runs are still classified correctly.
        learning_mode = meta.get("learning_mode")
        if learning_mode not in ("learn", "agent_learn"):
            learning_mode = "agent_learn" if (tool_calls > 0 or replayed) else "learn"

        record_ids = meta.get("record_ids")
        if record_ids is None:
            record_ids = [getattr(r, "id", None) for r in retrieved_records]
        record_ids = [rid for rid in record_ids if rid]

        steps = [
            {
                "step": s.step,
                "role": s.role,
                "tool_name": s.tool_name,
                "content": (s.content or "")[:200],
            }
            for s in traj.steps
        ]

        # Telemetry: real latency + honest token/cost estimates (see
        # learnkit/observability.py). LearnKit calls LLMs via DSPy, which does
        # not expose per-call usage, so token/cost are flagged ``estimated``.
        succeeded = traj.outcome == "success"
        trajectory_chars = sum(len(s.content or "") for s in traj.steps)
        telemetry = estimate_run_telemetry(
            task_chars=int(meta.get("task_chars", 0) or 0),
            context_chars=int(meta.get("context_chars", 0) or 0),
            response_chars=int(meta.get("response_chars", 0) or 0),
            trajectory_chars=trajectory_chars,
            models=resolve_models(),
            replayed=replayed,
            succeeded=succeeded,
        )

        self.backend.insert_run(
            {
                "run_id": traj.id,
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "task": traj.task,
                "task_type": meta.get("task_type"),
                "domains": domain_vector or {},
                "mode": learning_mode,
                "tool_calls": tool_calls,
                "baseline_calls": baseline,
                "calls_reduced": calls_reduced,
                "replayed": replayed,
                "outcome": traj.outcome,
                "quality_score": traj.quality_score,
                "record_ids": record_ids,
                "signature_fp": signature_fp,
                "steps": steps,
                "created_at": traj.created_at,
                "latency_ms": meta.get("latency_ms"),
                "prompt_tokens": telemetry["prompt_tokens"],
                "completion_tokens": telemetry["completion_tokens"],
                "total_tokens": telemetry["total_tokens"],
                "context_tokens": telemetry["context_tokens"],
                "cost_usd": telemetry["cost_usd"],
                "models": resolve_models(),
                "estimated": telemetry["estimated"],
            }
        )

    def _reinforce_or_demote_retrieved(self, records: list, eval_score: float) -> None:
        """Update retrieved-memory confidence with graded outcome feedback."""
        seen: set[str] = set()
        for idx, record in enumerate(records):
            if record.id in seen:
                continue
            seen.add(record.id)
            try:
                apply_retrieval_feedback(
                    self.backend,
                    record,
                    eval_score=eval_score,
                    quality_threshold=self.quality_threshold,
                    primary=(idx == 0),
                    update_util=not self.utility_external,
                )
            except Exception as e:
                logger.warning(
                    "Retrieved-memory confidence update failed",
                    extra={
                        "event": "retrieved_confidence_update_fail",
                        "record_id": getattr(record, "id", ""),
                        "error_type": type(e).__name__,
                    },
                )

    def _add_failure_deduped(self, failure) -> None:
        storage_decision = decide_storage(
            failure,
            self.backend,
            self.scope,
            duplicate_threshold=0.58,
        )
        if storage_decision.duplicate:
            reinforce_existing(self.backend, storage_decision.duplicate, delta=0.03)
            logger.info(
                "Failure dedup: reinforced existing failure record",
                extra={
                    "event": "failure_dedup",
                    "record_id": storage_decision.duplicate.id,
                },
            )
        elif storage_decision.should_store:
            self.backend.add(failure)
        else:
            logger.info(
                "Failure storage skipped by quality gate",
                extra={"event": "failure_store_skip", "reason": storage_decision.reason},
            )

    def inspect(self, task: str) -> dict:
        """Readonly view of the LearnKit loop's first three stages for a task.

        Runs Classify -> Retrieve -> Compose without registering a trajectory,
        running an agent, or writing anything. Returns plain JSON-serialisable
        data — intended for demos, debugging, and the marketing-site Playground.
        """
        try:
            classification = self.classifier(task)
            domain_vector = classification.domains
        except Exception as e:
            logger.warning(
                "inspect: classification failed, falling back",
                extra={
                    "event": "inspect_classifier_fallback",
                    "error_type": type(e).__name__,
                },
            )
            from .classifier import ClassificationOutput

            classification = ClassificationOutput(
                task_type="unknown", domains={}, complexity="medium"
            )
            domain_vector = {}

        try:
            records = self.retriever.retrieve(
                task=task,
                domain_vector=domain_vector,
                scope=self.scope,
                router=self.router,
            )
        except Exception as e:
            logger.warning(
                "inspect: retrieval failed, returning empty",
                extra={
                    "event": "inspect_retrieval_fallback",
                    "error_type": type(e).__name__,
                },
            )
            records = []

        mode = determine_inference_mode(records)
        context_block = compose_context(records, task, mode)
        attribution = build_attribution(records, context_block)

        return {
            "task": task,
            "classification": {
                "task_type": classification.task_type,
                "domains": dict(domain_vector),
                "complexity": getattr(classification, "complexity", "medium"),
            },
            "inference_mode": mode.value,
            "records": [
                {
                    "id": r.id,
                    "type": r.type,
                    "task_type": r.task_type,
                    "domains": dict(r.domains),
                    "confidence": round(r.confidence, 3),
                    "reuse_count": r.reuse_count,
                    "status": r.status,
                    "content": r.content,
                }
                for r in records
            ],
            "attribution": attribution,
            "context": context_block,
            "context_chars": len(context_block),
        }

    def maintain_memory(
        self,
        weeks: int = 1,
        decay_rate: float = 0.02,
        quarantine_hours: float = 24.0,
        consolidate: bool = False,
        stale_expired: bool = True,
    ) -> dict[str, int]:
        """Run the local maintenance loop: decay, stale marking, quarantine promotion.

        When ``consolidate`` is set, also run the umbrella-merge pass that folds
        overlapping active skills into a single canonical skill (archiving the
        rest as ``deprecated``) so the store doesn't bloat with near-duplicates.

        When ``stale_expired`` is False, records past their TTL are left
        ``active`` (not hidden from retrieval) — used by the dashboard's
        persist-until-deleted policy.
        """
        stats = {
            "decayed": (
                self.backend.decay_confidence(weeks=weeks, decay_rate=decay_rate)
                if decay_rate > 0
                else 0
            ),
            "stale": self.backend.mark_expired_stale() if stale_expired else 0,
            "promoted": self.backend.promote_quarantined(
                min_age_hours=quarantine_hours
            ),
        }
        if consolidate:
            merged = consolidate_skills(self.backend)
            stats["consolidated_clusters"] = merged["clusters"]
            stats["consolidated_archived"] = merged["archived"]
        return stats
