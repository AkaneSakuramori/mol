import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from compiler import compile_module
from vm import VM
from builtins_mod import UlangPanic


PURE = [
    "01_hello", "02_functions", "03_interpolation", "04_control_flow",
    "05_loops", "06_higher_order", "08_enums_match", "09_result",
    "10_option", "12_closures", "13_generics", "15_dicts",
    "16_tuples", "18_recursion", "19_const_ternary",
]

EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def capture(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


def run():
    failed = 0
    for name in PURE:
        path = os.path.join(EXAMPLES, name + ".ul")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = parse(source)
        try:
            interp_out = capture(lambda: Interpreter().run(parse(source)))
            vm_out = capture(lambda: VM(compile_module(parse(source))).run())
        except UlangPanic as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        if interp_out != vm_out:
            print(f"FAIL {name}: divergence")
            print(f"  interp: {interp_out!r}")
            print(f"  vm:     {vm_out!r}")
            failed += 1
        else:
            print(f"ok   {name}: interpreter == vm")
    total = len(PURE)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
