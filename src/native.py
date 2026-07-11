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


def compile_to_object(module_ast, opt_level=2, triple=None, reloc=None):
    import platform_abi
    _init()
    ir_module = generate_ir(module_ast)
    llvm_ir = str(ir_module)
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    if triple:
        target = llvm.Target.from_triple(triple)
    else:
        target = llvm.Target.from_default_triple()
    machine = target.create_target_machine(
        codemodel="default", opt=opt_level, reloc=reloc or platform_abi.reloc_model()
    )
    return machine.emit_object(mod), llvm_ir


_RUNTIME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runtime")


class ToolchainError(RuntimeError):
    pass


def build_executable(module_ast, output_path, opt_level=2, keep_ir=False):
    import platform_abi
    plat = platform_abi.HOST
    output_path = plat.executable_name(output_path)

    cc = platform_abi.find_c_compiler(plat)
    if cc is None:
        raise ToolchainError(
            "no C compiler found; install gcc or clang, or set ULANG_CC"
        )

    obj, llvm_ir = compile_to_object(module_ast, opt_level)
    with tempfile.NamedTemporaryFile(suffix=plat.obj_ext, delete=False) as f:
        obj_path = f.name
        f.write(obj)
    gc_src = os.path.join(_RUNTIME_DIR, "ulang_gc.c")
    link_inputs = [obj_path]
    if os.path.exists(gc_src):
        link_inputs.append(gc_src)
    link_libs = [] if plat.is_windows() else ["-lm"]
    try:
        result = subprocess.run(
            [cc] + link_inputs + ["-I", _RUNTIME_DIR, "-o", output_path, "-O2"] + link_libs,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise ToolchainError(f"link failed ({cc}): {result.stderr}")
    finally:
        os.unlink(obj_path)
    if keep_ir:
        with open(output_path + ".ll", "w") as f:
            f.write(llvm_ir)
    return output_path


def emit_ir(module_ast):
    return str(generate_ir(module_ast))
