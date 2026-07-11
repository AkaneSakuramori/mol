from builtins_mod import UlangPanic


def type_label(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, tuple):
        return "tuple"
    return type(value).__name__


def both_numbers(left, right):
    return (isinstance(left, (int, float)) and not isinstance(left, bool)
            and isinstance(right, (int, float)) and not isinstance(right, bool))


def binop(op, left, right):
    try:
        if op == "+":
            if isinstance(left, str) != isinstance(right, str):
                raise UlangPanic(f"cannot add {type_label(left)} and {type_label(right)}")
            if isinstance(left, bool) or isinstance(right, bool):
                raise UlangPanic("cannot use '+' on bool")
            return left + right
        if op == "-":
            _need_numbers(op, left, right)
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if isinstance(left, int) and isinstance(right, int) and not isinstance(left, bool) and not isinstance(right, bool):
                if right == 0:
                    raise UlangPanic("division by zero")
                return left // right
            _need_numbers(op, left, right)
            if right == 0:
                raise UlangPanic("division by zero")
            return left / right
        if op == "%":
            _need_numbers(op, left, right)
            if right == 0:
                raise UlangPanic("modulo by zero")
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op in ("<", "<=", ">", ">="):
            if type(left) is not type(right) and not both_numbers(left, right):
                raise UlangPanic(f"cannot compare {type_label(left)} and {type_label(right)}")
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            return left >= right
    except TypeError:
        raise UlangPanic(f"invalid operands for '{op}': {type_label(left)} and {type_label(right)}")
    raise UlangPanic(f"unknown operator {op}")


def _need_numbers(op, left, right):
    if not both_numbers(left, right):
        raise UlangPanic(f"'{op}' needs numbers, got {type_label(left)} and {type_label(right)}")


def index(target, idx):
    if isinstance(target, dict):
        if idx not in target:
            from values import ulang_str
            raise UlangPanic(f"key not found: {ulang_str(idx)}")
        return target[idx]
    if isinstance(target, (list, str, tuple)):
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise UlangPanic(f"index must be int, got {type_label(idx)}")
        if idx < 0 or idx >= len(target):
            raise UlangPanic(f"index {idx} out of range for {type_label(target)} of length {len(target)}")
        return target[idx]
    raise UlangPanic(f"cannot index {type_label(target)}")
