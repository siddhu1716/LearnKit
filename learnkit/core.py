import functools
from typing import Optional, Callable
from .classifier import classify_task
from .router import MemoryRouter
from .retriever import SemanticRetriever
from .composer import compose_context
from .evaluator import Evaluator
from .distiller import MemoryDistiller
from .trajectory import Trajectory
from .inference_mode import determine_inference_mode
from .backends.sqlite import SQLiteBackend
from .backends.registry import get_backend

class LearnKit:
    def __init__(
        self,
        memory_backend: str = "sqlite",
        evaluation: str = "llm_judge",
        scope: str = "team",
        capture_reasoning: bool = True,    # ReaComp: mandatory CoT capture
        quality_threshold: float = 3.5,
        classifier: Optional[Callable] = None,
        evaluator: Optional[Evaluator] = None,
        distiller: Optional[MemoryDistiller] = None,
        background_postprocess: bool = True,
        **backend_kwargs
    ):
        self.backend = get_backend(memory_backend, **backend_kwargs)
        self.router = MemoryRouter(max_records=8, max_tokens=1200)
        self.retriever = SemanticRetriever(backend=self.backend)
        self.classifier = classifier or classify_task
        self.evaluator = evaluator or Evaluator()
        self.distiller = distiller or MemoryDistiller()
        self.scope = scope
        self.capture_reasoning = capture_reasoning
        self.quality_threshold = quality_threshold
        self.evaluation_mode = evaluation
        self.background_postprocess = background_postprocess
        self.last_trajectory: Optional[Trajectory] = None

    def agent(self, domain: Optional[str] = None, task_type: Optional[str] = None):
        """
        Decorator that wraps any agent function with the full LearnKit loop.
        
        Usage:
            @lk.agent(domain="legal")
            def my_agent(task: str) -> str:
                return langchain_agent.run(task)
        """
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(task: str, *args, **kwargs) -> str:
                # 1. Classify
                classification = self.classifier(task)
                domain_vector = classification.domains

                # 2. Retrieve relevant memory
                records = self.retriever.retrieve(
                    task=task,
                    domain_vector=domain_vector,
                    scope=self.scope,
                    router=self.router
                )

                # 3. Determine inference mode (ReaComp two-stage pattern)
                mode = determine_inference_mode(records)

                # 4. Compose context
                context_block = compose_context(records, task, mode)

                # 5. Run agent with enriched context
                traj = Trajectory(task=task)
                traj.add_step("user", task)

                # Inject context into kwargs or modify the call
                enriched_kwargs = {**kwargs, "_learnkit_context": context_block}
                result = fn(task, *args, **enriched_kwargs)

                traj.add_step("assistant", result)
                self.last_trajectory = traj

                # 6. Evaluate (async — don't block the return)
                self._post_process(traj, domain_vector)

                return result
            return wrapper
        return decorator

    def _post_process(self, traj: Trajectory, domain_vector: dict):
        if not self.background_postprocess:
            self._post_process_now(traj, domain_vector)
            return
        self._post_process_async(traj, domain_vector)

    def _post_process_async(self, traj: Trajectory, domain_vector: dict) -> None:
        """
        Quality gate + distillation. Runs after response returned to user.
        In production: run in a background thread or async task.
        """
        import threading

        threading.Thread(
            target=self._post_process_now,
            args=(traj, domain_vector),
            daemon=True,
        ).start()

    def _post_process_now(self, traj: Trajectory, domain_vector: dict) -> None:
        eval_result = self.evaluator.evaluate_with_llm_judge(
            task=traj.task,
            response=traj.steps[-1].content if traj.steps else ""
        )
        traj.quality_score = eval_result.score
        traj.outcome = "success" if eval_result.score >= self.quality_threshold else "failure"

        if eval_result.score >= self.quality_threshold:
            skill, facts, failures = self.distiller.distill(
                trajectory=traj,
                domain_vector=domain_vector,
                quality_score=eval_result.score
            )
            if skill:
                self.backend.add(skill)
            for f in facts:
                self.backend.add(f)
            for f in failures:
                self.backend.add(f)
        else:
            # Low quality — store as failure record immediately
            from .schemas.failure import FailureRecord
            failure = FailureRecord(
                domains=domain_vector,
                content={
                    "description": f"Failed task: {traj.task[:100]}",
                    "what_to_avoid": "Approach used in this trace"
                },
                status="active"
            )
            self.backend.add(failure)
