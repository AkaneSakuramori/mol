# Mol Language Specification — v0

Status: frozen for Step 1. This is the contract the compiler is built against.

## 1. Overview

Mol is a compiled, statically-typed language with type inference and a layout-based,
readable syntax. It targets native code for high performance and ships an interpreter/VM
for development and scripting. This document defines the v0 surface language: lexical
structure, types, declarations, statements, and semantics.

## 2. Lexical Structure

- Source is UTF-8. Files use the `.mol` extension.
- Layout is significant. Indentation opens and closes blocks. The lexer emits
  `INDENT`, `DEDENT`, and `NEWLINE` tokens. Indentation is spaces; a block's indent must
  be consistent.
- Line comments start with `#` and run to end of line.
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`.
- Integer literals allow `_` separators: `1_000_000`.
- Float literals require a digit on each side of the dot: `3.14`, `0.5`.
- String literals are double-quoted and support `${expr}` interpolation and escapes
  `\n \t \\ \" \${`.

### Keywords

```
fn let var const type enum trait impl derive pub import from as
if elif else match while for in with as defer return break continue
and or not true false none
```

## 3. Types

- Primitive: `int`, `float`, `bool`, `str`.
- `none` is the single value of the unit-like absence type used with `Option`.
- Composite:
  - List: `[T]`
  - Dict: `{K: V}`
  - Tuple: `(A, B, ...)`
  - Function: `fn(A, B) -> R`
- Optional: `T?` is sugar for `Option[T]`.
- `dyn`: the dynamic escape hatch. Values typed `dyn` are checked at runtime. Crossing a
  `dyn` boundary is where dynamic behavior is allowed; the compiler may warn.
- User types: `type` (product/record), `enum` (sum type with payload variants).

### Built-in generic types

- `Option[T]` with variants `Some(T)` and `None`.
- `Result[T, E]` with variants `Ok(T)` and `Err(E)`.

## 4. Declarations

- `const NAME = expr` — module-level compile-time-known constant.
- `fn name(params) -> Ret:` — function. `pub` exports it. Return type optional (inferred).
- `type Name:` — record with typed fields, optional `derive(...)`.
- `enum Name:` — variants, each optionally carrying a tuple of types.
- `trait Name:` — set of method signatures.
- `impl Type:` or `impl Trait for Type:` — method implementations.
- In trait and `impl` methods, a leading `self` parameter is the receiver and needs no
  type annotation; its type is the implementing type.

## 5. Bindings & Mutability

- `let` binds an immutable value. Rebinding or mutation is a compile error.
- `var` binds a mutable variable.
- Immutability is the default to make intent explicit and enable optimization.

## 6. Statements

- `let` / `var` / assignment (`= += -= *= /= %=`).
- `if / elif / else`, `while`, `for x in iterable`, `match`.
- `with expr as name:` — scoped resource; runs cleanup on scope exit.
- `defer expr` — runs `expr` when the enclosing function returns.
- `return`, `break`, `continue`.
- `match` arms use `pattern [if guard] => expr-or-block`. Matches must be exhaustive.

## 7. Expressions

- Precedence (low to high): lambda, ternary (`x if c else y`), `or`, `and`, `not`,
  comparison, `+ -`, `* / %`, unary `-`, postfix (call/index/field/`?`).
- Lambdas: `x => x + 1` or `(a: int, b: int) => a + b`, with block bodies allowed.
- `?` postfix propagates `Err`/`None` out of the current function.
- String interpolation evaluates `${expr}` and converts via the `Display` trait.

## 8. Error Handling

- No exceptions for control flow. Recoverable errors are `Result[T, E]`; absence is
  `Option[T]`. `?` unwraps `Ok/Some` or returns the `Err/None` early.
- `panic(msg)` aborts on unrecoverable programmer error only.

## 9. Semantics Notes (v0)

- Evaluation is eager, left-to-right.
- Integer is 64-bit signed; float is 64-bit IEEE-754.
- Strings are immutable UTF-8.
- Lists and dicts are heap-allocated, reference-semantics containers.
- Functions are first-class values and may capture their environment (closures).

## 10. Out of Scope for v0

Concurrency syntax (`nursery`, `spawn`, channels), macros, and the full trait-resolution
algorithm are specified in later steps. v0 locks the core surface so the lexer, parser,
type checker, and interpreter (Steps 2–5) have a stable target.
