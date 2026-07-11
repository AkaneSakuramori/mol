import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from interpreter import Interpreter
from builtins_mod import UlangPanic


def run_source(src):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        Interpreter().run(parse(src))
    return b.getvalue().strip()


DOC_SNIPPETS = [
    ('fn greet(name: str) -> str:\n    return "hello, ${name}"\nfn main():\n    print(greet("world"))\n', "hello, world"),
    ('fn main():\n    let label = "pass" if 72 >= 50 else "fail"\n    print(label)\n', "pass"),
    ('fn main():\n    print([1, 2, 3, 4].map(n => n * n))\n', "[1, 4, 9, 16]"),
    ('fn main():\n    print([1, 2, 3].reduce((a, b) => a + b, 0))\n', "6"),
    ('fn main():\n    print("a,b,c".split(","))\n', '["a", "b", "c"]'),
    ('fn main():\n    let s = {"ada": 90}\n    print(s.get("bob"))\n', "None"),
    ('fn main():\n    let x = Some(5)\n    print(x.unwrap_or(0))\n', "5"),
    ('import math\nfn main():\n    print(math.sqrt(144.0))\n', "12.0"),
    ('extern fn strlen(s: str) -> int from "c"\nfn main():\n    print(strlen("hello"))\n', "5"),
    ('fn work(n: int) -> int:\n    return n * n\nfn main():\n    let t = spawn(() => work(6))\n    print(t.await())\n', "36"),
    ('fn producer(ch: dyn, n: int):\n    for i in range(0, n):\n        ch.send(i * i)\nfn main():\n    let ch = channel()\n    with nursery() as g:\n        g.spawn(() => producer(ch, 5))\n        var sum = 0\n        for i in range(0, 5):\n            sum += ch.recv()\n        print(sum)\n', "30"),
]


def run():
    failed = 0
    for i, (src, expected) in enumerate(DOC_SNIPPETS):
        try:
            got = run_source(src)
        except (UlangPanic, Exception) as e:
            print(f"FAIL doc {i}: {e}")
            failed += 1
            continue
        if got == expected:
            print(f"ok   doc {i}: {expected}")
        else:
            print(f"FAIL doc {i}: expected {expected!r}, got {got!r}")
            failed += 1
    total = len(DOC_SNIPPETS)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
