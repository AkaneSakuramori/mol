# Ulang

Ulang is a compiled, statically-typed programming language with type inference,
structured concurrency, and a clean, readable syntax. It compiles to native code,
runs without a global interpreter lock, and treats errors as values.

> Status: **1.0.0** — complete toolchain from source to native code.

## Features

- Static typing with type inference and no-null enforcement (`Option`/`Result`).
- Immutable bindings by default (`let`), explicit mutability (`var`).
- Algebraic data types (`enum`) with exhaustive pattern matching.
- Errors as values with the `?` propagation operator.
- Traits for polymorphism and generics with bounds.
- First-class functions, closures, and string interpolation.
- Structured concurrency: nurseries, tasks, and channels.
- C FFI: call native libraries directly with `extern fn`.
- Four execution engines: interpreter, bytecode VM, tiered JIT, and native (LLVM).
- Tooling: formatter, project scaffolding, and a standard library.

## Example

```ulang
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

## Concurrency

Concurrency is structured: tasks live inside a `nursery` scope that does not exit until
all of its children finish.

```ulang
fn main():
    with nursery() as g:
        let a = g.spawn(() => fetch(1))
        let b = g.spawn(() => fetch(2))
        print(a.await() + b.await())
```

Channels pass values between tasks:

```ulang
let ch = channel()
ch.send(42)
print(ch.recv())
```

## Foreign functions

`extern fn` binds a C library function and calls it directly:

```ulang
extern fn sqrt(x: float) -> float from "m"

fn main():
    print(sqrt(16.0))
```

## Execution engines

The same program runs on four engines that share a frontend and produce identical
results:

- **Interpreter** — tree-walking; simplest, used for development.
- **Bytecode VM** — compiles to bytecode for a stack machine; drives the REPL.
- **Tiered JIT** — the interpreter counts calls and compiles hot numeric functions to
  native code at runtime via LLVM, then swaps them in.
- **Native** — ahead-of-time compilation to a standalone executable.

```sh
ulang run   file.ul      # interpreter
ulang runvm file.ul      # bytecode VM
ulang jit   file.ul      # tiered JIT
ulang build file.ul -o a && ./a   # native
```

### Benchmarks

Indicative timings (single machine; all engines produce identical output):

| Benchmark            | Interpreter | Bytecode VM | JIT     | Native  |
|----------------------|-------------|-------------|---------|---------|
| `fib(30)`            | ~22 s       | ~11 s       | ~13 ms  | ~5 ms   |
| `count_primes(20k)`  | ~1.3 s      | ~1.4 s      | ~75 ms  | ~2 ms   |

Run them with `python3 bench/benchmark.py`.

## Self-hosting

`selfhost/tokenize.ul` is a lexer for Ulang **written in Ulang** — it tokenizes Ulang source
into keywords, identifiers, integers, and operators. It demonstrates that the language
is expressive enough to implement its own tooling.

```sh
ulang run selfhost/tokenize.ul
```

## Standard library

Modules available via `import`: `fs`, `json`, `math`, `time`, `str`, `random`, `list`.

## Tooling

```sh
ulang init myapp          # scaffold a project (ulang.toml + src/main.ul)
ulang fmt file.ul         # print canonical formatting
ulang fmt file.ul -w      # format in place
ulang escape file.ul      # show stack vs heap allocation analysis
```

## Getting started

Ulang is under active development. The toolchain builds from source and runs on
Python 3.10+.

```sh
# tokenize a source file
python3 src/ulang.py lex examples/01_hello.ul

# parse a source file to an AST
python3 src/ulang.py parse examples/01_hello.ul

# type-check a source file
python3 src/ulang.py check examples/09_result.ul

# run with the tree-walking interpreter
python3 src/ulang.py run examples/08_enums_match.ul

# run with the bytecode virtual machine
python3 src/ulang.py runvm examples/08_enums_match.ul

# compile to a native executable via LLVM, then run it
python3 src/ulang.py build examples/native/fib.ul -o fib
./fib

# print the generated LLVM IR
python3 src/ulang.py emit-ir examples/native/fib.ul

# start the interactive REPL
python3 src/ulang.py repl

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
- `src/jit.py`, `src/tiered.py` — JIT engine and tiered execution.
- `src/runtime.py` — tasks, nurseries, and channels.
- `src/escape.py` — escape analysis (stack vs heap allocation).
- `src/ffi.py` — C foreign-function interface.
- `src/formatter.py` — canonical source formatter.
- `src/repl.py` — interactive shell.
- `src/stdlib.py`, `src/builtins_mod.py` — built-in functions and modules.

## Repository layout

```
spec/            language specification and formal grammar
examples/        example .ul programs
examples/native/ programs the native backend compiles to binaries
selfhost/        Ulang tooling written in Ulang
src/             compiler implementation
tests/           compiler tests
bench/           benchmarks across execution engines
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
8. Runtime — structured concurrency and memory model. ✅
9. Standard library, tooling (`ulang` CLI, formatter, package manifest), and FFI. ✅
10. Tiered JIT, self-hosting tokenizer, benchmarks, and the 1.0 release. ✅

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

TBD.
