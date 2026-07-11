import ctypes

import llvmlite.binding as llvm

import ast_nodes as ast
from codegen import ModuleGen, native_type, TypeInfo, CodegenError


_initialized = False


def _init():
    global _initialized
    if _initialized:
        return
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    _initialized = True


_CTYPE = {
    TypeInfo.INT: ctypes.c_int64,
    TypeInfo.FLOAT: ctypes.c_double,
    TypeInfo.BOOL: ctypes.c_bool,
}


class JITEngine:
    def __init__(self, module_ast):
        _init()
        self.module_ast = module_ast
        self.functions = {name: fn for name, fn in _user_functions(module_ast)}
        self.signatures = {}
        self.compiled = {}
        self.engine = None
        self._mod_ref = None

    def eligible(self, name):
        decl = self.functions.get(name)
        if decl is None:
            return False
        if decl.name == "main":
            return False
        for p in decl.params:
            if native_type(p.type) not in (TypeInfo.INT, TypeInfo.FLOAT, TypeInfo.BOOL):
                return False
        return True

    def compile(self):
        gen = ModuleGen(emit_entry=False)
        try:
            ir_module = gen.generate(self.module_ast)
        except CodegenError:
            return False
        self.signatures = gen.signatures
        target = llvm.Target.from_default_triple()
        machine = target.create_target_machine(opt=3)
        backing = llvm.parse_assembly(str(ir_module))
        backing.verify()
        engine = llvm.create_mcjit_compiler(backing, machine)
        engine.finalize_object()
        engine.run_static_constructors()
        self.engine = engine
        self._mod_ref = backing
        return True

    def get_callable(self, name):
        if name in self.compiled:
            return self.compiled[name]
        if self.engine is None:
            if not self.compile():
                return None
        if name not in self.signatures:
            return None
        ret_type, param_types = self.signatures[name]
        addr = self.engine.get_function_address(name)
        if not addr:
            return None
        c_ret = _CTYPE.get(ret_type, ctypes.c_int64)
        c_args = [_CTYPE.get(p, ctypes.c_int64) for p in param_types]
        proto = ctypes.CFUNCTYPE(c_ret, *c_args)
        cfn = proto(addr)
        self.compiled[name] = (cfn, ret_type, param_types)
        return self.compiled[name]


def _user_functions(module_ast):
    for decl in module_ast.body:
        if isinstance(decl, ast.Function):
            yield decl.name, decl
