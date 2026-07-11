# Changelog

## 1.6.0

### Added
- Cross-platform support for Linux, macOS, and Windows (x86-64 and ARM64) with identical
  language semantics on every platform and execution engine.
  - `src/platform_abi.py`: central abstraction for executable/shared-library naming,
    FFI library resolution, relocation model, and C-compiler discovery (`ULANG_CC`).
  - `ulang build` now discovers a C compiler automatically, applies the platform's
    executable suffix, and links the portable GC runtime on every OS.
  - `platform` standard-library module (`os`, `arch`, `exe_ext`, `path_sep`, `line_sep`,
    `is_linux`/`is_macos`/`is_windows`).
  - `ulang platform` and `ulang doctor` commands.
  - Portable installer (`install.py`) producing a launcher for Unix or Windows.
  - Cross-platform CI matrix (Linux/macOS/Windows, Python 3.10 and 3.12) that also builds
    and runs a native binary on each OS.
  - Cross-platform guide (`docs/cross-platform.md`).

### Fixed
- The lexer now accepts Windows (`\r\n`) and classic-Mac (`\r`) line endings, producing
  identical tokens and output to Unix (`\n`). The formatter always writes `\n`.
- FFI library resolution is portable instead of assuming Linux `.so` names.

## 1.5.0

### Added
- Memory management: a generational, incremental mark-sweep tracing garbage collector.
  - Interpreter/VM: tracks lists, dicts, tuples, structs, enum variants, and closures;
    roots are globals and the live call stack; collection runs at statement safepoints.
    Reclaims cycles that reference counting cannot. Off by default (zero overhead);
    enable with `ULANG_GC=1` or `gc_enable()`.
  - Native backend: every binary links and initializes a C mark-sweep collector
    (`runtime/ulang_gc.c`), unit-tested in `runtime/test_gc.c`.
  - Built-ins `gc_enable`, `gc_disable`, `gc_collect`, `gc_alloc_count`, `gc_live_count`,
    and the `ulang gc-stats` command.
  - Memory management guide (`docs/memory.md`) and `bench/memory_benchmark.py`.
- Program output is identical with the collector on or off; existing code is unaffected.

## 1.4.0

### Added
- Compiler optimizations (behavior-preserving, on by default, `ULANG_NO_OPT=1` to
  disable): constant folding and propagation through immutable bindings, dead-branch and
  dead-loop elimination, algebraic identities, constant string folding, and a bytecode
  peephole pass. Verified to produce identical output on the interpreter and VM.
- Self-hosting progress: a complete lexer written in Ulang (`selfhost/lexer.ul`) whose
  output is conformance-tested against the reference lexer.
- Package manager: `ulang install`, `add`, `remove`, `update`, `publish`, `search`,
  and `list`. Manifests (`ulang.toml`), lockfiles (`ulang.lock`) for reproducible
  builds, semantic-version constraints (`^`, `~`, ranges), a dependency resolver with
  conflict detection, and a content-addressed registry with SHA-256 verification.
- `import <package>` loads installed packages from `ulang_modules/`.
- Package management guide in `docs/packages.md`.
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
