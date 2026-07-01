"""One-off cleanup: remove the Qwen2.5-Coder-32B agent from the live dashboard
store.

Coder-32B is a known FAIL on the agentic suite (sglang tool-parser config gap)
and was swapped out of the benchmark page in favor of Qwen2.5-32B-Instruct.
This drops its seeded agent rows so the Agents registry / Task History no longer
list it.

Safe by construction:
  * Makes a timestamped backup of the DB before touching anything.
  * Deletes ONLY runs whose agent_name = 'qwen2.5-coder-32b' and the memory
    records those runs distilled (referenced in runs.record_ids).
  * Prints a dry-run summary and requires LK_CONFIRM=1 to actually delete.

Run (dry run):   python examples/cleanup_coder_agent.py
Run (delete):    $env:LK_CONFIRM=1; python examples/cleanup_coder_agent.py
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.environ.get(
    "LEARNKIT_DB_PATH", str(Path.home() / ".learnkit" / "memory.db")
)
TARGET_NAME = "qwen2.5-coder-32b"


def main() -> None:
    db = Path(DB_PATH)
    if not db.exists():
        print(f"DB not found: {db}")
        return

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        runs = conn.execute(
            "SELECT run_id, agent_id, agent_name, record_ids FROM runs WHERE agent_name = ?",
            (TARGET_NAME,),
        ).fetchall()
        run_ids = [r["run_id"] for r in runs]
        record_ids: set[str] = set()
        for r in runs:
            try:
                ids = json.loads(r["record_ids"]) if r["record_ids"] else []
                record_ids.update(i for i in ids if i)
            except (json.JSONDecodeError, TypeError):
                pass

        print(f"DB: {db}")
        print(f"Target agent_name: {TARGET_NAME}")
        print(f"Runs to delete:    {len(run_ids)}")
        print(f"Records to delete: {len(record_ids)}")

        if not run_ids and not record_ids:
            print("Nothing to do.")
            return

        if os.environ.get("LK_CONFIRM") != "1":
            print("\nDRY RUN — set LK_CONFIRM=1 to apply the deletion.")
            return

        backup = db.with_name(
            f"{db.stem}.coder-cleanup-{datetime.now():%Y%m%d-%H%M%S}.bak"
        )
        shutil.copy2(db, backup)
        print(f"\nBackup written: {backup}")

        cur = conn.cursor()
        if record_ids:
            qmarks = ",".join("?" for _ in record_ids)
            cur.execute(f"DELETE FROM records WHERE id IN ({qmarks})", tuple(record_ids))
            print(f"Deleted records: {cur.rowcount}")
        if run_ids:
            qmarks = ",".join("?" for _ in run_ids)
            cur.execute(f"DELETE FROM runs WHERE run_id IN ({qmarks})", tuple(run_ids))
            print(f"Deleted runs:    {cur.rowcount}")
        conn.commit()
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
