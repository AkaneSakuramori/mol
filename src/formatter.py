import ast_nodes as ast


class Formatter:
    def __init__(self):
        self.out = []
        self.indent = 0

    def line(self, text=""):
        if text:
            self.out.append("    " * self.indent + text)
        else:
            self.out.append("")

    def format(self, module):
        prev = None
        for decl in module.body:
            if prev is not None and self._needs_blank(prev, decl):
                self.line()
            self.decl(decl)
            prev = decl
        text = "\n".join(self.out)
        return text.rstrip() + "\n"

    def _needs_blank(self, prev, curr):
        if isinstance(prev, ast.Import) and isinstance(curr, ast.Import):
            return False
        if isinstance(prev, ast.ExternFn) and isinstance(curr, ast.ExternFn):
            return False
        return True

    def decl(self, node):
        method = getattr(self, "d_" + type(node).__name__, None)
        if method:
            method(node)

    def d_Import(self, node):
        path = ".".join(node.path)
        if node.names is not None:
            self.line(f"from {path} import {', '.join(node.names)}")
        elif node.alias:
            self.line(f"import {path} as {node.alias}")
        else:
            self.line(f"import {path}")

    def d_ExternFn(self, node):
        params = ", ".join(self.param(p) for p in node.params)
        ret = f" -> {self.type(node.return_type)}" if node.return_type else ""
        lib = f' from "{node.library}"' if node.library else ""
        self.line(f"extern fn {node.name}({params}){ret}{lib}")

    def d_Const(self, node):
        t = f": {self.type(node.type)}" if node.type else ""
        self.line(f"const {node.name}{t} = {self.expr(node.value)}")

    def d_Function(self, node):
        pub = "pub " if node.is_pub else ""
        gen = self.generics(node.generics)
        params = ", ".join(self.param(p) for p in node.params)
        ret = f" -> {self.type(node.return_type)}" if node.return_type else ""
        self.line(f"{pub}fn {node.name}{gen}({params}){ret}:")
        self.block(node.body)

    def d_TypeDecl(self, node):
        pub = "pub " if node.is_pub else ""
        self.line(f"{pub}type {node.name}{self.generics(node.generics)}:")
        self.indent += 1
        for f in node.fields:
            self.line(f"{f.name}: {self.type(f.type)}")
        self.indent -= 1
        if node.derives:
            self.line(f"derive({', '.join(node.derives)})")

    def d_EnumDecl(self, node):
        pub = "pub " if node.is_pub else ""
        self.line(f"{pub}enum {node.name}{self.generics(node.generics)}:")
        self.indent += 1
        for v in node.variants:
            if v.types:
                self.line(f"{v.name}({', '.join(self.type(t) for t in v.types)})")
            else:
                self.line(v.name)
        self.indent -= 1
        if node.derives:
            self.line(f"derive({', '.join(node.derives)})")

    def d_TraitDecl(self, node):
        pub = "pub " if node.is_pub else ""
        self.line(f"{pub}trait {node.name}{self.generics(node.generics)}:")
        self.indent += 1
        for m in node.methods:
            params = ", ".join(self.param(p) for p in m.params)
            ret = f" -> {self.type(m.return_type)}" if m.return_type else ""
            self.line(f"fn {m.name}({params}){ret}")
        self.indent -= 1

    def d_ImplDecl(self, node):
        trait = f"{self.type(node.trait)} for " if node.trait else ""
        self.line(f"impl {self.generics(node.generics)}{trait}{self.type(node.type)}:".replace("impl (", "impl ("))
        self.block(node.methods, is_decls=True)

    def generics(self, generics):
        if not generics:
            return ""
        parts = []
        for g in generics:
            if g.bounds:
                parts.append(f"{g.name}: {' + '.join(self.type(b) for b in g.bounds)}")
            else:
                parts.append(g.name)
        return "[" + ", ".join(parts) + "]"

    def param(self, p):
        if p.name == "self" and p.type is None:
            return "self"
        base = f"{p.name}: {self.type(p.type)}" if p.type else p.name
        if p.default is not None:
            base += f" = {self.expr(p.default)}"
        return base

    def type(self, node):
        if node is None:
            return ""
        if isinstance(node, ast.NamedType):
            if node.args:
                return f"{node.name}[{', '.join(self.type(a) for a in node.args)}]"
            return node.name
        if isinstance(node, ast.ListType):
            return f"[{self.type(node.element)}]"
        if isinstance(node, ast.DictType):
            return f"{{{self.type(node.key)}: {self.type(node.value)}}}"
        if isinstance(node, ast.TupleType):
            return "(" + ", ".join(self.type(e) for e in node.elements) + ")"
        if isinstance(node, ast.FnType):
            return f"fn({', '.join(self.type(p) for p in node.params)}) -> {self.type(node.return_type)}"
        if isinstance(node, ast.OptionalType):
            return f"{self.type(node.inner)}?"
        if isinstance(node, ast.DynType):
            return "dyn"
        return "?"

    def block(self, stmts, is_decls=False):
        self.indent += 1
        if not stmts:
            self.line("pass")
        for s in stmts:
            if is_decls:
                self.decl(s)
            else:
                self.stmt(s)
        self.indent -= 1

    def stmt(self, node):
        method = getattr(self, "s_" + type(node).__name__, None)
        if method:
            method(node)

    def s_Let(self, node):
        t = f": {self.type(node.type)}" if node.type else ""
        self.line(f"let {self.pattern(node.pattern)}{t} = {self.expr(node.value)}")

    def s_Var(self, node):
        t = f": {self.type(node.type)}" if node.type else ""
        self.line(f"var {node.name}{t} = {self.expr(node.value)}")

    def s_Assign(self, node):
        self.line(f"{self.expr(node.target)} {node.op} {self.expr(node.value)}")

    def s_Return(self, node):
        if node.value is not None:
            self.line(f"return {self.expr(node.value)}")
        else:
            self.line("return")

    def s_Break(self, node):
        self.line("break")

    def s_Continue(self, node):
        self.line("continue")

    def s_Defer(self, node):
        self.line(f"defer {self.expr(node.expr)}")

    def s_If(self, node):
        self.line(f"if {self.expr(node.cond)}:")
        self.block(node.then)
        for cond, body in node.elifs:
            self.line(f"elif {self.expr(cond)}:")
            self.block(body)
        if node.orelse is not None:
            self.line("else:")
            self.block(node.orelse)

    def s_While(self, node):
        self.line(f"while {self.expr(node.cond)}:")
        self.block(node.body)

    def s_For(self, node):
        self.line(f"for {self.pattern(node.pattern)} in {self.expr(node.iter)}:")
        self.block(node.body)

    def s_With(self, node):
        alias = f" as {node.alias}" if node.alias else ""
        self.line(f"with {self.expr(node.expr)}{alias}:")
        self.block(node.body)

    def s_Match(self, node):
        self.line(f"match {self.expr(node.subject)}:")
        self.indent += 1
        for arm in node.arms:
            guard = f" if {self.expr(arm.guard)}" if arm.guard else ""
            if isinstance(arm.body, list):
                self.line(f"{self.pattern(arm.pattern)}{guard} =>")
                self.block(arm.body)
            else:
                self.line(f"{self.pattern(arm.pattern)}{guard} => {self.expr(arm.body)}")
        self.indent -= 1

    def s_ExprStmt(self, node):
        self.line(self.expr(node.expr))

    def pattern(self, node):
        if isinstance(node, ast.WildcardPattern):
            return "_"
        if isinstance(node, ast.BindPattern):
            return node.name
        if isinstance(node, ast.LiteralPattern):
            return self.expr(node.value)
        if isinstance(node, ast.VariantPattern):
            if node.args:
                return f"{node.name}({', '.join(self.pattern(a) for a in node.args)})"
            return node.name
        if isinstance(node, ast.TuplePattern):
            return "(" + ", ".join(self.pattern(e) for e in node.elements) + ")"
        return "?"

    def expr(self, node):
        method = getattr(self, "e_" + type(node).__name__, None)
        if method:
            return method(node)
        return "?"

    def e_Int(self, node):
        return str(node.value)

    def e_Float(self, node):
        return repr(node.value)

    def e_Bool(self, node):
        return "true" if node.value else "false"

    def e_NoneLit(self, node):
        return "none"

    def e_Str(self, node):
        parts = []
        for kind, value in node.parts:
            if kind == "str":
                parts.append(value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))
            else:
                parts.append("${" + self.expr(value) + "}")
        return '"' + "".join(parts) + '"'

    def e_Name(self, node):
        return node.id

    def e_ListLit(self, node):
        return "[" + ", ".join(self.expr(e) for e in node.elements) + "]"

    def e_DictLit(self, node):
        return "{" + ", ".join(f"{self.expr(k)}: {self.expr(v)}" for k, v in node.pairs) + "}"

    def e_TupleLit(self, node):
        if len(node.elements) == 1:
            return f"({self.expr(node.elements[0])},)"
        return "(" + ", ".join(self.expr(e) for e in node.elements) + ")"

    def e_Lambda(self, node):
        if len(node.params) == 1 and node.params[0].type is None:
            params = node.params[0].name
        else:
            params = "(" + ", ".join(self.param(p) for p in node.params) + ")"
        if isinstance(node.body, list):
            pad = "    " * (self.indent + 1)
            close = "    " * self.indent
            sub = Formatter()
            sub.indent = self.indent + 1
            for s in node.body:
                sub.stmt(s)
            inner = "\n".join(sub.out)
            return f"{params} => {{\n{inner}\n{close}}}"
        return f"{params} => {self.expr(node.body)}"

    def e_Ternary(self, node):
        return f"{self.expr(node.then)} if {self.expr(node.cond)} else {self.expr(node.orelse)}"

    def e_BinOp(self, node):
        return f"{self.expr(node.left)} {node.op} {self.expr(node.right)}"

    def e_UnaryOp(self, node):
        if node.op == "not":
            return f"not {self.expr(node.operand)}"
        return f"-{self.expr(node.operand)}"

    def e_Call(self, node):
        args = []
        for a in node.args:
            if a.name:
                args.append(f"{a.name} = {self.expr(a.value)}")
            else:
                args.append(self.expr(a.value))
        return f"{self.expr(node.func)}({', '.join(args)})"

    def e_Index(self, node):
        return f"{self.expr(node.target)}[{self.expr(node.index)}]"

    def e_Attribute(self, node):
        return f"{self.expr(node.target)}.{node.name}"

    def e_Try(self, node):
        return f"{self.expr(node.expr)}?"


def format_source(source):
    from parser import parse
    module = parse(source)
    return Formatter().format(module)
