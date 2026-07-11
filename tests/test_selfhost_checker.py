import os
import sys
import shutil
import glob
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


TYPE_CASES = [
    # annotation mismatches
    'fn main():\n    let x: int = "hi"\n',
    'fn main():\n    let x: str = 5\n',
    'fn main():\n    let x: float = 5\n',
    'fn main():\n    let x: bool = 1\n',
    'fn main():\n    let x: int = true\n',
    # ok annotations (no error)
    'fn main():\n    let x: int = 5\n',
    'fn main():\n    let b: bool = true\n',
    'fn main():\n    let s: str = "a" + "b"\n',
    'fn main():\n    let x: int = 1 + 2\n',
    'fn main():\n    let x: bool = 1 < 2\n',
    'fn main():\n    let d: dyn = 5\n',            # dyn annotation is nominal -> mismatch
    # lists and elements
    'fn main():\n    let xs: [int] = [1, 2]\n',
    'fn main():\n    let xs: [int] = ["a"]\n',
    'fn main():\n    let xs: [str] = [1]\n',
    # optionals
    'fn main():\n    let o: int? = none\n',
    'fn main():\n    let o: int? = Some(1)\n',
    'fn main():\n    let x: int = none\n',
    # tuples
    'fn main():\n    let t: (int, str) = (1, 2)\n',
    'fn main():\n    let t: (int, int) = (1, 2)\n',
    # function return types
    'fn f() -> int:\n    return 1\nfn main():\n    let x: str = f()\n',
    'fn f() -> int:\n    return 1\nfn main():\n    let x: int = f()\n',
    # struct construction and field access
    'type P:\n    x: int\n    y: int\nfn main():\n    let p = P(1, 2)\n    let a: int = p.x\n',
    'type P:\n    x: int\nfn main():\n    let p = P(1)\n    let a: str = p.x\n',
    # generic return
    'fn f() -> Result[int, str]:\n    return Ok(1)\nfn main():\n    let r: Result[int, str] = f()\n',
    # try operator return type
    'fn f() -> Result[int, str]:\n    let x: int = g()?\n    return Ok(x)\nfn g() -> Result[int, str]:\n    return Ok(1)\n',
    # arith producing float
    'fn main():\n    let x: float = 1 + 2\n',       # int -> float mismatch
    'fn main():\n    let x: int = 1 * 2 * 3\n',
    # index into list / dict
    'fn main():\n    let xs = [1, 2]\n    let a: int = xs[0]\n',
    'fn main():\n    let xs = [1, 2]\n    let a: str = xs[0]\n',
    # mixed multi-error ordering
    'fn main():\n    let a: int = "x"\n    print(undef)\n    let b: str = 5\n',
    'fn main():\n    let x: int = missing + "s"\n',
    # nested/undefined in expressions
    'fn f(a: int) -> int:\n    return a + b + c\n',
    # var declarations do not error on annotation
    'fn main():\n    var x: int = "wrong"\n    print(x)\n',
    # --- name resolution / scope coverage (checker now owns resolution) ---
    "fn main():\n    for i in range(0, 3):\n        print(i)\n    print(i)\n",
    "fn main():\n    match opt:\n        Some(v) => print(v)\n        None => print(w)\n",
    "fn main():\n    if true:\n        let y = 1\n    print(y)\n",
    "fn main():\n    let f = x => x + y\n    print(f)\n",
    "fn main():\n    let g = (a, b) => a + b + c\n    print(g)\n",
    "enum E:\n    A\n    B\nfn main():\n    print(A)\n    print(C)\n",
    "const K = 5\nfn main():\n    print(K)\n    print(J)\n",
    "fn main():\n    with open() as fh:\n        print(fh)\n    print(fh)\n",
    "fn main():\n    let (p, q) = pair\n    print(p + q + r)\n",
    "fn main():\n    match v:\n        Ok((m, n)) => print(m + n + missing)\n        Err(e) => print(e)\n",
    "import math\nfn main():\n    print(math)\n    print(other)\n",
    # --- pattern validation (variant existence + arity) ---
    "enum E:\n    A\nfn main():\n    let e = A\n    match e:\n        Zzz => print(1)\n        A => print(2)\n",
    "enum E:\n    A(int)\nfn main():\n    let e = A(1)\n    match e:\n        A(x, y) => print(1)\n",
    "enum E:\n    A(int)\n    B\nfn main():\n    let e = B\n    match e:\n        A(x) => print(x)\n        B => print(0)\n",
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(a, b) => print(1)\n        None => print(0)\n",
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(v) => print(v)\n        None => print(0)\n",
    "fn main():\n    let r = Ok(1)\n    match r:\n        Ok(x) => print(x)\n        Err(e) => print(e)\n",
    "fn main():\n    match pair:\n        (a, b) => print(a)\n",
    # --- exhaustiveness checking ---
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(v) => print(v)\n",
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(v) => print(v)\n        None => print(0)\n",
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(v) => print(v)\n        _ => print(0)\n",
    "fn main():\n    let r = Ok(1)\n    match r:\n        Ok(x) => print(x)\n",
    "fn main():\n    let r = Ok(1)\n    match r:\n        Ok(x) => print(x)\n        Err(e) => print(e)\n",
    "enum E:\n    A\n    B\n    C\nfn main():\n    let e = A\n    match e:\n        A => print(1)\n        B => print(2)\n",
    "enum E:\n    A\n    B\nfn main():\n    let e = A\n    match e:\n        A => print(1)\n        B => print(2)\n",
    "fn main():\n    let o = Some(1)\n    match o:\n        Some(v) if v > 0 => print(v)\n        None => print(0)\n",
    "enum Sh:\n    Circle(float)\n    Rect(float, float)\n    Point\nfn area(s: Sh) -> float:\n    match s:\n        Circle(r) => 1.0\n        Rect(w, h) => 2.0\n        Point => 0.0\n",
    "enum Sh:\n    Circle(float)\n    Rect(float, float)\n    Point\nfn area(s: Sh) -> float:\n    match s:\n        Circle(r) => 1.0\n        Point => 0.0\n",
]


def _normalize(lines):
    # Inference-variable numbers (?N) come from a global counter in the reference
    # that persists across checks; the specific number is not a diagnostic guarantee.
    # Normalize every ?N to ?_ so structural equivalence is what is compared.
    import re
    return [re.sub(r"\?\d+", "?_", line) for line in lines]


def reference(src):
    return _normalize([str(e).split(": ", 1)[-1] for e in check(parse(src))])


def selfhosted(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    chk = subprocess.run([sys.executable, ULANG, "run", "checker.ul"],
                         cwd=workdir, capture_output=True, text=True)
    if chk.returncode != 0:
        raise RuntimeError("checker: " + chk.stderr.strip())
    return _normalize([line for line in chk.stdout.splitlines() if line.strip()])


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "checker.ul"), os.path.join(workdir, "checker.ul"))
    failed = 0
    checked = 0

    for idx, src in enumerate(TYPE_CASES):
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL type[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            summary = "; ".join(expected) if expected else "(clean)"
            print(f"ok   type[{idx}]: {summary}")
        else:
            print(f"FAIL type[{idx}]:")
            print(f"     reference:   {expected}")
            print(f"     self-hosted: {actual}")
            failed += 1

    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: type checking matches reference")
        else:
            print(f"FAIL {name}: reference {expected}, self-hosted {actual}")
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0 and _fuzz(workdir):
        print("self-hosting Stage 2 (type inference and checking): matches the reference")
        return 0
    return 1 if failed else 0


def _fuzz(workdir, count=40, seed=7):
    import random
    import re
    rng = random.Random(seed)
    types = ["int", "str", "bool", "float", "[int]", "int?", "(int, str)"]
    vals = ['5', '"s"', 'true', '1.5', '[1, 2]', 'none', '(1, 2)',
            '1 + 2', '"a" + "b"', '1 < 2']
    mism = 0
    for _ in range(count):
        stmts = []
        for j in range(rng.randint(1, 4)):
            stmts.append(f"    let v{j}: {rng.choice(types)} = {rng.choice(vals)}")
        src = "fn main():\n" + "\n".join(stmts) + "\n"
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL fuzz: {e}")
            mism += 1
            continue
        if actual != expected:
            print(f"FAIL fuzz on:\n{src}  reference={expected}\n  self-hosted={actual}")
            mism += 1
    if mism == 0:
        print(f"ok   fuzz: {count} random typed programs match the reference")
        return True
    return False


if __name__ == "__main__":
    sys.exit(run())
