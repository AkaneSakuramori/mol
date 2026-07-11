import ast_nodes as ast
import operations
from builtins_mod import UlangPanic


def optimize_module(module):
    consts_env = {}
    body = []
    for decl in module.body:
        if isinstance(decl, ast.Const):
            decl.value = opt_expr(decl.value, consts_env)
            if _literal_value(decl.value) is not _NOTLIT:
                consts_env[decl.name] = decl.value
            body.append(decl)
        else:
            body.append(decl)
    out = []
    for decl in body:
        if isinstance(decl, ast.Function):
            out.append(_optimize_function(decl, consts_env))
        elif isinstance(decl, ast.ImplDecl):
            decl.methods = [_optimize_function(m, consts_env) for m in decl.methods]
            out.append(decl)
        else:
            out.append(decl)
    return ast.Module(body=out)


def _optimize_function(fn, consts_env):
    env = dict(consts_env)
    for p in fn.params:
        env.pop(p.name, None)
    fn.body = opt_block(fn.body, env)
    return fn


_TERMINATORS = (ast.Return, ast.Break, ast.Continue)


def opt_block(stmts, env):
    local = dict(env)
    out = []
    for stmt in stmts:
        for produced in opt_stmt(stmt, local):
            out.append(produced)
            if isinstance(produced, _TERMINATORS):
                return out
    return out


def opt_stmt(node, env):
    if isinstance(node, ast.Let):
        node.value = opt_expr(node.value, env)
        _bind_let(node.pattern, node.value, env)
        return [node]
    if isinstance(node, ast.Var):
        node.value = opt_expr(node.value, env)
        env.pop(node.name, None)
        return [node]
    if isinstance(node, ast.Assign):
        node.value = opt_expr(node.value, env)
        node.target = opt_expr(node.target, env)
        return [node]
    if isinstance(node, ast.Return):
        if node.value is not None:
            node.value = opt_expr(node.value, env)
        return [node]
    if isinstance(node, ast.Defer):
        node.expr = opt_expr(node.expr, env)
        return [node]
    if isinstance(node, ast.ExprStmt):
        node.expr = opt_expr(node.expr, env)
        return [node]
    if isinstance(node, ast.If):
        return _opt_if(node, env)
    if isinstance(node, ast.While):
        cond = opt_expr(node.cond, env)
        lit = _bool_literal(cond)
        if lit is False:
            return []
        node.cond = cond
        node.body = opt_block(node.body, env)
        return [node]
    if isinstance(node, ast.For):
        node.iter = opt_expr(node.iter, env)
        inner = dict(env)
        _remove_pattern(node.pattern, inner)
        node.body = opt_block(node.body, inner)
        return [node]
    if isinstance(node, ast.With):
        node.expr = opt_expr(node.expr, env)
        inner = dict(env)
        if node.alias:
            inner.pop(node.alias, None)
        node.body = opt_block(node.body, inner)
        return [node]
    if isinstance(node, ast.Match):
        node.subject = opt_expr(node.subject, env)
        for arm in node.arms:
            inner = dict(env)
            _remove_pattern(arm.pattern, inner)
            if arm.guard is not None:
                arm.guard = opt_expr(arm.guard, inner)
            if isinstance(arm.body, list):
                arm.body = opt_block(arm.body, inner)
            else:
                arm.body = opt_expr(arm.body, inner)
        return [node]
    return [node]


def _bind_let(pattern, value, env):
    if isinstance(pattern, ast.BindPattern):
        if _literal_value(value) is not _NOTLIT:
            env[pattern.name] = value
        else:
            env.pop(pattern.name, None)
    else:
        _remove_pattern(pattern, env)


def _remove_pattern(pattern, env):
    if isinstance(pattern, ast.BindPattern):
        env.pop(pattern.name, None)
    elif isinstance(pattern, ast.VariantPattern):
        for sub in pattern.args:
            _remove_pattern(sub, env)
    elif isinstance(pattern, ast.TuplePattern):
        for sub in pattern.elements:
            _remove_pattern(sub, env)


def _opt_if(node, env):
    cond = opt_expr(node.cond, env)
    lit = _bool_literal(cond)
    if lit is True:
        return opt_block(node.then, env)
    if lit is False:
        for idx, (econd, ebody) in enumerate(node.elifs):
            ec = opt_expr(econd, env)
            elit = _bool_literal(ec)
            if elit is True:
                return opt_block(ebody, env)
            if elit is False:
                continue
            new_if = ast.If(cond=ec, then=opt_block(ebody, env),
                            elifs=[(opt_expr(c, env), opt_block(b, env)) for c, b in node.elifs[idx + 1:]],
                            orelse=opt_block(node.orelse, env) if node.orelse is not None else None)
            return [new_if]
        if node.orelse is not None:
            return opt_block(node.orelse, env)
        return []
    node.cond = cond
    node.then = opt_block(node.then, env)
    node.elifs = [(opt_expr(c, env), opt_block(b, env)) for c, b in node.elifs]
    node.orelse = opt_block(node.orelse, env) if node.orelse is not None else None
    return [node]


def opt_expr(node, env):
    if isinstance(node, ast.Name):
        if node.id in env:
            return _clone_literal(env[node.id])
        return node
    if isinstance(node, ast.BinOp):
        return _opt_binop(node, env)
    if isinstance(node, ast.UnaryOp):
        return _opt_unary(node, env)
    if isinstance(node, ast.Ternary):
        return _opt_ternary(node, env)
    if isinstance(node, ast.Call):
        node.func = opt_expr(node.func, env)
        for arg in node.args:
            arg.value = opt_expr(arg.value, env)
        return node
    if isinstance(node, ast.Index):
        node.target = opt_expr(node.target, env)
        node.index = opt_expr(node.index, env)
        return node
    if isinstance(node, ast.Attribute):
        node.target = opt_expr(node.target, env)
        return node
    if isinstance(node, ast.Try):
        node.expr = opt_expr(node.expr, env)
        return node
    if isinstance(node, ast.ListLit):
        node.elements = [opt_expr(e, env) for e in node.elements]
        return node
    if isinstance(node, ast.TupleLit):
        node.elements = [opt_expr(e, env) for e in node.elements]
        return node
    if isinstance(node, ast.DictLit):
        node.pairs = [(opt_expr(k, env), opt_expr(v, env)) for k, v in node.pairs]
        return node
    if isinstance(node, ast.Str):
        return _opt_str(node, env)
    if isinstance(node, ast.Lambda):
        inner = dict(env)
        for p in node.params:
            inner.pop(p.name, None)
        if isinstance(node.body, list):
            node.body = opt_block(node.body, inner)
        else:
            node.body = opt_expr(node.body, inner)
        return node
    return node


def _opt_binop(node, env):
    left = opt_expr(node.left, env)
    right = opt_expr(node.right, env)
    node.left = left
    node.right = right

    if node.op in ("and", "or"):
        lb = _bool_literal(left)
        if lb is not None:
            if node.op == "and":
                return right if lb else left
            return left if lb else right
        return node

    lv = _literal_value(left)
    rv = _literal_value(right)
    if lv is not _NOTLIT and rv is not _NOTLIT:
        try:
            result = operations.binop(node.op, lv, rv)
            return _make_literal(result)
        except (UlangPanic, TypeError, ZeroDivisionError):
            return node

    if node.op in ("+", "-") and _is_zero(right):
        return left
    if node.op == "+" and _is_zero(left):
        return right
    if node.op == "*" and _is_one(right):
        return left
    if node.op == "*" and _is_one(left):
        return right
    return node


def _opt_unary(node, env):
    operand = opt_expr(node.operand, env)
    node.operand = operand
    v = _literal_value(operand)
    if v is not _NOTLIT:
        if node.op == "-" and isinstance(v, (int, float)) and not isinstance(v, bool):
            return _make_literal(-v)
        if node.op == "not" and isinstance(v, bool):
            return _make_literal(not v)
    return node


def _opt_ternary(node, env):
    cond = opt_expr(node.cond, env)
    lit = _bool_literal(cond)
    if lit is True:
        return opt_expr(node.then, env)
    if lit is False:
        return opt_expr(node.orelse, env)
    node.cond = cond
    node.then = opt_expr(node.then, env)
    node.orelse = opt_expr(node.orelse, env)
    return node


def _opt_str(node, env):
    parts = []
    for kind, value in node.parts:
        if kind == "expr":
            opt = opt_expr(value, env)
            sval = _literal_value(opt)
            if isinstance(sval, str):
                parts.append(("str", sval))
            elif sval is not _NOTLIT and not isinstance(sval, (list, dict, tuple)):
                parts.append(("str", _stringify(sval)))
            else:
                parts.append(("expr", opt))
        else:
            parts.append((kind, value))
    merged = []
    for kind, value in parts:
        if kind == "str" and merged and merged[-1][0] == "str":
            merged[-1] = ("str", merged[-1][1] + value)
        else:
            merged.append((kind, value))
    node.parts = merged
    return node


def _stringify(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value == int(value):
            return f"{value:.1f}"
        return repr(value)
    return str(value)


_NOTLIT = object()


def _literal_value(node):
    if isinstance(node, ast.Int):
        return node.value
    if isinstance(node, ast.Float):
        return node.value
    if isinstance(node, ast.Bool):
        return node.value
    if isinstance(node, ast.Str) and all(k == "str" for k, _ in node.parts):
        return "".join(v for _, v in node.parts)
    return _NOTLIT


def _clone_literal(node):
    v = _literal_value(node)
    if v is _NOTLIT:
        return node
    return _make_literal(v)


def _make_literal(value):
    if isinstance(value, bool):
        return ast.Bool(value=value)
    if isinstance(value, int):
        return ast.Int(value=value)
    if isinstance(value, float):
        return ast.Float(value=value)
    if isinstance(value, str):
        return ast.Str(parts=[("str", value)])
    raise ValueError("unsupported literal")


def _bool_literal(node):
    if isinstance(node, ast.Bool):
        return node.value
    return None


def _is_zero(node):
    return (isinstance(node, ast.Int) and node.value == 0) or \
           (isinstance(node, ast.Float) and node.value == 0.0)


def _is_one(node):
    return isinstance(node, ast.Int) and node.value == 1
