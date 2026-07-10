from enum import IntEnum, auto


class Op(IntEnum):
    LOAD_CONST = auto()
    LOAD_NAME = auto()
    STORE_NAME = auto()
    ASSIGN_NAME = auto()
    LOAD_LOCAL = auto()
    STORE_LOCAL = auto()
    LOAD_GLOBAL = auto()

    POP = auto()
    DUP = auto()

    BUILD_LIST = auto()
    BUILD_DICT = auto()
    BUILD_TUPLE = auto()

    BINARY = auto()
    UNARY = auto()

    JUMP = auto()
    JUMP_IF_FALSE = auto()
    JUMP_IF_TRUE = auto()

    CALL = auto()
    RETURN = auto()

    GET_INDEX = auto()
    SET_INDEX = auto()
    GET_ATTR = auto()
    SET_ATTR = auto()

    MAKE_CLOSURE = auto()
    MAKE_STRUCT = auto()
    MAKE_VARIANT = auto()

    MATCH_VARIANT = auto()
    GET_VARIANT_FIELD = auto()

    BUILD_STRING = auto()
    TRY_UNWRAP = auto()

    ITER_NEW = auto()
    ITER_NEXT = auto()


class Instr:
    __slots__ = ("op", "arg", "line")

    def __init__(self, op, arg=None, line=0):
        self.op = op
        self.arg = arg
        self.line = line

    def __repr__(self):
        if self.arg is None:
            return self.op.name
        return f"{self.op.name} {self.arg!r}"


class CodeObject:
    __slots__ = ("name", "instrs", "consts", "params", "num_locals", "local_names")

    def __init__(self, name):
        self.name = name
        self.instrs = []
        self.consts = []
        self.params = []
        self.num_locals = 0
        self.local_names = []

    def emit(self, op, arg=None, line=0):
        self.instrs.append(Instr(op, arg, line))
        return len(self.instrs) - 1

    def const(self, value):
        for i, c in enumerate(self.consts):
            if type(c) is type(value) and c == value:
                return i
        self.consts.append(value)
        return len(self.consts) - 1

    def __repr__(self):
        return f"<code {self.name} {len(self.instrs)} instrs>"
