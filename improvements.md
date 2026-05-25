# Future Enhancements & Architectural Improvements for LearnKit

This document outlines structural, performance, and cognitive improvements that can be introduced in subsequent phases of LearnKit development.

---

## 1. Core Engine & Cognitive Enhancements

### 🧠 Dynamic Domain Adaptation
- **Current**: The task classifier returns a static domain vector.
- **Improvement**: Implement a rolling multi-step classifier that evaluates context-shifts *mid-execution* (e.g., if a coding agent shifts from writing a script to reviewing a license, update the active retrieval plan dynamically).

### ⏳ Time-Aware Exponential Confidence Decay
- **Current**: Standard linear decay reduces confidence by a constant percentage weekly.
- **Improvement**: Implement a half-life formula based on domain volatility:
  $$C(t) = C_0 \cdot e^{-\lambda t}$$
  where $\lambda$ is high for fast-moving domains (e.g., frontend frameworks) and low for stable domains (e.g., legal clauses).

### 🎭 Structured Reflection & Negative Contrastive Learning
- **Current**: Failures bypass quarantine but are captured as simple text blobs.
- **Improvement**: Force the distiller to perform contrastive pairs: `(Successful Trace / Failed Trace)`. By presenting the agent with the exact branch where a success deviated from a failure, the agent learns *why* the failure occurred.

---

## 2. Storage & Vector Retrieval Upgrade

### 🔍 Native Vector Embeddings (`sqlite-vec` or `Qdrant`)
- **Current**: BM25 lexical text search via FTS5.
- **Improvement**: Complete the `sqlite-vec` or `Qdrant` adapter integration to perform Hybrid Search:
  $$\text{Score} = \alpha \cdot \text{DenseScore} + (1 - \alpha) \cdot \text{BM25Score}$$
  This captures semantic meaning (e.g., matching "exception in thread" with "stacktrace error") while keeping exact match capabilities.

### 🗄️ Concurrent Memory WAL Mode
- **Current**: Standard SQLite connection management.
- **Improvement**: Force WAL (Write-Ahead Logging) mode and connection pooling to support highly-concurrent multi-agent swarm environments safely:
  ```python
  conn.execute("PRAGMA journal_mode=WAL;")
  conn.execute("PRAGMA synchronous=NORMAL;")
  ```

---

## 3. Developer Experience & Integration

### 🔌 Auto-Instrumenting AST Parser
- **Current**: Decorator requires manual function wrapping and passing of context.
- **Improvement**: Provide automated middleware for popular frameworks (LangChain, AutoGen, CrewAI) that instruments LLM calls using Python’s `sys.settrace` or OpenTelemetry spans to capture trajectories completely invisibly.

### 📊 Local Dashboard / Wiki Viewer
- **Current**: SKILL.md and metadata.json are flat files on disk.
- **Improvement**: Build a lightweight Next.js or Streamlit UI to visualize:
  - Compounding skill graphs (showing how skills inherit/evolve from each other).
  - Trace playback (a time-series visualizer of the agent's reasoning).
  - Direct wiki editor to manually clean up or reinforce stored memories.

---

## 4. Current Repo Hardening Items

### Public API Stability
- Keep `learnkit.__all__` aligned with README examples so `import learnkit as lk` exposes the documented integration surface.

### Test Environment Pinning
- The project currently verifies cleanly with `python3.11`; add a short contributor note or tooling config so `pytest` does not accidentally run under a Python without project dependencies installed.

### Background Processing Controls
- The `LearnKit.agent` decorator starts post-processing in a daemon thread. Add a test-friendly synchronous mode before expanding integration adapters.
