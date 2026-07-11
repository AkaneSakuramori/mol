# Concurrency Tutorial

Ulang has structured concurrency built in. Tasks are cheap, run without a global
interpreter lock, and always live inside a scope that waits for them.

## Spawning a task

`spawn` starts a function running concurrently and returns a task handle. Call
`.await()` to get its result:

```ulang
fn work(n: int) -> int:
    return n * n

fn main():
    let t = spawn(() => work(6))
    print(t.await())   # 36
```

## Structured concurrency: nurseries

A `nursery` is a scope for tasks. The scope does not exit until every task spawned
inside it has finished. This means tasks can never outlive the scope that created
them — no leaked background work.

```ulang
fn main():
    with nursery() as g:
        let a = g.spawn(() => fetch(1))
        let b = g.spawn(() => fetch(2))
        let c = g.spawn(() => fetch(3))
        print(a.await() + b.await() + c.await())
    # all three tasks are guaranteed finished here
```

If any task fails, the nursery surfaces the error when the scope exits.

## Channels

Channels pass values between tasks. `send` puts a value in; `recv` takes one out,
waiting if necessary.

```ulang
fn produce(ch: dyn):
    ch.send(10)
    ch.send(20)
    ch.send(30)

fn main():
    let ch = channel()
    with nursery() as g:
        g.spawn(() => produce(ch))
        var total = 0
        for i in range(0, 3):
            total += ch.recv()
        print(total)   # 60
```

`try_recv()` returns an `Option` instead of blocking — `Some(value)` if one is ready,
`None` if the channel is empty.

## A producer/consumer pipeline

```ulang
fn producer(ch: dyn, n: int):
    for i in range(0, n):
        ch.send(i * i)

fn main():
    let ch = channel()
    with nursery() as g:
        g.spawn(() => producer(ch, 5))
        var sum = 0
        for i in range(0, 5):
            sum += ch.recv()
        print(sum)   # 0 + 1 + 4 + 9 + 16 = 30
```

## Why structured concurrency

- **No leaks.** A nursery joins its children, so tasks cannot escape their scope.
- **Clear lifetimes.** Concurrency follows the shape of your code, like normal blocks.
- **Errors propagate.** A failing task reports through the enclosing scope instead of
  vanishing.

This is the same model used by Trio and Kotlin's structured concurrency, made a
first-class part of the language.
