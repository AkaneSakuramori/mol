import os
import sys
import glob
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from lexer import tokenize, TokenType as T


LEXER_UL = os.path.join(ROOT, "selfhost", "compiler", "lexer.ul")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


def reference(src):
    out = []
    for t in tokenize(src):
        if t.type == T.EOF:
            out.append("eof")
        elif t.type == T.NEWLINE:
            out.append("newline")
        elif t.type == T.INDENT:
            out.append("indent")
        elif t.type == T.DEDENT:
            out.append("dedent")
        elif t.type == T.KEYWORD:
            out.append(f"kw {t.value}")
        elif t.type == T.IDENT:
            out.append(f"id {t.value}")
        elif t.type == T.INT:
            out.append(f"int {t.value}")
        elif t.type == T.FLOAT:
            out.append("float")
        elif t.type == T.STRING:
            out.append("str")
        else:
            out.append(f"op {t.value}")
    return out


def ulang_tokens(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    result = subprocess.run(
        [sys.executable, ULANG, "run", "lexer.ul"],
        cwd=workdir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return [line for line in result.stdout.split("\n") if line]


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(LEXER_UL, os.path.join(workdir, "lexer.ul"))
    failed = 0
    files = sorted(glob.glob(os.path.join(EXAMPLES, "*.ul")))
    for path in files:
        name = os.path.basename(path)
        with open(path) as f:
            src = f.read()
        expected = reference(src)
        try:
            actual = ulang_tokens(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        if actual == expected:
            print(f"ok   {name}: {len(expected)} tokens incl. layout match reference")
        else:
            print(f"FAIL {name}: {len(actual)} vs {len(expected)} tokens")
            for i, (a, b) in enumerate(zip(actual, expected)):
                if a != b:
                    print(f"     at {i}: ulang {a!r}, python {b!r}")
                    break
            failed += 1
    total = len(files)
    print(f"\n{total - failed}/{total} passed")
    if failed == 0:
        print("self-hosting: the Ulang full lexer (with layout) matches the reference on all examples")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
