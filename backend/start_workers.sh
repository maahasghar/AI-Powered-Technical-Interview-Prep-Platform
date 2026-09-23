#!/usr/bin/env bash
set -Eeuo pipefail

judge_pid=""
feedback_pid=""

shutdown() {
    local exit_code="${1:-0}"

    trap - TERM INT
    if [[ -n "$judge_pid" ]]; then
        kill -TERM "$judge_pid" 2>/dev/null || true
    fi
    if [[ -n "$feedback_pid" ]]; then
        kill -TERM "$feedback_pid" 2>/dev/null || true
    fi
    wait "$judge_pid" 2>/dev/null || true
    wait "$feedback_pid" 2>/dev/null || true
    exit "$exit_code"
}

trap 'shutdown 0' TERM INT

python -m app.judge.worker &
judge_pid=$!
python -m app.feedback.worker &
feedback_pid=$!

# Both workers inherit stdout and stderr, keeping their logs visible to Railway.
set +e
wait -n "$judge_pid" "$feedback_pid"
exit_code=$?
set -e

printf 'A worker exited unexpectedly; stopping the combined worker service.\n' >&2
shutdown "$([[ "$exit_code" -eq 0 ]] && echo 1 || echo "$exit_code")"
