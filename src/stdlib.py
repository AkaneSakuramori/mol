import math as _math

import values as V
from values import Module, Builtin, Struct, some, ok, err, NONE, mol_str


class FileHandle(V.MolValue):
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
            f.write(mol_str(data))
        return ok(None)
    except OSError as e:
        return err(str(e))


def _fs_open(args):
    path = args[0]
    mode = args[1] if len(args) > 1 else "w"
    return _FileValue(path, mode)


class _FileValue(V.MolValue):
    __slots__ = ("path", "fp")

    def __init__(self, path, mode):
        self.path = path
        self.fp = open(path, mode, encoding="utf-8")

    def method(self, name):
        if name == "write":
            return Builtin("write", lambda a: (self.fp.write(mol_str(a[0])), None)[1])
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
    "pi": _math.pi,
    "e": _math.e,
})


MODULES = {
    "fs": FS,
    "json": JSON,
    "math": MATH,
}


def get_module(name):
    return MODULES.get(name)
