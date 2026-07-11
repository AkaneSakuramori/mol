# Changelog

## Unreleased

### Added
- Language Server Protocol implementation (`ulang lsp`): diagnostics, hover,
  completion, go-to-definition, document symbols, and formatting over JSON-RPC.
- VS Code extension in `editors/vscode` with a TextMate grammar for highlighting.
- Editor setup guide covering VS Code, Neovim, and other LSP clients.

## 1.0.0

First stable release. The complete toolchain is in place: source to native code,
with development engines for fast iteration.

### Language
- Static typing with type inference and no-null semantics (`Option`, `Result`, `?`).
- Immutable-by-default bindings (`let` / `var`).
- Records (`type`), sum types (`enum`), traits, and generics with bounds.
- Exhaustive pattern matching.
- First-class functions, closures, lambdas, and string interpolation.
- Structured concurrency (`nursery`, `spawn`, channels).
- C foreign-function interface (`extern fn`).

### Toolchain
- Lexer, parser, and static type checker.
- Tree-walking interpreter.
- Bytecode compiler and stack virtual machine.
- REPL.
- Native backend via LLVM producing standalone executables.
- Tiered JIT that compiles hot functions to native code at runtime.
- Escape analysis for stack vs heap allocation.
- Standard library: `fs`, `json`, `math`, `time`, `str`, `random`, `list`.
- Formatter (`ulang fmt`) and project scaffolding (`ulang init`).

### Verified
- 9 test suites covering every stage.
- Native and JIT output verified identical to the interpreter.
- Bytecode VM output verified identical to the interpreter.
- Self-hosting: a Ulang tokenizer tokenizes Ulang source.
- Benchmarks: JIT ~1700x over the interpreter on recursive workloads;
  native in the millisecond range.
