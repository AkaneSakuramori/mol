# The Ulang Compiler, in Ulang

This directory holds the self-hosted Ulang compiler — the compiler for Ulang, written in
Ulang itself. It is being built incrementally, one compiler stage at a time, and each
stage is validated for identical behavior against the Python reference implementation in
`src/` before the next begins.

## Layout

Files are named by compiler responsibility, not by development milestone:

```
compiler/
  lexer.ul     source text  -> token stream (with significant-indentation layout)
  parser.ul    token stream -> syntax tree
```

Later stages (semantic analysis, then optimization and code generation) are added here as
they are completed and validated.

## Status

- **Stage 1 — Parsing: complete.** `lexer.ul` and `parser.ul` together parse every
  language construct the reference compiler supports. Their output is verified identical
  to the reference lexer and parser across all example programs and a stress corpus
  (`tests/test_selfhost_lexer.py`, `tests/test_selfhost_parser.py`).
- **Stage 2 — Semantic analysis: in progress.**
- **Stage 3 — Optimization and code generation: not started.**

## Running

Each component reads `input.ul` from the current directory:

```sh
cp path/to/program.ul input.ul
ulang run selfhost/compiler/lexer.ul     # print the token stream
ulang run selfhost/compiler/parser.ul    # print the syntax tree as S-expressions
```

## Validation approach

The self-hosted components emit a canonical, textual form of their output (token streams
and S-expression syntax trees). The Python reference emits the same canonical form via
`src/ast_serialize.py`. The conformance tests compare the two exactly, so any divergence
in behavior is caught immediately.
