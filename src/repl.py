import sys

from parser import Parser, parse, ParseError
from lexer import tokenize, LexError
from interpreter import Interpreter
from builtins_mod import UlangPanic
from values import ulang_str
import ast_nodes as ast


BANNER = "Ulang REPL — type expressions or statements, :quit to exit"


class Repl:
    def __init__(self):
        self.interp = Interpreter()
        self.interp.globals = self.interp.globals

    def eval_line(self, source):
        tokens = tokenize(source + "\n")
        parser = Parser(tokens)
        parser.skip_newlines()
        if parser.at_top_level_decl():
            tree = parse(source + "\n")
            self.interp.collect(tree)
            return None, False
        stmt = parser.parse_statement()
        if isinstance(stmt, ast.ExprStmt):
            value = self.interp.eval(stmt.expr, self.interp.globals)
            return value, True
        self.interp.exec(stmt, self.interp.globals)
        return None, False


def _at_top_level_decl(self):
    return self.at_keyword("fn", "type", "enum", "trait", "impl", "const", "import", "from", "pub")


Parser.at_top_level_decl = _at_top_level_decl


def repl():
    print(BANNER)
    r = Repl()
    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        line = line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in (":quit", ":q", ":exit"):
            return 0
        if stripped.endswith(":"):
            block = [line]
            while True:
                try:
                    cont = input("... ")
                except (EOFError, KeyboardInterrupt):
                    break
                if cont.strip() == "":
                    break
                block.append(cont)
            line = "\n".join(block)
        try:
            value, is_expr = r.eval_line(line)
            if is_expr and value is not None:
                print(ulang_str(value))
        except (LexError, ParseError) as e:
            print(f"syntax error: {e}", file=sys.stderr)
        except UlangPanic as e:
            print(f"panic: {e.message}", file=sys.stderr)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
    return 0
