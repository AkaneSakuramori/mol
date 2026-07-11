# Cross-Platform Support

Ulang runs on Linux, macOS, and Windows across common processor architectures
(x86-64 and ARM64). Language semantics are identical on every platform: the same
program produces the same result everywhere, on every execution engine.

## Supported platforms

| OS | Architectures | Interpreter | VM | JIT | Native build |
|----|---------------|:-----------:|:--:|:---:|:------------:|
| Linux | x86-64, ARM64 | ✅ | ✅ | ✅ | ✅ |
| macOS | x86-64, ARM64 | ✅ | ✅ | ✅ | ✅ |
| Windows | x86-64 | ✅ | ✅ | ✅ | ✅ |

The interpreter and VM are pure Python and run anywhere Python 3.10+ runs. The JIT and
native backend additionally require `llvmlite` and a C compiler.

## Requirements

- **Interpreter / VM / REPL / LSP / package manager:** Python 3.10 or newer. No other
  dependencies.
- **Native builds (`ulang build`) and JIT (`ulang jit`):** `llvmlite` and a C compiler
  (`cc`, `gcc`, or `clang`; on Windows, MinGW or clang).

Check your environment:

```sh
ulang doctor
```

This reports the detected OS and architecture, the Python version, whether a C compiler
is available, and whether the native backend is installed.

## Installation

A portable installer creates a launcher for your platform:

```sh
python3 install.py
```

- On Unix, this installs a `ulang` shell launcher (default `~/.local/bin`).
- On Windows, it installs a `ulang.cmd` launcher (default
  `%LOCALAPPDATA%\Programs\ulang`).

Add the install directory to your `PATH`, then run `ulang version`.

## Platform abstraction

All platform-specific behavior is centralized in `src/platform_abi.py`, which resolves:

- **Executable names** — `app` on Unix, `app.exe` on Windows. `ulang build` applies the
  correct suffix automatically.
- **Shared libraries** — `libz.so` (Linux), `libz.dylib` (macOS), `z.dll` (Windows).
- **C library resolution** for FFI — the right `libc`/`libm` equivalent per platform
  (`libc.so.6`, `libSystem.dylib`, `msvcrt.dll`, …).
- **Relocation model** — position-independent code on Unix; default on Windows.
- **C compiler discovery** — searches for `cc`/`gcc`/`clang`; override with the
  `ULANG_CC` environment variable.

## Line endings

Source files are accepted with Unix (`\n`), Windows (`\r\n`), or classic-Mac (`\r`) line
endings — all tokenize and execute identically. The formatter always writes `\n` so
formatted files are byte-identical across platforms.

## The `platform` module

Programs can inspect the host at runtime while keeping identical logic:

```ulang
import platform

fn main():
    print("running on ${platform.os}/${platform.arch}")
    if platform.is_windows():
        print("windows-specific path handling")
```

Members: `os` (`"linux"`, `"macos"`, `"windows"`), `arch` (`"x86_64"`, `"aarch64"`, …),
`exe_ext`, `path_sep`, `line_sep`, and the predicates `is_linux()`, `is_macos()`,
`is_windows()`.

## Native binaries

`ulang build` produces a standalone native executable for the host platform. It:

- Discovers a C compiler automatically (or uses `ULANG_CC`).
- Applies the platform's executable suffix.
- Links the portable C garbage-collector runtime.
- Uses the correct relocation model for the platform.

The generated binary has no dependency on Python or the Ulang toolchain.

## Continuous integration

Ulang's CI runs the full test suite on **Linux, macOS, and Windows** (Python 3.10 and
3.12) and additionally builds and runs a native binary on each, so cross-platform
behavior is verified on every change.

## Guarantees

- **Identical semantics.** Every language feature behaves the same on every platform.
- **Engine parity.** Interpreter, VM, JIT, and native backend produce the same results.
- **Backward compatibility.** Existing programs and projects continue to work unchanged.
