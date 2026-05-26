from learnkit.adapters import LangChainAdapter, LangGraphAdapter, OpenAIRawAdapter
from learnkit.classifier import ClassificationOutput
from learnkit.core import LearnKit
from learnkit.evaluator import EvaluationResult, EvaluationSignal
from learnkit.retriever import SemanticRetriever
from learnkit.schemas.skill import SkillRecord
from learnkit.backends.sqlite import SQLiteBackend


class FakeEvaluator:
    def evaluate_with_llm_judge(self, task, response, reasoning_trace=None, lm=None):
        return EvaluationResult(4.0, EvaluationSignal.LLM_JUDGE, "ok")


class FakeDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None


def fake_classifier(task):
    return ClassificationOutput(
        task_type="debug_python_error",
        domains={"coding": 0.9},
        complexity="medium",
    )


def build_learnkit():
    lk = LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        classifier=fake_classifier,
        evaluator=FakeEvaluator(),
        distiller=FakeDistiller(),
        background_postprocess=False,
    )
    lk.backend.add(SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["inspect traceback"]},
        confidence=0.91,
    ))
    return lk


def test_semantic_retriever_dense_rerank_without_lexical_overlap():
    def embedder(text):
        text = text.lower()
        if "deadlock" in text or "spawn" in text:
            return [1.0, 0.0]
        if "contract" in text:
            return [0.0, 1.0]
        return [0.0, 0.0]

    backend = SQLiteBackend(":memory:")
    target = SkillRecord(
        domains={"coding": 0.9},
        task_type="multiprocessing_fix",
        content={"steps": ["set spawn start method"]},
        confidence=0.4,
    )
    distractor = SkillRecord(
        domains={"coding": 0.9},
        task_type="contract_summary",
        content={"steps": ["extract contract terms"]},
        confidence=0.99,
    )
    backend.add(target)
    backend.add(distractor)

    retriever = SemanticRetriever(backend=backend, embedder=embedder, dense_weight=1.0)
    results = retriever.retrieve("thread deadlock", {"coding": 0.9})

    assert results[0].id == target.id


def test_openai_raw_adapter_injects_context_and_finalizes():
    lk = build_learnkit()
    seen = {}

    def complete_fn(model, messages, **kwargs):
        seen["messages"] = messages
        return {"choices": [{"message": {"content": "fixed"}}]}

    adapter = OpenAIRawAdapter(lk, complete_fn=complete_fn)
    result = adapter.complete(
        task="debug this traceback",
        messages=[{"role": "user", "content": "debug this"}],
    )

    assert result["choices"][0]["message"]["content"] == "fixed"
    assert seen["messages"][0]["role"] == "system"
    assert "inspect traceback" in seen["messages"][0]["content"]
    assert lk.last_trajectory.outcome == "success"


def test_langgraph_adapter_node_and_finalize():
    lk = build_learnkit()
    adapter = LangGraphAdapter(lk)

    state = adapter.as_node()({"task": "debug this traceback"})
    state["response"] = "fixed"

    assert "inspect traceback" in state["_learnkit_context"]
    assert adapter.finalize(state) == "fixed"
    assert lk.last_trajectory.outcome == "success"


def test_langchain_adapter_lifecycle():
    lk = build_learnkit()
    adapter = LangChainAdapter(lk)

    context = adapter.inject_context("debug this traceback")
    result = adapter.finalize("fixed")

    assert "inspect traceback" in context
    assert result == "fixed"
    assert lk.last_trajectory.outcome == "success"
