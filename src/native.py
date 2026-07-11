import os
import subprocess
import tempfile

import llvmlite.binding as llvm

from codegen import generate_ir


_initialized = False


def _init():
    global _initialized
    if _initialized:
        return
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    _initialized = True


def compile_to_object(module_ast, opt_level=2):
    _init()
    ir_module = generate_ir(module_ast)
    llvm_ir = str(ir_module)
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    target = llvm.Target.from_default_triple()
    machine = target.create_target_machine(
        codemodel="default", opt=opt_level, reloc="pic"
    )
    return machine.emit_object(mod), llvm_ir


_RUNTIME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runtime")


def build_executable(module_ast, output_path, opt_level=2, keep_ir=False):
    obj, llvm_ir = compile_to_object(module_ast, opt_level)
    with tempfile.NamedTemporaryFile(suffix=".o", delete=False) as f:
        obj_path = f.name
        f.write(obj)
    gc_src = os.path.join(_RUNTIME_DIR, "ulang_gc.c")
    link_inputs = [obj_path]
    if os.path.exists(gc_src):
        link_inputs.append(gc_src)
    try:
        result = subprocess.run(
            ["gcc"] + link_inputs + ["-I", _RUNTIME_DIR, "-o", output_path, "-lm", "-O2"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"link failed: {result.stderr}")
    finally:
        os.unlink(obj_path)
    if keep_ir:
        with open(output_path + ".ll", "w") as f:
            f.write(llvm_ir)
    return output_path


def emit_ir(module_ast):
    return str(generate_ir(module_ast))
