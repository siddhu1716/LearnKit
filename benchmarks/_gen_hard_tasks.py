import json
from pathlib import Path

prompts = [
    "We store created_at = datetime.utcnow() in Postgres, then compare it against datetime.now(timezone.utc) coming from the API layer and the comparison is always wrong. Diagnose the root cause and give the minimal fix.",
    "A session-token check `if datetime.utcnow() > token.expires_at:` raises 'can't compare offset-naive and offset-aware datetimes' because expires_at was parsed from an ISO string ending in +00:00. Explain why and fix it.",
    "Our structured logs built with datetime.utcnow().isoformat() show up an hour off in Grafana for users in Europe/London. What's the underlying bug and the correct fix?",
    "A scheduler computes the next run as datetime.utcnow() + timedelta(hours=24) and drifts by an hour twice a year. Explain the cause and the right way to do this.",
    "We build a JWT 'exp' claim from datetime.utcnow().timestamp(); clients in other timezones reject the token as already expired. Why, and how should we generate exp correctly?",
    "Subtracting datetime.utcnow() from a pandas UTC-localized Timestamp raises 'Cannot subtract tz-naive and tz-aware'. Diagnose and give the minimal correct fix.",
    "A Celery task scheduled with eta=datetime.utcnow()+timedelta(minutes=30) fires 30 minutes too early for some workers. Explain the root cause and fix it.",
    "Our cache TTL uses entry_time = datetime.utcnow() and entries expire inconsistently across workers in different regions. What's wrong and what's the correct pattern?",
    "Converting an epoch with datetime.utcfromtimestamp(ts) then formatting it drops timezone information and downstream parsing breaks. Explain and fix.",
    "An API returns datetime.utcnow().isoformat() with no 'Z' or offset, so JavaScript clients parse it as local time. Diagnose and give the correct server-side fix.",
    "A rate limiter computes the window key from datetime.utcnow() and double-counts requests around the midnight UTC boundary. Explain the bug and fix it.",
    "Computing age with `age = datetime.utcnow() - user.birthdate` raises TypeError because birthdate is a date. Explain the naive/aware and date/datetime issues and fix it.",
    "Audit-log latency computed as datetime.utcnow() - event.received_at is occasionally negative. The received_at is timezone-aware. Diagnose the root cause and the fix.",
    "With Django USE_TZ=True we get 'RuntimeWarning: DateTimeField received a naive datetime' when saving datetime.utcnow(). Why, and what is the correct value to store?",
    "We check file staleness with `datetime.utcnow() - datetime.utcfromtimestamp(os.path.getmtime(p)) > timedelta(days=7)` and it's wrong across DST. Explain and fix.",
    "A retry backoff uses started = datetime.utcnow() and then `if datetime.utcnow() - started > timeout` but mixing with an aware deadline passed in from the caller raises a TypeError. Diagnose and fix.",
    "Our nightly job parses '2026-03-29T01:30:00+00:00', compares it to datetime.utcnow(), and fails only on DST-change nights. Explain the offset-naive vs offset-aware cause and the fix.",
    "We persist `expires = datetime.utcnow() + timedelta(hours=1)` and a worker in America/New_York reads it back and treats it as local, expiring sessions early. Diagnose and give the minimal correct fix.",
]

path = Path("benchmarks/tasks/python_debugging.jsonl")
existing = path.read_text(encoding="utf-8")
if not existing.endswith("\n"):
    existing += "\n"
lines = []
for i, p in enumerate(prompts, 1):
    rec = {
        "id": f"pyh{i:02d}",
        "domain": "python_debugging",
        "pattern": "tz_aware_datetime",
        "prompt": p,
        "split": "hard",
    }
    lines.append(json.dumps(rec))
path.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")
print(f"Appended {len(lines)} tz_aware_datetime tasks (split=hard). New total lines:",
      len([l for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]))
