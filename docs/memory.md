# Memory Management

Ulang uses **tracing garbage collection** for heap-allocated values. The design is a
generational, incremental mark-sweep collector — chosen for its ability to reclaim
cyclic data (which reference counting cannot), keep pause times bounded through
incremental marking, and stay simple and maintainable.

## Architecture

Memory management spans the whole toolchain:

- **Interpreter and VM.** Heap values — lists, dicts, tuples, structs, enum variants,
  and closures — are tracked by a tracing collector. Roots are the global environment
  and the live call stack. Collection happens at statement boundaries (safepoints), so a
  value in the middle of being computed is never reclaimed.
- **Native backend.** Every native binary links a C mark-sweep collector
  (`runtime/ulang_gc.c`) and initializes it in `main`. This is the real allocator for
  compiled code as heap types are lowered to native.
- **Concurrency.** Tasks run on their own interpreter call stacks, each contributing its
  frames as roots; collection is coordinated at safepoints.
- **FFI.** Values crossing to C are marshaled by value, so foreign calls do not hold
  managed references across the boundary.

The collector is:

- **Tracing** — reachability is computed from roots, so cycles are reclaimed.
- **Generational** — objects that survive collections are promoted to an old generation;
  minor collections scan only the young generation (treating old objects as roots),
  which is where most garbage is.
- **Incremental** — marking can be split into bounded steps (`collect_step`) to keep any
  single pause small.

## Semantics and compatibility

Garbage collection does not change observable behavior. Programs produce identical output
whether the collector is active or not; it only reclaims memory that is no longer
reachable. Existing code needs no changes.

In the interpreter, tracking is **off by default** so ordinary runs have zero overhead —
the host already manages memory correctly. Turn the tracing collector on when you want
its statistics or deterministic collection:

- Set the environment variable `ULANG_GC=1`, or
- Call `gc_enable()` from within a program.

## Built-in functions

Available in every program:

| Function | Description |
|----------|-------------|
| `gc_enable()` | Start tracking allocations. |
| `gc_disable()` | Stop tracking. |
| `gc_collect()` | Run a full collection; returns the number of objects reclaimed. |
| `gc_alloc_count()` | Total tracked allocations so far. |
| `gc_live_count()` | Live tracked objects right now. |

```ulang
fn main():
    gc_enable()
    var i = 0
    while i < 100:
        let scratch = [i, i, i]
        i += 1
    print(gc_collect())     # reclaims the dead scratch lists
```

## Inspecting collection

`ulang gc-stats <file.ul>` runs a program with the collector enabled and prints
statistics:

```sh
ulang gc-stats program.ul
```

Output includes total allocations, live objects, young/old counts, minor and major
collection counts, objects reclaimed, promotions, and the maximum pause time.

## Performance

The collector is designed so that programs that do not allocate on the heap pay nothing,
and allocation-heavy programs pay only the tracing cost when collection is enabled.

Run the benchmark:

```sh
python3 bench/memory_benchmark.py
```

Representative results: scalar workloads show no measurable overhead; allocation-heavy
workloads reclaim the overwhelming majority of their garbage, with the tracing cost
incurred only when the collector is enabled.

## Native runtime

The C collector in `runtime/ulang_gc.c` provides:

- `ul_alloc(value, nchildren)` — allocate a managed object.
- `ul_set_child(obj, index, child)` — record a reference for tracing.
- `ul_gc_push_root` / `ul_gc_pop_root` — manage the root stack.
- `ul_gc_collect()` — mark from roots and sweep; returns objects reclaimed.
- `ul_gc_live_objects`, `ul_gc_total_allocated`, `ul_gc_collections` — statistics.

It is unit-tested (`runtime/test_gc.c`) for reclamation, cycle collection, and root
handling, and linked into every native build.
