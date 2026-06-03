#!/bin/bash
set -e

# run_eval.sh
# Runs the official SWE-bench evaluation harness on predictions.

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [control|treatment]"
    exit 1
fi

ARM=$1
PREDS_FILE="benchmarks/swe_bench_lite/predictions_${ARM}.jsonl"

if [ ! -f "$PREDS_FILE" ]; then
    echo "Error: Predictions file not found: $PREDS_FILE"
    exit 1
fi

echo "Running SWE-bench evaluation on ${PREDS_FILE}..."
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path "$PREDS_FILE" \
    --max_workers 4 \
    --run_id "pytest_${ARM}"
