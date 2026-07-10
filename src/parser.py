from lexer import TokenType as T, tokenize
import ast_nodes as ast


class ParseError(Exception):
    def __init__(self, message, token):
        line = token.line if token else 0
        col = token.col if token else 0
        super().__init__(f"{line}:{col}: {message}")
        self.token = token


ASSIGN_OPS = {
    T.EQ: "=",
    T.PLUS_EQ: "+=",
    T.MINUS_EQ: "-=",
    T.STAR_EQ: "*=",
    T.SLASH_EQ: "/=",
    T.PERCENT_EQ: "%=",
}

COMPARE_OPS = {
    T.EQ_EQ: "==",
    T.BANG_EQ: "!=",
    T.LT: "<",
    T.LT_EQ: "<=",
    T.GT: ">",
    T.GT_EQ: ">=",
}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    @property
    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=0):
        i = self.pos + offset
        if i < len(self.tokens):
            return self.tokens[i]
        return self.tokens[-1]

    def error(self, message):
        raise ParseError(message, self.current)

    def at(self, type, value=None):
        tok = self.current
        if tok.type != type:
            return False
        if value is not None and tok.value != value:
            return False
        return True

    def at_keyword(self, *words):
        return self.current.type == T.KEYWORD and self.current.value in words

    def advance(self):
        tok = self.current
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, type, value=None):
        if not self.at(type, value):
            want = value if value is not None else type.name
            self.error(f"expected {want}, got {self.current.value!r}")
        return self.advance()

    def expect_keyword(self, word):
        if not self.at_keyword(word):
            self.error(f"expected '{word}', got {self.current.value!r}")
        return self.advance()

    def skip_newlines(self):
        while self.at(T.NEWLINE):
            self.advance()

    def parse(self):
        body = []
        self.skip_newlines()
        while not self.at(T.EOF):
            body.append(self.parse_top_level())
            self.skip_newlines()
        return ast.Module(body=body)

    def parse_top_level(self):
        if self.at_keyword("import", "from"):
            return self.parse_import()
        if self.at_keyword("const"):
            return self.parse_const()
        if self.at_keyword("impl"):
            return self.parse_impl()
        is_pub = False
        if self.at_keyword("pub"):
            self.advance()
            is_pub = True
        if self.at_keyword("fn"):
            return self.parse_function(is_pub)
        if self.at_keyword("type"):
            return self.parse_type_decl(is_pub)
        if self.at_keyword("enum"):
            return self.parse_enum(is_pub)
        if self.at_keyword("trait"):
            return self.parse_trait(is_pub)
        self.error(f"unexpected token {self.current.value!r} at top level")

    def parse_import(self):
        if self.at_keyword("import"):
            self.advance()
            path = self.parse_import_path()
            alias = None
            if self.at_keyword("as"):
                self.advance()
                alias = self.expect(T.IDENT).value
            self.expect(T.NEWLINE)
            return ast.Import(path=path, alias=alias, names=None)
        self.expect_keyword("from")
        path = self.parse_import_path()
        self.expect_keyword("import")
        names = [self.expect(T.IDENT).value]
        while self.at(T.COMMA):
            self.advance()
            names.append(self.expect(T.IDENT).value)
        self.expect(T.NEWLINE)
        return ast.Import(path=path, alias=None, names=names)

    def parse_import_path(self):
        parts = [self.expect(T.IDENT).value]
        while self.at(T.DOT):
            self.advance()
            parts.append(self.expect(T.IDENT).value)
        return parts

    def parse_const(self):
        self.expect_keyword("const")
        name = self.expect(T.IDENT).value
        type = None
        if self.at(T.COLON):
            self.advance()
            type = self.parse_type()
        self.expect(T.EQ)
        value = self.parse_expr()
        self.expect(T.NEWLINE)
        return ast.Const(name=name, type=type, value=value)

    def parse_generics(self):
        if not self.at(T.LBRACKET):
            return []
        self.advance()
        params = [self.parse_generic_param()]
        while self.at(T.COMMA):
            self.advance()
            params.append(self.parse_generic_param())
        self.expect(T.RBRACKET)
        return params

    def parse_generic_param(self):
        name = self.expect(T.IDENT).value
        bounds = []
        if self.at(T.COLON):
            self.advance()
            bounds.append(self.parse_type())
            while self.at(T.PLUS):
                self.advance()
                bounds.append(self.parse_type())
        return ast.GenericParam(name=name, bounds=bounds)

    def parse_function(self, is_pub):
        self.expect_keyword("fn")
        name = self.expect(T.IDENT).value
        generics = self.parse_generics()
        self.expect(T.LPAREN)
        params = self.parse_params()
        self.expect(T.RPAREN)
        return_type = None
        if self.at(T.ARROW):
            self.advance()
            return_type = self.parse_type()
        body = self.parse_block()
        return ast.Function(
            name=name, generics=generics, params=params,
            return_type=return_type, body=body, is_pub=is_pub,
        )

    def parse_params(self):
        params = []
        if self.at(T.RPAREN):
            return params
        params.append(self.parse_param())
        while self.at(T.COMMA):
            self.advance()
            params.append(self.parse_param())
        return params

    def parse_param(self):
        name = self.expect(T.IDENT).value
        if name == "self" and not self.at(T.COLON):
            return ast.Param(name=name, type=None, default=None)
        self.expect(T.COLON)
        type = self.parse_type()
        default = None
        if self.at(T.EQ):
            self.advance()
            default = self.parse_expr()
        return ast.Param(name=name, type=type, default=default)

    def parse_type_decl(self, is_pub):
        self.expect_keyword("type")
        name = self.expect(T.IDENT).value
        generics = self.parse_generics()
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        fields = []
        while not self.at(T.DEDENT):
            fname = self.expect(T.IDENT).value
            self.expect(T.COLON)
            ftype = self.parse_type()
            self.expect(T.NEWLINE)
            fields.append(ast.Field(name=fname, type=ftype))
        self.expect(T.DEDENT)
        derives = self.parse_derive()
        return ast.TypeDecl(
            name=name, generics=generics, fields=fields,
            derives=derives, is_pub=is_pub,
        )

    def parse_enum(self, is_pub):
        self.expect_keyword("enum")
        name = self.expect(T.IDENT).value
        generics = self.parse_generics()
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        variants = []
        while not self.at(T.DEDENT):
            vname = self.expect(T.IDENT).value
            types = []
            if self.at(T.LPAREN):
                self.advance()
                types.append(self.parse_type())
                while self.at(T.COMMA):
                    self.advance()
                    types.append(self.parse_type())
                self.expect(T.RPAREN)
            self.expect(T.NEWLINE)
            variants.append(ast.Variant(name=vname, types=types))
        self.expect(T.DEDENT)
        derives = self.parse_derive()
        return ast.EnumDecl(
            name=name, generics=generics, variants=variants,
            derives=derives, is_pub=is_pub,
        )

    def parse_derive(self):
        if not self.at_keyword("derive"):
            return []
        self.advance()
        self.expect(T.LPAREN)
        names = [self.expect(T.IDENT).value]
        while self.at(T.COMMA):
            self.advance()
            names.append(self.expect(T.IDENT).value)
        self.expect(T.RPAREN)
        self.expect(T.NEWLINE)
        return names

    def parse_trait(self, is_pub):
        self.expect_keyword("trait")
        name = self.expect(T.IDENT).value
        generics = self.parse_generics()
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        methods = []
        while not self.at(T.DEDENT):
            self.expect_keyword("fn")
            mname = self.expect(T.IDENT).value
            self.expect(T.LPAREN)
            params = self.parse_params()
            self.expect(T.RPAREN)
            rtype = None
            if self.at(T.ARROW):
                self.advance()
                rtype = self.parse_type()
            self.expect(T.NEWLINE)
            methods.append(ast.TraitMethod(name=mname, params=params, return_type=rtype))
        self.expect(T.DEDENT)
        return ast.TraitDecl(name=name, generics=generics, methods=methods, is_pub=is_pub)

    def parse_impl(self):
        self.expect_keyword("impl")
        generics = self.parse_generics()
        first = self.parse_type()
        trait = None
        type = first
        if self.at_keyword("for"):
            self.advance()
            trait = first
            type = self.parse_type()
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        methods = []
        while not self.at(T.DEDENT):
            is_pub = False
            if self.at_keyword("pub"):
                self.advance()
                is_pub = True
            methods.append(self.parse_function(is_pub))
            self.skip_newlines()
        self.expect(T.DEDENT)
        return ast.ImplDecl(generics=generics, type=type, trait=trait, methods=methods)

    def parse_type(self):
        type = self.parse_type_atom()
        while self.at(T.QUESTION):
            self.advance()
            type = ast.OptionalType(inner=type)
        return type

    def parse_type_atom(self):
        if self.at_keyword("dyn"):
            self.advance()
            return ast.DynType()
        if self.at(T.LBRACKET):
            self.advance()
            element = self.parse_type()
            self.expect(T.RBRACKET)
            return ast.ListType(element=element)
        if self.at(T.LBRACE):
            self.advance()
            key = self.parse_type()
            self.expect(T.COLON)
            value = self.parse_type()
            self.expect(T.RBRACE)
            return ast.DictType(key=key, value=value)
        if self.at(T.LPAREN):
            self.advance()
            elements = []
            if not self.at(T.RPAREN):
                elements.append(self.parse_type())
                while self.at(T.COMMA):
                    self.advance()
                    elements.append(self.parse_type())
            self.expect(T.RPAREN)
            return ast.TupleType(elements=elements)
        if self.at_keyword("fn"):
            self.advance()
            self.expect(T.LPAREN)
            params = []
            if not self.at(T.RPAREN):
                params.append(self.parse_type())
                while self.at(T.COMMA):
                    self.advance()
                    params.append(self.parse_type())
            self.expect(T.RPAREN)
            self.expect(T.ARROW)
            rtype = self.parse_type()
            return ast.FnType(params=params, return_type=rtype)
        name = self.expect(T.IDENT).value
        args = []
        if self.at(T.LBRACKET):
            self.advance()
            args.append(self.parse_type())
            while self.at(T.COMMA):
                self.advance()
                args.append(self.parse_type())
            self.expect(T.RBRACKET)
        return ast.NamedType(name=name, args=args)

    def parse_block(self):
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        body = []
        while not self.at(T.DEDENT):
            body.append(self.parse_statement())
            self.skip_newlines()
        self.expect(T.DEDENT)
        return body

    def parse_statement(self):
        if self.at_keyword("let"):
            return self.parse_let()
        if self.at_keyword("var"):
            return self.parse_var()
        if self.at_keyword("return"):
            return self.parse_return()
        if self.at_keyword("break"):
            self.advance()
            self.expect(T.NEWLINE)
            return ast.Break()
        if self.at_keyword("continue"):
            self.advance()
            self.expect(T.NEWLINE)
            return ast.Continue()
        if self.at_keyword("defer"):
            self.advance()
            expr = self.parse_expr()
            self.expect(T.NEWLINE)
            return ast.Defer(expr=expr)
        if self.at_keyword("if"):
            return self.parse_if()
        if self.at_keyword("while"):
            return self.parse_while()
        if self.at_keyword("for"):
            return self.parse_for()
        if self.at_keyword("with"):
            return self.parse_with()
        if self.at_keyword("match"):
            return self.parse_match()
        return self.parse_expr_or_assign()

    def parse_let(self):
        self.expect_keyword("let")
        pattern = self.parse_pattern()
        type = None
        if self.at(T.COLON):
            self.advance()
            type = self.parse_type()
        self.expect(T.EQ)
        value = self.parse_expr()
        self.expect(T.NEWLINE)
        return ast.Let(pattern=pattern, type=type, value=value)

    def parse_var(self):
        self.expect_keyword("var")
        name = self.expect(T.IDENT).value
        type = None
        if self.at(T.COLON):
            self.advance()
            type = self.parse_type()
        self.expect(T.EQ)
        value = self.parse_expr()
        self.expect(T.NEWLINE)
        return ast.Var(name=name, type=type, value=value)

    def parse_return(self):
        self.expect_keyword("return")
        value = None
        if not self.at(T.NEWLINE):
            value = self.parse_expr()
        self.expect(T.NEWLINE)
        return ast.Return(value=value)

    def parse_if(self):
        self.expect_keyword("if")
        cond = self.parse_expr()
        then = self.parse_block()
        elifs = []
        while self.at_keyword("elif"):
            self.advance()
            econd = self.parse_expr()
            ebody = self.parse_block()
            elifs.append((econd, ebody))
        orelse = None
        if self.at_keyword("else"):
            self.advance()
            orelse = self.parse_block()
        return ast.If(cond=cond, then=then, elifs=elifs, orelse=orelse)

    def parse_while(self):
        self.expect_keyword("while")
        cond = self.parse_expr()
        body = self.parse_block()
        return ast.While(cond=cond, body=body)

    def parse_for(self):
        self.expect_keyword("for")
        pattern = self.parse_pattern()
        self.expect_keyword("in")
        iter = self.parse_expr()
        body = self.parse_block()
        return ast.For(pattern=pattern, iter=iter, body=body)

    def parse_with(self):
        self.expect_keyword("with")
        expr = self.parse_expr()
        alias = None
        if self.at_keyword("as"):
            self.advance()
            alias = self.expect(T.IDENT).value
        body = self.parse_block()
        return ast.With(expr=expr, alias=alias, body=body)

    def parse_match(self):
        self.expect_keyword("match")
        subject = self.parse_expr()
        self.expect(T.COLON)
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        arms = []
        while not self.at(T.DEDENT):
            pattern = self.parse_pattern()
            guard = None
            if self.at_keyword("if"):
                self.advance()
                guard = self.parse_expr()
            self.expect(T.FAT_ARROW)
            if self.at(T.NEWLINE):
                body = self.parse_block_after_arrow()
            else:
                body = self.parse_expr()
                self.expect(T.NEWLINE)
            arms.append(ast.MatchArm(pattern=pattern, guard=guard, body=body))
            self.skip_newlines()
        self.expect(T.DEDENT)
        return ast.Match(subject=subject, arms=arms)

    def parse_block_after_arrow(self):
        self.expect(T.NEWLINE)
        self.expect(T.INDENT)
        body = []
        while not self.at(T.DEDENT):
            body.append(self.parse_statement())
            self.skip_newlines()
        self.expect(T.DEDENT)
        return body

    def parse_pattern(self):
        if self.at(T.IDENT, "_"):
            self.advance()
            return ast.WildcardPattern()
        if self.at(T.INT) or self.at(T.FLOAT) or self.at(T.STRING):
            return ast.LiteralPattern(value=self.parse_primary())
        if self.at_keyword("true", "false", "none"):
            return ast.LiteralPattern(value=self.parse_primary())
        if self.at(T.LPAREN):
            self.advance()
            elements = [self.parse_pattern()]
            while self.at(T.COMMA):
                self.advance()
                elements.append(self.parse_pattern())
            self.expect(T.RPAREN)
            return ast.TuplePattern(elements=elements)
        name = self.expect(T.IDENT).value
        if self.at(T.LPAREN):
            self.advance()
            args = [self.parse_pattern()]
            while self.at(T.COMMA):
                self.advance()
                args.append(self.parse_pattern())
            self.expect(T.RPAREN)
            return ast.VariantPattern(name=name, args=args)
        if name and name[0].isupper():
            return ast.VariantPattern(name=name, args=[])
        return ast.BindPattern(name=name)

    def parse_expr_or_assign(self):
        expr = self.parse_expr()
        if self.current.type in ASSIGN_OPS and self._is_lvalue(expr):
            op = ASSIGN_OPS[self.current.type]
            self.advance()
            value = self.parse_expr()
            self.expect(T.NEWLINE)
            return ast.Assign(target=expr, op=op, value=value)
        self.expect(T.NEWLINE)
        return ast.ExprStmt(expr=expr)

    def _is_lvalue(self, expr):
        return isinstance(expr, (ast.Name, ast.Index, ast.Attribute))

    def parse_expr(self):
        if self._looks_like_lambda():
            return self.parse_lambda()
        return self.parse_ternary()

    def _looks_like_lambda(self):
        if self.at(T.IDENT) and self.peek(1).type == T.FAT_ARROW:
            return True
        if self.at(T.LPAREN):
            depth = 0
            i = self.pos
            while i < len(self.tokens):
                tt = self.tokens[i].type
                if tt == T.LPAREN:
                    depth += 1
                elif tt == T.RPAREN:
                    depth -= 1
                    if depth == 0:
                        return self.tokens[i + 1].type == T.FAT_ARROW
                elif tt in (T.NEWLINE, T.EOF):
                    return False
                i += 1
        return False

    def parse_lambda(self):
        if self.at(T.IDENT):
            params = [ast.Param(name=self.advance().value, type=None, default=None)]
        else:
            self.expect(T.LPAREN)
            params = self.parse_params()
            self.expect(T.RPAREN)
        self.expect(T.FAT_ARROW)
        if self.at(T.LBRACE):
            body = self.parse_brace_block()
        else:
            body = self.parse_expr()
        return ast.Lambda(params=params, body=body)

    def parse_brace_block(self):
        self.expect(T.LBRACE)
        self.skip_layout()
        body = []
        while not self.at(T.RBRACE):
            body.append(self.parse_statement())
            self.skip_layout()
        self.expect(T.RBRACE)
        return body

    def skip_layout(self):
        while self.current.type in (T.NEWLINE, T.INDENT, T.DEDENT):
            self.advance()

    def parse_ternary(self):
        expr = self.parse_or()
        if self.at_keyword("if"):
            self.advance()
            cond = self.parse_or()
            self.expect_keyword("else")
            orelse = self.parse_expr()
            return ast.Ternary(then=expr, cond=cond, orelse=orelse)
        return expr

    def parse_or(self):
        left = self.parse_and()
        while self.at_keyword("or"):
            self.advance()
            right = self.parse_and()
            left = ast.BinOp(op="or", left=left, right=right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.at_keyword("and"):
            self.advance()
            right = self.parse_not()
            left = ast.BinOp(op="and", left=left, right=right)
        return left

    def parse_not(self):
        if self.at_keyword("not"):
            self.advance()
            operand = self.parse_not()
            return ast.UnaryOp(op="not", operand=operand)
        return self.parse_compare()

    def parse_compare(self):
        left = self.parse_add()
        while self.current.type in COMPARE_OPS:
            op = COMPARE_OPS[self.current.type]
            self.advance()
            right = self.parse_add()
            left = ast.BinOp(op=op, left=left, right=right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.current.type in (T.PLUS, T.MINUS):
            op = self.advance().value
            right = self.parse_mul()
            left = ast.BinOp(op=op, left=left, right=right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.current.type in (T.STAR, T.SLASH, T.PERCENT):
            op = self.advance().value
            right = self.parse_unary()
            left = ast.BinOp(op=op, left=left, right=right)
        return left

    def parse_unary(self):
        if self.at(T.MINUS):
            self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(op="-", operand=operand)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            if self.at(T.LPAREN):
                expr = self.parse_call(expr)
            elif self.at(T.LBRACKET):
                self.advance()
                index = self.parse_expr()
                self.expect(T.RBRACKET)
                expr = ast.Index(target=expr, index=index)
            elif self.at(T.DOT):
                self.advance()
                name = self.expect(T.IDENT).value
                expr = ast.Attribute(target=expr, name=name)
            elif self.at(T.QUESTION):
                self.advance()
                expr = ast.Try(expr=expr)
            else:
                break
        return expr

    def parse_call(self, func):
        self.expect(T.LPAREN)
        args = []
        if not self.at(T.RPAREN):
            args.append(self.parse_argument())
            while self.at(T.COMMA):
                self.advance()
                args.append(self.parse_argument())
        self.expect(T.RPAREN)
        return ast.Call(func=func, args=args)

    def parse_argument(self):
        if self.at(T.IDENT) and self.peek(1).type == T.EQ:
            name = self.advance().value
            self.advance()
            value = self.parse_expr()
            return ast.Argument(name=name, value=value)
        return ast.Argument(name=None, value=self.parse_expr())

    def parse_primary(self):
        tok = self.current
        if tok.type == T.INT:
            self.advance()
            return ast.Int(value=tok.value)
        if tok.type == T.FLOAT:
            self.advance()
            return ast.Float(value=tok.value)
        if tok.type == T.STRING:
            self.advance()
            return self.build_string(tok.value)
        if self.at_keyword("true"):
            self.advance()
            return ast.Bool(value=True)
        if self.at_keyword("false"):
            self.advance()
            return ast.Bool(value=False)
        if self.at_keyword("none"):
            self.advance()
            return ast.NoneLit()
        if tok.type == T.IDENT:
            self.advance()
            return ast.Name(id=tok.value)
        if tok.type == T.LBRACKET:
            return self.parse_list()
        if tok.type == T.LBRACE:
            return self.parse_dict()
        if tok.type == T.LPAREN:
            return self.parse_paren()
        self.error(f"unexpected token {tok.value!r}")

    def build_string(self, parts):
        out = []
        for kind, value in parts:
            if kind == "str":
                out.append(("str", value))
            else:
                sub = Parser(tokenize(value)).parse_expr_string()
                out.append(("expr", sub))
        return ast.Str(parts=out)

    def parse_expr_string(self):
        expr = self.parse_expr()
        return expr

    def parse_list(self):
        self.expect(T.LBRACKET)
        elements = []
        if not self.at(T.RBRACKET):
            elements.append(self.parse_expr())
            while self.at(T.COMMA):
                self.advance()
                if self.at(T.RBRACKET):
                    break
                elements.append(self.parse_expr())
        self.expect(T.RBRACKET)
        return ast.ListLit(elements=elements)

    def parse_dict(self):
        self.expect(T.LBRACE)
        pairs = []
        if not self.at(T.RBRACE):
            pairs.append(self.parse_pair())
            while self.at(T.COMMA):
                self.advance()
                if self.at(T.RBRACE):
                    break
                pairs.append(self.parse_pair())
        self.expect(T.RBRACE)
        return ast.DictLit(pairs=pairs)

    def parse_pair(self):
        key = self.parse_expr()
        self.expect(T.COLON)
        value = self.parse_expr()
        return (key, value)

    def parse_paren(self):
        self.expect(T.LPAREN)
        first = self.parse_expr()
        if self.at(T.COMMA):
            elements = [first]
            while self.at(T.COMMA):
                self.advance()
                if self.at(T.RPAREN):
                    break
                elements.append(self.parse_expr())
            self.expect(T.RPAREN)
            return ast.TupleLit(elements=elements)
        self.expect(T.RPAREN)
        return first


def parse(source):
    tokens = tokenize(source)
    return Parser(tokens).parse()
