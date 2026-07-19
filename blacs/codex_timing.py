"""Small helpers for temporary, structured BLACS timing measurements."""

import json
import os
import time


TIMING_PREFIX = "CODEX_TIMING "


def log_event(logger, event, shot_file=None, **fields):
    """Write one wall-clock timestamp that can be compared across processes."""
    payload = {
        "event": event,
        "pid": os.getpid(),
        "run_id": os.environ.get("BLACS_TIMING_RUN_ID", "unset").strip(),
        "time_ns": time.time_ns(),
    }
    if shot_file is not None:
        payload["shot_file"] = str(shot_file)
    payload.update(fields)
    logger.info("%s%s", TIMING_PREFIX, json.dumps(payload, sort_keys=True))
