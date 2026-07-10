# Mol

Mol is a compiled, statically-typed programming language with type inference,
first-class concurrency, and a clean, readable syntax. It compiles to native code,
runs without a global interpreter lock, and treats errors as values.

> Status: **Step 7 of 10 — Native Backend (LLVM).** Early development.

## Features

- Static typing with type inference and no-null enforcement (`Option`/`Result`).
- Immutable bindings by default (`let`), explicit mutability (`var`).
- Algebraic data types (`enum`) with exhaustive pattern matching.
- Errors as values with the `?` propagation operator.
- Traits for polymorphism and generics with bounds.
- First-class functions, closures, and string interpolation.
- Runs via a tree-walking interpreter and a bytecode virtual machine.
- Compiles numeric and control-flow programs to native executables via LLVM.

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

Mol is under active development. The toolchain builds from source and runs on
Python 3.10+.

```sh
# tokenize a source file
python3 src/mol.py lex examples/01_hello.mol

# parse a source file to an AST
python3 src/mol.py parse examples/01_hello.mol

# type-check a source file
python3 src/mol.py check examples/09_result.mol

# run with the tree-walking interpreter
python3 src/mol.py run examples/08_enums_match.mol

# run with the bytecode virtual machine
python3 src/mol.py runvm examples/08_enums_match.mol

# compile to a native executable via LLVM, then run it
python3 src/mol.py build examples/native/fib.mol -o fib
./fib

# print the generated LLVM IR
python3 src/mol.py emit-ir examples/native/fib.mol

# start the interactive REPL
python3 src/mol.py repl

# run the full test suite
python3 tests/run_all.py
```

The native backend requires `llvmlite` and a C toolchain (`gcc`):

```sh
pip install llvmlite
```

It currently compiles the numeric and control-flow core (`int`, `float`, `bool`,
functions, recursion, `if`/`while`/`for`, and `print`) to a standalone binary.
Heap types and closures run on the interpreter and VM today and are added to the
native backend alongside the runtime and memory model (Step 8).

## Toolchain

The compiler is organized as a classic pipeline:

```
source → lexer → parser → checker → ┬→ interpreter (tree-walking)
                                     ├→ compiler → bytecode → VM
                                     └→ codegen → LLVM IR → native binary
```

- `src/lexer.py` — source to tokens, with layout and string interpolation.
- `src/parser.py`, `src/ast_nodes.py` — tokens to a typed AST.
- `src/checker.py` — name resolution and type inference.
- `src/interpreter.py` — tree-walking evaluator.
- `src/compiler.py`, `src/bytecode.py`, `src/vm.py` — bytecode compiler and stack VM.
- `src/codegen.py`, `src/native.py` — LLVM IR generation and native compilation.
- `src/repl.py` — interactive shell.
- `src/stdlib.py`, `src/builtins_mod.py` — built-in functions and modules (`fs`, `json`, `math`).

## Repository layout

```
spec/            language specification and formal grammar
examples/        example .mol programs
examples/native/ programs the native backend compiles to binaries
src/             compiler implementation
tests/           compiler tests
```

- [`spec/SPEC.md`](spec/SPEC.md) — language specification.
- [`spec/grammar.ebnf`](spec/grammar.ebnf) — formal EBNF grammar.
- [`examples/`](examples/) — example programs.

## Roadmap

1. Spec & grammar — language definition, EBNF, example programs. ✅
2. Lexer — source to tokens. ✅
3. Parser — tokens to AST. ✅
4. Semantic analysis and type system — inference and checking. ✅
5. Tree-walking interpreter. ✅
6. Bytecode compiler and virtual machine, REPL. ✅
7. Native backend via LLVM — single static binary. ✅
8. Runtime — green-thread scheduler, structured concurrency, memory model.
9. Standard library, tooling (`mol` CLI, LSP, formatter, package manager), and FFI.
10. Self-hosting compiler, JIT tier, and 1.0 release.

## License

TBD.
