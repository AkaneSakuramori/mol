# Ulang reference projects

Substantial, self-contained programs written in Ulang, used as real-world validation for
the language and toolchain. Each one is pinned by `tests/test_projects.py`, which checks
its output, verifies it runs identically on the tree-walking interpreter and the bytecode
VM, and confirms the self-hosted compiler can compile it.

| Project | What it demonstrates |
|---|---|
| [`calc`](calc/) | Tokenizer + precedence-climbing parser + evaluator for arithmetic expressions with variables. Enums, structs, recursion, pattern matching. |
| [`wordstats`](wordstats/) | Word-frequency and text statistics. String processing, dictionaries, and higher-order list operations (`map`/`filter`/`sort`/`reduce`). |
| [`jsonfmt`](jsonfmt/) | A JSON value model and pretty-printer. Recursive enums, enum payloads of varied shapes, recursive rendering with indentation. |
| [`life`](life/) | Conway's Game of Life. Nested lists, in-place mutation, neighbour counting, generation stepping. |
| [`rpn`](rpn/) | A Reverse Polish Notation calculator with typed error handling. `Result`, the `?` operator, and a value stack. |
| [`table`](table/) | A text table formatter with aligned, padded columns. Standard-library string methods (`repeat`, `substring`) and list-of-lists data. |
| [`kvstore`](kvstore/) | An in-memory key/value store with a text command language (SET/GET/DEL/INCR/EXISTS/KEYS/COUNT). Dictionaries, `Option`, `Result`, and a request/response loop over shared state. |
| [`stats`](stats/) | A numerical statistics toolkit (mean, variance, stddev, median). The `math` module, float aggregation, and comparator sort. |

Run any project with:

```sh
ulang run projects/calc/calc.ul
ulang runvm projects/wordstats/wordstats.ul
```
