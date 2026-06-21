import sqlite3
import glob
import json
import sys

run = sys.argv[1] if len(sys.argv) > 1 else "20260620_020507"
for db in sorted(glob.glob(f"benchmarks/results/{run}/*python_debugging*.db")):
    c = sqlite3.connect(db)
    tables = [r[0] for r in c.execute(
        "select name from sqlite_master where type='table'").fetchall()]
    # find a table with a 'content' column
    target = None
    for t in tables:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
        if "content" in cols:
            target = t
            break
    if target is None:
        print(db.split("\\")[-1], "tables=", tables, "-> no content col")
        c.close()
        continue
    rows = c.execute(f"select content from {target}").fetchall()
    c.close()
    us = []
    for (content,) in rows:
        try:
            d = json.loads(content) if isinstance(content, str) else content
        except Exception:
            continue
        if isinstance(d, dict) and "_utility" in d:
            us.append((round(d.get("_utility", 0), 3), d.get("_utility_trials", 0)))
    maxtrials = max([t for _, t in us], default=0)
    print(db.split("\\")[-1], "table=", target, "records=", len(rows),
          "with_utility=", len(us), "max_trials=", maxtrials, us[:10])
