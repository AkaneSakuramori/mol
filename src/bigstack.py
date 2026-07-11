import sys
import threading


_STACK_SIZES = [256 * 1024 * 1024, 128 * 1024 * 1024, 64 * 1024 * 1024, 32 * 1024 * 1024]

_BYTES_PER_FRAME = 12 * 2048

GRANTED_STACK = 8 * 1024 * 1024


def _set_large_stack():
    for size in _STACK_SIZES:
        try:
            previous = threading.stack_size(size)
            return previous, size
        except (ValueError, RuntimeError, OverflowError):
            continue
    return None, None


def safe_max_depth(requested):
    budget = int(GRANTED_STACK * 0.55 / _BYTES_PER_FRAME)
    return max(200, min(requested, budget))


def python_recursion_limit():
    return max(4000, int(GRANTED_STACK * 0.7 / 2048))


def run_with_large_stack(fn):
    global GRANTED_STACK
    result = {}

    def worker():
        try:
            result["value"] = fn()
        except BaseException as e:
            result["error"] = e

    previous, size = _set_large_stack()
    if size:
        GRANTED_STACK = size

    old_limit = sys.getrecursionlimit()
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    if previous is not None:
        try:
            threading.stack_size(previous)
        except (ValueError, RuntimeError):
            pass
    sys.setrecursionlimit(old_limit)

    if "error" in result:
        raise result["error"]
    return result.get("value")
