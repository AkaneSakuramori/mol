import os
import sys
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from lexer import tokenize as py_tokenize, TokenType as T


LEXER_UL = os.path.join(ROOT, "selfhost", "lexer.ul")
ULANG = os.path.join(ROOT, "src", "ulang.py")


SAMPLES = [
    "fn add(a: int, b: int) -> int:\n    return a + b\n",
    "fn main():\n    let xs = [1, 2, 3]\n    var total = 0\n    for x in xs:\n        total += x\n    print(total)\n",
    "const RATE = 100\nfn scale(n: int) -> int:\n    return n * RATE\n",
    "fn check(n: int) -> bool:\n    if n >= 0 and n <= 10:\n        return true\n    return false\n",
    "# a comment\nfn f():\n    let y = 3.14\n    print(y)\n",
    "enum Color:\n    Red\n    Green\n    Blue\n",
]


def py_core(src):
    out = []
    for tok in py_tokenize(src):
        if tok.type in (T.NEWLINE, T.INDENT, T.DEDENT, T.EOF):
            continue
        if tok.type == T.KEYWORD:
            out.append(f"KEYWORD {tok.value}")
        elif tok.type == T.IDENT:
            out.append(f"IDENT {tok.value}")
        elif tok.type == T.INT:
            out.append(f"INT {tok.value}")
        elif tok.type == T.FLOAT:
            out.append("FLOAT")
        elif tok.type == T.STRING:
            out.append("STRING")
        else:
            out.append(f"OP {tok.value}")
    return out


def ulang_tokens(src):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "input.ul"), "w") as f:
        f.write(src)
    shutil.copy(LEXER_UL, os.path.join(d, "lexer.ul"))
    result = subprocess.run(
        [sys.executable, ULANG, "run", "lexer.ul"],
        cwd=d, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return [line for line in result.stdout.strip().split("\n") if line]


def run():
    failed = 0
    for i, src in enumerate(SAMPLES):
        expected = py_core(src)
        try:
            actual = ulang_tokens(src)
        except RuntimeError as e:
            print(f"FAIL sample {i}: ulang lexer error: {e}")
            failed += 1
            continue
        if actual == expected:
            print(f"ok   sample {i}: {len(expected)} tokens match the reference lexer")
        else:
            print(f"FAIL sample {i}: divergence")
            for a, b in zip(actual, expected):
                if a != b:
                    print(f"     got {a!r}, expected {b!r}")
                    break
            if len(actual) != len(expected):
                print(f"     length {len(actual)} vs {len(expected)}")
            failed += 1

    total = len(SAMPLES)
    print(f"\n{total - failed}/{total} passed")
    if failed == 0:
        print("self-hosting: the Ulang-written lexer matches the reference lexer")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
