#!/usr/bin/env bash
# One full scored run:  ./run.sh NN-name   (for example ./run.sh 02-iso-dates)
# Calls the API once per message in sample_messages.txt, so it costs credit.
set -euo pipefail
cd "$(dirname "$0")"

name="${1:?usage: ./run.sh NN-name   (for example ./run.sh 02-iso-dates)}"
out="runs/$name.txt"

if [[ -e "$out" ]]; then
    echo "$out already exists. Pick a new name." >&2
    exit 1
fi
if ! git diff --quiet HEAD -- parse_order.py sample_messages.txt; then
    echo "parse_order.py or sample_messages.txt has uncommitted changes." >&2
    echo "Commit first, so the commit in the log is the code that made this run." >&2
    exit 1
fi

mkdir -p runs
{
    echo "commit: $(git rev-parse --short HEAD)  date: $(date +%F)"
    start=$(date +%s)
    # parse_order.py exits 1 if any message failed; the checker reports those.
    python -u parse_order.py --file sample_messages.txt 2>&1 || true
    echo "elapsed: $(( $(date +%s) - start ))s"
} | tee "$out"

python check_run.py "$out" --write
echo "Now judge the rows with a blank Pass in LOG.md, then fill in Score and Failed." >&2
