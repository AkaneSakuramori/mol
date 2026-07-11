import os
import sys
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from parser import parse
from optimizer import optimize_module
import ast_nodes as ast

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")


CASES = [
    "const A = 2 + 3 * 4\n",
    "const B = 10 / 3\n",
    "const C = 10 % 3\n",
    "const D = 7 - 2 - 1\n",
    "const E = 2 < 3\n",
    "const F = 2 == 2\n",
    "const G = true and false\n",
    "const H = not true\n",
    "const I = 3 * (4 + 5)\n",
    "const J = -5 + 3\n",
    "const K = 1 + 2 == 3\n",
    "const L = 100\n",
    "const M = x + 1\n",
    'const N = "a" + "b"\n',
    "const O = 1 != 2\n",
    "const P = 5 >= 5\n",
    "const Q = (10 - 4) / 2\n",
    "const R = 2 * 3 + 4 * 5\n",
    "const S = true or false and false\n",
    "const T = not (1 < 2)\n",
    "const A = 1\nconst B = 2 + 3\nconst C = A\n",  # C references a name -> not constant here
]


def reference(src):
    tree = optimize_module(parse(src))
    out = []
    for d in tree.body:
        if isinstance(d, ast.Const):
            v = d.value
            if isinstance(v, ast.Int):
                r = str(v.value)
            elif isinstance(v, ast.Bool):
                r = "true" if v.value else "false"
            else:
                r = "?"
            out.append(f"{d.name} = {r}")
    return out


def selfhosted(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    ce = subprocess.run([sys.executable, ULANG, "run", "consteval.ul"],
                        cwd=workdir, capture_output=True, text=True)
    if ce.returncode != 0:
        raise RuntimeError("consteval: " + ce.stderr.strip())
    return [line for line in ce.stdout.splitlines() if line.strip()]


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "consteval.ul"), os.path.join(workdir, "consteval.ul"))
    failed = 0
    checked = 0

    for idx, src in enumerate(CASES):
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL case[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   case[{idx}]: {expected}")
        else:
            print(f"FAIL case[{idx}]: reference {expected}, self-hosted {actual}")
            failed += 1

    if not _fuzz(workdir):
        failed += 1
    checked += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 2 (constant evaluation): matches the reference")
    return 1 if failed else 0


def _fuzz(workdir, count=50, seed=11):
    import random
    rng = random.Random(seed)
    def expr(depth):
        if depth <= 0 or rng.random() < 0.4:
            return str(rng.randint(0, 20))
        op = rng.choice(["+", "-", "*", "/", "%", "<", ">", "==", "!="])
        a, b = expr(depth - 1), expr(depth - 1)
        return f"({a} {op} {b})"
    for _ in range(count):
        src = f"const K = {expr(rng.randint(1, 3))}\n"
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL fuzz: {e}")
            return False
        if actual != expected:
            print(f"FAIL fuzz on {src!r}: reference {expected}, self-hosted {actual}")
            return False
    print(f"ok   fuzz: {count} random constant expressions match the reference")
    return True


if __name__ == "__main__":
    sys.exit(run())
