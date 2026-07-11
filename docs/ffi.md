# FFI Guide

Ulang can call C library functions directly through its foreign-function interface.
This lets you reuse the entire C ecosystem without writing bindings by hand.

## Declaring a foreign function

Use `extern fn` with a `from "library"` clause:

```ulang
extern fn sqrt(x: float) -> float from "m"
extern fn abs(x: int) -> int from "c"

fn main():
    print(sqrt(16.0))   # 4.0
    print(abs(-42))     # 42
```

- The function name matches the C symbol.
- `from "m"` names the library. `"c"` is the C standard library (libc); `"m"` is the
  math library (libm). Other names are resolved by the platform's dynamic loader.
- Parameter and return types tell Ulang how to marshal values across the boundary.

## Type mapping

| Ulang type | C type |
|------------|--------|
| `int` | 64-bit integer (`long`) |
| `float` | `double` |
| `bool` | `bool` |
| `str` | `char*` (UTF-8, null-terminated) |

Strings are passed as C strings; a `char*` returned from C is read back as a Ulang
`str`.

## A larger example

Calling into libc:

```ulang
extern fn strlen(s: str) -> int from "c"
extern fn getpid() -> int from "c"

fn main():
    print(strlen("hello"))   # 5
    print(getpid() > 0)      # true
```

## How it works

At startup the runtime resolves each `extern fn` to a symbol in the named library and
builds a typed wrapper. Calls marshal arguments to their C representation, invoke the
native function, and convert the result back to a Ulang value.

## Notes and limits

- Match the C signature exactly. A wrong type will misinterpret the value.
- For integer-returning C functions whose width is not 64-bit, prefer the `long`
  variants (for example `labs` instead of `abs`) so the return width matches.
- The FFI is available when running on the interpreter and VM. Only the numeric and
  control-flow core is compiled by the native backend today; FFI-heavy programs run on
  the interpreter or VM.
- There is no automatic memory management across the boundary; treat pointers returned
  by C with care.
