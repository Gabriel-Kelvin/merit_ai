from __future__ import annotations

import queue
import threading


def call_with_deadline(call, timeout_seconds: float):
    """Run a synchronous provider call behind a true wall-clock deadline."""
    outcome: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            outcome.put((True, call()), block=False)
        except BaseException as exc:
            outcome.put((False, exc), block=False)

    threading.Thread(target=run, daemon=True, name="bounded-provider-call").start()
    try:
        succeeded, value = outcome.get(timeout=timeout_seconds)
    except queue.Empty as exc:
        raise TimeoutError(f"Provider exceeded {timeout_seconds:g} seconds") from exc
    if succeeded:
        return value
    raise value
