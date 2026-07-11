import os
import sys
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from parser import parse
from checker import check

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


CASES = [
    "fn main():\n    print(x)\n",
    "fn f(a: int) -> int:\n    return a + b + c\n",
    "fn main():\n    let x = 1\n    print(x)\n",
    "fn g(n: int) -> int:\n    return n\n",
    "fn main():\n    for i in range(0, 3):\n        print(i)\n    print(i)\n",
    "fn main():\n    match opt:\n        Some(v) => print(v)\n        None => print(w)\n",
    "fn main():\n    frob(1)\n",
    "fn main():\n    if true:\n        let y = 1\n    print(y)\n",
    "fn main():\n    let f = x => x + y\n    print(f)\n",
    "fn main():\n    let g = (a, b) => a + b + c\n    print(g)\n",
    "type P:\n    x: int\nfn main():\n    let p = P(1)\n    print(p)\n",
    "enum E:\n    A\n    B\nfn main():\n    print(A)\n    print(C)\n",
    "const K = 5\nfn main():\n    print(K)\n    print(J)\n",
    "fn main():\n    var s = 0\n    while cond:\n        s += step\n    print(s)\n",
    "fn main():\n    with open() as fh:\n        print(fh)\n    print(fh)\n",
    "fn a():\n    return helper()\nfn helper() -> int:\n    return 1\n",
    "fn main():\n    let (p, q) = pair\n    print(p + q + r)\n",
    "fn main():\n    match v:\n        Ok((m, n)) => print(m + n + missing)\n        Err(e) => print(e)\n",
    "import math\nfn main():\n    print(math)\n    print(other)\n",
    "fn main():\n    print(gc_collect())\n    print(is_list(x))\n",
]


def reference_undefined(src):
    errs = check(parse(src))
    return sorted(str(e).split(": ", 1)[-1].replace("undefined name ", "").strip("'")
                  for e in errs if "undefined name" in str(e))


def selfhosted_undefined(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    res = subprocess.run([sys.executable, ULANG, "run", "resolver.ul"],
                         cwd=workdir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("resolver: " + res.stderr.strip())
    names = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("undefined name"):
            names.append(line.replace("undefined name ", "").strip("'"))
    return sorted(names)


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "resolver.ul"), os.path.join(workdir, "resolver.ul"))
    failed = 0
    checked = 0

    for idx, src in enumerate(CASES):
        expected = reference_undefined(src)
        try:
            actual = selfhosted_undefined(src, workdir)
        except RuntimeError as e:
            print(f"FAIL case[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            label = ", ".join(expected) if expected else "(none)"
            print(f"ok   case[{idx}]: undefined = {label}")
        else:
            print(f"FAIL case[{idx}]: reference {expected}, self-hosted {actual}")
            failed += 1

    for path in sorted(_iter_examples()):
        name = os.path.basename(path)
        src = open(path).read()
        expected = reference_undefined(src)
        try:
            actual = selfhosted_undefined(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: name resolution matches reference")
        else:
            print(f"FAIL {name}: reference {expected}, self-hosted {actual}")
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 2 (name resolution): matches the reference")
    return 1 if failed else 0


def _iter_examples():
    import glob
    return glob.glob(os.path.join(EXAMPLES, "*.ul"))


if __name__ == "__main__":
    sys.exit(run())
