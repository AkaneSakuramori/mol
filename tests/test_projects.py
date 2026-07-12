"""Regression test for the reference Ulang projects under projects/.

Each project is a substantial, self-contained Ulang program. This test pins its output
and verifies it runs identically on the tree-walking interpreter and the bytecode VM, and
that the self-hosted compiler can compile it to bytecode. These programs are the
real-world validation for the language and toolchain.
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ULANG = os.path.join(ROOT, "src", "ulang.py")
PROJECTS = os.path.join(ROOT, "projects")


CALC_EXPECTED = """\
1 + 2 * 3  =>  7.0
(1 + 2) * 3  =>  9.0
10 / 4  =>  2.5
2 + 3 * 4 - 5  =>  9.0
x = 6  =>  6.0
y = 7  =>  7.0
x * y + 1  =>  43.0
-x + 100  =>  94.0
x = 22.5  =>  22.5
x * 2  =>  45.0
100 % 7  =>  2.0
"""

PROGRAMS = [
    ("calc/calc.ul", CALC_EXPECTED),
]


def _run(cmd, path):
    r = subprocess.run([sys.executable, ULANG, cmd, os.path.join(PROJECTS, path)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def run():
    failed = 0
    checked = 0
    for rel, expected in PROGRAMS:
        # interpreter output pinned
        checked += 1
        code, out = _run("run", rel)
        if code == 0 and out == expected:
            print(f"ok   {rel}: interpreter output matches")
        else:
            print(f"FAIL {rel}: interpreter output\n--- expected ---\n{expected}\n--- got ---\n{out}")
            failed += 1

        # VM parity
        checked += 1
        vcode, vout = _run("runvm", rel)
        if vcode == 0 and vout == out:
            print(f"ok   {rel}: VM output matches interpreter")
        else:
            print(f"FAIL {rel}: VM output differs from interpreter")
            failed += 1

        # self-hosted compiler compiles it
        checked += 1
        scode, sout = _run("selfhost", rel)
        if scode == 0 and "code " in sout:
            n = sout.count("code ")
            print(f"ok   {rel}: self-hosted compiler emits bytecode ({n} functions)")
        else:
            print(f"FAIL {rel}: self-hosted compiler failed\n{sout}")
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
