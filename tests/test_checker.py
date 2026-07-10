import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from checker import check


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


NEGATIVE = [
    ("fn main():\n    print(undefined_var)\n", "undefined"),
    ("fn main():\n    let x: int = \"hello\"\n    print(x)\n", "mismatch"),
]


def run():
    failed = 0
    files = sorted(glob.glob(os.path.join(EXAMPLES, "*.mol")))
    for path in files:
        name = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        errors = check(parse(source))
        if errors:
            print(f"FAIL {name}: {[str(e) for e in errors]}")
            failed += 1
        else:
            print(f"ok   {name}")

    for i, (src, expect) in enumerate(NEGATIVE):
        errors = check(parse(src))
        if errors and any(expect in str(e) for e in errors):
            print(f"ok   negative {i}: caught {expect}")
        else:
            print(f"FAIL negative {i}: expected error containing {expect!r}, got {[str(e) for e in errors]}")
            failed += 1

    total = len(files) + len(NEGATIVE)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
