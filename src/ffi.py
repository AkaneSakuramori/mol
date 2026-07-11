import ctypes
import ctypes.util

import values as V
from values import Builtin
from builtins_mod import MolPanic


_CTYPES = {
    "int": ctypes.c_long,
    "float": ctypes.c_double,
    "bool": ctypes.c_bool,
    "str": ctypes.c_char_p,
}


def _ctype_for(type_node):
    import ast_nodes as ast
    if isinstance(type_node, ast.NamedType):
        return _CTYPES.get(type_node.name, ctypes.c_long)
    return ctypes.c_long


def load_library(name):
    if name is None or name in ("c", "libc"):
        path = ctypes.util.find_library("c") or "libc.so.6"
        return ctypes.CDLL(path)
    if name in ("m", "libm", "math"):
        path = ctypes.util.find_library("m") or "libm.so.6"
        return ctypes.CDLL(path)
    found = ctypes.util.find_library(name)
    return ctypes.CDLL(found or name)


def make_extern(decl):
    lib = load_library(decl.library)
    cfn = getattr(lib, decl.c_name)
    cfn.argtypes = [_ctype_for(p.type) for p in decl.params]
    cfn.restype = _ctype_for(decl.return_type) if decl.return_type else ctypes.c_long

    def call(args):
        cargs = []
        for value, param in zip(args, decl.params):
            cargs.append(_to_c(value, param.type))
        result = cfn(*cargs)
        return _from_c(result)

    return Builtin(decl.name, call)


def _to_c(value, type_node):
    import ast_nodes as ast
    if isinstance(type_node, ast.NamedType) and type_node.name == "str":
        if isinstance(value, str):
            return value.encode("utf8")
    return value


def _from_c(value):
    if isinstance(value, bytes):
        return value.decode("utf8")
    return value
