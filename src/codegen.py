import ast_nodes as ast
from llvmlite import ir


I64 = ir.IntType(64)
I32 = ir.IntType(32)
I8 = ir.IntType(8)
I1 = ir.IntType(1)
F64 = ir.DoubleType()
I8P = ir.PointerType(I8)
VOID = ir.VoidType()


class CodegenError(Exception):
    pass


class TypeInfo:
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STR = "str"

    @staticmethod
    def llvm(t):
        if t == TypeInfo.FLOAT:
            return F64
        if t == TypeInfo.BOOL:
            return I1
        if t == TypeInfo.STR:
            return I8P
        return I64


def native_type(node):
    if isinstance(node, ast.NamedType):
        if node.name == "float":
            return TypeInfo.FLOAT
        if node.name == "bool":
            return TypeInfo.BOOL
        return TypeInfo.INT
    return TypeInfo.INT


class ModuleGen:
    def __init__(self, name="mol", emit_entry=True):
        self.module = ir.Module(name=name)
        self.module.triple = ""
        self.functions = {}
        self.signatures = {}
        self.emit_entry = emit_entry
        self._declare_runtime()

    def _declare_runtime(self):
        printf_ty = ir.FunctionType(I32, [I8P], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        self._fmt_cache = {}
        self._str_cache = []

    def fmt(self, text, key):
        if key in self._fmt_cache:
            return self._fmt_cache[key]
        data = bytearray(text.encode("utf8")) + b"\x00"
        typ = ir.ArrayType(I8, len(data))
        gv = ir.GlobalVariable(self.module, typ, name=f".fmt.{key}.{len(self._fmt_cache)}")
        gv.linkage = "internal"
        gv.global_constant = True
        gv.initializer = ir.Constant(typ, bytearray(data))
        ptr = gv.bitcast(I8P)
        self._fmt_cache[key] = ptr
        return ptr

    def cstring(self, text):
        data = bytearray(text.encode("utf8")) + b"\x00"
        typ = ir.ArrayType(I8, len(data))
        idx = len(self._str_cache)
        gv = ir.GlobalVariable(self.module, typ, name=f".str.{idx}")
        gv.linkage = "internal"
        gv.global_constant = True
        gv.initializer = ir.Constant(typ, bytearray(data))
        self._str_cache.append(gv)
        return gv.bitcast(I8P)

    def generate(self, module_ast):
        for decl in module_ast.body:
            if isinstance(decl, ast.Function):
                self._declare(decl)
        for decl in module_ast.body:
            if isinstance(decl, ast.Function):
                self._define(decl)
        if self.emit_entry:
            self._emit_entry()
        return self.module

    def _emit_entry(self):
        if "main" not in self.functions:
            return
        entry_ty = ir.FunctionType(I32, [])
        entry = ir.Function(self.module, entry_ty, name="main")
        block = entry.append_basic_block("entry")
        b = ir.IRBuilder(block)
        result = b.call(self.functions["main"], [])
        b.ret(b.trunc(result, I32))

    def _declare(self, decl):
        ret = native_type(decl.return_type) if decl.return_type else TypeInfo.INT
        params = [native_type(p.type) for p in decl.params]
        llret = TypeInfo.llvm(ret) if decl.name != "main" else I64
        fnty = ir.FunctionType(llret, [TypeInfo.llvm(p) for p in params])
        name = "mol_main" if decl.name == "main" else decl.name
        fn = ir.Function(self.module, fnty, name=name)
        self.functions[decl.name] = fn
        self.signatures[decl.name] = (ret, params)

    def _define(self, decl):
        fn = self.functions[decl.name]
        gen = FunctionGen(self, fn, decl)
        gen.run()


class FunctionGen:
    def __init__(self, mod, fn, decl):
        self.mod = mod
        self.fn = fn
        self.decl = decl
        self.builder = None
        self.locals = {}
        self.local_types = {}
        self.ret_type, self.param_types = mod.signatures[decl.name]

    def run(self):
        block = self.fn.append_basic_block("entry")
        self.builder = ir.IRBuilder(block)
        for i, param in enumerate(self.decl.params):
            arg = self.fn.args[i]
            slot = self.builder.alloca(arg.type, name=param.name)
            self.builder.store(arg, slot)
            self.locals[param.name] = slot
            self.local_types[param.name] = self.param_types[i]
        self.gen_block(self.decl.body)
        if not self.builder.block.is_terminated:
            if self.decl.name == "main":
                self.builder.ret(ir.Constant(I64, 0))
            else:
                self.builder.ret(self._zero(self.ret_type))

    def _zero(self, t):
        if t == TypeInfo.FLOAT:
            return ir.Constant(F64, 0.0)
        if t == TypeInfo.BOOL:
            return ir.Constant(I1, 0)
        return ir.Constant(I64, 0)

    def gen_block(self, stmts):
        for stmt in stmts:
            if self.builder.block.is_terminated:
                break
            self.gen_stmt(stmt)

    def gen_stmt(self, node):
        method = getattr(self, "st_" + type(node).__name__, None)
        if method is None:
            raise CodegenError(f"native backend cannot compile statement {type(node).__name__}")
        method(node)

    def st_Let(self, node):
        if not isinstance(node.pattern, ast.BindPattern):
            raise CodegenError("native backend supports only simple let bindings")
        value, vtype = self.gen_expr(node.value)
        slot = self.builder.alloca(value.type, name=node.pattern.name)
        self.builder.store(value, slot)
        self.locals[node.pattern.name] = slot
        self.local_types[node.pattern.name] = vtype

    def st_Var(self, node):
        value, vtype = self.gen_expr(node.value)
        slot = self.builder.alloca(value.type, name=node.name)
        self.builder.store(value, slot)
        self.locals[node.name] = slot
        self.local_types[node.name] = vtype

    def st_Assign(self, node):
        if not isinstance(node.target, ast.Name):
            raise CodegenError("native backend supports only simple assignment targets")
        name = node.target.id
        slot = self.locals[name]
        value, vtype = self.gen_expr(node.value)
        if node.op != "=":
            cur = self.builder.load(slot)
            value = self.arith(node.op[:-1], cur, value, vtype)
        self.builder.store(value, slot)

    def st_Return(self, node):
        if node.value is None:
            self.builder.ret(self._zero(self.ret_type))
            return
        value, vtype = self.gen_expr(node.value)
        if self.decl.name == "main":
            value = self.to_i64(value, vtype)
        else:
            value = self.coerce(value, vtype, self.ret_type)
        self.builder.ret(value)

    def st_If(self, node):
        end = self.fn.append_basic_block("if.end")
        reached = [False]
        self._gen_if(node.cond, node.then, node.elifs, node.orelse, end, reached)
        self.builder.position_at_end(end)
        if not reached[0]:
            self.builder.unreachable()
            dead = self.fn.append_basic_block("if.dead")
            self.builder.position_at_end(dead)

    def _gen_if(self, cond, then, elifs, orelse, end, reached):
        cval, _ = self.gen_expr(cond)
        cbool = self.to_bool(cval)
        then_bb = self.fn.append_basic_block("if.then")
        else_bb = self.fn.append_basic_block("if.else")
        self.builder.cbranch(cbool, then_bb, else_bb)
        self.builder.position_at_end(then_bb)
        self.gen_block(then)
        if not self.builder.block.is_terminated:
            self.builder.branch(end)
            reached[0] = True
        self.builder.position_at_end(else_bb)
        if elifs:
            first, rest = elifs[0], elifs[1:]
            self._gen_if(first[0], first[1], rest, orelse, end, reached)
        elif orelse is not None:
            self.gen_block(orelse)
            if not self.builder.block.is_terminated:
                self.builder.branch(end)
                reached[0] = True
        else:
            if not self.builder.block.is_terminated:
                self.builder.branch(end)
                reached[0] = True

    def st_While(self, node):
        cond_bb = self.fn.append_basic_block("while.cond")
        body_bb = self.fn.append_basic_block("while.body")
        end_bb = self.fn.append_basic_block("while.end")
        self.builder.branch(cond_bb)
        self.builder.position_at_end(cond_bb)
        cval, _ = self.gen_expr(node.cond)
        self.builder.cbranch(self.to_bool(cval), body_bb, end_bb)
        self.builder.position_at_end(body_bb)
        self.loop_end = getattr(self, "loop_end", [])
        self.loop_end.append(end_bb)
        self.loop_cond = getattr(self, "loop_cond", [])
        self.loop_cond.append(cond_bb)
        self.gen_block(node.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_bb)
        self.loop_end.pop()
        self.loop_cond.pop()
        self.builder.position_at_end(end_bb)

    def st_For(self, node):
        if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"):
            raise CodegenError("native backend supports only 'for x in range(...)'")
        if not isinstance(node.pattern, ast.BindPattern):
            raise CodegenError("native backend for-loop needs a simple variable")
        args = node.iter.args
        if len(args) == 1:
            start = ir.Constant(I64, 0)
            stop, _ = self.gen_expr(args[0].value)
        else:
            start, _ = self.gen_expr(args[0].value)
            stop, _ = self.gen_expr(args[1].value)
        step = ir.Constant(I64, 1)
        if len(args) == 3:
            step, _ = self.gen_expr(args[2].value)
        var = self.builder.alloca(I64, name=node.pattern.name)
        self.builder.store(start, var)
        self.locals[node.pattern.name] = var
        self.local_types[node.pattern.name] = TypeInfo.INT
        cond_bb = self.fn.append_basic_block("for.cond")
        body_bb = self.fn.append_basic_block("for.body")
        end_bb = self.fn.append_basic_block("for.end")
        self.builder.branch(cond_bb)
        self.builder.position_at_end(cond_bb)
        cur = self.builder.load(var)
        cmp = self.builder.icmp_signed("<", cur, stop)
        self.builder.cbranch(cmp, body_bb, end_bb)
        self.builder.position_at_end(body_bb)
        self.gen_block(node.body)
        if not self.builder.block.is_terminated:
            cur2 = self.builder.load(var)
            self.builder.store(self.builder.add(cur2, step), var)
            self.builder.branch(cond_bb)
        self.builder.position_at_end(end_bb)

    def st_Break(self, node):
        self.builder.branch(self.loop_end[-1])

    def st_Continue(self, node):
        self.builder.branch(self.loop_cond[-1])

    def st_ExprStmt(self, node):
        self.gen_expr(node.expr)

    def gen_expr(self, node):
        method = getattr(self, "ex_" + type(node).__name__, None)
        if method is None:
            raise CodegenError(f"native backend cannot compile expression {type(node).__name__}")
        return method(node)

    def ex_Int(self, node):
        return ir.Constant(I64, node.value), TypeInfo.INT

    def ex_Float(self, node):
        return ir.Constant(F64, node.value), TypeInfo.FLOAT

    def ex_Bool(self, node):
        return ir.Constant(I1, 1 if node.value else 0), TypeInfo.BOOL

    def ex_Str(self, node):
        if any(kind == "expr" for kind, _ in node.parts):
            raise CodegenError("native backend supports only constant strings (no interpolation yet)")
        text = "".join(value for _, value in node.parts)
        return self.mod.cstring(text), TypeInfo.STR

    def ex_Name(self, node):
        if node.id not in self.locals:
            raise CodegenError(f"native backend: undefined name '{node.id}'")
        slot = self.locals[node.id]
        return self.builder.load(slot), self.local_types[node.id]

    def ex_UnaryOp(self, node):
        value, vtype = self.gen_expr(node.operand)
        if node.op == "-":
            if vtype == TypeInfo.FLOAT:
                return self.builder.fneg(value), vtype
            return self.builder.neg(value), vtype
        if node.op == "not":
            return self.builder.not_(self.to_bool(value)), TypeInfo.BOOL
        raise CodegenError(f"native unary {node.op}")

    def ex_BinOp(self, node):
        if node.op in ("and", "or"):
            return self._logical(node)
        left, lt = self.gen_expr(node.left)
        right, rt = self.gen_expr(node.right)
        if node.op in ("==", "!=", "<", "<=", ">", ">="):
            return self.compare(node.op, left, lt, right, rt), TypeInfo.BOOL
        result_type = TypeInfo.FLOAT if TypeInfo.FLOAT in (lt, rt) else lt
        left = self.coerce(left, lt, result_type)
        right = self.coerce(right, rt, result_type)
        return self.arith(node.op, left, right, result_type), result_type

    def _logical(self, node):
        left, _ = self.gen_expr(node.left)
        lb = self.to_bool(left)
        result = self.builder.alloca(I1)
        self.builder.store(lb, result)
        rhs_bb = self.fn.append_basic_block("logic.rhs")
        end_bb = self.fn.append_basic_block("logic.end")
        if node.op == "and":
            self.builder.cbranch(lb, rhs_bb, end_bb)
        else:
            self.builder.cbranch(lb, end_bb, rhs_bb)
        self.builder.position_at_end(rhs_bb)
        right, _ = self.gen_expr(node.right)
        self.builder.store(self.to_bool(right), result)
        self.builder.branch(end_bb)
        self.builder.position_at_end(end_bb)
        return self.builder.load(result), TypeInfo.BOOL

    def ex_Ternary(self, node):
        cond, _ = self.gen_expr(node.cond)
        cbool = self.to_bool(cond)
        then_val, tt = self.gen_expr(node.then)
        result_type = tt
        slot = self.builder.alloca(then_val.type)
        then_bb = self.fn.append_basic_block("tern.then")
        else_bb = self.fn.append_basic_block("tern.else")
        end_bb = self.fn.append_basic_block("tern.end")
        self.builder.cbranch(cbool, then_bb, else_bb)
        self.builder.position_at_end(then_bb)
        tv, _ = self.gen_expr(node.then)
        self.builder.store(tv, slot)
        self.builder.branch(end_bb)
        self.builder.position_at_end(else_bb)
        ev, et = self.gen_expr(node.orelse)
        self.builder.store(self.coerce(ev, et, result_type), slot)
        self.builder.branch(end_bb)
        self.builder.position_at_end(end_bb)
        return self.builder.load(slot), result_type

    def ex_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            return self._print(node.args)
        if not isinstance(node.func, ast.Name) or node.func.id not in self.mod.functions:
            raise CodegenError("native backend supports only calls to user functions and print")
        callee = self.mod.functions[node.func.id]
        ret_type, param_types = self.mod.signatures[node.func.id]
        args = []
        for i, arg in enumerate(node.args):
            val, vt = self.gen_expr(arg.value)
            args.append(self.coerce(val, vt, param_types[i]))
        result = self.builder.call(callee, args)
        return result, ret_type

    def _print(self, args):
        if not args:
            self.builder.call(self.mod.printf, [self.mod.fmt("\n", "nl")])
            return ir.Constant(I64, 0), TypeInfo.INT
        val, vt = self.gen_expr(args[0].value)
        if vt == TypeInfo.FLOAT:
            fmt = self.mod.fmt("%g\n", "f")
            self.builder.call(self.mod.printf, [fmt, val])
        elif vt == TypeInfo.BOOL:
            self._print_bool(val)
        elif vt == TypeInfo.STR:
            fmt = self.mod.fmt("%s\n", "s")
            self.builder.call(self.mod.printf, [fmt, val])
        else:
            fmt = self.mod.fmt("%ld\n", "d")
            self.builder.call(self.mod.printf, [fmt, val])
        return ir.Constant(I64, 0), TypeInfo.INT

    def _print_bool(self, val):
        true_str = self.mod.fmt("true\n", "true")
        false_str = self.mod.fmt("false\n", "false")
        ptr = self.builder.select(val, true_str, false_str)
        self.builder.call(self.mod.printf, [ptr])

    def arith(self, op, left, right, t):
        if t == TypeInfo.FLOAT:
            return {
                "+": self.builder.fadd, "-": self.builder.fsub,
                "*": self.builder.fmul, "/": self.builder.fdiv,
                "%": self.builder.frem,
            }[op](left, right)
        if op == "/":
            return self.builder.sdiv(left, right)
        if op == "%":
            return self.builder.srem(left, right)
        return {
            "+": self.builder.add, "-": self.builder.sub, "*": self.builder.mul,
        }[op](left, right)

    def compare(self, op, left, lt, right, rt):
        if TypeInfo.FLOAT in (lt, rt):
            left = self.coerce(left, lt, TypeInfo.FLOAT)
            right = self.coerce(right, rt, TypeInfo.FLOAT)
            return self.builder.fcmp_ordered(op, left, right)
        return self.builder.icmp_signed(op, left, right)

    def coerce(self, value, from_t, to_t):
        if from_t == to_t:
            return value
        if from_t == TypeInfo.INT and to_t == TypeInfo.FLOAT:
            return self.builder.sitofp(value, F64)
        if from_t == TypeInfo.BOOL and to_t == TypeInfo.INT:
            return self.builder.zext(value, I64)
        if from_t == TypeInfo.BOOL and to_t == TypeInfo.FLOAT:
            return self.builder.sitofp(self.builder.zext(value, I64), F64)
        return value

    def to_i64(self, value, vtype):
        if vtype == TypeInfo.FLOAT:
            return self.builder.fptosi(value, I64)
        if vtype == TypeInfo.BOOL:
            return self.builder.zext(value, I64)
        return value

    def to_bool(self, value):
        if value.type == I1:
            return value
        if value.type == F64:
            return self.builder.fcmp_ordered("!=", value, ir.Constant(F64, 0.0))
        return self.builder.icmp_signed("!=", value, ir.Constant(value.type, 0))


def generate_ir(module_ast):
    return ModuleGen().generate(module_ast)
