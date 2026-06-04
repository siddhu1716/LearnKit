#!/bin/bash
set -e

# run_eval.sh
# Runs the official SWE-bench evaluation harness on predictions.
# Each invocation uses a timestamped run_id so results are never skipped.

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [control|treatment]"
    exit 1
fi

ARM=$1
PREDS_FILE="benchmarks/swe_bench_lite/predictions_${ARM}.jsonl"
RUN_ID="pytest_${ARM}_$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$PREDS_FILE" ]; then
    echo "Error: Predictions file not found: $PREDS_FILE"
    exit 1
fi

# Remove previous result JSON so the report file name is deterministic
rm -f "learnkit_${ARM}.pytest_${ARM}*.json"

echo "Running SWE-bench evaluation on ${PREDS_FILE}  [run_id=${RUN_ID}]..."
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path "$PREDS_FILE" \
    --max_workers 4 \
    --run_id "${RUN_ID}"
