# Mol

Mol is a compiled, statically-typed programming language with type inference,
first-class concurrency, and a clean, readable syntax. It compiles to native code,
runs without a global interpreter lock, and treats errors as values.

> Status: **Step 3 of 10 — Parser.** Early development.

## Features

- Static typing with full local type inference — annotate only at boundaries.
- Immutable bindings by default (`let`), explicit mutability (`var`).
- Algebraic data types (`enum`) with exhaustive pattern matching.
- No null: `Option[T]` and `Result[T, E]` with the `?` propagation operator.
- Traits for polymorphism and generics with bounds.
- First-class functions, closures, and string interpolation.
- Compiles to a single native binary with fast startup.

## Example

```mol
type User:
    id: int
    name: str
    email: str?
derive(Display)

fn greet(u: User) -> str:
    match u.email:
        Some(e) => "${u.name} <${e}>"
        None    => u.name

fn main():
    let u = User(1, "ada", none)
    print(greet(u))
```

## Getting started

Mol is under active development. The toolchain currently builds from source and runs
on Python 3.10+.

```sh
# tokenize a source file
python3 src/mol.py lex examples/01_hello.mol

# parse a source file to an AST
python3 src/mol.py parse examples/01_hello.mol

# run the test suite
python3 tests/test_lexer.py
python3 tests/test_parser.py
```

## Repository layout

```
spec/        language specification and formal grammar
examples/    example .mol programs
src/         compiler implementation
tests/       compiler tests
```

- [`spec/SPEC.md`](spec/SPEC.md) — language specification.
- [`spec/grammar.ebnf`](spec/grammar.ebnf) — formal EBNF grammar.
- [`examples/`](examples/) — example programs.

## Roadmap

1. Spec & grammar — language definition, EBNF, example programs. ✅
2. Lexer — source to tokens. ✅
3. Parser — tokens to AST. ✅
4. Semantic analysis and type system — inference and checking.
5. Tree-walking interpreter.
6. Bytecode compiler and virtual machine, REPL.
7. Native backend via LLVM — single static binary.
8. Runtime — green-thread scheduler, structured concurrency, memory model.
9. Standard library, tooling (`mol` CLI, LSP, formatter, package manager), and FFI.
10. Self-hosting compiler, JIT tier, and 1.0 release.

## License

TBD.
