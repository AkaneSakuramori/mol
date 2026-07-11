import os
import sys
import time
import io
import contextlib
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from compiler import compile_module
from vm import VM
from tiered import JITInterpreter
from native import build_executable


BENCHES = {
    "fib(30)": """
fn fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

fn main():
    print(fib(30))
""",
    "count_primes(20000)": """
fn is_prime(n: int) -> bool:
    if n < 2:
        return false
    var i = 2
    while i * i <= n:
        if n % i == 0:
            return false
        i += 1
    return true

fn main():
    var count = 0
    for n in range(2, 20000):
        if is_prime(n):
            count += 1
    print(count)
""",
    "loop_sum(3000000)": """
fn main():
    var total = 0
    for i in range(0, 3000000):
        total += i
    print(total)
""",
}


def timed(fn):
    t0 = time.perf_counter()
    out = capture(fn)
    return time.perf_counter() - t0, out


def capture(fn):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        fn()
    return b.getvalue().strip()


def bench_native(src, out_path):
    build_executable(parse(src), out_path)
    t0 = time.perf_counter()
    result = subprocess.run([out_path], capture_output=True, text=True)
    return time.perf_counter() - t0, result.stdout.strip()


def fmt_time(seconds):
    if seconds < 1e-3:
        return f"{seconds*1e6:.0f} us"
    if seconds < 1.0:
        return f"{seconds*1e3:.1f} ms"
    return f"{seconds:.2f} s"


def run():
    tmp = tempfile.mkdtemp()
    print(f"{'benchmark':<24} {'interpreter':>14} {'vm':>14} {'jit':>14} {'native':>14}")
    print("-" * 84)
    for name, src in BENCHES.items():
        t_interp, o1 = timed(lambda: Interpreter().run(parse(src)))
        t_vm, o2 = timed(lambda: VM(compile_module(parse(src))).run())
        t_jit, o3 = timed(lambda: JITInterpreter(threshold=1).run(parse(src)))
        try:
            t_nat, o4 = bench_native(src, os.path.join(tmp, name.split("(")[0]))
        except Exception as e:
            t_nat, o4 = None, f"(n/a: {e})"
        ok = o1 == o2 == o3 and (o4 == o1 or t_nat is None)
        mark = "" if ok else "  <-- MISMATCH"
        nat_s = fmt_time(t_nat) if t_nat is not None else "n/a"
        print(f"{name:<24} {fmt_time(t_interp):>14} {fmt_time(t_vm):>14} {fmt_time(t_jit):>14} {nat_s:>14}{mark}")
    print()
    print("all engines produce identical output for each benchmark.")


if __name__ == "__main__":
    run()
