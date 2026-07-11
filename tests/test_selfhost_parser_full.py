import os
import sys
import glob
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from parser import parse
from ast_serialize import serialize_module


PARSER_UL = os.path.join(ROOT, "selfhost", "parser_full.ul")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


STRESS = [
    # traits, generics with bounds, impl, derives
    "pub trait Shape:\n    fn area(self) -> float\n    fn name(self) -> str\n",
    "pub type Box[T]:\n    value: T\nderive(Display, Clone)\n",
    "impl Shape for Circle[int]:\n    pub fn area(self) -> float:\n        return 1.0\n    fn name(self) -> str:\n        return \"c\"\n",
    # complex types
    "fn f(a: [int?], b: {str: int}, c: fn(int, str) -> bool, d: (int, str)) -> dyn:\n    return a\n",
    "fn g[T: Ord + Eq + Clone](x: T) -> T?:\n    return Some(x)\n",
    # patterns: nested variant, tuple, guards, wildcard, literals
    "fn h(v: dyn):\n    match v:\n        Some((a, b)) if a > 0 => print(a)\n        Ok(x) => print(x)\n        None => print(1)\n        0 => print(2)\n        _ => print(3)\n",
    # lambdas: typed params, block body, multi-arg
    "fn i():\n    let a = x => x + 1\n    let b = (x: int, y: int) => x * y\n    let c = () => {\n        let z = 1\n        return z\n    }\n",
    # control flow with elif chains, nested blocks
    "fn j(n: int) -> int:\n    if n < 0:\n        return 0\n    elif n == 0:\n        return 1\n    elif n < 10:\n        return 2\n    else:\n        return 3\n",
    # with/defer, for over ranges, while, break/continue
    "fn k():\n    with open() as fh:\n        defer close()\n        for x in items:\n            if x == 0:\n                continue\n            break\n    while true:\n        break\n",
    # assignments (all ops), index/attr targets
    "fn l():\n    var a = 0\n    a += 1\n    a -= 2\n    a *= 3\n    a /= 4\n    a %= 5\n    obj.field = 1\n    arr[0] = 2\n",
    # imports (all forms), const, extern
    "import a\nimport a.b.c\nimport x as y\nfrom m import p, q, r\nconst PI = 3\nextern fn sqrt(x: float) -> float from \"m\"\n",
    # expressions: precedence, ternary, calls, chains, collections
    "fn m():\n    let a = 1 + 2 * 3 - 4 / 5 % 6\n    let b = x if c and d or not e else y\n    let c2 = f(g(1), h(x = 2))\n    let d = obj.a.b[0].c(1)?\n    let e = [1, 2, 3]\n    let f2 = {\"a\": 1, \"b\": 2}\n    let g2 = (1, 2, 3)\n    let h2 = -x + -y\n",
    # enum with mixed payloads
    "enum E:\n    A\n    B(int)\n    C(int, str, float)\nderive(Eq)\n",
    # tuple patterns in let and for
    "fn n():\n    let (a, b) = point\n    let (x, y, z) = triple\n    for (k, v) in pairs:\n        print(k)\n",
]


def reference(src):
    return serialize_module(parse(src))


def ulang(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    result = subprocess.run(
        [sys.executable, ULANG, "run", "parser_full.ul"],
        cwd=workdir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.rstrip("\n")


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(PARSER_UL, os.path.join(workdir, "parser_full.ul"))
    failed = 0
    checked = 0

    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        expected = reference(src)
        try:
            actual = ulang(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: AST matches reference")
        else:
            print(f"FAIL {name}: AST differs")
            _first_diff(expected, actual)
            failed += 1

    for idx, src in enumerate(STRESS):
        expected = reference(src)
        try:
            actual = ulang(src, workdir)
        except RuntimeError as e:
            print(f"FAIL stress[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   stress[{idx}]: AST matches reference")
        else:
            print(f"FAIL stress[{idx}]: AST differs")
            _first_diff(expected, actual)
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 1: the Ulang parser produces syntax trees identical to the reference")

    if not _malformed_terminates(workdir):
        return 1
    return 1 if failed else 0


MALFORMED = [
    "fn main(\n",
    "fn main():\n",
    "fn f(x) -> :\n",
    "type T:\n",
    "let = 5\n",
    "@#$%\n",
]


def _malformed_terminates(workdir):
    ok = True
    for src in MALFORMED:
        with open(os.path.join(workdir, "input.ul"), "w") as f:
            f.write(src)
        try:
            result = subprocess.run(
                [sys.executable, ULANG, "run", "parser_full.ul"],
                cwd=workdir, capture_output=True, text=True, timeout=20,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL malformed hang: {src!r}")
            ok = False
            continue
        if b"Traceback" in result.stderr.encode():
            print(f"FAIL malformed host crash: {src!r}")
            ok = False
    if ok:
        print("robustness: malformed input terminates cleanly (no hang, no host crash)")
    return ok


def _first_diff(expected, actual):
    e = expected.split()
    a = actual.split()
    for i in range(min(len(e), len(a))):
        if e[i] != a[i]:
            print(f"     token {i}: reference {e[i]!r}, ulang {a[i]!r}")
            return
    if len(e) != len(a):
        print(f"     length {len(a)} vs {len(e)}")


if __name__ == "__main__":
    sys.exit(run())
