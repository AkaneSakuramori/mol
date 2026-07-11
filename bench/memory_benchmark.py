import os
import sys
import io
import time
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter


WORKLOADS = {
    "scalar fib(26)":
        "fn fib(n: int) -> int:\n"
        "    if n < 2:\n        return n\n    return fib(n-1) + fib(n-2)\n"
        "fn main():\n    print(fib(26))\n",
    "100k short-lived lists":
        "fn main():\n    var s = 0\n"
        "    for i in range(0, 100000):\n        let t = [i, i]\n        s += t[0]\n"
        "    print(s)\n",
    "struct churn 50k":
        "type P:\n    x: int\n    y: int\n"
        "fn main():\n    var s = 0\n"
        "    for i in range(0, 50000):\n        let p = P(i, i)\n        s += p.x\n"
        "    print(s)\n",
}


def measure(src, gc_on):
    buf = io.StringIO()
    start = time.perf_counter()
    with contextlib.redirect_stdout(buf):
        interp = Interpreter()
        interp.memory.enabled = gc_on
        interp.memory.auto = gc_on
        interp.run(parse(src))
    elapsed = time.perf_counter() - start
    stats = interp.memory.stats() if gc_on else None
    return elapsed, stats


def run():
    print(f"{'workload':<26} {'gc off':>10} {'gc on':>10} {'overhead':>9}   {'allocated':>10} {'reclaimed':>10}")
    print("-" * 90)
    for name, src in WORKLOADS.items():
        off, _ = measure(src, False)
        on, stats = measure(src, True)
        overhead = 100 * (on - off) / off if off else 0
        alloc = stats["total_allocated"] if stats else 0
        recl = stats["objects_reclaimed"] if stats else 0
        print(f"{name:<26} {off*1000:>8.1f}ms {on*1000:>8.1f}ms {overhead:>7.1f}%   {alloc:>10} {recl:>10}")
    print()
    print("gc off = default (no tracking); gc on = tracing GC enabled (ULANG_GC=1).")


if __name__ == "__main__":
    run()
