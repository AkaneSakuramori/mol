# Ulang reference projects

Substantial, self-contained programs written in Ulang, used as real-world validation for
the language and toolchain. Each one is pinned by `tests/test_projects.py`, which checks
its output, verifies it runs identically on the tree-walking interpreter and the bytecode
VM, and confirms the self-hosted compiler can compile it.

| Project | What it demonstrates |
|---|---|
| [`calc`](calc/) | Tokenizer + precedence-climbing parser + evaluator for arithmetic expressions with variables. Enums, structs, recursion, pattern matching. |
| [`wordstats`](wordstats/) | Word-frequency and text statistics. String processing, dictionaries, and higher-order list operations (`map`/`filter`/`sort`/`reduce`). |

Run any project with:

```sh
ulang run projects/calc/calc.ul
ulang runvm projects/wordstats/wordstats.ul
```
