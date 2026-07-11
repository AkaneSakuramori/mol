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
```

The next stage (optimization and code generation) is added here as it is completed and
validated.

## Status

- **Stage 1 — Parsing: complete.** `lexer.ul` and `parser.ul` together parse every
  language construct the reference compiler supports. Their output is verified identical
  to the reference lexer and parser across all example programs and a stress corpus
  (`tests/test_selfhost_lexer.py`, `tests/test_selfhost_parser.py`).
- **Stage 2 — Semantic analysis: complete.** Every semantic rule the reference compiler
  performs is reproduced in Ulang and verified equivalent:
  - Name resolution and type checking (`checker.ul`): symbol and scope management,
    undefined-name detection, type inference, type-mismatch diagnostics, pattern
    validation (unknown-variant and arity), and match exhaustiveness checking, in a single
    walk mirroring the reference `src/checker.py`
    (`tests/test_selfhost_checker.py`).
  - Visibility / package exports (`exports.ul`): a module's public API, identical to what
    the runtime package loader exposes (`tests/test_selfhost_exports.py`).
  - Constant evaluation (`consteval.ul`): compile-time evaluation of integer and boolean
    constant expressions, including constant propagation across `const` declarations,
    matching the reference's folding semantics (`tests/test_selfhost_consteval.py`).
- **Stage 3 — Optimization and code generation: not started.**

## Running

Each component reads its input from the current directory:

```sh
cp path/to/program.ul input.ul
ulang run selfhost/compiler/lexer.ul     # print the token stream
ulang run selfhost/compiler/parser.ul    # print the syntax tree as S-expressions

ulang run selfhost/compiler/parser.ul > tree.sexpr
ulang run selfhost/compiler/checker.ul   # print semantic diagnostics
```

## Validation approach

The self-hosted components emit a canonical, textual form of their output (token streams
and S-expression syntax trees). The Python reference emits the same canonical form via
`src/ast_serialize.py`. The conformance tests compare the two exactly, so any divergence
in behavior is caught immediately.
