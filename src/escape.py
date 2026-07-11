import ast_nodes as ast


ALLOC_NODES = (ast.ListLit, ast.DictLit, ast.TupleLit)


class FunctionEscape:
    def __init__(self, name):
        self.name = name
        self.allocs = {}
        self.escaping = set()

    def decisions(self):
        result = []
        for var in self.allocs:
            where = "heap" if var in self.escaping else "stack"
            result.append((var, where))
        return result


class EscapeAnalyzer:
    def __init__(self, module):
        self.module = module
        self.user_functions = set()
        self.struct_types = set()
        for decl in module.body:
            if isinstance(decl, ast.Function):
                self.user_functions.add(decl.name)
            elif isinstance(decl, ast.TypeDecl):
                self.struct_types.add(decl.name)

    def analyze(self):
        results = {}
        for decl in self.module.body:
            if isinstance(decl, ast.Function):
                results[decl.name] = self.analyze_function(decl)
        return results

    def analyze_function(self, decl):
        fe = FunctionEscape(decl.name)
        self.collect_allocs(decl.body, fe)
        self.mark_escapes(decl.body, fe)
        return fe

    def is_alloc(self, node):
        if isinstance(node, ALLOC_NODES):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return node.func.id in self.struct_types
        return False

    def collect_allocs(self, stmts, fe):
        for stmt in stmts:
            if isinstance(stmt, ast.Let) and isinstance(stmt.pattern, ast.BindPattern):
                if self.is_alloc(stmt.value):
                    fe.allocs[stmt.pattern.name] = stmt.value
            elif isinstance(stmt, ast.Var):
                if self.is_alloc(stmt.value):
                    fe.allocs[stmt.name] = stmt.value
            for child in self.child_blocks(stmt):
                self.collect_allocs(child, fe)

    def child_blocks(self, stmt):
        blocks = []
        if isinstance(stmt, ast.If):
            blocks.append(stmt.then)
            for _, b in stmt.elifs:
                blocks.append(b)
            if stmt.orelse:
                blocks.append(stmt.orelse)
        elif isinstance(stmt, (ast.While, ast.For, ast.With)):
            blocks.append(stmt.body)
        elif isinstance(stmt, ast.Match):
            for arm in stmt.arms:
                if isinstance(arm.body, list):
                    blocks.append(arm.body)
        return blocks

    def mark_escapes(self, stmts, fe):
        for stmt in stmts:
            self.mark_stmt(stmt, fe)

    def mark_stmt(self, stmt, fe):
        if isinstance(stmt, ast.Return):
            if stmt.value is not None:
                for name in self.ref_names(stmt.value):
                    fe.escaping.add(name)
                self.mark_escaping_lambdas(stmt.value, fe)
        elif isinstance(stmt, ast.Assign):
            if isinstance(stmt.target, (ast.Attribute, ast.Index)):
                for name in self.ref_names(stmt.value):
                    fe.escaping.add(name)
            elif isinstance(stmt.target, ast.Name) and stmt.target.id not in fe.allocs:
                for name in self.ref_names(stmt.value):
                    fe.escaping.add(name)
        elif isinstance(stmt, (ast.ExprStmt, ast.Let, ast.Var, ast.Defer)):
            expr = getattr(stmt, "expr", None)
            if expr is None:
                expr = getattr(stmt, "value", None)
            if expr is not None:
                self.mark_calls(expr, fe)
        for child in self.child_blocks(stmt):
            self.mark_escapes(child, fe)

    def ref_names(self, node):
        found = set()
        self._ref_names(node, found)
        return found

    def _ref_names(self, node, found):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, (ast.ListLit, ast.TupleLit)):
            for e in node.elements:
                self._ref_names(e, found)
        elif isinstance(node, ast.DictLit):
            for _, v in node.pairs:
                self._ref_names(v, found)
        elif isinstance(node, ast.Ternary):
            self._ref_names(node.then, found)
            self._ref_names(node.orelse, found)
        elif isinstance(node, ast.Try):
            self._ref_names(node.expr, found)
        elif isinstance(node, (ast.Attribute, ast.Index)):
            self._ref_names(node.target, found)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.struct_types:
                for a in node.args:
                    self._ref_names(a.value, found)

    def mark_calls(self, node, fe):
        if isinstance(node, ast.Call):
            is_user = isinstance(node.func, ast.Name) and node.func.id in self.user_functions
            for arg in node.args:
                if is_user and isinstance(arg.value, ast.Name):
                    fe.escaping.add(arg.value.id)
                self.mark_calls(arg.value, fe)
            self.mark_calls(node.func, fe)
        else:
            for sub in self.subexprs(node):
                self.mark_calls(sub, fe)

    def mark_escaping_lambdas(self, node, fe):
        if isinstance(node, ast.Lambda):
            body = node.body if isinstance(node.body, list) else [ast.Return(value=node.body)]
            for name in self.free_names(body):
                fe.escaping.add(name)
        for sub in self.subexprs(node):
            self.mark_escaping_lambdas(sub, fe)

    def names_in(self, node):
        found = set()
        self._collect_names(node, found)
        return found

    def _collect_names(self, node, found):
        if isinstance(node, ast.Name):
            found.add(node.id)
            return
        for sub in self.subexprs(node):
            self._collect_names(sub, found)

    def free_names(self, stmts):
        found = set()
        for stmt in stmts:
            expr = getattr(stmt, "value", None) or getattr(stmt, "expr", None)
            if expr is not None:
                self._collect_names(expr, found)
        return found

    def subexprs(self, node):
        result = []
        if isinstance(node, ast.BinOp):
            result = [node.left, node.right]
        elif isinstance(node, ast.UnaryOp):
            result = [node.operand]
        elif isinstance(node, ast.Call):
            result = [node.func] + [a.value for a in node.args]
        elif isinstance(node, ast.Index):
            result = [node.target, node.index]
        elif isinstance(node, ast.Attribute):
            result = [node.target]
        elif isinstance(node, ast.ListLit):
            result = list(node.elements)
        elif isinstance(node, ast.TupleLit):
            result = list(node.elements)
        elif isinstance(node, ast.DictLit):
            for k, v in node.pairs:
                result.append(k)
                result.append(v)
        elif isinstance(node, ast.Ternary):
            result = [node.cond, node.then, node.orelse]
        elif isinstance(node, ast.Try):
            result = [node.expr]
        elif isinstance(node, ast.Lambda):
            if not isinstance(node.body, list):
                result = [node.body]
        elif isinstance(node, ast.Str):
            result = [v for k, v in node.parts if k == "expr"]
        return result


def analyze(module):
    return EscapeAnalyzer(module).analyze()
