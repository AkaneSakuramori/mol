import os
import sys
import io
import contextlib
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from lexer import tokenize, LexError
from parser import parse, ParseError
from checker import check
from interpreter import Interpreter
from compiler import compile_module
from vm import VM
from builtins_mod import UlangPanic


SEED = 1234
FUZZ_INPUTS = 400
GEN_PROGRAMS = 150

ALPHABET = list("abcdefghijklmnop 0123456789\n\t:()[]{}=+-*/%<>,.\"?_")
KEYWORDS = ["fn", "let", "var", "if", "else", "elif", "while", "for", "in",
            "return", "match", "print", "true", "false", "none", "and", "or", "not"]


def random_source(rng):
    n = rng.randint(0, 60)
    parts = []
    for _ in range(n):
        if rng.random() < 0.2:
            parts.append(rng.choice(KEYWORDS))
            parts.append(" ")
        else:
            parts.append(rng.choice(ALPHABET))
    return "".join(parts)


def fuzz_frontend(rng):
    crashes = 0
    for _ in range(FUZZ_INPUTS):
        src = random_source(rng)
        try:
            parse(src)
        except (LexError, ParseError):
            pass
        except RecursionError:
            pass
        except Exception as e:
            print(f"FUZZ CRASH on input {src!r}: {type(e).__name__}: {e}")
            crashes += 1
    return crashes


def gen_expr(rng, depth, vars):
    if depth <= 0 or rng.random() < 0.3:
        if vars and rng.random() < 0.5:
            return rng.choice(vars)
        return str(rng.randint(0, 100))
    op = rng.choice(["+", "-", "*"])
    left = gen_expr(rng, depth - 1, vars)
    right = gen_expr(rng, depth - 1, vars)
    if op == "*" and rng.random() < 0.5:
        right = str(rng.randint(1, 9))
    return f"({left} {op} {right})"


def gen_program(rng):
    lines = ["fn main():"]
    vars = []
    n = rng.randint(1, 6)
    for i in range(n):
        name = f"v{i}"
        expr = gen_expr(rng, rng.randint(1, 3), vars)
        lines.append(f"    let {name} = {expr}")
        vars.append(name)
    lines.append(f"    print({gen_expr(rng, 2, vars)})")
    return "\n".join(lines) + "\n"


def capture(fn):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        fn()
    return b.getvalue().strip()


def fuzz_engines(rng):
    mismatches = 0
    for _ in range(GEN_PROGRAMS):
        src = gen_program(rng)
        try:
            tree = parse(src)
            errs = check(tree)
            i_out = capture(lambda: Interpreter().run(parse(src)))
            v_out = capture(lambda: VM(compile_module(parse(src))).run())
        except UlangPanic:
            continue
        except Exception as e:
            print(f"GEN CRASH on {src!r}: {type(e).__name__}: {e}")
            mismatches += 1
            continue
        if i_out != v_out:
            print(f"ENGINE MISMATCH on {src!r}: interp={i_out!r} vm={v_out!r}")
            mismatches += 1
    return mismatches


def run():
    rng = random.Random(SEED)
    print(f"fuzzing frontend with {FUZZ_INPUTS} random inputs...")
    frontend = fuzz_frontend(rng)
    print(f"generating {GEN_PROGRAMS} random valid programs, checking engine agreement...")
    engines = fuzz_engines(rng)
    total = frontend + engines
    if total == 0:
        print(f"\nok: no frontend crashes, no engine mismatches")
        return 0
    print(f"\nFAIL: {frontend} frontend crashes, {engines} engine mismatches")
    return 1


if __name__ == "__main__":
    sys.exit(run())
