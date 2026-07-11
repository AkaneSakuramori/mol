# Language Reference

This is a practical reference for the Ulang language. For the formal contract see
[`spec/SPEC.md`](../spec/SPEC.md) and [`spec/grammar.ebnf`](../spec/grammar.ebnf).

## Comments

```ulang
# a line comment runs to the end of the line
```

## Bindings

`let` is an immutable binding; `var` is mutable. Types are inferred and rarely need
annotation.

```ulang
let x = 10          # immutable
var count = 0       # mutable
count += 1
let name: str = "ada"   # explicit annotation
```

Reassigning a `let` is a compile error. Use `var` when a value changes.

## Primitive types

- `int` — 64-bit signed integer
- `float` — 64-bit floating point
- `bool` — `true` or `false`
- `str` — immutable UTF-8 string

Integer literals may use `_` as a separator: `1_000_000`.

## Strings

Strings are double-quoted and support `${expr}` interpolation:

```ulang
let who = "world"
print("hello, ${who}")      # hello, world
print("1 + 1 = ${1 + 1}")   # 1 + 1 = 2
```

Escapes: `\n`, `\t`, `\\`, `\"`, `\${`.

## Operators

- Arithmetic: `+ - * / %`
- Comparison: `== != < <= > >=`
- Logical: `and`, `or`, `not` (short-circuiting)
- Error propagation: postfix `?`

Integer `/` is integer division; if either operand is a float the result is a float.

## Collections

```ulang
let nums = [1, 2, 3]                 # list
let scores = {"ada": 90, "bob": 85}  # dict
let point = (3, 4)                    # tuple
```

Indexing is bounds-checked:

```ulang
let first = nums[0]
let ada = scores["ada"]
```

## Functions

```ulang
fn add(a: int, b: int) -> int:
    return a + b
```

Parameters are typed; the return type is optional when it can be inferred. `pub` marks a
function as exported.

Functions are first-class values and can be passed around and returned.

## Closures and lambdas

```ulang
let double = x => x * 2
let add = (a, b) => a + b

fn make_counter() -> fn() -> int:
    var n = 0
    return () => {
        n += 1
        return n
    }
```

## Control flow

```ulang
if x < 0:
    print("negative")
elif x == 0:
    print("zero")
else:
    print("positive")

while count > 0:
    count -= 1

for i in range(0, 10):
    print(i)
```

`if`/`else` also work as an expression:

```ulang
let label = "pass" if score >= 50 else "fail"
```

## Records (`type`)

```ulang
type User:
    id: int
    name: str
    email: str?
derive(Display)

let u = User(1, "ada", none)
print(u.name)
```

`derive(...)` requests automatically generated behavior such as `Display`, `Serialize`,
and `Deserialize`.

## Enums and pattern matching

```ulang
enum Shape:
    Circle(float)
    Rect(float, float)
    Point

fn area(s: Shape) -> float:
    match s:
        Circle(r)  => 3.14159 * r * r
        Rect(w, h) => w * h
        Point      => 0.0
```

`match` must be exhaustive. Arms can bind payload values and use guards:

```ulang
match n:
    x if x < 0 => print("negative")
    0          => print("zero")
    _          => print("positive")
```

## No null: Option and Result

There is no `null`. Absence is `Option[T]` (`Some`/`None`); fallible results are
`Result[T, E]` (`Ok`/`Err`). `T?` is shorthand for `Option[T]`.

```ulang
fn first_even(nums: [int]) -> int?:
    for n in nums:
        if n % 2 == 0:
            return Some(n)
    return None
```

The `?` operator unwraps `Ok`/`Some` or returns the `Err`/`None` from the current
function:

```ulang
fn load(path: str) -> Result[int, str]:
    let contents = fs.read(path)?     # returns early on Err
    return Ok(contents.len())
```

## Traits and generics

```ulang
trait Greet:
    fn hello(self) -> str

type Dog:
    name: str

impl Greet for Dog:
    fn hello(self) -> str:
        return "woof from ${self.name}"
```

Generics use square brackets with optional bounds:

```ulang
fn max[T: Ord](a: T, b: T) -> T:
    if a > b:
        return a
    return b
```

## Resource cleanup: with and defer

```ulang
with fs.open("out.txt") as f:
    f.write("logged")

fn process():
    defer print("done")     # runs when the function returns
    print("working")
```

## Modules

```ulang
import math
from list import repeat

fn main():
    print(math.sqrt(16.0))
    print(repeat(0, 3))
```

See the [Standard Library](stdlib.md) for available modules.

## Foreign functions

```ulang
extern fn sqrt(x: float) -> float from "m"
```

See the [FFI Guide](ffi.md).

## Concurrency

```ulang
with nursery() as g:
    let a = g.spawn(() => work(1))
    let b = g.spawn(() => work(2))
    print(a.await() + b.await())
```

See the [Concurrency Tutorial](concurrency.md).
