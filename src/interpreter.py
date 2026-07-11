import ast_nodes as ast
import values as V
from values import Struct, Variant, Closure, Builtin, BoundMethod, some, ok, err, NONE, mol_str
from builtins_mod import BUILTINS, get_method, MolPanic
import stdlib
import runtime


class Environment:
    __slots__ = ("vars", "parent")

    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise MolPanic(f"undefined name '{name}'")

    def set(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        raise MolPanic(f"assignment to undefined '{name}'")


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class TryUnwind(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.types = {}
        self.enums = {}
        self.traits = {}
        self.impls = {}
        self.functions = {}
        for name, val in BUILTINS.items():
            self.globals.set(name, val)
        runtime.install(self)

    def run(self, module):
        self.collect(module)
        main = self.functions.get("main")
        if main is None:
            raise MolPanic("no main function")
        return self.call(main, [])

    def collect(self, module):
        for decl in module.body:
            if isinstance(decl, ast.Function):
                closure = Closure(decl.params, decl.body, self.globals, decl.name)
                self.functions[decl.name] = closure
                self.globals.set(decl.name, closure)
            elif isinstance(decl, ast.TypeDecl):
                self.types[decl.name] = decl
                self.globals.set(decl.name, self.make_struct_ctor(decl))
            elif isinstance(decl, ast.EnumDecl):
                self.enums[decl.name] = decl
                for variant in decl.variants:
                    self.globals.set(variant.name, self.make_variant_ctor(decl.name, variant))
            elif isinstance(decl, ast.Const):
                self.globals.set(decl.name, self.eval(decl.value, self.globals))
            elif isinstance(decl, ast.ImplDecl):
                self.register_impl(decl)
            elif isinstance(decl, ast.TraitDecl):
                self.traits[decl.name] = decl
            elif isinstance(decl, ast.Import):
                self.exec_import(decl)
            elif isinstance(decl, ast.ExternFn):
                self.register_extern(decl)

    def register_extern(self, decl):
        import ffi
        try:
            self.globals.set(decl.name, ffi.make_extern(decl))
        except (OSError, AttributeError) as e:
            raise MolPanic(f"extern '{decl.name}': {e}")

    def exec_import(self, decl):
        name = decl.path[-1]
        module = stdlib.get_module(name)
        if module is None:
            return
        if decl.names is not None:
            for member in decl.names:
                if member in module.members:
                    self.globals.set(member, module.members[member])
        else:
            bind = decl.alias if decl.alias else name
            self.globals.set(bind, module)

    def register_impl(self, decl):
        type_name = self.type_name_of(decl.type)
        table = self.impls.setdefault(type_name, {})
        for method in decl.methods:
            table[method.name] = Closure(method.params, method.body, self.globals, method.name)

    def type_name_of(self, type_node):
        if isinstance(type_node, ast.NamedType):
            return type_node.name
        return None

    def make_struct_ctor(self, decl):
        field_names = [f.name for f in decl.fields]

        def ctor(args):
            if len(args) != len(field_names):
                raise MolPanic(f"{decl.name}: expected {len(field_names)} fields, got {len(args)}")
            return Struct(decl.name, dict(zip(field_names, args)))

        return Builtin(decl.name, ctor)

    def make_variant_ctor(self, enum_name, variant):
        if not variant.types:
            return Variant(enum_name, variant.name, [])

        def ctor(args):
            return Variant(enum_name, variant.name, list(args))

        return Builtin(variant.name, ctor)

    def call(self, fn, args):
        if isinstance(fn, Builtin):
            return fn.fn(args)
        if isinstance(fn, Variant):
            return fn
        if isinstance(fn, BoundMethod):
            return self.call(fn.fn, [fn.receiver] + args)
        if isinstance(fn, Closure):
            return self.call_closure(fn, args)
        raise MolPanic(f"not callable: {fn!r}")

    def call_closure(self, closure, args):
        env = Environment(closure.env)
        params = closure.params
        for i, param in enumerate(params):
            if i < len(args):
                env.set(param.name, args[i])
            elif param.default is not None:
                env.set(param.name, self.eval(param.default, env))
            else:
                raise MolPanic(f"{closure.name}: missing argument '{param.name}'")
        deferred = []
        env.set("__defer__", deferred)
        try:
            if isinstance(closure.body, list):
                result = self.exec_block(closure.body, env)
            else:
                result = self.eval(closure.body, env)
            self.run_deferred(deferred, env)
            return result
        except ReturnSignal as r:
            self.run_deferred(deferred, env)
            return r.value
        except TryUnwind as t:
            self.run_deferred(deferred, env)
            return t.value

    def run_deferred(self, deferred, env):
        for expr in reversed(deferred):
            self.eval(expr, env)

    def exec_block(self, stmts, env):
        result = None
        for stmt in stmts:
            result = self.exec(stmt, env)
        return result

    def exec(self, node, env):
        method = getattr(self, "exec_" + type(node).__name__, None)
        if method is None:
            return self.eval(node, env)
        return method(node, env)

    def exec_Let(self, node, env):
        value = self.eval(node.value, env)
        self.bind_pattern(node.pattern, value, env)
        return None

    def exec_Var(self, node, env):
        env.set(node.name, self.eval(node.value, env))
        return None

    def exec_Assign(self, node, env):
        value = self.eval(node.value, env)
        target = node.target
        if node.op != "=":
            current = self.eval(target, env)
            value = self.apply_binop(node.op[:-1], current, value)
        if isinstance(target, ast.Name):
            env.assign(target.id, value)
        elif isinstance(target, ast.Index):
            container = self.eval(target.target, env)
            key = self.eval(target.index, env)
            container[key] = value
        elif isinstance(target, ast.Attribute):
            obj = self.eval(target.target, env)
            if isinstance(obj, Struct):
                obj.fields[target.name] = value
            else:
                raise MolPanic("cannot assign attribute")
        return None

    def exec_Return(self, node, env):
        value = self.eval(node.value, env) if node.value is not None else None
        raise ReturnSignal(value)

    def exec_Break(self, node, env):
        raise BreakSignal()

    def exec_Continue(self, node, env):
        raise ContinueSignal()

    def exec_Defer(self, node, env):
        env.get("__defer__").append(node.expr)
        return None

    def exec_If(self, node, env):
        if self.truthy(self.eval(node.cond, env)):
            return self.exec_block(node.then, Environment(env))
        for econd, ebody in node.elifs:
            if self.truthy(self.eval(econd, env)):
                return self.exec_block(ebody, Environment(env))
        if node.orelse is not None:
            return self.exec_block(node.orelse, Environment(env))
        return None

    def exec_While(self, node, env):
        while self.truthy(self.eval(node.cond, env)):
            try:
                self.exec_block(node.body, Environment(env))
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return None

    def exec_For(self, node, env):
        iterable = self.eval(node.iter, env)
        for item in self.iterate(iterable):
            loop_env = Environment(env)
            self.bind_pattern(node.pattern, item, loop_env)
            try:
                self.exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return None

    def exec_With(self, node, env):
        resource = self.eval(node.expr, env)
        with_env = Environment(env)
        if node.alias:
            with_env.set(node.alias, resource)
        try:
            self.exec_block(node.body, with_env)
        finally:
            if isinstance(resource, runtime.Nursery):
                resource.join()
            elif isinstance(resource, stdlib._FileValue):
                resource.fp.close()
            else:
                closer = get_method(resource, "close", self)
                if closer is not None:
                    self.call(closer, [])
        return None

    def exec_Match(self, node, env):
        subject = self.eval(node.subject, env)
        for arm in node.arms:
            arm_env = Environment(env)
            if self.match_pattern(arm.pattern, subject, arm_env):
                if arm.guard is not None and not self.truthy(self.eval(arm.guard, arm_env)):
                    continue
                if isinstance(arm.body, list):
                    return self.exec_block(arm.body, arm_env)
                return self.eval(arm.body, arm_env)
        raise MolPanic("no match arm matched")

    def exec_ExprStmt(self, node, env):
        return self.eval(node.expr, env)

    def iterate(self, value):
        if isinstance(value, (list, tuple, str)):
            return value
        if isinstance(value, dict):
            return list(value.keys())
        raise MolPanic(f"not iterable: {type(value).__name__}")

    def bind_pattern(self, pattern, value, env):
        if not self.match_pattern(pattern, value, env):
            raise MolPanic("pattern binding failed")

    def match_pattern(self, pattern, value, env):
        if isinstance(pattern, ast.WildcardPattern):
            return True
        if isinstance(pattern, ast.BindPattern):
            env.set(pattern.name, value)
            return True
        if isinstance(pattern, ast.LiteralPattern):
            return self.eval(pattern.value, env) == value
        if isinstance(pattern, ast.VariantPattern):
            if not isinstance(value, Variant) or value.name != pattern.name:
                return False
            if len(pattern.args) != len(value.values):
                return False
            for sub, val in zip(pattern.args, value.values):
                if not self.match_pattern(sub, val, env):
                    return False
            return True
        if isinstance(pattern, ast.TuplePattern):
            if not isinstance(value, tuple) or len(value) != len(pattern.elements):
                return False
            for sub, val in zip(pattern.elements, value):
                if not self.match_pattern(sub, val, env):
                    return False
            return True
        raise MolPanic(f"unknown pattern {type(pattern).__name__}")

    def eval(self, node, env):
        method = getattr(self, "eval_" + type(node).__name__, None)
        if method is None:
            raise MolPanic(f"cannot evaluate {type(node).__name__}")
        return method(node, env)

    def eval_Int(self, node, env):
        return node.value

    def eval_Float(self, node, env):
        return node.value

    def eval_Bool(self, node, env):
        return node.value

    def eval_NoneLit(self, node, env):
        return NONE

    def eval_Str(self, node, env):
        out = []
        for kind, value in node.parts:
            if kind == "str":
                out.append(value)
            else:
                out.append(mol_str(self.eval(value, env)))
        return "".join(out)

    def eval_Name(self, node, env):
        return env.get(node.id)

    def eval_ListLit(self, node, env):
        return [self.eval(e, env) for e in node.elements]

    def eval_DictLit(self, node, env):
        return {self.eval(k, env): self.eval(v, env) for k, v in node.pairs}

    def eval_TupleLit(self, node, env):
        return tuple(self.eval(e, env) for e in node.elements)

    def eval_Lambda(self, node, env):
        return Closure(node.params, node.body, env, "<lambda>")

    def eval_Ternary(self, node, env):
        if self.truthy(self.eval(node.cond, env)):
            return self.eval(node.then, env)
        return self.eval(node.orelse, env)

    def eval_BinOp(self, node, env):
        if node.op == "and":
            left = self.eval(node.left, env)
            if not self.truthy(left):
                return left
            return self.eval(node.right, env)
        if node.op == "or":
            left = self.eval(node.left, env)
            if self.truthy(left):
                return left
            return self.eval(node.right, env)
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        return self.apply_binop(node.op, left, right)

    def apply_binop(self, op, left, right):
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if isinstance(left, int) and isinstance(right, int):
                if right == 0:
                    raise MolPanic("division by zero")
                return left // right
            return left / right
        if op == "%":
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        raise MolPanic(f"unknown operator {op}")

    def eval_UnaryOp(self, node, env):
        operand = self.eval(node.operand, env)
        if node.op == "-":
            return -operand
        if node.op == "not":
            return not self.truthy(operand)
        raise MolPanic(f"unknown unary {node.op}")

    def eval_Call(self, node, env):
        func = self.eval(node.func, env)
        args = []
        for arg in node.args:
            args.append(self.eval(arg.value, env))
        return self.call(func, args)

    def eval_Index(self, node, env):
        target = self.eval(node.target, env)
        index = self.eval(node.index, env)
        if isinstance(target, dict):
            if index not in target:
                raise MolPanic(f"key not found: {index!r}")
            return target[index]
        return target[index]

    def eval_Attribute(self, node, env):
        obj = self.eval(node.target, env)
        if isinstance(obj, Struct) and node.name in obj.fields:
            return obj.fields[node.name]
        if isinstance(obj, V.Module):
            if node.name in obj.members:
                return obj.members[node.name]
            raise MolPanic(f"module '{obj.name}' has no member '{node.name}'")
        if isinstance(obj, stdlib._FileValue):
            method = obj.method(node.name)
            if method is not None:
                return method
        type_name = self.value_type_name(obj)
        if type_name in self.impls and node.name in self.impls[type_name]:
            return BoundMethod(obj, self.impls[type_name][node.name], node.name)
        rt_method = runtime.get_method(obj, node.name)
        if rt_method is not None:
            return rt_method
        method = get_method(obj, node.name, self)
        if method is not None:
            return method
        raise MolPanic(f"no attribute '{node.name}'")

    def eval_Try(self, node, env):
        value = self.eval(node.expr, env)
        if isinstance(value, Variant):
            if value.name in ("Err", "None"):
                raise TryUnwind(value)
            if value.name in ("Ok", "Some"):
                return value.values[0] if value.values else None
        return value

    def value_type_name(self, value):
        if isinstance(value, Struct):
            return value.type_name
        if isinstance(value, Variant):
            return value.enum_name
        return None

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        return bool(value)


def interpret(module):
    return Interpreter().run(module)
