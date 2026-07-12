import math as _math
import time as _time
import random as _random

import values as V
from values import Module, Builtin, Struct, some, ok, err, NONE, ulang_str


class FileHandle(V.UlangValue):
    __slots__ = ("path", "fp", "mode")

    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        self.fp = open(path, mode, encoding="utf-8")

    def __repr__(self):
        return f"<file {self.path}>"


def _fs_read(args):
    path = args[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            return ok(f.read())
    except OSError as e:
        return err(str(e))


def _fs_write(args):
    path, data = args[0], args[1]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ulang_str(data))
        return ok(None)
    except OSError as e:
        return err(str(e))


def _fs_open(args):
    path = args[0]
    mode = args[1] if len(args) > 1 else "w"
    return _FileValue(path, mode)


class _FileValue(V.UlangValue):
    __slots__ = ("path", "fp")

    def __init__(self, path, mode):
        self.path = path
        self.fp = open(path, mode, encoding="utf-8")

    def method(self, name):
        if name == "write":
            return Builtin("write", lambda a: (self.fp.write(ulang_str(a[0])), None)[1])
        if name == "read":
            return Builtin("read", lambda a: self.fp.read())
        if name == "close":
            return Builtin("close", lambda a: self.fp.close())
        return None

    def __repr__(self):
        return f"<file {self.path}>"


def _fs_exists(args):
    import os
    return __import__("os").path.exists(args[0])


def _json_dumps(args):
    import json as _json
    return _json.dumps(_to_plain(args[0]))


def _json_loads(args):
    import json as _json
    return _from_plain(_json.loads(args[0]))


def _to_plain(value):
    if isinstance(value, Struct):
        return {k: _to_plain(v) for k, v in value.fields.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    return value


def _from_plain(value):
    if isinstance(value, dict):
        return {k: _from_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_plain(v) for v in value]
    return value


FS = Module("fs", {
    "read": Builtin("read", _fs_read),
    "write": Builtin("write", _fs_write),
    "open": Builtin("open", _fs_open),
    "exists": Builtin("exists", _fs_exists),
})

JSON = Module("json", {
    "dumps": Builtin("dumps", _json_dumps),
    "loads": Builtin("loads", _json_loads),
})

MATH = Module("math", {
    "sqrt": Builtin("sqrt", lambda a: _math.sqrt(a[0])),
    "pow": Builtin("pow", lambda a: _math.pow(a[0], a[1])),
    "floor": Builtin("floor", lambda a: int(_math.floor(a[0]))),
    "ceil": Builtin("ceil", lambda a: int(_math.ceil(a[0]))),
    "abs": Builtin("abs", lambda a: abs(a[0])),
    "sin": Builtin("sin", lambda a: _math.sin(a[0])),
    "cos": Builtin("cos", lambda a: _math.cos(a[0])),
    "tan": Builtin("tan", lambda a: _math.tan(a[0])),
    "log": Builtin("log", lambda a: _math.log(a[0], a[1]) if len(a) > 1 else _math.log(a[0])),
    "exp": Builtin("exp", lambda a: _math.exp(a[0])),
    "min": Builtin("min", lambda a: min(a[0], a[1])),
    "max": Builtin("max", lambda a: max(a[0], a[1])),
    "round": Builtin("round", lambda a: int(_math.floor(a[0] + 0.5))),
    "pi": _math.pi,
    "e": _math.e,
})


TIME = Module("time", {
    "now": Builtin("now", lambda a: _time.time()),
    "now_ms": Builtin("now_ms", lambda a: int(_time.time() * 1000)),
    "sleep": Builtin("sleep", lambda a: _sleep_ms(a[0])),
})

STR = Module("str", {
    "from_int": Builtin("from_int", lambda a: str(a[0])),
    "to_int": Builtin("to_int", lambda a: _parse_int(a[0])),
    "repeat": Builtin("repeat", lambda a: a[0] * a[1]),
    "join": Builtin("join", lambda a: a[0].join(ulang_str(x) for x in a[1])),
})

RANDOM = Module("random", {
    "int": Builtin("int", lambda a: _random.randint(a[0], a[1] - 1)),
    "float": Builtin("float", lambda a: _random.random()),
    "choice": Builtin("choice", lambda a: _random.choice(a[0])),
    "seed": Builtin("seed", lambda a: _random.seed(a[0])),
})

LIST = Module("list", {
    "range": Builtin("range", lambda a: list(range(a[0], a[1]))),
    "repeat": Builtin("repeat", lambda a: [a[0]] * a[1]),
    "concat": Builtin("concat", lambda a: a[0] + a[1]),
})


def _sleep_ms(ms):
    _time.sleep(ms / 1000.0)
    return None


def _parse_int(s):
    try:
        return ok(int(s))
    except ValueError:
        return err(f"invalid int: {s}")


def _platform_module():
    import platform_abi
    host = platform_abi.HOST
    return Module("platform", {
        "os": host.os,
        "arch": host.arch,
        "exe_ext": host.exe_ext,
        "path_sep": host.path_sep,
        "line_sep": host.line_sep,
        "is_windows": Builtin("is_windows", lambda a: host.os == platform_abi.WINDOWS),
        "is_macos": Builtin("is_macos", lambda a: host.os == platform_abi.MACOS),
        "is_linux": Builtin("is_linux", lambda a: host.os == platform_abi.LINUX),
    })


MODULES = {
    "fs": FS,
    "json": JSON,
    "math": MATH,
    "time": TIME,
    "str": STR,
    "random": RANDOM,
    "list": LIST,
}


def get_module(name):
    if name == "platform":
        return _platform_module()
    return MODULES.get(name)
