# The Ulang Compiler, in Ulang

This directory holds the self-hosted Ulang compiler — the compiler for Ulang, written in
Ulang itself. It is being built incrementally, one compiler stage at a time, and each
stage is validated for identical behavior against the Python reference implementation in
`src/` before the next begins.

## Layout

Files are named by compiler responsibility, not by development milestone:

```
compiler/
  lexer.ul       source text  -> token stream (with significant-indentation layout)
  parser.ul      token stream -> syntax tree
  checker.ul     syntax tree  -> semantic diagnostics (name resolution + type checking)
  exports.ul     syntax tree  -> a module's public API (visibility / package exports)
  consteval.ul   syntax tree  -> compile-time values of constant expressions
  optimizer.ul   syntax tree  -> optimized syntax tree (behavior-preserving passes)
  bytecode.ul    syntax tree  -> stack-VM bytecode (with peephole)
  codegen.ul     syntax tree  -> native LLVM IR (numeric / control-flow core)
```

## Status

- **Stage 1 — Parsing: complete.** `lexer.ul` and `parser.ul` together parse every
  language construct the reference compiler supports, verified identical to the reference
  (`tests/test_selfhost_lexer.py`, `tests/test_selfhost_parser.py`).
- **Stage 2 — Semantic analysis: complete.** Every semantic rule the reference performs is
  reproduced in Ulang and verified equivalent:
  - Name resolution and type checking, pattern validation, and exhaustiveness (`checker.ul`).
  - Visibility / package exports (`exports.ul`).
  - Constant evaluation (`consteval.ul`).
- **Stage 3 — Optimization and code generation: complete.**
  - AST optimizer (`optimizer.ul`): the behavior-preserving passes of the reference
    `src/optimizer.py` — constant folding, constant propagation through immutable
    `let`/`const` bindings, dead-branch elimination (`if`/`elif`/`else`, `while false`,
    ternaries), and algebraic identities (`x + 0`, `x * 1`) — producing an optimized syntax
    tree byte-identical to the reference (`tests/test_selfhost_optimizer.py`).
  - Bytecode generation (`bytecode.ul`): compiles the syntax tree to stack-VM bytecode,
    mirroring the reference `src/compiler.py` — expressions, control flow, loops with
    `break`/`continue`, pattern-matching dispatch, tail-position block values, nested
    closures, and the same peephole pass. Verified instruction-for-instruction identical to
    the reference (`tests/test_selfhost_bytecode.py`).
  - Native code generation (`codegen.ul`): compiles the syntax tree to LLVM IR for the
    numeric and control-flow core (`int`/`float`/`bool`, functions, `if`/`while`/`for`,
    arithmetic with coercion, comparisons, logical operators, ternaries, calls, and
    `print`), the same surface as the reference `src/codegen.py`. Its IR is compiled to a
    native binary and verified to produce output identical to the reference `ulang build`
    across an execution corpus and the native example programs
    (`tests/test_selfhost_codegen.py`).

## Note on literals

The self-hosted pipeline exchanges a canonical syntax-tree form in which string and float
literals are opaque atoms (`(str)`, `(flt)`); integer and boolean literals carry their
values. Every pass over integer, boolean, and structural forms is therefore reproduced
exactly. A few behaviors depend on literal *values* that this representation intentionally
omits — constant folding of string/float values (e.g. `"a" + "b"`, `1.5 + 2.5`), the
bytecode for string interpolation, and native codegen for programs whose control flow or
output depends on a specific float/string literal value. These are covered by the
reference's own tests and do not affect program behavior; the structural code generation
for those forms (float arithmetic and coercion, string handling) is still exercised.

## Running

```sh
cp path/to/program.ul input.ul
ulang run selfhost/compiler/lexer.ul       # token stream
ulang run selfhost/compiler/parser.ul > tree.sexpr
ulang run selfhost/compiler/checker.ul     # semantic diagnostics
ulang run selfhost/compiler/exports.ul     # public API
ulang run selfhost/compiler/consteval.ul   # constant values
ulang run selfhost/compiler/optimizer.ul   # optimized syntax tree
```

## Validation approach

The self-hosted components emit a canonical, textual form of their output (token streams
and S-expression syntax trees). The Python reference emits the same canonical form via
`src/ast_serialize.py`. The conformance tests compare the two exactly, so any divergence
in behavior is caught immediately.
