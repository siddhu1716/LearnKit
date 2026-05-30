# examples/test_package_connection.py
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
    
    print(f"      - Retrieved: {len(results)} memory records.")
    print(f"      - Target Mode: {inference_mode.value.upper()}")
    print(f"      - Prompt context size: {len(prompt_context)} characters.")
    
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
    
    print(f"      - Database contains: {len(memory.backend.list_all())} records before run.")
    
    @memory.agent(domain="coding")
    def run_agent_multiprocessing(task: str, _learnkit_context: str = "") -> str:
        # Verify the context block was injected into the keyword arguments
        print(f"      - Injected context length: {len(_learnkit_context)}")
        print(f"      - Injected context content:\n{_learnkit_context}")
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
