import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import tokenize, LexError, TokenType
from parser import parse, ParseError
from interpreter import Interpreter
from checker import check as type_check
from compiler import compile_module
from vm import VM
from builtins_mod import MolPanic
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


def cmd_run(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    try:
        Interpreter().run(tree)
    except MolPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    return 0


def cmd_check(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    errors = type_check(tree)
    if errors:
        for e in errors:
            print(f"{path}:{e}", file=sys.stderr)
        return 1
    print(f"{path}: ok")
    return 0


def cmd_runvm(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    try:
        VM(compile_module(tree)).run()
    except MolPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    return 0


def cmd_build(path, output=None):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from native import build_executable
    from codegen import CodegenError
    if output is None:
        output = os.path.splitext(os.path.basename(path))[0]
    try:
        build_executable(tree, output, keep_ir=True)
    except CodegenError as e:
        print(f"error: {path}: native backend: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    print(f"built {output}")
    return 0


def cmd_emit_ir(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from native import emit_ir
    from codegen import CodegenError
    try:
        print(emit_ir(tree))
    except CodegenError as e:
        print(f"error: {path}: native backend: {e}", file=sys.stderr)
        return 1
    return 0


def main(argv):
    if len(argv) < 2:
        print("usage: mol <lex|parse|check|run|runvm|build|emit-ir|repl> <file.mol>", file=sys.stderr)
        return 2
    command = argv[1]
    if command == "repl":
        from repl import repl
        return repl()
    if len(argv) < 3:
        print(f"usage: mol {command} <file.mol>", file=sys.stderr)
        return 2
    if command == "lex":
        return cmd_lex(argv[2])
    if command == "parse":
        return cmd_parse(argv[2])
    if command == "check":
        return cmd_check(argv[2])
    if command == "run":
        return cmd_run(argv[2])
    if command == "runvm":
        return cmd_runvm(argv[2])
    if command == "build":
        output = argv[4] if len(argv) > 4 and argv[3] == "-o" else None
        return cmd_build(argv[2], output)
    if command == "emit-ir":
        return cmd_emit_ir(argv[2])
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
