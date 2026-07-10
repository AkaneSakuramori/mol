import ast_nodes as ast
from values import Variant, NONE


def literal_value(node):
    if isinstance(node, ast.Int):
        return node.value
    if isinstance(node, ast.Float):
        return node.value
    if isinstance(node, ast.Bool):
        return node.value
    if isinstance(node, ast.Str):
        return "".join(v for k, v in node.parts if k == "str")
    if isinstance(node, ast.NoneLit):
        return NONE
    return None


def match(pattern, value):
    if isinstance(pattern, ast.WildcardPattern):
        return {}
    if isinstance(pattern, ast.BindPattern):
        return {pattern.name: value}
    if isinstance(pattern, ast.LiteralPattern):
        if literal_value(pattern.value) == value:
            return {}
        return None
    if isinstance(pattern, ast.VariantPattern):
        if not isinstance(value, Variant) or value.name != pattern.name:
            return None
        if len(pattern.args) != len(value.values):
            return None
        bindings = {}
        for sub, val in zip(pattern.args, value.values):
            b = match(sub, val)
            if b is None:
                return None
            bindings.update(b)
        return bindings
    if isinstance(pattern, ast.TuplePattern):
        if not isinstance(value, tuple) or len(value) != len(pattern.elements):
            return None
        bindings = {}
        for sub, val in zip(pattern.elements, value):
            b = match(sub, val)
            if b is None:
                return None
            bindings.update(b)
        return bindings
    return None
