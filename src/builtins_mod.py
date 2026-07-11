import values as V
from values import Struct, Variant, Builtin, some, ok, err, NONE, ulang_str, ulang_repr


class UlangPanic(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.line = 0


def _print(args):
    print(" ".join(ulang_str(a) for a in args))
    return None


def _len(args):
    obj = args[0]
    if isinstance(obj, (str, list, dict, tuple)):
        return len(obj)
    raise UlangPanic(f"len: unsupported type {type(obj).__name__}")


def _range(args):
    if len(args) == 1:
        return list(range(args[0]))
    if len(args) == 2:
        return list(range(args[0], args[1]))
    return list(range(args[0], args[1], args[2]))


def _panic(args):
    raise UlangPanic(ulang_str(args[0]) if args else "panic")


def _int(args):
    return int(args[0])


def _float(args):
    return float(args[0])


def _str(args):
    return ulang_str(args[0])


def _bool(args):
    return bool(args[0])


def _abs(args):
    return abs(args[0])


def _min(args):
    if len(args) == 1:
        return min(args[0])
    return min(args)


def _max(args):
    if len(args) == 1:
        return max(args[0])
    return max(args)


def _sum(args):
    return sum(args[0])


def _some(args):
    return some(args[0])


def _ok(args):
    return ok(args[0])


def _err(args):
    return err(args[0])


BUILTINS = {
    "print": Builtin("print", _print),
    "len": Builtin("len", _len),
    "range": Builtin("range", _range),
    "panic": Builtin("panic", _panic),
    "int": Builtin("int", _int),
    "float": Builtin("float", _float),
    "str": Builtin("str", _str),
    "bool": Builtin("bool", _bool),
    "abs": Builtin("abs", _abs),
    "min": Builtin("min", _min),
    "max": Builtin("max", _max),
    "sum": Builtin("sum", _sum),
    "Some": Builtin("Some", _some),
    "Ok": Builtin("Ok", _ok),
    "Err": Builtin("Err", _err),
    "None": NONE,
}


def call_builtin(fn, args):
    return fn.fn(args)


def get_method(obj, name, interp):
    if isinstance(obj, list):
        return _list_method(obj, name, interp)
    if isinstance(obj, str):
        return _str_method(obj, name)
    if isinstance(obj, dict):
        return _dict_method(obj, name)
    if isinstance(obj, int) or isinstance(obj, float):
        return _num_method(obj, name)
    if isinstance(obj, Variant):
        return _variant_method(obj, name)
    return None


def _list_method(obj, name, interp):
    if name == "map":
        return Builtin("map", lambda a: [interp.call(a[0], [x]) for x in obj])
    if name == "filter":
        return Builtin("filter", lambda a: [x for x in obj if _truthy(interp.call(a[0], [x]))])
    if name == "reduce":
        return Builtin("reduce", lambda a: _reduce(obj, a, interp))
    if name == "each":
        return Builtin("each", lambda a: _each(obj, a[0], interp))
    if name == "len":
        return Builtin("len", lambda a: len(obj))
    if name == "push":
        return Builtin("push", lambda a: obj.append(a[0]))
    if name == "pop":
        return Builtin("pop", lambda a: obj.pop())
    if name == "contains":
        return Builtin("contains", lambda a: a[0] in obj)
    if name == "reverse":
        return Builtin("reverse", lambda a: list(reversed(obj)))
    if name == "sort":
        return Builtin("sort", lambda a: sorted(obj))
    if name == "first":
        return Builtin("first", lambda a: some(obj[0]) if obj else NONE)
    if name == "last":
        return Builtin("last", lambda a: some(obj[-1]) if obj else NONE)
    if name == "join":
        return Builtin("join", lambda a: a[0].join(ulang_str(x) for x in obj))
    return None


def _reduce(obj, args, interp):
    fn = args[0]
    acc = args[1]
    for x in obj:
        acc = interp.call(fn, [acc, x])
    return acc


def _each(obj, fn, interp):
    for x in obj:
        interp.call(fn, [x])
    return None


def _str_method(obj, name):
    if name == "len":
        return Builtin("len", lambda a: len(obj))
    if name == "upper":
        return Builtin("upper", lambda a: obj.upper())
    if name == "lower":
        return Builtin("lower", lambda a: obj.lower())
    if name == "split":
        return Builtin("split", lambda a: obj.split(a[0]))
    if name == "trim":
        return Builtin("trim", lambda a: obj.strip())
    if name == "replace":
        return Builtin("replace", lambda a: obj.replace(a[0], a[1]))
    if name == "contains":
        return Builtin("contains", lambda a: a[0] in obj)
    if name == "starts_with":
        return Builtin("starts_with", lambda a: obj.startswith(a[0]))
    if name == "ends_with":
        return Builtin("ends_with", lambda a: obj.endswith(a[0]))
    if name == "chars":
        return Builtin("chars", lambda a: list(obj))
    return None


def _dict_method(obj, name):
    if name == "len":
        return Builtin("len", lambda a: len(obj))
    if name == "keys":
        return Builtin("keys", lambda a: list(obj.keys()))
    if name == "values":
        return Builtin("values", lambda a: list(obj.values()))
    if name == "get":
        return Builtin("get", lambda a: some(obj[a[0]]) if a[0] in obj else NONE)
    if name == "has":
        return Builtin("has", lambda a: a[0] in obj)
    if name == "set":
        return Builtin("set", lambda a: obj.__setitem__(a[0], a[1]))
    if name == "remove":
        return Builtin("remove", lambda a: obj.pop(a[0], None))
    return None


def _num_method(obj, name):
    if name == "to_str":
        return Builtin("to_str", lambda a: ulang_str(obj))
    if name == "abs":
        return Builtin("abs", lambda a: abs(obj))
    return None


def _variant_method(obj, name):
    if name == "is_some":
        return Builtin("is_some", lambda a: obj.name == "Some")
    if name == "is_none":
        return Builtin("is_none", lambda a: obj.name == "None")
    if name == "is_ok":
        return Builtin("is_ok", lambda a: obj.name == "Ok")
    if name == "is_err":
        return Builtin("is_err", lambda a: obj.name == "Err")
    if name == "unwrap":
        return Builtin("unwrap", lambda a: _unwrap(obj))
    if name == "unwrap_or":
        return Builtin("unwrap_or", lambda a: obj.values[0] if obj.values else a[0])
    return None


def _unwrap(obj):
    if obj.name in ("Some", "Ok"):
        return obj.values[0]
    raise UlangPanic(f"unwrap on {obj.name}")


def _truthy(v):
    return bool(v)
