class UlangValue:
    pass


class Struct(UlangValue):
    __slots__ = ("type_name", "fields")

    def __init__(self, type_name, fields):
        self.type_name = type_name
        self.fields = fields

    def __eq__(self, other):
        return (
            isinstance(other, Struct)
            and self.type_name == other.type_name
            and self.fields == other.fields
        )

    def __repr__(self):
        inner = ", ".join(f"{k}={ulang_repr(v)}" for k, v in self.fields.items())
        return f"{self.type_name}({inner})"


class Variant(UlangValue):
    __slots__ = ("enum_name", "name", "values")

    def __init__(self, enum_name, name, values):
        self.enum_name = enum_name
        self.name = name
        self.values = values

    def __eq__(self, other):
        return (
            isinstance(other, Variant)
            and self.enum_name == other.enum_name
            and self.name == other.name
            and self.values == other.values
        )

    def __repr__(self):
        if not self.values:
            return self.name
        inner = ", ".join(ulang_repr(v) for v in self.values)
        return f"{self.name}({inner})"


class Closure(UlangValue):
    __slots__ = ("params", "body", "env", "name")

    def __init__(self, params, body, env, name="<lambda>"):
        self.params = params
        self.body = body
        self.env = env
        self.name = name

    def __repr__(self):
        return f"<fn {self.name}>"


class Builtin(UlangValue):
    __slots__ = ("name", "fn")

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn

    def __repr__(self):
        return f"<builtin {self.name}>"


class BoundMethod(UlangValue):
    __slots__ = ("receiver", "fn", "name")

    def __init__(self, receiver, fn, name):
        self.receiver = receiver
        self.fn = fn
        self.name = name

    def __repr__(self):
        return f"<method {self.name}>"


class Module(UlangValue):
    __slots__ = ("name", "members")

    def __init__(self, name, members):
        self.name = name
        self.members = members

    def __repr__(self):
        return f"<module {self.name}>"


def some(value):
    return Variant("Option", "Some", [value])


NONE = Variant("Option", "None", [])


def ok(value):
    return Variant("Result", "Ok", [value])


def err(value):
    return Variant("Result", "Err", [value])


def is_none(value):
    return isinstance(value, Variant) and value.enum_name == "Option" and value.name == "None"


def is_err(value):
    return isinstance(value, Variant) and value.enum_name == "Result" and value.name == "Err"


def ulang_repr(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value + '"'
    if isinstance(value, list):
        return "[" + ", ".join(ulang_repr(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(ulang_repr(v) for v in value) + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{ulang_repr(k)}: {ulang_repr(v)}" for k, v in value.items()) + "}"
    return repr(value)


def ulang_str(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if value == int(value):
            return f"{value:.1f}"
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(ulang_str_inner(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(ulang_str_inner(v) for v in value) + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{ulang_str_inner(k)}: {ulang_str_inner(v)}" for k, v in value.items()) + "}"
    if isinstance(value, Struct):
        inner = ", ".join(f"{k}: {ulang_str_inner(v)}" for k, v in value.fields.items())
        return f"{value.type_name}({inner})"
    if isinstance(value, Variant):
        if not value.values:
            return value.name
        inner = ", ".join(ulang_str_inner(v) for v in value.values)
        return f"{value.name}({inner})"
    return str(value)


def ulang_str_inner(value):
    if isinstance(value, str):
        return '"' + value + '"'
    return ulang_str(value)
