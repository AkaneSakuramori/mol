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

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


CASES = [
    "pub fn a() -> int:\n    return 1\nfn b() -> int:\n    return 2\n",
    "pub type P:\n    x: int\ntype H:\n    y: int\n",
    "pub enum C:\n    Red\n    Green\nenum S:\n    S1\n    S2\n",
    "const V = 3\npub fn f():\n    print(1)\n",
    "fn only_private():\n    print(1)\n",
    "pub fn a():\n    print(1)\npub fn b():\n    print(2)\nconst K = 9\n",
    "import other\npub fn a():\n    print(1)\nextern fn ext() -> int from \"m\"\n",
    "pub enum E:\n    A(int)\n    B(int, str)\n    C\n",
    "trait T:\n    fn m(self) -> int\npub fn use_it():\n    print(1)\n",
]


def reference_exports(src):
    tree = parse(src)
    members = []
    for decl in tree.body:
        tn = type(decl).__name__
        if tn == "Function" and getattr(decl, "is_pub", False):
            members.append(decl.name)
        elif tn == "TypeDecl" and getattr(decl, "is_pub", False):
            members.append(decl.name)
        elif tn == "EnumDecl" and getattr(decl, "is_pub", False):
            for v in decl.variants:
                members.append(v.name)
        elif tn == "Const":
            members.append(decl.name)
    return members


def selfhosted_exports(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    ex = subprocess.run([sys.executable, ULANG, "run", "exports.ul"],
                        cwd=workdir, capture_output=True, text=True)
    if ex.returncode != 0:
        raise RuntimeError("exports: " + ex.stderr.strip())
    return [line for line in ex.stdout.splitlines() if line.strip()]


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "exports.ul"), os.path.join(workdir, "exports.ul"))
    failed = 0
    checked = 0

    for idx, src in enumerate(CASES):
        expected = reference_exports(src)
        try:
            actual = selfhosted_exports(src, workdir)
        except RuntimeError as e:
            print(f"FAIL case[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   case[{idx}]: exports = {expected}")
        else:
            print(f"FAIL case[{idx}]: reference {expected}, self-hosted {actual}")
            failed += 1

    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        expected = reference_exports(src)
        try:
            actual = selfhosted_exports(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: export set matches the loader")
        else:
            print(f"FAIL {name}: reference {expected}, self-hosted {actual}")
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 2 (visibility / package exports): matches the reference loader")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
