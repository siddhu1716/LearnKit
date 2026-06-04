import sqlite3
import json
import uuid
from datetime import datetime, timezone

def main():
    db_path = "benchmarks/swe_bench_lite/learnkit_swebench_pytest.db"
    print(f"Connecting to database {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing tables and recreate or just clean
    # The tables will be created automatically if we use LearnKit, but let's clear records
    try:
        cursor.execute("DELETE FROM records")
        cursor.execute("DELETE FROM records_fts")
        print("Cleared existing records.")
    except Exception as e:
        print(f"Tables do not exist yet: {e}")

    # Define a high-quality skill for pytest skipping/xfail mark handling
    record_id = str(uuid.uuid4())
    domains = {"Testing": 1.0, "Python": 1.0, "Software Development": 1.0}
    task_type = "skipping: xfail and skip mark handling in pytest"
    content = {
        "steps": [
            "Ensure that skipped_by_mark_key is updated in pytest_runtest_setup to reflect whether the test was skipped by a mark: item._store[skipped_by_mark_key] = skipped is not None",
            "Ensure that evaluate_xfail_marks(item) is evaluated and stored in item._store[xfailed_key] = xfailed during pytest_runtest_setup, and evaluated check of not runxfail is performed",
            "Ensure that dynamic xfails are checked at the end of pytest_runtest_call by retrieving xfailed from item._store and re-evaluating evaluate_xfail_marks(item) if None",
            "When setting outcomes in pytest_runtest_makereport, handle rep.skipped with item._store.get(skipped_by_mark_key, True) correctly"
        ],
        "tools_used": ["pytest", "python"],
        "constraints": ["Keep compatibility with standard test report output and --runxfail flag."],
        "failure_modes": ["Using a static skipped_by_mark_key assignment like item._store[skipped_by_mark_key] = False can overwrite earlier marked skip states in the test execution loop."],
        "examples": {
            "good": "item._store[skipped_by_mark_key] = skipped is not None\n... \nxfailed = item._store.get(xfailed_key, None)\nif xfailed is None:\n    item._store[xfailed_key] = xfailed = evaluate_xfail_marks(item)",
            "bad": "item._store[skipped_by_mark_key] = False\n... \nif not item.config.option.runxfail:\n    item._store[xfailed_key] = xfailed = evaluate_xfail_marks(item)"
        }
    }

    created_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    expires_at = (datetime.now(timezone.utc).replace(tzinfo=None) + datetime.timedelta(days=180)).isoformat() if hasattr(datetime, "timedelta") else (datetime.now(timezone.utc).replace(tzinfo=None)).isoformat()
    
    # Simple manual expires_at calculation to avoid AttributeError if timedelta isn't directly on datetime
    from datetime import timedelta
    expires_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=180)).isoformat()

    full_record = {
        "id": record_id,
        "type": "skill",
        "domains": domains,
        "task_type": task_type,
        "content": content,
        "confidence": 0.9,
        "reuse_count": 0,
        "success_rate": None,
        "scope": "user",
        "status": "active",
        "created_at": created_at,
        "expires_at": expires_at,
        "last_reinforced": None,
        "transfer_domains": [],
        "transfer_confidence": None,
        "evolution_gen": 0
    }

    # Insert into records table
    cursor.execute("""
        INSERT INTO records (id, type, domains, task_type, content, confidence, reuse_count,
                             success_rate, scope, status, created_at, expires_at, full_record)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record_id,
        "skill",
        json.dumps(domains),
        task_type,
        json.dumps(content),
        0.9,
        0,
        None,
        "user",
        "active",
        created_at,
        expires_at,
        json.dumps(full_record)
    ))

    # Insert into records_fts table for full-text search matching
    content_text = " ".join([
        task_type,
        " ".join(content["steps"]),
        " ".join(content["tools_used"]),
        " ".join(content["constraints"]),
        " ".join(content["failure_modes"]),
        content["examples"]["good"],
        content["examples"]["bad"]
    ])
    domains_text = " ".join(domains.keys())
    cursor.execute("""
        INSERT INTO records_fts (id, task_type, content_text, domains_text)
        VALUES (?,?,?,?)
    """, (
        record_id,
        task_type,
        content_text,
        domains_text
    ))

    conn.commit()
    conn.close()
    print("Successfully populated skipping skill!")

if __name__ == "__main__":
    main()
