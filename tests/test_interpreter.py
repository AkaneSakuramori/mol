import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from builtins_mod import UlangPanic
import io
import contextlib


CASES = [
    ("const x = 2 + 3 * 4\nfn main():\n    print(x)\n", "14"),
    ("fn main():\n    print(10 / 3)\n", "3"),
    ("fn main():\n    print(10.0 / 4.0)\n", "2.5"),
    ("fn main():\n    let s = [1, 2, 3].map(x => x * 2)\n    print(s)\n", "[2, 4, 6]"),
    ("fn main():\n    let t = [1, 2, 3, 4].filter(x => x % 2 == 0)\n    print(t)\n", "[2, 4]"),
    ("fn main():\n    print([1, 2, 3].reduce((a, b) => a + b, 0))\n", "6"),
    ("fn main():\n    let r = \"a,b,c\".split(\",\")\n    print(r.len())\n", "3"),
    ("fn main():\n    print(\"HELLO\".lower())\n", "hello"),
    ("fn main():\n    var n = 0\n    for i in range(1, 5):\n        n += i\n    print(n)\n", "10"),
    ("fn f(x: int) -> int:\n    return x * x\nfn main():\n    print(f(6))\n", "36"),
    ("enum C:\n    A\n    B\nfn main():\n    match B:\n        A => print(\"a\")\n        B => print(\"b\")\n", "b"),
    ("fn main():\n    let x = 5 if true else 9\n    print(x)\n", "5"),
    ("fn main():\n    let d = {\"a\": 1, \"b\": 2}\n    print(d[\"b\"])\n", "2"),
    ("fn g() -> int?:\n    return Some(7)\nfn main():\n    match g():\n        Some(v) => print(v)\n        None => print(\"no\")\n", "7"),
    ("fn h(b: int) -> Result[int, str]:\n    if b == 0:\n        return Err(\"zero\")\n    return Ok(100 / b)\nfn main():\n    match h(0):\n        Ok(v) => print(v)\n        Err(e) => print(e)\n", "zero"),
]


def run_source(src):
    tree = parse(src)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(tree)
    return buf.getvalue().strip()


def run():
    failed = 0
    for i, (src, expected) in enumerate(CASES):
        try:
            got = run_source(src)
        except (UlangPanic, Exception) as e:
            print(f"FAIL case {i}: raised {e}")
            failed += 1
            continue
        if got != expected:
            print(f"FAIL case {i}: expected {expected!r}, got {got!r}")
            failed += 1
        else:
            print(f"ok   case {i}: {expected!r}")
    total = len(CASES)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
