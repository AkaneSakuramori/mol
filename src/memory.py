import os

from gc_heap import GcHeap, Record
from values import Struct, Variant, Closure


_MANAGED = (list, dict, tuple, Struct, Variant, Closure)


def trace_value(obj):
    t = type(obj)
    if t is list or t is tuple:
        return obj
    if t is dict:
        return list(obj.keys()) + list(obj.values())
    if isinstance(obj, Struct):
        return obj.fields.values()
    if isinstance(obj, Variant):
        return obj.values
    if isinstance(obj, Closure):
        env = obj.env
        if env is not None and hasattr(env, "vars"):
            return (env,)
        return ()
    if _is_env(obj):
        return _env_refs(obj)
    return ()


def _is_env(obj):
    return hasattr(obj, "vars") and hasattr(obj, "parent")


def _env_refs(env):
    refs = list(env.vars.values())
    if env.parent is not None:
        refs.append(env.parent)
    return refs


class MemoryManager:
    def __init__(self, roots_fn, young_threshold=8192, auto=True):
        self.heap = GcHeap(trace_value, roots_fn=roots_fn, young_threshold=1 << 60)
        self.enabled = bool(os.environ.get("ULANG_GC"))
        self.auto = auto
        self.auto_threshold = young_threshold
        self._since_collect = 0
        self._records = self.heap.records
        self._young = self.heap.young
        self._stats = self.heap.stats

    def record(self, obj):
        if not self.enabled or not isinstance(obj, _MANAGED):
            return obj
        key = id(obj)
        recs = self._records
        if key not in recs:
            recs[key] = Record(obj, 1)
            self._young.add(key)
            self._stats.total_allocated += 1
            self._since_collect += 1
        return obj

    def safepoint(self):
        if self.auto and self._since_collect >= self.auto_threshold:
            self._since_collect = 0
            self.heap.collect(full=False)

    def collect(self, full=True):
        self._since_collect = 0
        return self.heap.collect(full=full)

    def collect_incremental(self, budget=256):
        self._since_collect = 0
        return self.heap.collect_incremental(budget)

    def stats(self):
        return self.heap.snapshot()
