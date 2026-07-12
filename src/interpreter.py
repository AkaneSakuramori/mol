import os
import ast_nodes as ast
import values as V
from values import Struct, Variant, Closure, Builtin, BoundMethod, some, ok, err, NONE, ulang_str
from builtins_mod import BUILTINS, get_method, UlangPanic
import stdlib
import runtime
import operations


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
        raise UlangPanic(f"undefined name '{name}'")

    def set(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        raise UlangPanic(f"assignment to undefined '{name}'")


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
        self.depth = 0
        self.max_depth = 5000
        self.env_stack = []
        import memory
        self.memory = memory.MemoryManager(self._gc_roots)
        for name, val in BUILTINS.items():
            self.globals.set(name, val)
        self._install_gc_builtins()
        runtime.install(self)

    def _gc_roots(self):
        roots = [self.globals]
        roots.extend(self.env_stack)
        return roots

    def _install_gc_builtins(self):
        from values import Builtin
        def enable_and_collect(a):
            self.memory.enabled = True
            return self.memory.collect(full=True)
        self.globals.set("gc_collect", Builtin("gc_collect", enable_and_collect))
        self.globals.set("gc_alloc_count", Builtin("gc_alloc_count", lambda a: self.memory.stats()["total_allocated"]))
        self.globals.set("gc_live_count", Builtin("gc_live_count", lambda a: self.memory.stats()["live_objects"]))
        self.globals.set("gc_enable", Builtin("gc_enable", lambda a: self._gc_set(True)))
        self.globals.set("gc_disable", Builtin("gc_disable", lambda a: self._gc_set(False)))

    def _gc_set(self, on):
        self.memory.enabled = on
        return None

    def run(self, module):
        import bigstack
        return bigstack.run_with_large_stack(lambda: self._run(module))

    def _run(self, module):
        import sys as _sys
        import bigstack
        self.max_depth = bigstack.safe_max_depth(self.max_depth)
        _sys.setrecursionlimit(max(_sys.getrecursionlimit(), bigstack.python_recursion_limit()))
        self.cur_line = 0
        self.collect(module)
        main = self.functions.get("main")
        if main is None:
            raise UlangPanic("no main function")
        try:
            return self.call(main, [])
        except UlangPanic as e:
            if getattr(e, "line", 0) == 0 and self.cur_line:
                e.line = self.cur_line
                e.message = f"{e.message} (line {self.cur_line})"
                e.args = (e.message,)
            raise

    def collect(self, module):
        self._collect(module, run_imports=True)

    def collect_library(self, module):
        self._collect(module, run_imports=True)

    def _collect(self, module, run_imports=True):
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
                if run_imports:
                    self.exec_import(decl)
            elif isinstance(decl, ast.ExternFn):
                self.register_extern(decl)

    def register_extern(self, decl):
        import ffi
        try:
            self.globals.set(decl.name, ffi.make_extern(decl))
        except (OSError, AttributeError) as e:
            raise UlangPanic(f"extern '{decl.name}': {e}")

    def exec_import(self, decl):
        name = decl.path[-1]
        module = stdlib.get_module(name)
        if module is None:
            module = self._load_package_module(name)
        if module is None:
            return
        if decl.names is not None:
            for member in decl.names:
                if member in module.members:
                    self.globals.set(member, module.members[member])
        else:
            bind = decl.alias if decl.alias else name
            self.globals.set(bind, module)

    def _load_package_module(self, name):
        import loader
        roots = getattr(self, "search_roots", None) or [os.getcwd()]
        try:
            return loader.load_package(name, roots, type(self))
        except Exception:
            return None

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
                raise UlangPanic(f"{decl.name}: expected {len(field_names)} fields, got {len(args)}")
            return self.memory.record(Struct(decl.name, dict(zip(field_names, args))))

        return Builtin(decl.name, ctor)

    def make_variant_ctor(self, enum_name, variant):
        if not variant.types:
            return Variant(enum_name, variant.name, [])

        def ctor(args):
            return self.memory.record(Variant(enum_name, variant.name, list(args)))

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
        raise UlangPanic(f"not callable: {fn!r}")

    def call_closure(self, closure, args):
        self.depth = getattr(self, "depth", 0) + 1
        if self.depth > self.max_depth:
            self.depth -= 1
            raise UlangPanic(f"stack overflow: recursion exceeded {self.max_depth} frames")
        try:
            return self._call_closure_inner(closure, args)
        finally:
            self.depth -= 1

    def _call_closure_inner(self, closure, args):
        env = Environment(closure.env)
        params = closure.params
        if len(args) > len(params):
            raise UlangPanic(f"{closure.name}: expected {len(params)} argument(s), got {len(args)}")
        for i, param in enumerate(params):
            if i < len(args):
                env.set(param.name, args[i])
            elif param.default is not None:
                env.set(param.name, self.eval(param.default, env))
            else:
                raise UlangPanic(f"{closure.name}: missing argument '{param.name}'")
        deferred = []
        env.set("__defer__", deferred)
        self.env_stack.append(env)
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
        finally:
            self.env_stack.pop()

    def run_deferred(self, deferred, env):
        for expr in reversed(deferred):
            self.eval(expr, env)

    def exec_block(self, stmts, env):
        result = None
        for stmt in stmts:
            result = self.exec(stmt, env)
            self.memory.safepoint()
        return result

    def exec(self, node, env):
        line = getattr(node, "line", 0)
        if line:
            self.cur_line = line
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
                raise UlangPanic("cannot assign attribute")
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
        raise UlangPanic("no match arm matched")

    def exec_ExprStmt(self, node, env):
        return self.eval(node.expr, env)

    def iterate(self, value):
        if isinstance(value, (list, tuple, str)):
            return value
        if isinstance(value, dict):
            return list(value.keys())
        raise UlangPanic(f"not iterable: {type(value).__name__}")

    def bind_pattern(self, pattern, value, env):
        if not self.match_pattern(pattern, value, env):
            raise UlangPanic("pattern binding failed")

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
        raise UlangPanic(f"unknown pattern {type(pattern).__name__}")

    def eval(self, node, env):
        method = getattr(self, "eval_" + type(node).__name__, None)
        if method is None:
            raise UlangPanic(f"cannot evaluate {type(node).__name__}")
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
                out.append(ulang_str(self.eval(value, env)))
        return "".join(out)

    def eval_Name(self, node, env):
        return env.get(node.id)

    def eval_ListLit(self, node, env):
        return self.memory.record([self.eval(e, env) for e in node.elements])

    def eval_DictLit(self, node, env):
        return self.memory.record({self.eval(k, env): self.eval(v, env) for k, v in node.pairs})

    def eval_TupleLit(self, node, env):
        return self.memory.record(tuple(self.eval(e, env) for e in node.elements))

    def eval_Lambda(self, node, env):
        return self.memory.record(Closure(node.params, node.body, env, "<lambda>"))

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
        return operations.binop(op, left, right)

    def _both_numbers(self, left, right):
        return operations.both_numbers(left, right)

    def type_label(self, value):
        return operations.type_label(value)

    def eval_UnaryOp(self, node, env):
        operand = self.eval(node.operand, env)
        if node.op == "-":
            return -operand
        if node.op == "not":
            return not self.truthy(operand)
        raise UlangPanic(f"unknown unary {node.op}")

    def eval_Call(self, node, env):
        func = self.eval(node.func, env)
        args = []
        for arg in node.args:
            args.append(self.eval(arg.value, env))
        return self.call(func, args)

    def eval_Index(self, node, env):
        target = self.eval(node.target, env)
        index = self.eval(node.index, env)
        return operations.index(target, index)

    def eval_Attribute(self, node, env):
        obj = self.eval(node.target, env)
        if isinstance(obj, Struct) and node.name in obj.fields:
            return obj.fields[node.name]
        if isinstance(obj, V.Module):
            if node.name in obj.members:
                return obj.members[node.name]
            raise UlangPanic(f"module '{obj.name}' has no member '{node.name}'")
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
        raise UlangPanic(f"no attribute '{node.name}'")

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
