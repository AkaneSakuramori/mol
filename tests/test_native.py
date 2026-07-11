import os
import sys
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from native import build_executable
from interpreter import Interpreter
import io
import contextlib


NATIVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "native")

EXACT = ["hello", "fib", "primes"]
RUNS = ["floats"]


def interp_output(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(parse(source))
    return buf.getvalue()


def build_and_run(path, out):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    exe = build_executable(parse(source), out)
    result = subprocess.run([exe], capture_output=True, text=True)
    return result.returncode, result.stdout


def run():
    failed = 0
    try:
        import platform_abi
        import llvmlite  # noqa: F401
        if platform_abi.find_c_compiler() is None:
            print("skip: no C compiler available")
            print("\n0/0 passed (skipped)")
            return 0
    except ImportError:
        print("skip: llvmlite not installed")
        print("\n0/0 passed (skipped)")
        return 0
    tmp = tempfile.mkdtemp()
    for name in EXACT:
        path = os.path.join(NATIVE, name + ".ul")
        out = os.path.join(tmp, name)
        try:
            code, native_out = build_and_run(path, out)
            expected = interp_output(path)
        except Exception as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        if code == 0 and native_out == expected:
            print(f"ok   {name}: native == interpreter")
        else:
            print(f"FAIL {name}: native={native_out!r} interp={expected!r}")
            failed += 1

    for name in RUNS:
        path = os.path.join(NATIVE, name + ".ul")
        out = os.path.join(tmp, name)
        try:
            code, native_out = build_and_run(path, out)
        except Exception as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        if code == 0 and native_out.strip():
            print(f"ok   {name}: built and ran")
        else:
            print(f"FAIL {name}: exit {code}")
            failed += 1

    total = len(EXACT) + len(RUNS)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
