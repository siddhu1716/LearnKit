# improvements.md — LearnKit Enhancement Tracking

Last updated: 2026-05-28

---

## ✅ Completed (v1 → MVP hardening)

| Item | Where | Notes |
|---|---|---|
| `datetime.utcnow()` → timezone-aware | `schemas/base.py`, `backends/sqlite.py`, all tests | Eliminated all in-house deprecation warnings |
| Mutable Pydantic defaults | `schemas/base.py` | Converted `domains={}`, `content={}`, `transfer_domains=[]` to `Field(default_factory=...)` |
| FTS5 BM25 sign inversion bug | `backends/sqlite.py` | `bm25()` returns negative values; negated to fix DESC ordering |
| Hybrid search LEFT JOIN bug | `backends/sqlite.py:hybrid_search` | Was always returning 0.0 BM25; fixed via FTS5 subquery MATCH |
| Scope propagation | `core.py:_post_process_now` | All distilled records now inherit `self.scope` |
| atexit drain of worker pool | `core.py` | Eliminates "cannot schedule new futures after shutdown" |
| Router token budget enforcement | `router.py` | Dual cap: 8 records AND ~1200 tokens |
| Write-time scope validation | `backends/sqlite.py:add()` | Raises `BackendError` on invalid scope string |
| `[langchain]` install extra | `pyproject.toml` | `pip install learnkit[langchain]` works |
| `__pycache__` in .gitignore | `.gitignore` | Removed tracked pyc files from index |

---

## 🔨 MVP Changes (current sprint — agents_v2_mvp.md)

| Item | Source | Priority | Status |
|---|---|---|---|
| **k=1 PRIMARY/SECONDARY prompt split** | ReasoningBank (ICLR 2026) | HIGH | 🔨 In Progress |
| **Bundled starter skills** (`skills/legal/`, `skills/coding/`) | Hermes Agent `skills/*.md` format | HIGH | 🔨 In Progress |
| **AWM slot substitution in skill content** | Agent Workflow Memory (arXiv 2409.07429) | MEDIUM | Pending |
| **Confidence-gate on quarantine promotion** | Voyager promotion gates | MEDIUM | Pending |
| **Contrastive failure prompting** | ReasoningBank dual-pass failure extraction | MEDIUM | Pending |

---

## 📋 Future — v2 Production

| Improvement | Source | Reason / Notes |
|---|---|---|
| Native vector embeddings (`sentence-transformers` push-down) | Hermes + sqlite-vec | Vector store integration; push-down query not yet fully verified |
| Dynamic domain adaptation | ReaComp pipeline | Requires extensive tracing; scheduled for v2 |
| Time-aware exponential confidence decay | Karpathy LLM Wiki "keep current" | Linear decay sufficient for MVP |
| Auto-instrumenting AST parser | — | Invasive; will rely on explicit wrappers |
| Local dashboard / memory wiki viewer | Karpathy LLM Wiki | Developer tooling after core stability |
| GEPA evolution hardening (lineage, dedup, trial-failure handling) | Hermes GEPA | Planned after core modules stabilize |
| Optional backends (`mem0`, `zep`, `qdrant`) | Hermes toolset pattern | Implement adapters + contract tests |
| Native framework adapters (LangChain callbacks, LangGraph nodes, AutoGen reply) | — | LangChain demo exists; native integrations still to do |
| Post-processing interpreter-shutdown race (narrow case) | — | Wider "after shutdown" class fixed by atexit drain (A3); narrow sub-task race remains — document `background_postprocess=False` as mitigation |
| Memory pollution controls — explicit promotion API + confidence-floor filter | Hermes bounded memory | Quarantine exclusion from search is in place; promotion API pending |
| Ensemble reranking surface (expose per-record final_score to callers) | ReaComp ensemble diversity | Currently scored internally; expose for downstream integrations |
| Retriever `list_all()` elimination (push-down vector retrieval) | sqlite-vec push-down | Zero-lexical-overlap fallback currently does a bounded `list_all(100)` scan |
