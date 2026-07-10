import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import tokenize, LexError, TokenType
from parser import parse, ParseError
import ast_nodes as ast


def _dump(node, indent=0):
    pad = "  " * indent
    if isinstance(node, ast.Node):
        lines = [f"{type(node).__name__}"]
        for field in node._fields:
            value = getattr(node, field, None)
            lines.append(f"{pad}  {field}: {_dump(value, indent + 2)}")
        return "\n".join(lines)
    if isinstance(node, list):
        if not node:
            return "[]"
        items = [f"\n{pad}  - {_dump(v, indent + 2)}" for v in node]
        return "".join(items)
    return repr(node)


def cmd_lex(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tokens = tokenize(source)
    except LexError as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    for tok in tokens:
        if tok.type == TokenType.EOF:
            print("EOF")
        else:
            print(f"{tok.type.name:12} {tok.value!r}")
    return 0


def cmd_parse(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    print(_dump(tree))
    return 0


def main(argv):
    if len(argv) < 3:
        print("usage: mol <lex|parse> <file.mol>", file=sys.stderr)
        return 2
    command = argv[1]
    if command == "lex":
        return cmd_lex(argv[2])
    if command == "parse":
        return cmd_parse(argv[2])
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
