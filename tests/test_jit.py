import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from tiered import JITInterpreter
from builtins_mod import UlangPanic




def capture(fn):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        fn()
    return b.getvalue().strip()


JIT_CASES = [
    """
fn fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
fn main():
    print(fib(20))
""",
    """
fn mul(a: int, b: int) -> int:
    return a * b
fn main():
    var s = 0
    for i in range(0, 100):
        s += mul(i, 2)
    print(s)
""",
    """
fn area(r: float) -> float:
    return 3.14 * r * r
fn main():
    var i = 0
    while i < 10:
        print(area(2.0))
        i += 1
""",
]


def run():
    failed = 0

    for i, src in enumerate(JIT_CASES):
        interp_out = capture(lambda: Interpreter().run(parse(src)))
        jit = JITInterpreter(threshold=1)
        jit_out = capture(lambda: jit.run(parse(src)))
        if interp_out == jit_out and jit.jit_stats["native_calls"] > 0:
            print(f"ok   jit {i}: matches interpreter, {jit.jit_stats['native_calls']} native calls")
        elif interp_out == jit_out:
            print(f"ok   jit {i}: matches interpreter (no promotion)")
        else:
            print(f"FAIL jit {i}: interp={interp_out!r} jit={jit_out!r}")
            failed += 1

    total = len(JIT_CASES)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
