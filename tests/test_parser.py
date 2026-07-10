import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse, ParseError
from lexer import LexError
import ast_nodes as ast


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def run():
    files = sorted(glob.glob(os.path.join(EXAMPLES, "*.mol")))
    if not files:
        print("no example files found")
        return 1
    failed = 0
    for path in files:
        name = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            tree = parse(source)
            assert isinstance(tree, ast.Module), "root is not a Module"
            assert len(tree.body) > 0, "empty module"
        except (LexError, ParseError, AssertionError) as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        print(f"ok   {name}: {len(tree.body)} top-level decls")
    total = len(files)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
