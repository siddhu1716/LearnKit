import atexit
import functools
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional

from .backends.registry import get_backend
from .classifier import classify_task
from .composer import compose_context
from .distiller import MemoryDistiller
from .errors import PostProcessError
from .evaluator import Evaluator
from .inference_mode import determine_inference_mode
from .logging import get_logger
from .retriever import SemanticRetriever
from .router import MemoryRouter
from .schemas.base import MemoryScope
from .trajectory import Trajectory

logger = get_logger("core")


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
        **backend_kwargs,
    ):
        self.backend = get_backend(memory_backend, **backend_kwargs)
        self.router = MemoryRouter(max_records=8, max_tokens=1200)
        self.retriever = SemanticRetriever(backend=self.backend, embedder=embedder)
        self.classifier = classifier or classify_task
        self.evaluator = evaluator or Evaluator()
        self.distiller = distiller or MemoryDistiller()
        self.scope = scope
        self.capture_reasoning = capture_reasoning
        self.quality_threshold = quality_threshold
        self.evaluation_mode = evaluation
        self.background_postprocess = background_postprocess

        # Concurrency safety: trajectory registry and bounded worker pool
        self._trajectories: Dict[str, Trajectory] = {}
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

        traj = Trajectory(task=task)
        traj.add_step("user", task)

        with self._trajectory_lock:
            self._trajectories[traj.id] = traj
            self._last_run_id = traj.id

        return {
            "classification": classification,
            "domain_vector": domain_vector,
            "records": records,
            "mode": mode,
            "context": context_block,
            "trajectory": traj,
        }

    def finalize_run(self, run: dict, response: str) -> str:
        traj = run["trajectory"]
        traj.add_step("assistant", response)

        self._post_process(traj, run["domain_vector"])
        return response

    def _post_process(self, traj: Trajectory, domain_vector: dict):
        if not self.background_postprocess:
            self._post_process_now(traj, domain_vector)
            return
        self._post_process_async(traj, domain_vector)

    def _post_process_async(self, traj: Trajectory, domain_vector: dict) -> None:
        """
        Quality gate + distillation. Runs after response returned to user.
        Uses a bounded thread pool to avoid unbound thread growth and logs exceptions.
        Falls back to sync if the pool has been drained (e.g. after shutdown).
        """
        if self._is_shutdown:
            self._post_process_now(traj, domain_vector)
            return
        future = self._worker_pool.submit(self._post_process_now, traj, domain_vector)

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

    def _post_process_now(self, traj: Trajectory, domain_vector: dict) -> None:
        try:
            eval_result = self.evaluator.evaluate_with_llm_judge(
                task=traj.task, response=traj.steps[-1].content if traj.steps else ""
            )
            traj.quality_score = eval_result.score
            traj.outcome = (
                "success" if eval_result.score >= self.quality_threshold else "failure"
            )

            if eval_result.score >= self.quality_threshold:
                skill, facts, failures, trace_record = self.distiller.distill(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=eval_result.score,
                )
                if skill:
                    skill.scope = self.scope
                    self.backend.add(skill)
                for fact in facts:
                    fact.scope = self.scope
                    self.backend.add(fact)
                for failure in failures:
                    failure.scope = self.scope
                    self.backend.add(failure)
                if trace_record:
                    trace_record.scope = self.scope
                    self.backend.add(trace_record)
            else:
                # Low quality — store as failure record immediately
                from .schemas.failure import FailureRecord

                failure = FailureRecord(
                    domains=domain_vector,
                    content={
                        "description": f"Failed task: {traj.task[:100]}",
                        "what_to_avoid": "Approach used in this trace",
                    },
                    status="active",
                    scope=self.scope,
                )
                self.backend.add(failure)
        except Exception as e:
            raise PostProcessError(f"Post-processing failed: {e}") from e

    def maintain_memory(
        self,
        weeks: int = 1,
        decay_rate: float = 0.02,
        quarantine_hours: float = 24.0,
    ) -> dict[str, int]:
        """Run the local maintenance loop: decay, stale marking, quarantine promotion."""
        return {
            "decayed": self.backend.decay_confidence(
                weeks=weeks, decay_rate=decay_rate
            ),
            "stale": self.backend.mark_expired_stale(),
            "promoted": self.backend.promote_quarantined(
                min_age_hours=quarantine_hours
            ),
        }
