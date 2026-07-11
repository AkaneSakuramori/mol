from enum import Enum, auto


class TokenType(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    IDENT = auto()
    KEYWORD = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    STAR_EQ = auto()
    SLASH_EQ = auto()
    PERCENT_EQ = auto()
    EQ_EQ = auto()
    BANG_EQ = auto()
    LT = auto()
    LT_EQ = auto()
    GT = auto()
    GT_EQ = auto()
    ARROW = auto()
    FAT_ARROW = auto()
    QUESTION = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    PLUS_PLUS = auto()

    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


KEYWORDS = {
    "fn", "let", "var", "const", "type", "enum", "trait", "impl", "derive",
    "pub", "import", "from", "as", "if", "elif", "else", "match", "while",
    "for", "in", "with", "defer", "return", "break", "continue", "extern",
    "and", "or", "not", "true", "false", "none",
}


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type, value, line, col):
        self.type = type
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"

    def __eq__(self, other):
        return (
            isinstance(other, Token)
            and self.type == other.type
            and self.value == other.value
        )


class LexError(Exception):
    def __init__(self, message, line, col):
        super().__init__(f"{line}:{col}: {message}")
        self.line = line
        self.col = col


_SINGLE = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ",": TokenType.COMMA,
    ":": TokenType.COLON,
    ".": TokenType.DOT,
}


class Lexer:
    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.indents = [0]
        self.paren_depth = 0

    def error(self, message):
        raise LexError(message, self.line, self.col)

    def peek(self, offset=0):
        i = self.pos + offset
        if i < len(self.src):
            return self.src[i]
        return ""

    def advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def add(self, type, value):
        self.tokens.append(Token(type, value, self.line, self.col))

    def tokenize(self):
        while self.pos < len(self.src):
            if self.col == 1 and self.paren_depth == 0:
                if not self.handle_line_start():
                    continue
            self.scan_token()
        self.finish()
        return self.tokens

    def handle_line_start(self):
        start = self.pos
        indent = 0
        while self.peek() in (" ", "\t"):
            indent += 1
            self.advance()
        ch = self.peek()
        if ch == "" or ch == "\n" or ch == "#":
            if ch == "#":
                while self.peek() not in ("", "\n"):
                    self.advance()
            if self.peek() == "\n":
                self.advance()
            return False
        self.emit_indentation(indent)
        return True

    def emit_indentation(self, indent):
        current = self.indents[-1]
        if indent > current:
            self.indents.append(indent)
            self.add(TokenType.INDENT, indent)
        elif indent < current:
            while self.indents[-1] > indent:
                self.indents.pop()
                self.add(TokenType.DEDENT, self.indents[-1])
            if self.indents[-1] != indent:
                self.error("inconsistent indentation")

    def scan_token(self):
        ch = self.peek()

        if ch == "" :
            return
        if ch == "#":
            while self.peek() not in ("", "\n"):
                self.advance()
            return
        if ch == "\n":
            self.advance()
            if self.paren_depth == 0:
                self.add(TokenType.NEWLINE, "\\n")
            return
        if ch in (" ", "\t"):
            self.advance()
            return
        if ch == '"':
            self.scan_string()
            return
        if ch.isdigit():
            self.scan_number()
            return
        if ch.isalpha() or ch == "_":
            self.scan_ident()
            return
        self.scan_operator()

    def scan_ident(self):
        start_col = self.col
        chars = []
        while self.peek().isalnum() or self.peek() == "_":
            chars.append(self.advance())
        text = "".join(chars)
        type = TokenType.KEYWORD if text in KEYWORDS else TokenType.IDENT
        self.tokens.append(Token(type, text, self.line, start_col))

    def scan_number(self):
        start_col = self.col
        chars = []
        is_float = False
        while self.peek().isdigit() or self.peek() == "_":
            chars.append(self.advance())
        if self.peek() == "." and self.peek(1).isdigit():
            is_float = True
            chars.append(self.advance())
            while self.peek().isdigit() or self.peek() == "_":
                chars.append(self.advance())
        text = "".join(chars).replace("_", "")
        if is_float:
            self.tokens.append(Token(TokenType.FLOAT, float(text), self.line, start_col))
        else:
            self.tokens.append(Token(TokenType.INT, int(text), self.line, start_col))

    def scan_string(self):
        start_col = self.col
        self.advance()
        parts = []
        buf = []
        while True:
            ch = self.peek()
            if ch == "":
                self.error("unterminated string")
            if ch == '"':
                self.advance()
                break
            if ch == "\\":
                self.advance()
                esc = self.advance()
                buf.append(self._unescape(esc))
                continue
            if ch == "$" and self.peek(1) == "{":
                if buf:
                    parts.append(("str", "".join(buf)))
                    buf = []
                self.advance()
                self.advance()
                expr = self.scan_interpolation()
                parts.append(("expr", expr))
                continue
            buf.append(self.advance())
        if buf or not parts:
            parts.append(("str", "".join(buf)))
        self.tokens.append(Token(TokenType.STRING, parts, self.line, start_col))

    def scan_interpolation(self):
        depth = 1
        chars = []
        while True:
            ch = self.peek()
            if ch == "":
                self.error("unterminated interpolation")
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    self.advance()
                    break
            chars.append(self.advance())
        return "".join(chars)

    def _unescape(self, esc):
        table = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "$": "$", "r": "\r", "0": "\0"}
        if esc not in table:
            self.error(f"invalid escape \\{esc}")
        return table[esc]

    def scan_operator(self):
        start_col = self.col
        ch = self.advance()
        two = ch + self.peek()

        two_map = {
            "==": TokenType.EQ_EQ,
            "!=": TokenType.BANG_EQ,
            "<=": TokenType.LT_EQ,
            ">=": TokenType.GT_EQ,
            "->": TokenType.ARROW,
            "=>": TokenType.FAT_ARROW,
            "+=": TokenType.PLUS_EQ,
            "-=": TokenType.MINUS_EQ,
            "*=": TokenType.STAR_EQ,
            "/=": TokenType.SLASH_EQ,
            "%=": TokenType.PERCENT_EQ,
            "++": TokenType.PLUS_PLUS,
        }
        if two in two_map:
            self.advance()
            self.tokens.append(Token(two_map[two], two, self.line, start_col))
            return

        single_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "=": TokenType.EQ,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "?": TokenType.QUESTION,
        }
        if ch in single_map:
            self.tokens.append(Token(single_map[ch], ch, self.line, start_col))
            return
        if ch in _SINGLE:
            type = _SINGLE[ch]
            if ch in "([":
                self.paren_depth += 1
            elif ch in ")]":
                self.paren_depth = max(0, self.paren_depth - 1)
            self.tokens.append(Token(type, ch, self.line, start_col))
            return
        self.error(f"unexpected character {ch!r}")

    def finish(self):
        if self.tokens and self.tokens[-1].type not in (TokenType.NEWLINE,):
            self.add(TokenType.NEWLINE, "\\n")
        while len(self.indents) > 1:
            self.indents.pop()
            self.add(TokenType.DEDENT, 0)
        self.add(TokenType.EOF, None)


def tokenize(source):
    return Lexer(source).tokenize()
