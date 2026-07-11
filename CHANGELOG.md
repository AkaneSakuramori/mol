# Changelog

## 1.8.4

Completes **Stage 2 of the self-hosting roadmap**: the self-hosted compiler now reproduces
every semantic rule the Python reference compiler performs, each proven equivalent.

### Added
- **Pattern validation** (`src/checker.py` and `selfhost/compiler/checker.ul`): a variant
  pattern referencing an unknown variant, or with the wrong number of fields, is reported
  (`unknown variant 'X'`, `variant 'X' expects N field(s), got M`). Recognizes user enum
  variants and the built-in `Some`/`None`/`Ok`/`Err`.
- **Exhaustiveness checking** (`src/checker.py` and `selfhost/compiler/checker.ul`): a
  `match` on a known enum type (a user `enum`, `Option`, or `Result`) that omits variants
  without a catch-all arm is reported (`non-exhaustive match: missing 'X', 'Y'`). Guarded
  arms do not count toward coverage.
- **Visibility / package exports** (`selfhost/compiler/exports.ul`): computes a module's
  public API — the exact set of names the runtime package loader (`src/loader.py`) exposes
  to importers: `pub` functions and types, the variants of `pub` enums, and all consts;
  everything else (non-`pub` items, imports, externs, impls, traits) is private.
- **Constant evaluation** (`selfhost/compiler/consteval.ul`): compile-time evaluation of
  integer and boolean constant expressions — arithmetic, comparisons, boolean logic,
  negation, and constant propagation across `const` declarations — matching the reference
  compiler's folding semantics exactly (including bool-in-arithmetic and
  division/modulo-by-zero handling). Non-constant expressions are reported as such.
- Validation for each subsystem (`tests/test_selfhost_checker.py`,
  `tests/test_selfhost_exports.py`, `tests/test_selfhost_consteval.py`): each is verified
  identical to the reference across curated corpora, all example programs, and randomly
  generated programs.

### Stage 2 complete
The self-hosted semantic analyzer now performs name resolution, type inference and
checking, pattern validation, exhaustiveness checking, visibility/package exports, and
constant evaluation — each proven equivalent to the reference. Stage 3 (optimization and
code generation) has not begun.

### Notes
- Pattern validation and exhaustiveness are additive diagnostics surfaced by `ulang check`;
  runtime behavior is unchanged (`ulang run` does not gate on the checker), and all example
  programs remain valid. The reference and self-hosted checkers were extended together to
  stay equivalent.

## 1.8.3

### Added
- **Self-hosting Stage 2 — type inference and type checking**
  (`selfhost/compiler/checker.ul`). The self-hosted semantic analyzer now performs name
  resolution and type checking in a single pass, mirroring the reference `src/checker.py`:
  type inference for every expression form, resolution of declared type annotations,
  type-mismatch detection, function/method/constructor typing, struct field typing,
  generic and optional handling, `try`/index/attribute typing, and constant handling.
  It produces the same diagnostics in the same order as the reference.
- Validated identical to the reference (`tests/test_selfhost_checker.py`) across a
  type-checking corpus, name-resolution/scope scenarios, all 23 example programs, and 40
  randomly generated typed programs. Inference-variable numbers (`?N`), which come from a
  global counter in the reference, are normalized structurally in the comparison.

### Changed
- Consolidated the self-hosted semantic analysis into a single `checker.ul`, replacing the
  separate `resolver.ul` from the previous release. This matches the reference's unified
  checker and keeps the self-hosted compiler clean (one component per compiler stage). The
  checker subsumes all of the resolver's name-resolution behavior, verified by the scope
  coverage now included in the checker's test.

## 1.8.2

### Changed
- Reorganized the self-hosted compiler into a clean, responsibility-based architecture
  under `selfhost/compiler/` with production names (`lexer.ul`, `parser.ul`). Removed
  obsolete milestone/demo files (`tokenize.ul`, the early `lexer.ul`, `expr_parser.ul`)
  and renamed their tests accordingly. Added `selfhost/compiler/README.md`.

### Added
- **Self-hosting Stage 2 begins — name resolution** (`selfhost/compiler/resolver.ul`).
  It consumes the parser's syntax tree and performs symbol and scope management and
  undefined-name detection, with the same scope rules as the reference (function
  parameters, `let`/`var`, `for` and `match` bindings, `with` aliases, lambda parameters,
  block scoping, and global declarations). Validated identical to the reference across 20
  scope scenarios and all 23 example programs (`tests/test_selfhost_resolver.py`).
- Built-in functions `is_list` and `is_str` — a minimal, genuinely required addition for
  the resolver to walk the syntax tree (distinguishing compound nodes from atoms).

## 1.8.1

### Added
- **Self-hosting Stage 1 complete: a full parser written in Ulang**
  (`selfhost/parser_full.ul`). It is a complete recursive-descent parser covering every
  construct the reference compiler supports: modules; `fn`/`type`/`enum`/`trait`/`impl`
  declarations; `const`, `import` (all forms), and `extern`; generics with bounds;
  parameters, fields, variants, and derives; all statements (`let`/`var`, assignments with
  every compound operator, `return`/`break`/`continue`/`defer`, `if`/`elif`/`else`,
  `while`, `for`, `with`, `match`); full pattern matching (wildcard, binding, literal,
  variant, tuple, guards); lambdas (typed params, block bodies); and the complete
  expression grammar with correct precedence and associativity.
- Reference validation (`test_selfhost_parser_full.py`): the Ulang parser's syntax trees
  are compared against the Python reference parser (via a shared canonical AST
  serialization, `src/ast_serialize.py`) across all 23 example programs plus a 14-case
  stress corpus exercising every construct — 37/37 produce identical trees. Malformed
  input is verified to terminate cleanly (no hang, no host crash).

### Notes
- The self-hosted parser required no new language features. String and float token
  contents are treated as opaque atoms on both sides (the self-hosted lexer does not
  reconstruct literal values), so structural equivalence is validated exactly.

## 1.8.0

### Added
- Self-hosting: a **full layout-aware lexer written in Ulang** (`selfhost/lexer_full.ul`),
  the first step of Stage 1 (completing the self-hosted parser). Unlike the earlier
  demonstration lexer, it produces the complete token stream — including significant
  indentation as `INDENT`/`DEDENT`/`NEWLINE`, comment handling, string skipping, and
  bracket-depth tracking — exactly as the reference lexer does.
- `test_selfhost_lexer_full.py` validates it token-for-token (including all layout tokens)
  against the Python reference lexer on all 23 example programs.

### Notes
- This lexer is the token source the self-hosted parser consumes. Implementing it required
  no new language features and surfaced no language gaps — structs as mutable lexer state,
  lists, and string indexing were sufficient.

## 1.7.0

### Added
- Self-hosting: an **expression parser written in Ulang** (`selfhost/expr_parser.ul`),
  the next compiler stage after the self-hosted lexer. It is a precedence-climbing parser
  producing a canonical AST (serialized as S-expressions) covering operator precedence and
  associativity, unary and postfix operators, function calls, indexing, attribute access,
  list literals, and ternaries.
- `test_selfhost_parser.py` validates the Ulang parser's AST against the Python reference
  parser across a 28-expression corpus, guaranteeing identical structure.

### Notes
- Implementing the parser in Ulang required no new language features, confirming the core
  language is sufficient for real compiler work. It exercises structs (as mutable parser
  state), lists, string operations, and recursion.

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
