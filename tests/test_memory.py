import os
import sys
import io
import subprocess
import tempfile
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from gc_heap import GcHeap, YOUNG, OLD
from parser import parse
from interpreter import Interpreter


class Node:
    def __init__(self, name):
        self.name = name
        self.refs = []


def _trace(o):
    return o.refs if isinstance(o, Node) else []


def run_ulang(src, env=None):
    buf = io.StringIO()
    it = Interpreter()
    with contextlib.redirect_stdout(buf):
        it.run(parse(src))
    return buf.getvalue().strip()


def test_reclaim_unreachable():
    roots = []
    h = GcHeap(_trace, roots_fn=lambda: roots, young_threshold=1 << 30)
    a, b = Node("a"), Node("b")
    h.allocate(a); h.allocate(b)
    roots.append(a)
    r = h.collect(full=True)
    assert r == 1 and len(h.records) == 1
    return "gc core: unreachable objects reclaimed"


def test_cycle_collection():
    roots = []
    h = GcHeap(_trace, roots_fn=lambda: roots, young_threshold=1 << 30)
    x, y = Node("x"), Node("y")
    x.refs.append(y); y.refs.append(x)
    h.allocate(x); h.allocate(y)
    assert h.collect(full=True) == 2
    assert len(h.records) == 0
    return "gc core: cycles collected (beyond refcounting)"


def test_generational_promotion():
    roots = []
    h = GcHeap(_trace, roots_fn=lambda: roots, young_threshold=1 << 30)
    g = Node("g"); roots.append(g); h.allocate(g)
    h.collect(full=False); h.collect(full=False)
    assert h.records[id(g)].gen == OLD
    return "gc core: survivors promoted to old generation"


def test_minor_keeps_old_to_young():
    roots = []
    h = GcHeap(_trace, roots_fn=lambda: roots, young_threshold=1 << 30)
    old = Node("old"); roots.append(old); h.allocate(old)
    h.collect(full=False); h.collect(full=False)
    child = Node("child"); old.refs.append(child); h.allocate(child)
    h.collect(full=False)
    assert id(child) in h.records
    return "gc core: minor collection follows old->young references"


def test_incremental_matches():
    roots = []
    h = GcHeap(_trace, roots_fn=lambda: roots, young_threshold=1 << 30)
    nodes = [Node(str(i)) for i in range(40)]
    for n in nodes:
        h.allocate(n)
    for i in range(39):
        nodes[i].refs.append(nodes[i + 1])
    roots.append(nodes[0])
    steps = 0
    while not h.collect_step(budget=4):
        steps += 1
    assert len(h.records) == 40 and steps > 1
    return "gc core: incremental marking within a bounded budget"


def test_interpreter_reclaims():
    out = run_ulang(
        "fn main():\n"
        "    gc_enable()\n"
        "    var i = 0\n"
        "    while i < 80:\n"
        "        let junk = [i, i, i]\n"
        "        i += 1\n"
        "    print(gc_collect())\n"
    )
    assert out == "80", out
    return "interpreter: dead allocations reclaimed via gc_collect"


def test_live_data_survives():
    out = run_ulang(
        "fn main():\n"
        "    gc_enable()\n"
        "    let keep = [10, 20, 30]\n"
        "    var i = 0\n"
        "    while i < 40:\n"
        "        let junk = [i]\n"
        "        i += 1\n"
        "    gc_collect()\n"
        "    print(keep[0] + keep[1] + keep[2])\n"
    )
    assert out == "60", out
    return "interpreter: reachable data survives collection"


def test_semantics_unchanged():
    src = ("fn fib(n: int) -> int:\n"
           "    if n < 2:\n        return n\n    return fib(n-1) + fib(n-2)\n"
           "fn main():\n    print(fib(15))\n")
    a = run_ulang(src)
    os.environ["ULANG_GC"] = "1"
    b = run_ulang(src)
    os.environ.pop("ULANG_GC", None)
    assert a == b == "610"
    return "semantics: output identical with GC on and off"


def _have_native():
    try:
        import platform_abi
        import llvmlite  # noqa: F401
        return platform_abi.find_c_compiler() is not None
    except ImportError:
        return False


def test_native_gc_runtime():
    if not _have_native():
        return "native runtime: skipped (no C compiler)"
    runtime = os.path.join(ROOT, "runtime")
    exe = tempfile.mktemp()
    r = subprocess.run(
        ["gcc", "-O2", os.path.join(runtime, "test_gc.c"),
         os.path.join(runtime, "ulang_gc.c"), "-I", runtime, "-o", exe],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    run = subprocess.run([exe], capture_output=True, text=True)
    os.unlink(exe)
    assert run.returncode == 0 and "OK" in run.stdout
    return "native runtime: C mark-sweep GC reclaims garbage and cycles"


def test_native_binary_links_gc():
    if not _have_native():
        return "native backend: skipped (no C compiler)"
    from native import build_executable
    exe = tempfile.mktemp()
    src = "fn main():\n    print(21 + 21)\n"
    build_executable(parse(src), exe)
    run = subprocess.run([exe], capture_output=True, text=True)
    syms = subprocess.run(["nm", exe], capture_output=True, text=True).stdout
    os.unlink(exe)
    if os.path.exists(exe + ".ll"):
        os.unlink(exe + ".ll")
    assert run.stdout.strip() == "42"
    assert "ul_gc_init" in syms
    return "native backend: binaries link and initialize the GC runtime"


TESTS = [
    test_reclaim_unreachable,
    test_cycle_collection,
    test_generational_promotion,
    test_minor_keeps_old_to_young,
    test_incremental_matches,
    test_interpreter_reclaims,
    test_live_data_survives,
    test_semantics_unchanged,
    test_native_gc_runtime,
    test_native_binary_links_gc,
]


def run():
    failed = 0
    for t in TESTS:
        try:
            print("ok   " + t())
        except Exception as e:
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    total = len(TESTS)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
