import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from escape import analyze
from builtins_mod import UlangPanic


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def run_source(src):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(parse(src))
    return buf.getvalue().strip()


CONCURRENCY = [
    (open(os.path.join(EXAMPLES, "21_concurrency.ul")).read(), "110"),
    (open(os.path.join(EXAMPLES, "22_channels.ul")).read(), "60"),
    ("fn work(n: int) -> int:\n    return n + 1\nfn main():\n    let t = spawn(() => work(41))\n    print(t.await())\n", "42"),
    ("fn main():\n    let ch = channel()\n    ch.send(7)\n    print(ch.recv())\n", "7"),
]


ESCAPE = [
    ("fn f() -> int:\n    let x = [1, 2, 3]\n    return x.len()\n", "f", "x", "stack"),
    ("fn g() -> [int]:\n    let x = [1, 2, 3]\n    return x\n", "g", "x", "heap"),
    ("fn h() -> int:\n    let a = [1]\n    let b = [2]\n    return b.len()\n", "h", "a", "stack"),
]


def run():
    failed = 0
    for i, (src, expected) in enumerate(CONCURRENCY):
        try:
            got = run_source(src)
        except (UlangPanic, Exception) as e:
            print(f"FAIL concurrency {i}: {e}")
            failed += 1
            continue
        if got == expected:
            print(f"ok   concurrency {i}: {expected}")
        else:
            print(f"FAIL concurrency {i}: expected {expected!r}, got {got!r}")
            failed += 1

    for i, (src, fn, var, where) in enumerate(ESCAPE):
        results = analyze(parse(src))
        fe = results.get(fn)
        decisions = dict(fe.decisions()) if fe else {}
        if decisions.get(var) == where:
            print(f"ok   escape {i}: {var} -> {where}")
        else:
            print(f"FAIL escape {i}: expected {var} -> {where}, got {decisions}")
            failed += 1

    total = len(CONCURRENCY) + len(ESCAPE)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
