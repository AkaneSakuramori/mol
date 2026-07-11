# Why Ulang?

Ulang is a compiled, statically-typed language designed around a small set of goals.
This page explains what it is trying to be and the choices that follow from that.

## The goals

### Readable, low-ceremony syntax

Code is read far more often than it is written. Ulang uses significant indentation,
type inference, and a small keyword set so that programs stay close to the ideas they
express. You annotate types at function boundaries, not everywhere.

```ulang
fn greet(name: str) -> str:
    return "hello, ${name}"
```

### Fast execution

Ulang compiles to native machine code through LLVM. For long-running programs a tiered
JIT compiles hot functions to native code at runtime. The same source also runs on a
tree-walking interpreter and a bytecode VM during development, so you get a fast edit
loop and fast execution from one language.

### Safe by default

- **No null.** Absence is modeled with `Option`, and fallible operations return
  `Result`. The `?` operator makes propagating errors concise. Whole classes of
  null-reference and forgotten-error bugs are ruled out by the type system.
- **Immutable by default.** `let` bindings cannot be reassigned; you opt into mutation
  with `var`.
- **Exhaustive matching.** `match` must cover every case.

### Concurrency that is easy to reason about

Structured concurrency is built in. Tasks live inside a `nursery` scope that waits for
them, so background work cannot leak, and errors propagate to the enclosing scope.
There is no global interpreter lock.

### Deploys as one file

`ulang build` produces a standalone native executable. There is no separate runtime to
install alongside it.

### Interoperable

`extern fn` calls C libraries directly, so Ulang can reuse existing native code instead
of reimplementing it.

## Design choices that follow

| Choice | Reason |
|--------|--------|
| Significant indentation | Less visual noise; structure matches layout. |
| Type inference | Static safety without annotation fatigue. |
| `Option` / `Result` instead of exceptions and null | Errors are visible in types and handled explicitly. |
| Immutable bindings by default | Intent is explicit; enables optimization. |
| Traits over inheritance | Composition without deep class hierarchies. |
| Structured concurrency | Task lifetimes follow lexical scope. |
| Multiple execution engines | Fast iteration during development, fast code in production. |

## Where Ulang is today

Ulang 1.0 is a complete, working toolchain: a lexer, parser, type checker, tree-walking
interpreter, bytecode VM, tiered JIT, and an LLVM native backend, plus structured
concurrency, a C FFI, a standard library, and tooling (formatter, project scaffolding).
Its test suite runs in continuous integration, and the interpreter, VM, JIT, and native
backend are checked to produce identical results.

It is honest about its stage. The compiler is currently written in Python; the native
backend compiles the numeric and control-flow core, while heap-heavy programs run on the
interpreter and VM. The roadmap beyond 1.0 is stabilization and depth: broader native
coverage, a self-hosting compiler, richer tooling, and an ecosystem.

## Who it is for

Ulang is for people who want a language that reads like a scripting language but
compiles and runs like a systems language, with safety and concurrency built in rather
than bolted on. It is also for anyone who wants to study how a language is built: the
implementation is small, staged, and readable.
