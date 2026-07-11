# Standard Library

The standard library ships with the toolchain. Modules are brought in with `import`.

## Built-in functions

Always available, no import needed:

| Function | Description |
|----------|-------------|
| `print(x)` | Print a value followed by a newline. |
| `len(x)` | Length of a string, list, dict, or tuple. |
| `range(a, b)` | List of integers from `a` up to (not including) `b`. |
| `panic(msg)` | Abort with a message. |
| `int(x)`, `float(x)`, `str(x)`, `bool(x)` | Conversions. |
| `abs(x)`, `min(...)`, `max(...)`, `sum(list)` | Numeric helpers. |
| `Some(x)`, `None`, `Ok(x)`, `Err(x)` | Option and Result constructors. |

## Methods

### List

`map(f)`, `filter(f)`, `reduce(f, init)`, `each(f)`, `len()`, `push(x)`, `pop()`,
`contains(x)`, `reverse()`, `sort()`, `first()`, `last()`, `join(sep)`.

```ulang
let squares = [1, 2, 3, 4].map(n => n * n)      # [1, 4, 9, 16]
let evens = [1, 2, 3, 4].filter(n => n % 2 == 0) # [2, 4]
let total = [1, 2, 3].reduce((a, b) => a + b, 0) # 6
```

`first()` and `last()` return an `Option`.

### String

`len()`, `upper()`, `lower()`, `split(sep)`, `trim()`, `replace(a, b)`, `contains(s)`,
`starts_with(s)`, `ends_with(s)`, `chars()`.

```ulang
let parts = "a,b,c".split(",")   # ["a", "b", "c"]
print("Hello".lower())           # hello
```

### Dict

`len()`, `keys()`, `values()`, `get(k)`, `has(k)`, `set(k, v)`, `remove(k)`.

```ulang
let scores = {"ada": 90}
print(scores.keys())        # ["ada"]
print(scores.get("bob"))    # None
```

`get(k)` returns an `Option`.

### Option and Result

`is_some()`, `is_none()`, `is_ok()`, `is_err()`, `unwrap()`, `unwrap_or(default)`.

```ulang
let x = Some(5)
print(x.unwrap_or(0))   # 5
print(None.unwrap_or(0)) # 0
```

## Modules

### `fs` — filesystem

| Function | Returns |
|----------|---------|
| `fs.read(path)` | `Result[str, str]` |
| `fs.write(path, data)` | `Result[none, str]` |
| `fs.open(path)` | file handle with `.write`, `.read`, `.close` |
| `fs.exists(path)` | `bool` |

### `json`

| Function | Description |
|----------|-------------|
| `json.dumps(value)` | Serialize to a JSON string. |
| `json.loads(text)` | Parse a JSON string. |

### `math`

`math.sqrt(x)`, `math.pow(x, y)`, `math.floor(x)`, `math.ceil(x)`, `math.abs(x)`,
and the constants `math.pi`, `math.e`.

### `time`

`time.now()` (seconds), `time.now_ms()` (milliseconds), `time.sleep(ms)`.

### `str`

`str.from_int(n)`, `str.to_int(s)` (returns `Result`), `str.repeat(s, n)`,
`str.join(sep, list)`.

### `random`

`random.int(lo, hi)`, `random.float()`, `random.choice(list)`, `random.seed(n)`.

### `list`

`list.range(a, b)`, `list.repeat(x, n)`, `list.concat(a, b)`.

## Example

```ulang
import math
import json

type Point:
    x: int
    y: int
derive(Serialize)

fn main():
    print(math.sqrt(144.0))       # 12.0
    let p = Point(3, 4)
    print(json.dumps(p))          # {"x": 3, "y": 4}
```
