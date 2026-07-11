import ast_nodes as ast


def serialize_module(module):
    return "\n".join(ser(d) for d in module.body)


def ser(node):
    return _DISPATCH[type(node).__name__](node)


def _list(nodes):
    return " ".join(ser(n) for n in nodes)


def _opt(node):
    return ser(node) if node is not None else "_"


def _type(node):
    if node is None:
        return "_"
    return ser(node)


def _block(stmts):
    inner = " ".join(ser(s) for s in stmts)
    return f"(block {inner})" if inner else "(block)"


def _generics(gs):
    return "(gen " + " ".join(ser(g) for g in gs) + ")" if gs else "(gen)"


def _params(ps):
    return "(params " + " ".join(ser(p) for p in ps) + ")" if ps else "(params)"


def s_Module(n):
    return serialize_module(n)


def s_Function(n):
    pub = "pub" if n.is_pub else "-"
    return (f"(fn {pub} {n.name} {_generics(n.generics)} {_params(n.params)} "
            f"{_type(n.return_type)} {_block(n.body)})")


def s_Param(n):
    return f"(p {n.name} {_type(n.type)} {_opt(n.default)})"


def s_GenericParam(n):
    bounds = " ".join(ser(b) for b in n.bounds)
    return f"(g {n.name} {bounds})" if n.bounds else f"(g {n.name})"


def s_TypeDecl(n):
    fields = " ".join(f"(field {f.name} {_type(f.type)})" for f in n.fields)
    derives = "(derive " + " ".join(n.derives) + ")" if n.derives else "(derive)"
    return f"(type {'pub' if n.is_pub else '-'} {n.name} {_generics(n.generics)} ({fields}) {derives})"


def s_EnumDecl(n):
    variants = " ".join(
        "(variant " + v.name + ("".join(" " + _type(t) for t in v.types)) + ")"
        for v in n.variants
    )
    derives = "(derive " + " ".join(n.derives) + ")" if n.derives else "(derive)"
    return f"(enum {'pub' if n.is_pub else '-'} {n.name} {_generics(n.generics)} ({variants}) {derives})"


def s_TraitDecl(n):
    methods = " ".join(
        f"(method {m.name} {_params(m.params)} {_type(m.return_type)})"
        for m in n.methods
    )
    return f"(trait {'pub' if n.is_pub else '-'} {n.name} {_generics(n.generics)} ({methods}))"


def s_ImplDecl(n):
    methods = " ".join(ser(m) for m in n.methods)
    return f"(impl {_generics(n.generics)} {ser(n.type)} {_opt(n.trait)} ({methods}))"


def s_Const(n):
    return f"(const {n.name} {_type(n.type)} {ser(n.value)})"


def s_Import(n):
    path = "(path " + " ".join(n.path) + ")"
    alias = n.alias if n.alias else "_"
    names = "(names " + " ".join(n.names) + ")" if n.names is not None else "_"
    return f"(import {path} {alias} {names})"


def s_ExternFn(n):
    lib = "lib" if n.library else "_"
    return f"(extern {n.name} {_params(n.params)} {_type(n.return_type)} {lib})"


def s_Let(n):
    return f"(let {ser(n.pattern)} {_type(n.type)} {ser(n.value)})"


def s_Var(n):
    return f"(var {n.name} {_type(n.type)} {ser(n.value)})"


def s_Assign(n):
    return f"(asn {n.op} {ser(n.target)} {ser(n.value)})"


def s_Return(n):
    return f"(ret {ser(n.value)})" if n.value is not None else "(ret)"


def s_Break(n):
    return "(brk)"


def s_Continue(n):
    return "(cnt)"


def s_Defer(n):
    return f"(defer {ser(n.expr)})"


def s_ExprStmt(n):
    return f"(expr {ser(n.expr)})"


def s_If(n):
    elifs = " ".join(f"(elif {ser(c)} {_block(b)})" for c, b in n.elifs)
    orelse = _block(n.orelse) if n.orelse is not None else "_"
    return f"(if {ser(n.cond)} {_block(n.then)} ({elifs}) {orelse})"


def s_While(n):
    return f"(while {ser(n.cond)} {_block(n.body)})"


def s_For(n):
    return f"(for {ser(n.pattern)} {ser(n.iter)} {_block(n.body)})"


def s_With(n):
    alias = n.alias if n.alias else "_"
    return f"(with {ser(n.expr)} {alias} {_block(n.body)})"


def s_Match(n):
    arms = " ".join(
        f"(arm {ser(a.pattern)} {_opt(a.guard)} "
        f"{_block(a.body) if isinstance(a.body, list) else ser(a.body)})"
        for a in n.arms
    )
    return f"(match {ser(n.subject)} {arms})"


def s_Int(n):
    return str(n.value)


def s_Float(n):
    return "(flt)"


def s_Bool(n):
    return "true" if n.value else "false"


def s_NoneLit(n):
    return "none"


def s_Str(n):
    return "(str)"


def s_Name(n):
    return n.id


def s_ListLit(n):
    return "(list " + _list(n.elements) + ")" if n.elements else "(list)"


def s_DictLit(n):
    pairs = " ".join(f"(pair {ser(k)} {ser(v)})" for k, v in n.pairs)
    return f"(dict {pairs})" if n.pairs else "(dict)"


def s_TupleLit(n):
    return "(tuple " + _list(n.elements) + ")"


def s_Lambda(n):
    body = _block(n.body) if isinstance(n.body, list) else ser(n.body)
    return f"(lam {_params(n.params)} {body})"


def s_Ternary(n):
    return f"(ternary {ser(n.cond)} {ser(n.then)} {ser(n.orelse)})"


def s_BinOp(n):
    return f"({n.op} {ser(n.left)} {ser(n.right)})"


def s_UnaryOp(n):
    op = "neg" if n.op == "-" else n.op
    return f"({op} {ser(n.operand)})"


def s_Call(n):
    args = " ".join(
        f"(named {a.name} {ser(a.value)})" if a.name else ser(a.value)
        for a in n.args
    )
    if args:
        return f"(cll {ser(n.func)} {args})"
    return f"(cll {ser(n.func)})"


def s_Index(n):
    return f"(idx {ser(n.target)} {ser(n.index)})"


def s_Attribute(n):
    return f"(att {ser(n.target)} {n.name})"


def s_Try(n):
    return f"(try {ser(n.expr)})"


def s_NamedType(n):
    if n.args:
        return "(gent " + n.name + " " + " ".join(ser(a) for a in n.args) + ")"
    return n.name


def s_ListType(n):
    return f"(ltt {ser(n.element)})"


def s_DictType(n):
    return f"(dtt {ser(n.key)} {ser(n.value)})"


def s_TupleType(n):
    return "(ttt " + " ".join(ser(e) for e in n.elements) + ")"


def s_FnType(n):
    params = " ".join(ser(p) for p in n.params)
    return f"(fnt ({params}) {ser(n.return_type)})"


def s_OptionalType(n):
    return f"(optt {ser(n.inner)})"


def s_DynType(n):
    return "dyn"


def s_WildcardPattern(n):
    return "_"


def s_BindPattern(n):
    return n.name


def s_LiteralPattern(n):
    return f"(litp {ser(n.value)})"


def s_VariantPattern(n):
    if n.args:
        return "(vp " + n.name + " " + " ".join(ser(a) for a in n.args) + ")"
    return f"(vp {n.name})"


def s_TuplePattern(n):
    return "(tp " + " ".join(ser(e) for e in n.elements) + ")"


_DISPATCH = {name[2:]: fn for name, fn in globals().items() if name.startswith("s_")}
