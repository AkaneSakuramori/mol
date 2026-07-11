# Ulang

[![CI](https://github.com/AkaneSakuramori/ulang/actions/workflows/ci.yml/badge.svg)](https://github.com/AkaneSakuramori/ulang/actions/workflows/ci.yml)

Ulang is a compiled, statically-typed programming language with type inference,
structured concurrency, and a clean, readable syntax. It compiles to native code,
runs without a global interpreter lock, and treats errors as values.

> Status: **1.8.7** — self-hosting Stages 1–3 complete (parser, semantic analysis, optimizer + bytecode + native codegen), cross-platform, optimizing compiler, garbage collector, package manager, and LSP.

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
- Editor support via a built-in Language Server (`ulang lsp`).
- Package manager with reproducible builds and verified downloads (`ulang install`).
- Generational tracing garbage collector across the interpreter, VM, and native runtime.
- Cross-platform: identical semantics on Linux, macOS, and Windows (x86-64 and ARM64).
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

Ulang is progressing toward a self-hosted compiler — the Ulang compiler written in Ulang
itself, in [`selfhost/compiler/`](selfhost/compiler/). It is built one compiler stage at a
time; each stage is validated for identical behavior against the Python reference in
[`src/`](src/) before the next begins.

- **Stage 1 — Parsing: complete.**
  - `selfhost/compiler/lexer.ul` — source text to a token stream, including significant
    indentation (`INDENT`/`DEDENT`/`NEWLINE`), verified token-for-token against the
    reference lexer on every example program.
  - `selfhost/compiler/parser.ul` — token stream to a syntax tree, covering every language
    construct (modules, functions, types, enums, traits, `impl` blocks, generics with
    bounds, all statements and control flow, pattern matching, lambdas, and the full
    expression grammar). Its syntax trees are verified **identical to the reference
    parser** across all example programs plus a stress corpus, and it terminates cleanly
    on malformed input.
- **Stage 2 — Semantic analysis: complete.** The self-hosted semantic analyzer reproduces
  every rule the reference compiler performs, each proven equivalent:
  - `selfhost/compiler/checker.ul` — name resolution, type inference/checking, pattern
    validation, and match exhaustiveness checking.
  - `selfhost/compiler/exports.ul` — visibility / package exports (a module's public API).
  - `selfhost/compiler/consteval.ul` — compile-time constant evaluation with propagation.
- **Stage 3 — Optimization and code generation: complete.**
  - `selfhost/compiler/optimizer.ul` — the reference AST optimizer's behavior-preserving
    passes, producing optimized syntax trees byte-identical to the reference.
  - `selfhost/compiler/bytecode.ul` — stack-VM bytecode generation (all control flow,
    closures, pattern dispatch, and the peephole pass), instruction-for-instruction
    identical to the reference.
  - `selfhost/compiler/codegen.ul` — native LLVM code generation for the numeric and
    control-flow core, producing binaries whose output is identical to `ulang build`.

All three self-hosting stages — parsing, semantic analysis, and optimization/code
generation — are complete, each validated against the Python reference.

```sh
cp path/to/program.ul input.ul
ulang run selfhost/compiler/lexer.ul     # token stream for input.ul
ulang run selfhost/compiler/parser.ul    # syntax tree (S-expressions) for input.ul
```

## Optimizations

The compiler applies behavior-preserving optimizations to every execution engine:

- **Constant folding** — compile-time evaluation of constant expressions, using the same
  arithmetic as the runtime so results are identical.
- **Constant propagation** — immutable `let`/`const` bindings are substituted and folded.
- **Dead-code elimination** — branches with constant conditions, `while false` loops, and
  unreachable code are removed.
- **Algebraic identities** — `x + 0`, `x * 1`, and similar simplifications.
- **String folding** — constant concatenation and interpolation are precomputed.
- **Bytecode peephole** — redundant jumps and unreachable instructions are removed.

Optimizations are on by default; set `ULANG_NO_OPT=1` to disable them.

## Standard library

Modules available via `import`: `fs`, `json`, `math`, `time`, `str`, `random`, `list`.

## Tooling

```sh
ulang init myapp          # scaffold a project (ulang.toml + src/main.ul)
ulang add greeter         # add a dependency and install it
ulang install             # install dependencies from the lockfile
ulang update              # re-resolve to the newest allowed versions
ulang publish             # publish the current package to the registry
ulang search json         # search the registry
ulang fmt file.ul         # print canonical formatting
ulang fmt file.ul -w      # format in place
ulang escape file.ul      # show stack vs heap allocation analysis
ulang lsp                 # start the language server for editors
```

Package management is described in [docs/packages.md](docs/packages.md); editor
integration in [docs/editor-setup.md](docs/editor-setup.md).

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
- `src/optimizer.py`, `src/peephole.py` — AST optimizations and bytecode peephole.
- `src/gc_heap.py`, `src/memory.py` — generational tracing garbage collector.
- `src/platform_abi.py` — cross-platform abstraction (OS/arch, toolchain, libraries).
- `src/codegen.py`, `src/native.py` — LLVM IR generation and native compilation.
- `src/jit.py`, `src/tiered.py` — JIT engine and tiered execution.
- `src/runtime.py` — tasks, nurseries, and channels.
- `src/escape.py` — escape analysis (stack vs heap allocation).
- `src/ffi.py` — C foreign-function interface.
- `src/formatter.py` — canonical source formatter.
- `src/lsp.py`, `src/lsp_analysis.py` — Language Server Protocol implementation.
- `src/semver.py`, `src/manifest.py`, `src/registry.py`, `src/resolver.py`, `src/lockfile.py`, `src/packages.py`, `src/loader.py` — package manager.
- `src/repl.py` — interactive shell.
- `src/stdlib.py`, `src/builtins_mod.py` — built-in functions and modules.

## Repository layout

```
spec/            language specification and formal grammar
examples/        example .ul programs
examples/native/ programs the native backend compiles to binaries
selfhost/        the Ulang compiler written in Ulang (selfhost/compiler/)
src/             compiler implementation
editors/         editor integrations (VS Code extension)
docs/            guides and reference documentation
tests/           compiler tests
bench/           benchmarks across execution engines
```

- [`spec/SPEC.md`](spec/SPEC.md) — language specification.
- [`spec/grammar.ebnf`](spec/grammar.ebnf) — formal EBNF grammar.
- [`examples/`](examples/) — example programs.

## Documentation

Full guides and references live in [`docs/`](docs/):

- [Getting Started](docs/getting-started.md)
- [Language Reference](docs/language-reference.md)
- [Standard Library](docs/stdlib.md)
- [FFI Guide](docs/ffi.md)
- [Concurrency Tutorial](docs/concurrency.md)
- [Package Management](docs/packages.md)
- [Memory Management](docs/memory.md)
- [Cross-Platform Support](docs/cross-platform.md)
- [Editor Setup](docs/editor-setup.md)
- [Why Ulang?](docs/why-ulang.md)

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
