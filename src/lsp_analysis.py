import lexer
from lexer import tokenize, LexError, TokenType as T
from parser import parse, ParseError
from checker import check
from builtins_mod import BUILTINS
import stdlib


SYMBOL_KIND = {
    "fn": 12,       # Function
    "type": 23,     # Struct
    "enum": 10,     # Enum
    "trait": 11,    # Interface
    "const": 14,    # Constant
    "extern": 12,   # Function
}

COMPLETION_KIND = {
    "keyword": 14,
    "function": 3,
    "module": 9,
    "variable": 6,
    "type": 7,
}

DEF_KEYWORDS = ("fn", "type", "enum", "trait", "const", "var")


def _tok_text(tok):
    if tok.type in (T.IDENT, T.KEYWORD):
        return tok.value
    if tok.type in (T.INT, T.FLOAT):
        return str(tok.value)
    return ""


def _tok_len(tok):
    text = _tok_text(tok)
    return len(text) if text else 1


class Analyzer:
    def __init__(self, text):
        self.text = text
        self.tokens = []
        self.tree = None
        self.lex_error = None
        self.parse_error = None
        self._analyze()

    def _analyze(self):
        try:
            self.tokens = tokenize(self.text)
        except LexError as e:
            self.lex_error = e
            return
        try:
            self.tree = parse(self.text)
        except (LexError, ParseError) as e:
            self.parse_error = e

    def diagnostics(self):
        out = []
        if self.lex_error is not None:
            out.append(self._diag(self.lex_error.line, self.lex_error.col,
                                  1, str(self.lex_error).split(": ", 1)[-1]))
            return out
        if self.parse_error is not None:
            e = self.parse_error
            line = getattr(getattr(e, "token", None), "line", 0) or 0
            col = getattr(getattr(e, "token", None), "col", 0) or 1
            msg = str(e).split(": ", 1)[-1] if ": " in str(e) else str(e)
            out.append(self._diag(line, col, 1, msg))
            return out
        if self.tree is not None:
            for err in check(self.tree):
                line = getattr(err, "line", 0) or 1
                out.append(self._diag(line, 1, 1, str(err).split(": ", 1)[-1]))
        return out

    def _diag(self, line, col, severity, message):
        line0 = max(0, line - 1)
        col0 = max(0, col - 1)
        return {
            "range": {
                "start": {"line": line0, "character": col0},
                "end": {"line": line0, "character": col0 + 1},
            },
            "severity": severity,
            "source": "ulang",
            "message": message,
        }

    def definitions(self):
        defs = {}
        toks = self.tokens
        for i, t in enumerate(toks):
            if t.type == T.KEYWORD and t.value in DEF_KEYWORDS and i + 1 < len(toks):
                nxt = toks[i + 1]
                if nxt.type == T.IDENT and nxt.value not in defs:
                    defs[nxt.value] = (nxt.line, nxt.col)
            elif t.type == T.KEYWORD and t.value == "let" and i + 1 < len(toks):
                nxt = toks[i + 1]
                if nxt.type == T.IDENT and nxt.value not in defs:
                    defs[nxt.value] = (nxt.line, nxt.col)
            elif t.type == T.KEYWORD and t.value == "fn":
                self._scan_params(toks, i, defs)
        return defs

    def _scan_params(self, toks, i, defs):
        j = i + 1
        while j < len(toks) and toks[j].type != T.LPAREN:
            if toks[j].type == T.NEWLINE:
                return
            j += 1
        depth = 0
        while j < len(toks):
            tj = toks[j]
            if tj.type == T.LPAREN:
                depth += 1
            elif tj.type == T.RPAREN:
                depth -= 1
                if depth == 0:
                    return
            elif (tj.type == T.IDENT and depth == 1 and j + 1 < len(toks)
                  and toks[j + 1].type == T.COLON):
                if tj.value not in defs:
                    defs[tj.value] = (tj.line, tj.col)
            j += 1

    def symbols(self):
        out = []
        toks = self.tokens
        for i, t in enumerate(toks):
            if (t.type == T.KEYWORD and t.value in SYMBOL_KIND and t.col == 1
                    and i + 1 < len(toks) and toks[i + 1].type == T.IDENT):
                name_tok = toks[i + 1]
                out.append({
                    "name": name_tok.value,
                    "kind": SYMBOL_KIND[t.value],
                    "range": self._range(name_tok),
                    "selectionRange": self._range(name_tok),
                })
            elif (t.type == T.KEYWORD and t.value == "pub" and t.col == 1
                  and i + 2 < len(toks) and toks[i + 1].type == T.KEYWORD
                  and toks[i + 1].value in SYMBOL_KIND and toks[i + 2].type == T.IDENT):
                name_tok = toks[i + 2]
                out.append({
                    "name": name_tok.value,
                    "kind": SYMBOL_KIND[toks[i + 1].value],
                    "range": self._range(name_tok),
                    "selectionRange": self._range(name_tok),
                })
        return out

    def _range(self, tok):
        line0 = tok.line - 1
        col0 = tok.col - 1
        return {
            "start": {"line": line0, "character": col0},
            "end": {"line": line0, "character": col0 + _tok_len(tok)},
        }

    def token_at(self, line0, char0):
        line1 = line0 + 1
        col1 = char0 + 1
        for tok in self.tokens:
            if tok.line != line1:
                continue
            start = tok.col
            end = tok.col + _tok_len(tok)
            if start <= col1 < end:
                return tok
        return None

    def hover(self, line0, char0):
        tok = self.token_at(line0, char0)
        if tok is None:
            return None
        name = _tok_text(tok)
        if not name:
            return None
        info = self._describe(tok, name)
        if info is None:
            return None
        return {"contents": {"kind": "markdown", "value": info}}

    def _describe(self, tok, name):
        if tok.type == T.KEYWORD:
            return f"**keyword** `{name}`"
        defs = self.definitions()
        if name in defs:
            kind = self._def_kind(name)
            return f"**{kind}** `{name}`"
        if name in BUILTINS:
            return f"**builtin** `{name}`"
        if name in stdlib.MODULES:
            members = ", ".join(sorted(stdlib.MODULES[name].members))
            return f"**module** `{name}`\n\nMembers: {members}"
        return None

    def _def_kind(self, name):
        for i, t in enumerate(self.tokens):
            if t.type == T.KEYWORD and t.value in DEF_KEYWORDS and i + 1 < len(self.tokens):
                if self.tokens[i + 1].value == name:
                    return {"fn": "function", "type": "type", "enum": "enum",
                            "trait": "trait", "const": "constant", "var": "variable"}[t.value]
        return "binding"

    def definition(self, line0, char0):
        tok = self.token_at(line0, char0)
        if tok is None or tok.type != T.IDENT:
            return None
        defs = self.definitions()
        if tok.value not in defs:
            return None
        line, col = defs[tok.value]
        return {
            "line": line - 1,
            "character": col - 1,
            "length": len(tok.value),
        }

    def completions(self):
        items = []
        for kw in sorted(lexer.KEYWORDS):
            items.append({"label": kw, "kind": COMPLETION_KIND["keyword"]})
        for name in sorted(BUILTINS):
            items.append({"label": name, "kind": COMPLETION_KIND["function"]})
        for name in sorted(stdlib.MODULES):
            items.append({"label": name, "kind": COMPLETION_KIND["module"]})
        for name in sorted(self.definitions()):
            items.append({"label": name, "kind": COMPLETION_KIND["variable"]})
        return items

    def formatted(self):
        from formatter import format_source
        try:
            return format_source(self.text)
        except (LexError, ParseError):
            return None
