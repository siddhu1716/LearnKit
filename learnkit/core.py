import atexit
import functools
import hashlib
import sys
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional

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
from .memory_quality import apply_retrieval_feedback, decide_storage, demote_existing, reinforce_existing
from .retriever import SemanticRetriever
from .router import MemoryRouter
from .schemas.base import MemoryScope
from .trajectory import Trajectory

logger = get_logger("core")


def _skill_fingerprint(skill) -> str:
    """Compute a stable fingerprint for a SkillRecord's step sequence.

    AWM + Voyager pattern: prevents storing near-duplicate skills from
    similar trajectories. Steps are normalized (lowercased, stripped) before
    hashing so minor wording variations don't bypass dedup.
    """
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
        retrieval_fusion: str = "weighted",
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
        )
        self.classifier = classifier or classify_task
        self.evaluator = evaluator or Evaluator()
        self.distiller = distiller or MemoryDistiller()
        self.scope = scope
        self.capture_reasoning = capture_reasoning
        self.quality_threshold = quality_threshold
        self.evaluation_mode = evaluation
        self.background_postprocess = background_postprocess
        # When True, distilled skill/fact/strategy/etc. records skip the 24h
        # quarantine window and are stored as `active` so they're retrievable
        # on the next task. Use for benchmark/online-learning scenarios.
        self.auto_promote = auto_promote

        # Concurrency safety: trajectory registry and bounded worker pool
        self._trajectories: Dict[str, Trajectory] = {}
        self._attributions: Dict[str, dict] = {}
        self._trajectory_lock = threading.Lock()
        self._last_run_id: Optional[str] = None
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

    @property
    def last_attribution(self) -> Optional[dict]:
        """Attribution dict for the most recent prepared run, if any."""
        with self._trajectory_lock:
            if self._last_run_id and self._last_run_id in self._attributions:
                return self._attributions[self._last_run_id]
        return None

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

    def shutdown(self, wait: bool = True) -> None:
        """Drain the post-processing worker pool. Safe to call multiple times."""
        with self._shutdown_lock:
            if self._is_shutdown:
                return
            self._is_shutdown = True
            self._worker_pool.shutdown(wait=wait)

    def agent(self, domain: Optional[str] = None, task_type: Optional[str] = None):
        """
        Decorator that wraps any agent function with the full LearnKit loop.
        """

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(task: str, *args, **kwargs) -> str:
                run = self.prepare_run(task)

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

        return {
            "classification": classification,
            "domain_vector": domain_vector,
            "records": records,
            "mode": mode,
            "context": context_block,
            "attribution": attribution,
            "trajectory": traj,
        }

    def finalize_run(self, run: dict, response: str) -> str:
        traj = run["trajectory"]
        traj.add_step("assistant", response)

        self._post_process(traj, run["domain_vector"], run.get("records", []))
        return response

    def _post_process(self, traj: Trajectory, domain_vector: dict, retrieved_records=None):
        if not self.background_postprocess:
            self._post_process_now(traj, domain_vector, retrieved_records or [])
            return
        self._post_process_async(traj, domain_vector, retrieved_records or [])

    def _post_process_async(
        self, traj: Trajectory, domain_vector: dict, retrieved_records: list
    ) -> None:
        """
        Quality gate + distillation. Runs after response returned to user.
        Uses a bounded thread pool to avoid unbound thread growth and logs exceptions.
        Falls back to sync if the pool has been drained (e.g. after shutdown).
        """
        if self._is_shutdown:
            self._post_process_now(traj, domain_vector, retrieved_records)
            return
        future = self._worker_pool.submit(
            self._post_process_now, traj, domain_vector, retrieved_records
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
        self, traj: Trajectory, domain_vector: dict, retrieved_records: list | None = None
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
            eval_result = self.evaluator.evaluate_with_llm_judge(
                task=traj.task, response=traj.steps[-1].content if traj.steps else ""
            )
            traj.quality_score = eval_result.score
            traj.outcome = (
                "success" if eval_result.score >= self.quality_threshold else "failure"
            )
            self._reinforce_or_demote_retrieved(
                retrieved_records or [], eval_result.score
            )

            if eval_result.score >= self.quality_threshold:
                skill, facts, failures, trace_record = self.distiller.distill(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=eval_result.score,
                )
                if skill:
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
                        skill.content["_quality_score"] = eval_result.score
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

                failure = self.distiller.distill_failure(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=eval_result.score,
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
    ) -> dict[str, int]:
        """Run the local maintenance loop: decay, stale marking, quarantine promotion.

        When ``consolidate`` is set, also run the umbrella-merge pass that folds
        overlapping active skills into a single canonical skill (archiving the
        rest as ``deprecated``) so the store doesn't bloat with near-duplicates.
        """
        stats = {
            "decayed": self.backend.decay_confidence(
                weeks=weeks, decay_rate=decay_rate
            ),
            "stale": self.backend.mark_expired_stale(),
            "promoted": self.backend.promote_quarantined(
                min_age_hours=quarantine_hours
            ),
        }
        if consolidate:
            merged = consolidate_skills(self.backend)
            stats["consolidated_clusters"] = merged["clusters"]
            stats["consolidated_archived"] = merged["archived"]
        return stats
