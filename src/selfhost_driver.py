"""Self-hosted compiler driver.

Orchestrates the self-hosted Ulang compiler stages (each a program in
``selfhost/compiler/*.ul``) into a single pipeline: source -> tokens -> syntax tree ->
diagnostics -> optimized tree -> bytecode / native IR.

The compiler *logic* is written entirely in Ulang; this module is the thin bootstrap host
that runs those Ulang programs on the Ulang runtime and passes the canonical S-expression
tree between stages. It is the integration point behind ``ulang selfhost``.
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")

STAGES = ("lexer", "parser", "checker", "exports", "consteval", "optimizer", "bytecode",
          "codegen")


class SelfhostError(Exception):
    pass


class Driver:
    """Runs the self-hosted compiler stages over a working directory."""

    def __init__(self, workdir=None):
        self._owns = workdir is None
        self.workdir = workdir or tempfile.mkdtemp(prefix="ulangc.")
        for stage in STAGES:
            shutil.copy(os.path.join(COMPILER, stage + ".ul"),
                        os.path.join(self.workdir, stage + ".ul"))

    def close(self):
        if self._owns:
            shutil.rmtree(self.workdir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _run(self, stage, stdin_file=None):
        # Force UTF-8 decoding regardless of the host locale (Windows defaults to a
        # non-UTF-8 codepage), so the canonical tree piped between stages is exact.
        r = subprocess.run([sys.executable, ULANG, "run", stage + ".ul"],
                           cwd=self.workdir, capture_output=True, text=True,
                           encoding="utf-8")
        if r.returncode != 0:
            raise SelfhostError(f"{stage}: {(r.stderr or '').strip()}")
        return r.stdout

    def _write(self, name, text):
        # newline="" keeps line endings exactly as written: the self-hosted stages
        # split intermediate files on "\n", so platform newline translation (CRLF on
        # Windows) must not be introduced here.
        with open(os.path.join(self.workdir, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)

    # -- individual stages -------------------------------------------------

    def tokens(self, source):
        self._write("input.ul", source)
        return self._run("lexer")

    def parse(self, source):
        self._write("input.ul", source)
        return self._run("parser")

    def diagnostics(self, tree):
        self._write("tree.sexpr", tree)
        return self._run("checker")

    def exports(self, tree):
        self._write("tree.sexpr", tree)
        return self._run("exports")

    def optimize(self, tree):
        self._write("tree.sexpr", tree)
        return self._run("optimizer")

    def bytecode(self, tree):
        self._write("tree.sexpr", tree)
        return self._run("bytecode")

    def native_ir(self, tree):
        self._write("tree.sexpr", tree)
        return self._run("codegen")

    # -- full pipeline -----------------------------------------------------

    def compile(self, source, target="bytecode"):
        """Run the complete pipeline. Returns (diagnostics, output).

        ``diagnostics`` is the checker output (empty when the program is clean).
        ``output`` is the bytecode listing (target="bytecode") or LLVM IR
        (target="native"), computed from the optimized syntax tree, or None when
        diagnostics are present.
        """
        tree = self.parse(source)
        diags = self.diagnostics(tree)
        if diags.strip():
            return diags, None
        optimized = self.optimize(tree)
        if target == "native":
            self._write("tree.sexpr", optimized)
            return diags, self._run("codegen")
        self._write("tree.sexpr", optimized)
        return diags, self._run("bytecode")
