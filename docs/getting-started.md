# Getting Started

This guide takes you from nothing to a running Ulang program.

## Requirements

- Python 3.10 or newer (the toolchain runs on Python during development).
- A C compiler (`gcc` or `clang`) for building native binaries.
- `llvmlite` for the native backend and JIT.

```sh
pip install llvmlite
```

## Get the code

```sh
git clone https://github.com/AkaneSakuramori/mol.git
cd mol
```

The command-line tool is `src/ulang.py`. For convenience you can alias it:

```sh
alias ulang="python3 $(pwd)/src/ulang.py"
```

The rest of this guide assumes that alias.

## Your first program

Create `hello.ul`:

```ulang
fn main():
    print("hello, world")
```

Run it:

```sh
ulang run hello.ul
# hello, world
```

## A real program

`greet.ul`:

```ulang
fn greet(name: str) -> str:
    return "hello, ${name}"

fn main():
    let names = ["ada", "linus", "grace"]
    for name in names:
        print(greet(name))
```

```sh
ulang run greet.ul
# hello, ada
# hello, linus
# hello, grace
```

## Ways to run

Ulang has several execution engines that all produce the same results:

```sh
ulang run   file.ul          # tree-walking interpreter (default)
ulang runvm file.ul          # bytecode virtual machine
ulang jit   file.ul          # tiered JIT (native for hot functions)
ulang build file.ul -o app   # compile to a native binary
./app
```

## Other commands

```sh
ulang check file.ul          # type-check without running
ulang fmt   file.ul          # print canonical formatting
ulang fmt   file.ul -w       # format in place
ulang repl                   # interactive shell
ulang version
```

## Start a project

```sh
ulang init myapp             # creates ulang.toml and src/main.ul
```

## Next steps

- [Language Reference](language-reference.md) for the full syntax.
- [Concurrency Tutorial](concurrency.md) to run tasks in parallel.
- [Standard Library](stdlib.md) for the built-in modules.
