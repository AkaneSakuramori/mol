import threading
import queue
import time as _time

import values as V
from values import UlangValue, Builtin, some, ok, err, NONE


class Task(UlangValue):
    __slots__ = ("result", "error", "done", "_thread", "cancelled")

    def __init__(self, fn, interp):
        self.result = None
        self.error = None
        self.done = threading.Event()
        self.cancelled = False
        self._thread = threading.Thread(target=self._run, args=(fn, interp), daemon=True)

    def start(self):
        self._thread.start()

    def _run(self, fn, interp):
        try:
            self.result = interp.call(fn, [])
        except BaseException as e:
            self.error = e
        finally:
            self.done.set()

    def await_(self):
        self.done.wait()
        if self.error is not None:
            raise self.error
        return self.result

    def is_done(self):
        return self.done.is_set()

    def __repr__(self):
        return "<task>"


class Nursery(UlangValue):
    __slots__ = ("interp", "tasks")

    def __init__(self, interp):
        self.interp = interp
        self.tasks = []

    def spawn(self, fn):
        t = Task(fn, self.interp)
        self.tasks.append(t)
        t.start()
        return t

    def join(self):
        first_error = None
        for t in self.tasks:
            t.done.wait()
            if t.error is not None and first_error is None:
                first_error = t.error
        if first_error is not None:
            raise first_error

    def results(self):
        return [t.await_() for t in self.tasks]

    def __repr__(self):
        return "<nursery>"


class Channel(UlangValue):
    __slots__ = ("q",)

    def __init__(self, capacity=0):
        self.q = queue.Queue(capacity if capacity and capacity > 0 else 0)

    def send(self, value):
        self.q.put(value)
        return None

    def recv(self):
        return self.q.get()

    def try_recv(self):
        try:
            return some(self.q.get_nowait())
        except queue.Empty:
            return NONE

    def __repr__(self):
        return "<channel>"


def install(interp):
    g = interp.globals
    g.set("spawn", Builtin("spawn", lambda a: _spawn(interp, a[0])))
    g.set("sleep", Builtin("sleep", lambda a: _sleep(a[0])))
    g.set("channel", Builtin("channel", lambda a: Channel(a[0] if a else 0)))
    g.set("nursery", Builtin("nursery", lambda a: Nursery(interp)))


def _spawn(interp, fn):
    t = Task(fn, interp)
    t.start()
    return t


def _sleep(ms):
    _time.sleep(ms / 1000.0)
    return None


def get_method(obj, name):
    if isinstance(obj, Task):
        if name == "await":
            return Builtin("await", lambda a: obj.await_())
        if name == "is_done":
            return Builtin("is_done", lambda a: obj.is_done())
    if isinstance(obj, Nursery):
        if name == "spawn":
            return Builtin("spawn", lambda a: obj.spawn(a[0]))
        if name == "results":
            return Builtin("results", lambda a: obj.results())
    if isinstance(obj, Channel):
        if name == "send":
            return Builtin("send", lambda a: obj.send(a[0]))
        if name == "recv":
            return Builtin("recv", lambda a: obj.recv())
        if name == "try_recv":
            return Builtin("try_recv", lambda a: obj.try_recv())
    return None
