import ast_nodes as ast
from bytecode import Op, CodeObject


class CompileError(Exception):
    pass


class FunctionCompiler:
    def __init__(self, name, params, program):
        self.code = CodeObject(name)
        self.code.params = [p.name for p in params]
        self.program = program
        self.loop_stack = []

    def emit(self, op, arg=None, line=0):
        return self.code.emit(op, arg, line)

    def load_const(self, value, line=0):
        idx = self.code.const(value)
        self.emit(Op.LOAD_CONST, idx, line)

    def compile_body(self, body):
        if isinstance(body, list):
            self.compile_block_value(body)
            self.emit(Op.RETURN)
        else:
            self.compile_expr(body)
            self.emit(Op.RETURN)
        return self.code

    def compile_block_value(self, stmts):
        if not stmts:
            self.load_const(None)
            return
        for stmt in stmts[:-1]:
            self.compile_stmt(stmt)
        self.compile_stmt_value(stmts[-1])

    def compile_stmt_value(self, node):
        if isinstance(node, ast.ExprStmt):
            self.compile_expr(node.expr)
        elif isinstance(node, ast.Return):
            self.compile_stmt(node)
        elif isinstance(node, ast.Match):
            self.compile_match_value(node)
        elif isinstance(node, ast.If):
            self.compile_if_value(node)
        else:
            self.compile_stmt(node)
            self.load_const(None)

    def compile_match_value(self, node):
        self.compile_expr(node.subject)
        self.emit(Op.STORE_NAME, "__match__")
        end_jumps = []
        for arm in node.arms:
            self.emit(Op.LOAD_NAME, "__match__")
            self.emit(Op.MATCH_VARIANT, arm.pattern)
            no_match = self.emit(Op.JUMP_IF_FALSE)
            if isinstance(arm.body, list):
                self.compile_block_value(arm.body)
            else:
                self.compile_expr(arm.body)
            end_jumps.append(self.emit(Op.JUMP))
            self.patch(no_match)
        self.load_const(None)
        for j in end_jumps:
            self.patch(j)

    def compile_if_value(self, node):
        end_jumps = []
        self.compile_expr(node.cond)
        skip = self.emit(Op.JUMP_IF_FALSE)
        self.compile_block_value(node.then)
        end_jumps.append(self.emit(Op.JUMP))
        self.patch(skip)
        for cond, body in node.elifs:
            self.compile_expr(cond)
            s = self.emit(Op.JUMP_IF_FALSE)
            self.compile_block_value(body)
            end_jumps.append(self.emit(Op.JUMP))
            self.patch(s)
        if node.orelse is not None:
            self.compile_block_value(node.orelse)
        else:
            self.load_const(None)
        for j in end_jumps:
            self.patch(j)

    def compile_block(self, stmts):
        for stmt in stmts:
            self.compile_stmt(stmt)

    def compile_stmt(self, node):
        method = getattr(self, "st_" + type(node).__name__, None)
        if method is None:
            self.compile_expr(node)
            self.emit(Op.POP)
            return
        method(node)

    def st_Let(self, node):
        self.compile_expr(node.value)
        self.store_pattern(node.pattern)

    def store_pattern(self, pattern):
        if isinstance(pattern, ast.BindPattern):
            self.emit(Op.STORE_NAME, pattern.name)
        elif isinstance(pattern, ast.WildcardPattern):
            self.emit(Op.POP)
        elif isinstance(pattern, ast.TuplePattern):
            self.emit(Op.STORE_NAME, "__tuple__")
            for i, sub in enumerate(pattern.elements):
                self.emit(Op.LOAD_NAME, "__tuple__")
                self.load_const(i)
                self.emit(Op.GET_INDEX)
                self.store_pattern(sub)
        else:
            raise CompileError(f"unsupported let pattern {type(pattern).__name__}")

    def st_Var(self, node):
        self.compile_expr(node.value)
        self.emit(Op.STORE_NAME, node.name)

    def st_Assign(self, node):
        target = node.target
        if isinstance(target, ast.Name):
            if node.op != "=":
                self.emit(Op.LOAD_NAME, target.id)
                self.compile_expr(node.value)
                self.emit(Op.BINARY, node.op[:-1])
            else:
                self.compile_expr(node.value)
            self.emit(Op.ASSIGN_NAME, target.id)
        elif isinstance(target, ast.Index):
            self.compile_expr(target.target)
            self.compile_expr(target.index)
            if node.op != "=":
                self.compile_expr(target.target)
                self.compile_expr(target.index)
                self.emit(Op.GET_INDEX)
                self.compile_expr(node.value)
                self.emit(Op.BINARY, node.op[:-1])
            else:
                self.compile_expr(node.value)
            self.emit(Op.SET_INDEX)
        elif isinstance(target, ast.Attribute):
            self.compile_expr(target.target)
            self.compile_expr(node.value)
            self.emit(Op.SET_ATTR, target.name)
        else:
            raise CompileError("invalid assignment target")

    def st_Return(self, node):
        if node.value is not None:
            self.compile_expr(node.value)
        else:
            self.load_const(None)
        self.emit(Op.RETURN)

    def st_If(self, node):
        end_jumps = []
        self.compile_expr(node.cond)
        skip = self.emit(Op.JUMP_IF_FALSE)
        self.compile_block(node.then)
        end_jumps.append(self.emit(Op.JUMP))
        self.patch(skip)
        for cond, body in node.elifs:
            self.compile_expr(cond)
            s = self.emit(Op.JUMP_IF_FALSE)
            self.compile_block(body)
            end_jumps.append(self.emit(Op.JUMP))
            self.patch(s)
        if node.orelse is not None:
            self.compile_block(node.orelse)
        for j in end_jumps:
            self.patch(j)

    def st_While(self, node):
        start = len(self.code.instrs)
        self.compile_expr(node.cond)
        exit_jump = self.emit(Op.JUMP_IF_FALSE)
        self.loop_stack.append(([], start))
        self.compile_block(node.body)
        self.emit(Op.JUMP, start)
        self.patch(exit_jump)
        breaks, _ = self.loop_stack.pop()
        for b in breaks:
            self.patch(b)

    def st_For(self, node):
        self.compile_expr(node.iter)
        self.emit(Op.ITER_NEW)
        self.emit(Op.STORE_NAME, "__iter__")
        start = len(self.code.instrs)
        self.emit(Op.LOAD_NAME, "__iter__")
        self.emit(Op.ITER_NEXT)
        exit_jump = self.emit(Op.JUMP_IF_FALSE)
        self.store_pattern(node.pattern)
        self.loop_stack.append(([], start))
        self.compile_block(node.body)
        self.emit(Op.JUMP, start)
        self.patch(exit_jump)
        breaks, _ = self.loop_stack.pop()
        for b in breaks:
            self.patch(b)

    def st_Break(self, node):
        if not self.loop_stack:
            raise CompileError("break outside loop")
        j = self.emit(Op.JUMP)
        self.loop_stack[-1][0].append(j)

    def st_Continue(self, node):
        if not self.loop_stack:
            raise CompileError("continue outside loop")
        _, start = self.loop_stack[-1]
        self.emit(Op.JUMP, start)

    def st_Match(self, node):
        self.compile_expr(node.subject)
        self.emit(Op.STORE_NAME, "__match__")
        end_jumps = []
        for arm in node.arms:
            self.emit(Op.LOAD_NAME, "__match__")
            self.emit(Op.MATCH_VARIANT, arm.pattern)
            no_match = self.emit(Op.JUMP_IF_FALSE)
            if isinstance(arm.body, list):
                self.compile_block(arm.body)
            else:
                self.compile_expr(arm.body)
                self.emit(Op.POP)
            end_jumps.append(self.emit(Op.JUMP))
            self.patch(no_match)
        for j in end_jumps:
            self.patch(j)

    def st_ExprStmt(self, node):
        self.compile_expr(node.expr)
        self.emit(Op.POP)

    def st_Defer(self, node):
        self.compile_expr(node.expr)
        self.emit(Op.POP)

    def st_With(self, node):
        self.compile_expr(node.expr)
        if node.alias:
            self.emit(Op.STORE_NAME, node.alias)
        else:
            self.emit(Op.POP)
        self.compile_block(node.body)

    def patch(self, index):
        self.code.instrs[index].arg = len(self.code.instrs)

    def compile_expr(self, node):
        method = getattr(self, "ex_" + type(node).__name__, None)
        if method is None:
            raise CompileError(f"cannot compile {type(node).__name__}")
        method(node)

    def ex_Int(self, node):
        self.load_const(node.value)

    def ex_Float(self, node):
        self.load_const(node.value)

    def ex_Bool(self, node):
        self.load_const(node.value)

    def ex_NoneLit(self, node):
        from values import NONE
        self.load_const(NONE)

    def ex_Str(self, node):
        n = 0
        for kind, value in node.parts:
            if kind == "str":
                self.load_const(value)
            else:
                self.compile_expr(value)
            n += 1
        self.emit(Op.BUILD_STRING, n)

    def ex_Name(self, node):
        self.emit(Op.LOAD_NAME, node.id)

    def ex_ListLit(self, node):
        for e in node.elements:
            self.compile_expr(e)
        self.emit(Op.BUILD_LIST, len(node.elements))

    def ex_DictLit(self, node):
        for k, v in node.pairs:
            self.compile_expr(k)
            self.compile_expr(v)
        self.emit(Op.BUILD_DICT, len(node.pairs))

    def ex_TupleLit(self, node):
        for e in node.elements:
            self.compile_expr(e)
        self.emit(Op.BUILD_TUPLE, len(node.elements))

    def ex_Lambda(self, node):
        code = FunctionCompiler("<lambda>", node.params, self.program).compile_body(node.body)
        self.emit(Op.MAKE_CLOSURE, code)

    def ex_Ternary(self, node):
        self.compile_expr(node.cond)
        skip = self.emit(Op.JUMP_IF_FALSE)
        self.compile_expr(node.then)
        end = self.emit(Op.JUMP)
        self.patch(skip)
        self.compile_expr(node.orelse)
        self.patch(end)

    def ex_BinOp(self, node):
        if node.op == "and":
            self.compile_expr(node.left)
            self.emit(Op.DUP)
            skip = self.emit(Op.JUMP_IF_FALSE)
            self.emit(Op.POP)
            self.compile_expr(node.right)
            self.patch(skip)
            return
        if node.op == "or":
            self.compile_expr(node.left)
            self.emit(Op.DUP)
            skip = self.emit(Op.JUMP_IF_TRUE)
            self.emit(Op.POP)
            self.compile_expr(node.right)
            self.patch(skip)
            return
        self.compile_expr(node.left)
        self.compile_expr(node.right)
        self.emit(Op.BINARY, node.op)

    def ex_UnaryOp(self, node):
        self.compile_expr(node.operand)
        self.emit(Op.UNARY, node.op)

    def ex_Call(self, node):
        self.compile_expr(node.func)
        for arg in node.args:
            self.compile_expr(arg.value)
        self.emit(Op.CALL, len(node.args))

    def ex_Index(self, node):
        self.compile_expr(node.target)
        self.compile_expr(node.index)
        self.emit(Op.GET_INDEX)

    def ex_Attribute(self, node):
        self.compile_expr(node.target)
        self.emit(Op.GET_ATTR, node.name)

    def ex_Try(self, node):
        self.compile_expr(node.expr)
        self.emit(Op.TRY_UNWRAP)


class Program:
    def __init__(self):
        self.functions = {}
        self.types = {}
        self.enums = {}
        self.consts = []
        self.imports = []


def compile_module(module):
    program = Program()
    for decl in module.body:
        if isinstance(decl, ast.TypeDecl):
            program.types[decl.name] = [f.name for f in decl.fields]
        elif isinstance(decl, ast.EnumDecl):
            for v in decl.variants:
                program.enums[v.name] = (decl.name, len(v.types))
        elif isinstance(decl, ast.Import):
            program.imports.append(decl)
    for decl in module.body:
        if isinstance(decl, ast.Function):
            fc = FunctionCompiler(decl.name, decl.params, program)
            program.functions[decl.name] = fc.compile_body(decl.body)
        elif isinstance(decl, ast.Const):
            program.consts.append(decl)
    return program
