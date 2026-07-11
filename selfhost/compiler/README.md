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
```

Later stages (the rest of semantic analysis, then optimization and code generation) are
added here as they are completed and validated.

## Status

- **Stage 1 — Parsing: complete.** `lexer.ul` and `parser.ul` together parse every
  language construct the reference compiler supports. Their output is verified identical
  to the reference lexer and parser across all example programs and a stress corpus
  (`tests/test_selfhost_lexer.py`, `tests/test_selfhost_parser.py`).
- **Stage 2 — Semantic analysis: in progress.**
  - Name resolution and type checking (`checker.ul`): symbol and scope management,
    undefined-name detection, type inference, type-mismatch diagnostics, pattern
    validation (unknown-variant and arity), and match exhaustiveness checking, in a single
    walk mirroring the reference `src/checker.py`. Verified identical to the reference —
    same diagnostics in the same order — across a semantic corpus, all example programs,
    and randomly generated typed programs (`tests/test_selfhost_checker.py`).
  - Visibility / package exports (`exports.ul`): computes a module's public API — the set
    the runtime package loader (`src/loader.py`) exposes to importers — and is verified
    identical to it (`tests/test_selfhost_exports.py`). Remaining Stage-2 subsystem:
    constant evaluation.
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
