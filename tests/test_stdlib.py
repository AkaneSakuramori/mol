import os
import sys
import io
import glob
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from formatter import format_source
from builtins_mod import UlangPanic


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def run_source(src):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(parse(src))
    return buf.getvalue().strip()


FFI_STDLIB = [
    ('extern fn sqrt(x: float) -> float from "m"\nfn main():\n    print(sqrt(9.0))\n', "3.0"),
    ('extern fn abs(x: int) -> int from "c"\nfn main():\n    print(abs(-5))\n', "5"),
    ('import math\nfn main():\n    print(math.floor(3.7))\n', "3"),
    ('import str\nfn main():\n    print(str.repeat("ab", 3))\n', "ababab"),
    ('from list import repeat\nfn main():\n    print(repeat(0, 4))\n', "[0, 0, 0, 0]"),
    ('import random\nfn main():\n    random.seed(1)\n    let x = random.int(0, 10)\n    print(x >= 0 and x < 10)\n', "true"),
]


def run():
    failed = 0
    for i, (src, expected) in enumerate(FFI_STDLIB):
        try:
            got = run_source(src)
        except (UlangPanic, Exception) as e:
            print(f"FAIL stdlib/ffi {i}: {e}")
            failed += 1
            continue
        if got == expected:
            print(f"ok   stdlib/ffi {i}: {expected}")
        else:
            print(f"FAIL stdlib/ffi {i}: expected {expected!r}, got {got!r}")
            failed += 1

    fmt_fail = 0
    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        src = open(path).read()
        try:
            once = format_source(src)
            parse(once)
            twice = format_source(once)
            if once != twice:
                fmt_fail += 1
        except Exception:
            fmt_fail += 1
    if fmt_fail == 0:
        print("ok   formatter: idempotent and reparses on all examples")
    else:
        print(f"FAIL formatter: {fmt_fail} examples failed")
        failed += 1

    total = len(FFI_STDLIB) + 1
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
