import time


WHITE = 0
GRAY = 1
BLACK = 2

YOUNG = 0
OLD = 1

PROMOTE_AFTER = 2


class Record:
    __slots__ = ("obj", "gen", "color", "survived", "size")

    def __init__(self, obj, size):
        self.obj = obj
        self.gen = YOUNG
        self.color = WHITE
        self.survived = 0
        self.size = size


class Stats:
    def __init__(self):
        self.total_allocated = 0
        self.bytes_allocated = 0
        self.minor_collections = 0
        self.major_collections = 0
        self.objects_reclaimed = 0
        self.bytes_reclaimed = 0
        self.total_pause_ms = 0.0
        self.max_pause_ms = 0.0
        self.promotions = 0

    def snapshot(self, heap):
        return {
            "live_objects": len(heap.records),
            "live_bytes": sum(r.size for r in heap.records.values()),
            "young": sum(1 for r in heap.records.values() if r.gen == YOUNG),
            "old": sum(1 for r in heap.records.values() if r.gen == OLD),
            "total_allocated": self.total_allocated,
            "bytes_allocated": self.bytes_allocated,
            "minor_collections": self.minor_collections,
            "major_collections": self.major_collections,
            "objects_reclaimed": self.objects_reclaimed,
            "bytes_reclaimed": self.bytes_reclaimed,
            "promotions": self.promotions,
            "total_pause_ms": round(self.total_pause_ms, 4),
            "max_pause_ms": round(self.max_pause_ms, 4),
        }


class GcHeap:
    def __init__(self, tracer, roots_fn=None, young_threshold=1024, clock=None):
        self.tracer = tracer
        self.roots_fn = roots_fn or (lambda: [])
        self.young_threshold = young_threshold
        self.records = {}
        self.young = set()
        self.old = set()
        self.stats = Stats()
        self._clock = clock or time.perf_counter
        self._incremental = None

    def allocate(self, obj, size=1):
        key = id(obj)
        if key in self.records:
            return obj
        rec = Record(obj, size)
        self.records[key] = rec
        self.young.add(key)
        self.stats.total_allocated += 1
        self.stats.bytes_allocated += size
        if len(self.young) >= self.young_threshold:
            self.collect(full=False)
        return obj

    def track(self, obj, size=1):
        return self.allocate(obj, size)

    def _roots(self):
        return list(self.roots_fn())

    def collect(self, full=False):
        start = self._clock()
        for rec in self.records.values():
            rec.color = WHITE

        gray = []
        for root in self._roots():
            self._shade(root, gray)
        if not full:
            for key in self.old:
                rec = self.records.get(key)
                if rec is not None and rec.color == WHITE:
                    rec.color = GRAY
                    gray.append(key)

        while gray:
            key = gray.pop()
            rec = self.records.get(key)
            if rec is None or rec.color == BLACK:
                continue
            rec.color = BLACK
            for child in self.tracer(rec.obj):
                self._shade(child, gray)

        reclaimed, bytes_freed, promoted = self._sweep(full)

        elapsed = (self._clock() - start) * 1000.0
        self.stats.total_pause_ms += elapsed
        self.stats.max_pause_ms = max(self.stats.max_pause_ms, elapsed)
        self.stats.objects_reclaimed += reclaimed
        self.stats.bytes_reclaimed += bytes_freed
        self.stats.promotions += promoted
        if full:
            self.stats.major_collections += 1
        else:
            self.stats.minor_collections += 1
        return reclaimed

    def _shade(self, obj, gray):
        key = id(obj)
        rec = self.records.get(key)
        if rec is not None and rec.color == WHITE:
            rec.color = GRAY
            gray.append(key)

    def _sweep(self, full):
        reclaimed = 0
        bytes_freed = 0
        promoted = 0
        candidates = list(self.records.keys()) if full else list(self.young)
        for key in candidates:
            rec = self.records.get(key)
            if rec is None:
                continue
            if rec.color == BLACK:
                rec.survived += 1
                if rec.gen == YOUNG and rec.survived >= PROMOTE_AFTER:
                    rec.gen = OLD
                    self.young.discard(key)
                    self.old.add(key)
                    promoted += 1
            else:
                reclaimed += 1
                bytes_freed += rec.size
                del self.records[key]
                self.young.discard(key)
                self.old.discard(key)
        return reclaimed, bytes_freed, promoted

    def collect_step(self, budget=64):
        if self._incremental is None:
            for rec in self.records.values():
                rec.color = WHITE
            gray = []
            for root in self._roots():
                self._shade(root, gray)
            self._incremental = {"gray": gray, "phase": "mark"}
        state = self._incremental
        if state["phase"] == "mark":
            steps = 0
            gray = state["gray"]
            while gray and steps < budget:
                key = gray.pop()
                rec = self.records.get(key)
                if rec is None or rec.color == BLACK:
                    continue
                rec.color = BLACK
                for child in self.tracer(rec.obj):
                    self._shade(child, gray)
                steps += 1
            if not gray:
                state["phase"] = "sweep"
            return False
        if state["phase"] == "sweep":
            reclaimed, bytes_freed, promoted = self._sweep(full=True)
            self.stats.objects_reclaimed += reclaimed
            self.stats.bytes_reclaimed += bytes_freed
            self.stats.major_collections += 1
            self._incremental = None
            return True
        return True

    def collect_incremental(self, budget=64):
        while not self.collect_step(budget):
            pass
        return self.stats.objects_reclaimed

    def snapshot(self):
        return self.stats.snapshot(self)
