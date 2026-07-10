import ast_nodes as ast


class Type:
    def __eq__(self, other):
        return isinstance(other, Type) and str(self) == str(other)

    def __hash__(self):
        return hash(str(self))


class Primitive(Type):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class ListT(Type):
    def __init__(self, element):
        self.element = element

    def __str__(self):
        return f"[{self.element}]"


class DictT(Type):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __str__(self):
        return f"{{{self.key}: {self.value}}}"


class TupleT(Type):
    def __init__(self, elements):
        self.elements = elements

    def __str__(self):
        return "(" + ", ".join(str(e) for e in self.elements) + ")"


class FnT(Type):
    def __init__(self, params, ret):
        self.params = params
        self.ret = ret

    def __str__(self):
        return "fn(" + ", ".join(str(p) for p in self.params) + f") -> {self.ret}"


class NamedT(Type):
    def __init__(self, name, args=None):
        self.name = name
        self.args = args or []

    def __str__(self):
        if self.args:
            return f"{self.name}[" + ", ".join(str(a) for a in self.args) + "]"
        return self.name


class OptionalT(Type):
    def __init__(self, inner):
        self.inner = inner

    def __str__(self):
        return f"{self.inner}?"


class Dyn(Type):
    def __str__(self):
        return "dyn"


class Var(Type):
    _counter = 0

    def __init__(self):
        Var._counter += 1
        self.id = Var._counter
        self.ref = None

    def __str__(self):
        if self.ref is not None:
            return str(self.ref)
        return f"?{self.id}"


INT = Primitive("int")
FLOAT = Primitive("float")
BOOL = Primitive("bool")
STR = Primitive("str")
NONE_T = Primitive("none")
UNIT = Primitive("unit")
DYN = Dyn()


class TypeError_(Exception):
    def __init__(self, message, line=0):
        super().__init__(f"{line}: {message}" if line else message)
        self.line = line


def prune(t):
    if isinstance(t, Var) and t.ref is not None:
        t.ref = prune(t.ref)
        return t.ref
    return t


class Scope:
    def __init__(self, parent=None):
        self.names = {}
        self.parent = parent

    def get(self, name):
        s = self
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        return None

    def set(self, name, type):
        self.names[name] = type


class Checker:
    def __init__(self):
        self.types = {}
        self.enums = {}
        self.variants = {}
        self.traits = {}
        self.impls = {}
        self.functions = {}
        self.errors = []
        self.builtins = self._builtins()

    def _builtins(self):
        return {
            "print": FnT([DYN], UNIT),
            "len": FnT([DYN], INT),
            "range": FnT([INT, INT], ListT(INT)),
            "panic": FnT([STR], UNIT),
            "int": FnT([DYN], INT),
            "float": FnT([DYN], FLOAT),
            "str": FnT([DYN], STR),
            "bool": FnT([DYN], BOOL),
            "abs": FnT([DYN], DYN),
            "min": FnT([DYN], DYN),
            "max": FnT([DYN], DYN),
            "sum": FnT([DYN], DYN),
            "Some": FnT([DYN], NamedT("Option", [DYN])),
            "None": NamedT("Option", [DYN]),
            "Ok": FnT([DYN], NamedT("Result", [DYN, DYN])),
            "Err": FnT([DYN], NamedT("Result", [DYN, DYN])),
        }

    def check(self, module):
        self.declare(module)
        for decl in module.body:
            if isinstance(decl, ast.Function):
                self.check_function(decl)
            elif isinstance(decl, ast.ImplDecl):
                self.check_impl(decl)
            elif isinstance(decl, ast.Const):
                self.infer(decl.value, Scope())
        return self.errors

    def declare(self, module):
        self.consts = {}
        self.modules = set()
        for decl in module.body:
            if isinstance(decl, ast.TypeDecl):
                self.types[decl.name] = decl
            elif isinstance(decl, ast.EnumDecl):
                self.enums[decl.name] = decl
                for v in decl.variants:
                    self.variants[v.name] = (decl.name, v)
            elif isinstance(decl, ast.TraitDecl):
                self.traits[decl.name] = decl
            elif isinstance(decl, ast.Function):
                self.functions[decl.name] = self.fn_type(decl)
            elif isinstance(decl, ast.ImplDecl):
                self.register_impl(decl)
            elif isinstance(decl, ast.Const):
                self.consts[decl.name] = DYN
            elif isinstance(decl, ast.Import):
                self._declare_import(decl)

    def _declare_import(self, decl):
        if decl.names is not None:
            for name in decl.names:
                self.consts[name] = DYN
        else:
            bind = decl.alias if decl.alias else decl.path[-1]
            self.consts[bind] = DYN
            self.modules.add(bind)

    def register_impl(self, decl):
        name = decl.type.name if isinstance(decl.type, ast.NamedType) else None
        if name is None:
            return
        table = self.impls.setdefault(name, {})
        for m in decl.methods:
            table[m.name] = self.fn_type(m)

    def fn_type(self, decl):
        params = [self.resolve(p.type) if p.type else DYN for p in decl.params]
        ret = self.resolve(decl.return_type) if decl.return_type else UNIT
        return FnT(params, ret)

    def resolve(self, node):
        if node is None:
            return DYN
        if isinstance(node, ast.NamedType):
            base = {"int": INT, "float": FLOAT, "bool": BOOL, "str": STR}.get(node.name)
            if base is not None:
                return base
            args = [self.resolve(a) for a in node.args]
            return NamedT(node.name, args)
        if isinstance(node, ast.ListType):
            return ListT(self.resolve(node.element))
        if isinstance(node, ast.DictType):
            return DictT(self.resolve(node.key), self.resolve(node.value))
        if isinstance(node, ast.TupleType):
            return TupleT([self.resolve(e) for e in node.elements])
        if isinstance(node, ast.FnType):
            return FnT([self.resolve(p) for p in node.params], self.resolve(node.return_type))
        if isinstance(node, ast.OptionalType):
            return OptionalT(self.resolve(node.inner))
        if isinstance(node, ast.DynType):
            return DYN
        return DYN

    def error(self, message, node=None):
        line = getattr(node, "line", 0) if node else 0
        self.errors.append(TypeError_(message, line))

    def check_function(self, decl, self_type=None):
        scope = Scope()
        if self_type is not None:
            scope.set("self", self_type)
        for p in decl.params:
            if p.name == "self" and p.type is None:
                scope.set("self", self_type if self_type else DYN)
            else:
                scope.set(p.name, self.resolve(p.type))
        ret = self.resolve(decl.return_type) if decl.return_type else UNIT
        self.current_return = ret
        self.check_block(decl.body, scope)

    def check_impl(self, decl):
        name = decl.type.name if isinstance(decl.type, ast.NamedType) else None
        self_type = NamedT(name) if name else DYN
        for m in decl.methods:
            self.check_function(m, self_type)

    def check_block(self, stmts, scope):
        for stmt in stmts:
            self.check_stmt(stmt, scope)

    def check_stmt(self, node, scope):
        method = getattr(self, "st_" + type(node).__name__, None)
        if method:
            method(node, scope)
        else:
            self.infer(node, scope)

    def st_Let(self, node, scope):
        t = self.infer(node.value, scope)
        if node.type is not None:
            declared = self.resolve(node.type)
            if not self.compatible(declared, t):
                self.error(f"type mismatch: expected {declared}, got {t}", node)
            t = declared
        self.bind_pattern(node.pattern, t, scope)

    def st_Var(self, node, scope):
        t = self.infer(node.value, scope)
        if node.type is not None:
            t = self.resolve(node.type)
        scope.set(node.name, t)

    def st_Assign(self, node, scope):
        self.infer(node.value, scope)
        self.infer(node.target, scope)

    def st_Return(self, node, scope):
        if node.value is not None:
            self.infer(node.value, scope)

    def st_If(self, node, scope):
        self.infer(node.cond, scope)
        self.check_block(node.then, Scope(scope))
        for c, b in node.elifs:
            self.infer(c, scope)
            self.check_block(b, Scope(scope))
        if node.orelse:
            self.check_block(node.orelse, Scope(scope))

    def st_While(self, node, scope):
        self.infer(node.cond, scope)
        self.check_block(node.body, Scope(scope))

    def st_For(self, node, scope):
        it = prune(self.infer(node.iter, scope))
        elem = DYN
        if isinstance(it, ListT):
            elem = it.element
        inner = Scope(scope)
        self.bind_pattern(node.pattern, elem, inner)
        self.check_block(node.body, inner)

    def st_With(self, node, scope):
        t = self.infer(node.expr, scope)
        inner = Scope(scope)
        if node.alias:
            inner.set(node.alias, t)
        self.check_block(node.body, inner)

    def st_Match(self, node, scope):
        subject = self.infer(node.subject, scope)
        for arm in node.arms:
            arm_scope = Scope(scope)
            self.bind_pattern(arm.pattern, subject, arm_scope)
            if arm.guard is not None:
                self.infer(arm.guard, arm_scope)
            if isinstance(arm.body, list):
                self.check_block(arm.body, arm_scope)
            else:
                self.infer(arm.body, arm_scope)

    def st_Break(self, node, scope):
        pass

    def st_Continue(self, node, scope):
        pass

    def st_Defer(self, node, scope):
        self.infer(node.expr, scope)

    def st_ExprStmt(self, node, scope):
        self.infer(node.expr, scope)

    def bind_pattern(self, pattern, t, scope):
        if isinstance(pattern, ast.BindPattern):
            scope.set(pattern.name, t)
        elif isinstance(pattern, ast.WildcardPattern):
            pass
        elif isinstance(pattern, ast.VariantPattern):
            info = self.variants.get(pattern.name)
            for i, sub in enumerate(pattern.args):
                sub_t = DYN
                if info is not None:
                    _, variant = info
                    if i < len(variant.types):
                        sub_t = self.resolve(variant.types[i])
                self.bind_pattern(sub, sub_t, scope)
        elif isinstance(pattern, ast.TuplePattern):
            elems = t.elements if isinstance(t, TupleT) else [DYN] * len(pattern.elements)
            for sub, et in zip(pattern.elements, elems):
                self.bind_pattern(sub, et, scope)

    def infer(self, node, scope):
        method = getattr(self, "in_" + type(node).__name__, None)
        if method is None:
            return DYN
        return method(node, scope)

    def in_Int(self, node, scope):
        return INT

    def in_Float(self, node, scope):
        return FLOAT

    def in_Bool(self, node, scope):
        return BOOL

    def in_Str(self, node, scope):
        for kind, value in node.parts:
            if kind == "expr":
                self.infer(value, scope)
        return STR

    def in_NoneLit(self, node, scope):
        return NamedT("Option", [Var()])

    def in_Name(self, node, scope):
        t = scope.get(node.id)
        if t is not None:
            return t
        if node.id in self.consts:
            return self.consts[node.id]
        if node.id in self.functions:
            return self.functions[node.id]
        if node.id in self.builtins:
            return self.builtins[node.id]
        if node.id in self.types:
            decl = self.types[node.id]
            params = [self.resolve(f.type) for f in decl.fields]
            return FnT(params, NamedT(node.id))
        if node.id in self.variants:
            enum_name, variant = self.variants[node.id]
            if variant.types:
                return FnT([self.resolve(t) for t in variant.types], NamedT(enum_name))
            return NamedT(enum_name)
        if node.id in ("Some", "Ok", "Err"):
            return DYN
        self.error(f"undefined name '{node.id}'", node)
        return DYN

    def in_ListLit(self, node, scope):
        if not node.elements:
            return ListT(Var())
        first = self.infer(node.elements[0], scope)
        for e in node.elements[1:]:
            self.infer(e, scope)
        return ListT(first)

    def in_DictLit(self, node, scope):
        if not node.pairs:
            return DictT(Var(), Var())
        k = self.infer(node.pairs[0][0], scope)
        v = self.infer(node.pairs[0][1], scope)
        for kk, vv in node.pairs[1:]:
            self.infer(kk, scope)
            self.infer(vv, scope)
        return DictT(k, v)

    def in_TupleLit(self, node, scope):
        return TupleT([self.infer(e, scope) for e in node.elements])

    def in_Lambda(self, node, scope):
        inner = Scope(scope)
        params = []
        for p in node.params:
            pt = self.resolve(p.type) if p.type else DYN
            inner.set(p.name, pt)
            params.append(pt)
        if isinstance(node.body, list):
            self.check_block(node.body, inner)
            ret = DYN
        else:
            ret = self.infer(node.body, inner)
        return FnT(params, ret)

    def in_Ternary(self, node, scope):
        self.infer(node.cond, scope)
        t = self.infer(node.then, scope)
        self.infer(node.orelse, scope)
        return t

    def in_BinOp(self, node, scope):
        left = prune(self.infer(node.left, scope))
        right = prune(self.infer(node.right, scope))
        if node.op in ("and", "or"):
            return BOOL
        if node.op in ("==", "!=", "<", "<=", ">", ">="):
            return BOOL
        if node.op in ("+", "-", "*", "/", "%"):
            if isinstance(left, Dyn) or isinstance(right, Dyn):
                return left if not isinstance(left, Dyn) else right
            if left == right:
                return left
            if {left, right} == {INT, FLOAT}:
                return FLOAT
            return left
        return DYN

    def in_UnaryOp(self, node, scope):
        t = self.infer(node.operand, scope)
        if node.op == "not":
            return BOOL
        return t

    def in_Call(self, node, scope):
        fn = prune(self.infer(node.func, scope))
        for arg in node.args:
            self.infer(arg.value, scope)
        if isinstance(fn, FnT):
            if not isinstance(fn, Dyn) and len(node.args) != len(fn.params):
                pass
            return fn.ret
        return DYN

    def in_Index(self, node, scope):
        t = prune(self.infer(node.target, scope))
        self.infer(node.index, scope)
        if isinstance(t, ListT):
            return t.element
        if isinstance(t, DictT):
            return t.value
        return DYN

    def in_Attribute(self, node, scope):
        t = prune(self.infer(node.target, scope))
        if isinstance(t, NamedT):
            decl = self.types.get(t.name)
            if decl is not None:
                for f in decl.fields:
                    if f.name == node.name:
                        return self.resolve(f.type)
            impl = self.impls.get(t.name)
            if impl is not None and node.name in impl:
                return impl[node.name]
        return DYN

    def in_Try(self, node, scope):
        t = prune(self.infer(node.expr, scope))
        if isinstance(t, NamedT) and t.name in ("Option", "Result") and t.args:
            return t.args[0]
        if isinstance(t, OptionalT):
            return t.inner
        return DYN

    def compatible(self, expected, got):
        expected = prune(expected)
        got = prune(got)
        if isinstance(expected, Dyn) or isinstance(got, Dyn):
            return True
        if isinstance(expected, Var) or isinstance(got, Var):
            return True
        if isinstance(expected, OptionalT):
            if isinstance(got, NamedT) and got.name == "Option":
                return True
            return self.compatible(expected.inner, got)
        if isinstance(expected, NamedT) and expected.name == "Option":
            return True
        if isinstance(expected, ListT) and isinstance(got, ListT):
            return self.compatible(expected.element, got.element)
        return str(expected) == str(got)


def check(module):
    return Checker().check(module)
