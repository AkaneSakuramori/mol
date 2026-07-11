class Node:
    _fields = ()

    def __init__(self, *args, **kwargs):
        for name, value in zip(self._fields, args):
            setattr(self, name, value)
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.line = kwargs.get("line", 0)

    def __repr__(self):
        parts = ", ".join(f"{f}={getattr(self, f, None)!r}" for f in self._fields)
        return f"{type(self).__name__}({parts})"

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return all(getattr(self, f) == getattr(other, f) for f in self._fields)


class Module(Node):
    _fields = ("body",)


class Import(Node):
    _fields = ("path", "alias", "names")


class Const(Node):
    _fields = ("name", "type", "value")


class Param(Node):
    _fields = ("name", "type", "default")


class GenericParam(Node):
    _fields = ("name", "bounds")


class Function(Node):
    _fields = ("name", "generics", "params", "return_type", "body", "is_pub")


class ExternFn(Node):
    _fields = ("name", "params", "return_type", "c_name", "library")


class Field(Node):
    _fields = ("name", "type")


class TypeDecl(Node):
    _fields = ("name", "generics", "fields", "derives", "is_pub")


class Variant(Node):
    _fields = ("name", "types")


class EnumDecl(Node):
    _fields = ("name", "generics", "variants", "derives", "is_pub")


class TraitDecl(Node):
    _fields = ("name", "generics", "methods", "is_pub")


class TraitMethod(Node):
    _fields = ("name", "params", "return_type")


class ImplDecl(Node):
    _fields = ("generics", "type", "trait", "methods")


class NamedType(Node):
    _fields = ("name", "args")


class ListType(Node):
    _fields = ("element",)


class DictType(Node):
    _fields = ("key", "value")


class TupleType(Node):
    _fields = ("elements",)


class FnType(Node):
    _fields = ("params", "return_type")


class OptionalType(Node):
    _fields = ("inner",)


class DynType(Node):
    _fields = ()


class Let(Node):
    _fields = ("pattern", "type", "value")


class Var(Node):
    _fields = ("name", "type", "value")


class Assign(Node):
    _fields = ("target", "op", "value")


class Return(Node):
    _fields = ("value",)


class Break(Node):
    _fields = ()


class Continue(Node):
    _fields = ()


class Defer(Node):
    _fields = ("expr",)


class If(Node):
    _fields = ("cond", "then", "elifs", "orelse")


class While(Node):
    _fields = ("cond", "body")


class For(Node):
    _fields = ("pattern", "iter", "body")


class With(Node):
    _fields = ("expr", "alias", "body")


class Match(Node):
    _fields = ("subject", "arms")


class MatchArm(Node):
    _fields = ("pattern", "guard", "body")


class ExprStmt(Node):
    _fields = ("expr",)


class WildcardPattern(Node):
    _fields = ()


class LiteralPattern(Node):
    _fields = ("value",)


class BindPattern(Node):
    _fields = ("name",)


class VariantPattern(Node):
    _fields = ("name", "args")


class TuplePattern(Node):
    _fields = ("elements",)


class Int(Node):
    _fields = ("value",)


class Float(Node):
    _fields = ("value",)


class Str(Node):
    _fields = ("parts",)


class Bool(Node):
    _fields = ("value",)


class NoneLit(Node):
    _fields = ()


class Name(Node):
    _fields = ("id",)


class ListLit(Node):
    _fields = ("elements",)


class DictLit(Node):
    _fields = ("pairs",)


class TupleLit(Node):
    _fields = ("elements",)


class Lambda(Node):
    _fields = ("params", "body")


class Ternary(Node):
    _fields = ("then", "cond", "orelse")


class BinOp(Node):
    _fields = ("op", "left", "right")


class UnaryOp(Node):
    _fields = ("op", "operand")


class Call(Node):
    _fields = ("func", "args")


class Argument(Node):
    _fields = ("name", "value")


class Index(Node):
    _fields = ("target", "index")


class Attribute(Node):
    _fields = ("target", "name")


class Try(Node):
    _fields = ("expr",)
