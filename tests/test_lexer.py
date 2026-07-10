import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from lexer import tokenize, LexError, TokenType


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def check_balanced(tokens):
    depth = 0
    for t in tokens:
        if t.type == TokenType.INDENT:
            depth += 1
        elif t.type == TokenType.DEDENT:
            depth -= 1
    if depth != 0:
        raise AssertionError(f"unbalanced INDENT/DEDENT: {depth}")


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
            tokens = tokenize(source)
            assert tokens[-1].type == TokenType.EOF, "missing EOF"
            check_balanced(tokens)
        except (LexError, AssertionError) as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        print(f"ok   {name}: {len(tokens)} tokens")
    total = len(files)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
