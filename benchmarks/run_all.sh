#!/usr/bin/env bash
# One-shot benchmark launcher for the new P0 + P1 changes
# (auto_promote, last_attribution, generality gate, harmful-hits demotion).
#
# Usage on the Linux box that has the venv + can reach the model server:
#
#   export LEARNKIT_API_BASE="https://b3143e205d30f1.lhr.life/v1"
#   export LEARNKIT_AGENT_MODEL="Qwen/Qwen2.5-72B-Instruct"
#   export ANTHROPIC_API_KEY="sk-ant-..."   # for the LLM judge / distiller
#   bash benchmarks/run_all.sh
#
# If you have a venv at .venv/, this script will use it. Otherwise it falls
# back to `python` on PATH.

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

# ---- pick a python interpreter ------------------------------------------------
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    PY="python"
fi
echo "Using interpreter: $PY"
"$PY" --version

# ---- model + server env -------------------------------------------------------
: "${LEARNKIT_API_BASE:=http://localhost:8001/v1}"
: "${LEARNKIT_AGENT_MODEL:=openai/Qwen/Qwen2.5-72B-Instruct}"
# litellm needs the openai/ prefix to route to an OpenAI-compatible endpoint
case "$LEARNKIT_AGENT_MODEL" in
    openai/*) ;;
    *) LEARNKIT_AGENT_MODEL="openai/$LEARNKIT_AGENT_MODEL" ;;
esac
export LEARNKIT_API_BASE LEARNKIT_AGENT_MODEL

echo "API base : $LEARNKIT_API_BASE"
echo "Model    : $LEARNKIT_AGENT_MODEL"

# ---- sanity-ping the model server --------------------------------------------
echo
echo "==> Pinging model server..."
curl -fsS -m 15 "$LEARNKIT_API_BASE/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${LEARNKIT_AGENT_MODEL#openai/}\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":4}" \
    > /tmp/learnkit_ping.json || { echo "Model server unreachable. Aborting."; exit 2; }
echo "OK: $(head -c 200 /tmp/learnkit_ping.json)"
echo

RUN_TS="$(date +%Y%m%d_%H%M%S)"
OUT_ROOT="benchmarks/results/all_${RUN_TS}"
mkdir -p "$OUT_ROOT"
echo "Output root: $OUT_ROOT"

# ---- 1. unit tests ------------------------------------------------------------
echo
echo "==> [1/4] Running unit tests"
"$PY" -m pytest tests -q 2>&1 | tee "$OUT_ROOT/pytest.log" || {
    echo "Unit tests failed. Aborting benchmark."
    exit 3
}

# ---- 2. retrieval eval (no model calls, fast) --------------------------------
echo
echo "==> [2/4] retrieval_eval.py"
"$PY" benchmarks/retrieval_eval.py --json > "$OUT_ROOT/retrieval_eval.json"
"$PY" benchmarks/retrieval_eval.py | tee "$OUT_ROOT/retrieval_eval.md"

# ---- 3. PBE bench -------------------------------------------------------------
echo
echo "==> [3/4] PBEBench-Lite (20 tasks x 3 arms)"
"$PY" benchmarks/run_pbebench.py --limit 20 2>&1 | tee "$OUT_ROOT/pbe.log"

# ---- 4. SLR bench -------------------------------------------------------------
echo
echo "==> [4/4] SLR-Bench (20 tasks x 3 arms)"
"$PY" benchmarks/run_slr_bench.py --limit 20 2>&1 | tee "$OUT_ROOT/slr.log"

# ---- attribution report -------------------------------------------------------
echo
echo "==> Building attribution summary"
"$PY" - <<'PY' > "$OUT_ROOT/attribution_summary.md"
"""Quick post-run attribution report so we can verify auto_promote is working
(i.e. SkillRecords appear as the primary record once a few tasks have run)."""
import json, glob, os, collections, sys

ROOT = os.environ.get("OUT_ROOT", ".")
runs = []
for name in ("pbe", "slr"):
    matches = sorted(glob.glob(f"benchmarks/results/{name}_*/raw.json"))
    if matches:
        runs.append((name, matches[-1]))

print("# Attribution Summary\n")
for name, path in runs:
    print(f"## {name} — `{path}`\n")
    data = json.loads(open(path).read())
    by_arm = collections.defaultdict(list)
    for row in data:
        by_arm[row["arm"]].append(row)
    print("| Arm | tasks | mean ctx chars | primary type histogram | mean #records |")
    print("|---|---|---|---|---|")
    for arm, rows in sorted(by_arm.items()):
        ctx = [r.get("learnkit_context_chars", 0) for r in rows]
        attr_rows = [r.get("attribution") or {} for r in rows]
        primaries = collections.Counter(a.get("primary_record_type") or "—" for a in attr_rows)
        nrecs = [a.get("records_retrieved", 0) for a in attr_rows]
        hist = ", ".join(f"{k}={v}" for k, v in sorted(primaries.items()))
        mean_ctx = sum(ctx) / len(ctx) if ctx else 0
        mean_n = sum(nrecs) / len(nrecs) if nrecs else 0
        print(f"| {arm} | {len(rows)} | {mean_ctx:.0f} | {hist} | {mean_n:.1f} |")
    print()
PY
cat "$OUT_ROOT/attribution_summary.md"

echo
echo "===================================================================="
echo "Done. All artifacts in: $OUT_ROOT"
echo "===================================================================="
