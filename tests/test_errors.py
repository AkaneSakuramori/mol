import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse, ParseError
from interpreter import Interpreter
from compiler import compile_module
from vm import VM
from builtins_mod import UlangPanic


def expect_panic(src, needle):
    try:
        Interpreter().run(parse(src))
    except UlangPanic as e:
        return needle in e.message
    return False


def expect_panic_vm(src, needle):
    try:
        VM(compile_module(parse(src))).run()
    except UlangPanic as e:
        return needle in e.message
    return False


def expect_parse_error(src, needle):
    try:
        parse(src)
    except ParseError as e:
        return needle in str(e)
    return False


PANIC_CASES = [
    ("fn main():\n    print([1, 2][9])\n", "out of range"),
    ("fn main():\n    print(\"ab\"[9])\n", "out of range"),
    ("fn main():\n    print(\"a\" + 1)\n", "cannot add"),
    ("fn main():\n    print(1 - \"x\")\n", "needs numbers"),
    ("fn main():\n    print(5 % 0)\n", "modulo by zero"),
    ("fn main():\n    print(5 / 0)\n", "division by zero"),
    ("fn main():\n    print(1 < \"a\")\n", "cannot compare"),
    ("fn f(n: int) -> int:\n    return f(n + 1)\nfn main():\n    print(f(0))\n", "stack overflow"),
    ("fn main():\n    print(undefined_thing)\n", "undefined name"),
    ("fn main():\n    let d = {1: 2}\n    print(d[9])\n", "key not found"),
]

PARSE_CASES = [
    ("fn main()\n    print(1)\n", "expected ':'"),
    ("fn main():\n    print(1\n", "expected ')'"),
]


def run():
    failed = 0
    for src, needle in PANIC_CASES:
        ok_i = expect_panic(src, needle)
        ok_v = expect_panic_vm(src, needle)
        if ok_i and ok_v:
            print(f"ok   panic: {needle!r} (interp + vm)")
        else:
            print(f"FAIL panic: {needle!r} interp={ok_i} vm={ok_v}")
            failed += 1

    for src, needle in PARSE_CASES:
        if expect_parse_error(src, needle):
            print(f"ok   parse error: {needle!r}")
        else:
            print(f"FAIL parse error: {needle!r}")
            failed += 1

    line_ok = False
    try:
        Interpreter().run(parse("fn main():\n    let a = 1\n    print(a + b)\n"))
    except UlangPanic as e:
        line_ok = "line 3" in e.message
    print("ok   panic reports line" if line_ok else "FAIL panic line")
    if not line_ok:
        failed += 1

    total = len(PANIC_CASES) + len(PARSE_CASES) + 1
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
