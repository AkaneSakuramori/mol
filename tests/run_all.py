import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    "test_lexer.py",
    "test_parser.py",
    "test_checker.py",
    "test_interpreter.py",
    "test_vm.py",
    "test_native.py",
]


def main():
    failed = 0
    for suite in SUITES:
        result = subprocess.run(
            [sys.executable, os.path.join(HERE, suite)],
            capture_output=True, text=True,
        )
        last = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"[{status}] {suite}: {last}")
        if result.returncode != 0:
            failed += 1
            print(result.stdout)
            print(result.stderr)
    print()
    print(f"{len(SUITES) - failed}/{len(SUITES)} suites passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
