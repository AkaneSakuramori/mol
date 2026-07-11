from bytecode import Op
import values as V
from values import Struct, Variant, Closure, Builtin, BoundMethod, some, ok, err, NONE, ulang_str
from builtins_mod import BUILTINS, get_method, UlangPanic
import patterns
import stdlib
import operations


class Env:
    __slots__ = ("vars", "parent")

    def __init__(self, vars, parent=None):
        self.vars = vars
        self.parent = parent

    def get(self, name):
        e = self
        while e is not None:
            if name in e.vars:
                return e.vars[name], True
            e = e.parent
        return None, False

    def define(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        e = self
        while e is not None:
            if name in e.vars:
                e.vars[name] = value
                return
            e = e.parent
        self.vars[name] = value


class Frame:
    __slots__ = ("code", "env", "stack", "ip")

    def __init__(self, code, env):
        self.code = code
        self.env = env
        self.stack = []
        self.ip = 0


class VM:
    def __init__(self, program):
        self.program = program
        self.globals = {}
        self.depth = 0
        self.max_depth = 2500
        self._setup()

    def _setup(self):
        for name, val in BUILTINS.items():
            self.globals[name] = val
        for name, code in self.program.functions.items():
            self.globals[name] = Closure(None, code, None, name)
        for name, fields in self.program.types.items():
            self.globals[name] = self._struct_ctor(name, fields)
        for name, (enum_name, arity) in self.program.enums.items():
            if arity == 0:
                self.globals[name] = Variant(enum_name, name, [])
            else:
                self.globals[name] = self._variant_ctor(enum_name, name)
        for decl in self.program.imports:
            self._import(decl)
        for const in self.program.consts:
            self.globals[const.name] = self.eval_const(const.value)

    def _import(self, decl):
        name = decl.path[-1]
        module = stdlib.get_module(name)
        if module is None:
            return
        if decl.names is not None:
            for m in decl.names:
                if m in module.members:
                    self.globals[m] = module.members[m]
        else:
            bind = decl.alias if decl.alias else name
            self.globals[bind] = module

    def eval_const(self, node):
        code = _compile_const(node, self.program)
        return self.run_code(code, Env({}))

    def _struct_ctor(self, name, fields):
        def ctor(args):
            return Struct(name, dict(zip(fields, args)))
        return Builtin(name, ctor)

    def _variant_ctor(self, enum_name, name):
        def ctor(args):
            return Variant(enum_name, name, list(args))
        return Builtin(name, ctor)

    def run(self):
        import bigstack
        return bigstack.run_with_large_stack(self._run)

    def _run(self):
        import sys as _sys
        import bigstack
        self.max_depth = bigstack.safe_max_depth(self.max_depth)
        _sys.setrecursionlimit(max(_sys.getrecursionlimit(), bigstack.python_recursion_limit()))
        main = self.globals.get("main")
        if main is None:
            raise UlangPanic("no main function")
        return self.call(main, [])

    def call(self, fn, args):
        if isinstance(fn, Builtin):
            return fn.fn(args)
        if isinstance(fn, BoundMethod):
            return self.call(fn.fn, [fn.receiver] + args)
        if isinstance(fn, Closure):
            self.depth += 1
            if self.depth > self.max_depth:
                self.depth -= 1
                raise UlangPanic(f"stack overflow: recursion exceeded {self.max_depth} frames")
            try:
                parent = fn.env if isinstance(fn.env, Env) else None
                env = Env({}, parent)
                code = fn.body
                params = code.params
                if len(args) > len(params):
                    raise UlangPanic(f"{code.name}: expected {len(params)} argument(s), got {len(args)}")
                for i, pname in enumerate(params):
                    env.define(pname, args[i] if i < len(args) else None)
                return self.run_code(code, env)
            finally:
                self.depth -= 1
        if isinstance(fn, Variant):
            return fn
        raise UlangPanic(f"not callable: {fn!r}")

    def run_code(self, code, env):
        frame = Frame(code, env)
        stack = frame.stack
        instrs = code.instrs
        consts = code.consts
        while frame.ip < len(instrs):
            instr = instrs[frame.ip]
            frame.ip += 1
            op = instr.op
            arg = instr.arg

            if op == Op.LOAD_CONST:
                stack.append(consts[arg])
            elif op == Op.LOAD_NAME:
                value, found = env.get(arg)
                if found:
                    stack.append(value)
                elif arg in self.globals:
                    stack.append(self.globals[arg])
                else:
                    raise UlangPanic(f"undefined name '{arg}'")
            elif op == Op.STORE_NAME:
                env.define(arg, stack.pop())
            elif op == Op.ASSIGN_NAME:
                env.assign(arg, stack.pop())
            elif op == Op.POP:
                stack.pop()
            elif op == Op.DUP:
                stack.append(stack[-1])
            elif op == Op.BINARY:
                right = stack.pop()
                left = stack.pop()
                stack.append(self.binary(arg, left, right))
            elif op == Op.UNARY:
                stack.append(self.unary(arg, stack.pop()))
            elif op == Op.BUILD_LIST:
                items = stack[len(stack) - arg:]
                del stack[len(stack) - arg:]
                stack.append(list(items))
            elif op == Op.BUILD_DICT:
                d = {}
                pairs = stack[len(stack) - arg * 2:]
                del stack[len(stack) - arg * 2:]
                for i in range(0, len(pairs), 2):
                    d[pairs[i]] = pairs[i + 1]
                stack.append(d)
            elif op == Op.BUILD_TUPLE:
                items = stack[len(stack) - arg:]
                del stack[len(stack) - arg:]
                stack.append(tuple(items))
            elif op == Op.BUILD_STRING:
                parts = stack[len(stack) - arg:]
                del stack[len(stack) - arg:]
                stack.append("".join(ulang_str(p) for p in parts))
            elif op == Op.JUMP:
                frame.ip = arg
            elif op == Op.JUMP_IF_FALSE:
                if not self.truthy(stack.pop()):
                    frame.ip = arg
            elif op == Op.JUMP_IF_TRUE:
                if self.truthy(stack.pop()):
                    frame.ip = arg
            elif op == Op.CALL:
                args = stack[len(stack) - arg:]
                del stack[len(stack) - arg:]
                fn = stack.pop()
                stack.append(self.call(fn, args))
            elif op == Op.RETURN:
                return stack.pop()
            elif op == Op.GET_INDEX:
                index = stack.pop()
                target = stack.pop()
                stack.append(self.get_index(target, index))
            elif op == Op.SET_INDEX:
                value = stack.pop()
                index = stack.pop()
                target = stack.pop()
                target[index] = value
            elif op == Op.GET_ATTR:
                stack.append(self.get_attr(stack.pop(), arg))
            elif op == Op.SET_ATTR:
                value = stack.pop()
                target = stack.pop()
                if isinstance(target, Struct):
                    target.fields[arg] = value
                else:
                    raise UlangPanic("cannot set attribute")
            elif op == Op.MAKE_CLOSURE:
                stack.append(Closure(None, arg, env, "<lambda>"))
            elif op == Op.MATCH_VARIANT:
                value = stack.pop()
                bindings = patterns.match(arg, value)
                if bindings is None:
                    stack.append(False)
                else:
                    for k, v in bindings.items():
                        env.define(k, v)
                    stack.append(True)
            elif op == Op.TRY_UNWRAP:
                value = stack.pop()
                if isinstance(value, Variant) and value.name in ("Err", "None"):
                    return value
                if isinstance(value, Variant) and value.name in ("Ok", "Some"):
                    stack.append(value.values[0] if value.values else None)
                else:
                    stack.append(value)
            elif op == Op.ITER_NEW:
                stack.append(_Iter(self.iterate(stack.pop())))
            elif op == Op.ITER_NEXT:
                it = stack.pop()
                nxt = it.next()
                if nxt is _STOP:
                    stack.append(False)
                else:
                    stack.append(nxt)
                    stack.append(True)
            else:
                raise UlangPanic(f"unknown op {op}")
        return None

    def iterate(self, value):
        if isinstance(value, (list, tuple, str)):
            return iter(value)
        if isinstance(value, dict):
            return iter(list(value.keys()))
        raise UlangPanic(f"not iterable: {type(value).__name__}")

    def get_index(self, target, index):
        return operations.index(target, index)

    def get_attr(self, obj, name):
        if isinstance(obj, Struct) and name in obj.fields:
            return obj.fields[name]
        if isinstance(obj, V.Module):
            if name in obj.members:
                return obj.members[name]
            raise UlangPanic(f"module '{obj.name}' has no member '{name}'")
        if isinstance(obj, stdlib._FileValue):
            m = obj.method(name)
            if m is not None:
                return m
        type_name = None
        if isinstance(obj, Struct):
            type_name = obj.type_name
        method = get_method(obj, name, self)
        if method is not None:
            return method
        raise UlangPanic(f"no attribute '{name}'")

    def binary(self, op, left, right):
        return operations.binop(op, left, right)

    def unary(self, op, value):
        if op == "-":
            return -value
        if op == "not":
            return not self.truthy(value)
        raise UlangPanic(f"unknown unary {op}")

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        return bool(value)


_STOP = object()


class _Iter:
    __slots__ = ("it",)

    def __init__(self, it):
        self.it = it

    def next(self):
        return next(self.it, _STOP)


def _compile_const(node, program):
    from compiler import FunctionCompiler
    from bytecode import Op as _Op
    fc = FunctionCompiler("<const>", [], program)
    fc.compile_expr(node)
    fc.emit(_Op.RETURN)
    return fc.code


def execute(program):
    return VM(program).run()
