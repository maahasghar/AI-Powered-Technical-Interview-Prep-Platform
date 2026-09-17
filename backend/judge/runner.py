"""Runs only INSIDE the restricted judge container. Receives no expected answers."""

import contextlib
import json
import os
import sys

source, raw_input = sys.argv[1:]
namespace = {"__name__": "submission"}
# Ordinary debug prints are discarded; output is the JSON-serializable return value.
with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink):
    exec(  # noqa: S102 - runs only inside the isolated judge container
        compile(source, "submission.py", "exec"), namespace
    )
    answer = namespace["solve"](**json.loads(raw_input))
print(json.dumps(answer, allow_nan=False, separators=(",", ":")))
