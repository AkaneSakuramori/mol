import sys
import threading


_DESIRED_STACK = 256 * 1024 * 1024


def run_with_large_stack(fn):
    result = {}

    def worker():
        try:
            sys.setrecursionlimit(200000)
            result["value"] = fn()
        except BaseException as e:
            result["error"] = e

    previous = None
    try:
        previous = threading.stack_size(_DESIRED_STACK)
    except (ValueError, RuntimeError, OverflowError):
        previous = None

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    if previous is not None:
        try:
            threading.stack_size(previous)
        except (ValueError, RuntimeError):
            pass

    if "error" in result:
        raise result["error"]
    return result.get("value")
