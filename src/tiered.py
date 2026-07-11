import ast_nodes as ast
from interpreter import Interpreter
from values import Closure
from jit import JITEngine, _CTYPE
from codegen import TypeInfo


HOT_THRESHOLD = 2


class JITInterpreter(Interpreter):
    def __init__(self, threshold=HOT_THRESHOLD):
        super().__init__()
        self.threshold = threshold
        self.call_counts = {}
        self.jit = None
        self.jit_stats = {"native_calls": 0, "compiled": set()}
        self._module_ast = None

    def run(self, module):
        self._module_ast = module
        self.jit = JITEngine(module)
        return super().run(module)

    def call(self, fn, args):
        if isinstance(fn, Closure) and fn.name in self.functions and fn.body is not None:
            name = fn.name
            if self._can_jit(name, args):
                native = self._maybe_native(name, args)
                if native is not None:
                    return native
        return super().call(fn, args)

    def _can_jit(self, name, args):
        if self.jit is None or not self.jit.eligible(name):
            return False
        for a in args:
            if not isinstance(a, (int, float, bool)):
                return False
        return True

    def _maybe_native(self, name, args):
        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        if self.call_counts[name] < self.threshold:
            return None
        entry = self.jit.get_callable(name)
        if entry is None:
            return None
        cfn, ret_type, param_types = entry
        cargs = []
        for value, pt in zip(args, param_types):
            if pt == TypeInfo.FLOAT:
                cargs.append(float(value))
            elif pt == TypeInfo.BOOL:
                cargs.append(bool(value))
            else:
                cargs.append(int(value))
        result = cfn(*cargs)
        self.jit_stats["native_calls"] += 1
        self.jit_stats["compiled"].add(name)
        if ret_type == TypeInfo.BOOL:
            return bool(result)
        return result


def run_jit(module, threshold=HOT_THRESHOLD):
    interp = JITInterpreter(threshold)
    interp.run(module)
    return interp.jit_stats
