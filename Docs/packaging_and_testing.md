# LearnKit Packaging & Integration Testing Guide

This document provides a comprehensive guide for binding **LearnKit** as a standardized Python package and testing the integration layer from external codebases.

---

## 1. How to Bind LearnKit as a Python Package

LearnKit’s repository is pre-configured according to the modern Python Packaging Authority (PyPA) standards using PEP 517/621 metadata via `pyproject.toml`.

### 1.1 Package Metadata Configuration (`pyproject.toml`)
LearnKit uses **Hatchling** as its build backend. The structure is declared as:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "learnkit"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "dspy-ai>=2.4.0",
    "sentence-transformers>=3.0.0",
    "rank-bm25>=0.2.2",
    "sqlite-vec>=0.1.0",
    "pydantic>=2.0.0",
    "opentelemetry-sdk>=1.25.0",
    "anthropic>=0.34.0",
]
```

### 1.2 Step-by-Step Package Build Process
To compile LearnKit into standard distributable wheels (`.whl`) and source archives (`.tar.gz`), run the following commands:

```bash
# 1. Install the standardized build frontend tool
pip install --upgrade build

# 2. Build the package from the repository root (where pyproject.toml resides)
python -m build
```

Upon successful completion, the compiled assets will be placed under the `dist/` directory:
```
dist/
├── learnkit-0.1.0-py3-none-any.whl   ← Bounded wheel distribution
└── learnkit-0.1.0.tar.gz             ← Source distribution
```

### 1.3 Publishing to a Package Registry
To distribute the package to your private enterprise artifact store (e.g., AWS CodeArtifact, JFrog Artifactory) or public PyPI:
```bash
pip install --upgrade twine
twine upload dist/*
```

---

## 2. How to Connect and Test the Package Locally

Before publishing the package online, you can easily connect any local script or neighboring project to LearnKit using **Editable Mode** (`pip install -e`).

### 2.1 Installing Locally
Run this from your active virtual environment within the `LearnKit` repository directory:

```bash
# Core SDK only
pip install -e .

# Core SDK + LangChain adapters + Dev dependencies
pip install -e ".[dev,langchain]"
```
*Editable mode links the package directly to your source files, meaning any local modifications in `learnkit/*.py` are instantly visible to your scripts without re-installation.*

---

## 3. Playbook: Connecting and Verifying LearnKit (Offline Sandbox)

Use the following standalone python script to verify that your active python environment successfully imports, retrieves, and processes trajectories with LearnKit's SQLite backend. 

Create a file named `test_package_connection.py` anywhere on your machine:

```python
# test_package_connection.py
import os
import learnkit as lk

def test_learnkit_connection():
    print("=" * 60)
    print("LEARNKIT INTEGRATION TEST SANDBOX")
    print("=" * 60)

    # 1. Initialize local SQLite memory backend
    print("[1/4] Connecting to in-memory database...")
    backend = lk.SQLiteBackend(db_path=":memory:")
    
    # 2. Populate memory records
    print("[2/4] Seeding core procedural skill record...")
    skill = lk.SkillRecord(
        domains={"coding": 0.9},
        task_type="python_multiprocessing",
        content={
            "steps": [
                "Verify OS architecture context (macOS defaults to spawn)",
                "Wrap code block in 'if __name__ == \"__main__\"' gate",
                "Construct pool explicitly using 'spawn' start method"
            ]
        },
        confidence=0.9
    )
    backend.add(skill)
    
    # Save a failure warning (immediately active)
    failure = lk.FailureRecord(
        domains={"coding": 0.9},
        content={
            "description": "Multiprocessing deadlocks caused by 'fork' state sharing",
            "what_to_avoid": "Do not call mp.set_start_method('fork') on macOS/Windows"
        },
        status="active"
    )
    backend.add(failure)
    
    # 3. Retrieve and Compose Context
    print("[3/4] Testing semantic search and prompt composition...")
    query = "macOS python multiprocessing deadlock fix"
    results = backend.search(query, domain="coding")
    
    assert len(results) >= 2, "Expected to retrieve at least 2 matching memory records."
    
    inference_mode = lk.determine_inference_mode(results)
    prompt_context = lk.compose_context(results, query, inference_mode)
    
    print(f"      - Retreived: {len(results)} memory records.")
    print(f"      - Target Mode: {inference_mode.value.upper()}")
    print(f"      - prompt context size: {len(prompt_context)} characters.")
    
    # 4. Running the Wrapped Agent Loop
    print("[4/4] Exercising wrapped @lk.agent decorator...")
    
    # Define a mock classifier to bypass Anthropic API network calls during offline sandbox tests
    def mock_classifier(task: str):
        from learnkit.classifier import ClassificationOutput
        return ClassificationOutput(
            task_type="python_multiprocessing",
            domains={"coding": 1.0},
            complexity="medium"
        )
        
    memory = lk.LearnKit(
        memory_backend="sqlite", 
        db_path=":memory:", 
        classifier=mock_classifier
    )
    
    # Seed the test memory database so our decorated agent retrieves the skills
    memory.backend.add(skill)
    memory.backend.add(failure)
    
    @memory.agent(domain="coding")
    def run_agent_multiprocessing(task: str, _learnkit_context: str = "") -> str:
        # Verify the context block was injected into the keyword arguments
        assert "=== LearnKit Context" in _learnkit_context
        print("      - [INJECTED] Prompt block successfully spliced into agent execution.")
        return "Agent executed task successfully."

    result = run_agent_multiprocessing("Fix macOS multiprocessing issues")
    print(f"      - Execution Output: {result}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] LearnKit is properly packaged, imported, and connected!")
    print("=" * 60)

if __name__ == "__main__":
    test_learnkit_connection()
```

Run the script to verify the installation:
```bash
python test_package_connection.py
```

---

## 4. Verification Checklist

Ensure your packaging environment is in a green state by running the automated testing suite from the repo root:

```bash
# Run the complete test suite
pytest tests/ -v
```
All 41 tests (validating schemas, SQLite WAL concurrency, FTS5 escaping, and decorator integrations) must pass.
