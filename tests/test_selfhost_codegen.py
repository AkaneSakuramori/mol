import os
import sys
import glob
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")
NATIVE_EX = os.path.join(ROOT, "examples", "native")
RUNTIME = os.path.join(ROOT, "runtime")


def _have_toolchain():
    try:
        import platform_abi
        import llvmlite  # noqa: F401
        return platform_abi.find_c_compiler() is not None
    except ImportError:
        return False


def compile_ir_to_binary(ir_text, out_path):
    """Compile self-hosted LLVM IR text to a native binary, linking the GC runtime."""
    import llvmlite.binding as llvm
    import platform_abi
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    triple = platform_abi.llvm_triple_override()
    mod = llvm.parse_assembly(ir_text)
    mod.verify()
    if triple:
        mod.triple = triple
        target = llvm.Target.from_triple(triple)
    else:
        target = llvm.Target.from_default_triple()
    machine = target.create_target_machine(
        codemodel="default", opt=2, reloc=platform_abi.reloc_model()
    )
    obj = machine.emit_object(mod)
    plat = platform_abi.HOST
    out_path = plat.executable_name(out_path)
    with tempfile.NamedTemporaryFile(suffix=plat.obj_ext, delete=False) as f:
        obj_path = f.name
        f.write(obj)
    cc = platform_abi.find_c_compiler(plat)
    gc_src = os.path.join(RUNTIME, "ulang_gc.c")
    link_libs = [] if plat.is_windows() else ["-lm"]
    try:
        r = subprocess.run(
            [cc, obj_path, gc_src, "-I", RUNTIME, "-o", out_path, "-O2"] + link_libs,
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise RuntimeError("link failed: " + r.stderr)
    finally:
        os.unlink(obj_path)
    return out_path


def selfhosted_ir(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    cg = subprocess.run([sys.executable, ULANG, "run", "codegen.ul"],
                        cwd=workdir, capture_output=True, text=True)
    if cg.returncode != 0:
        raise RuntimeError("codegen: " + cg.stderr.strip())
    return cg.stdout


def reference_output(ul_path, out_path):
    from native import build_executable
    from parser import parse
    exe = build_executable(parse(open(ul_path).read()), out_path)
    r = subprocess.run([exe], capture_output=True, text=True)
    return r.stdout


# Programs whose runtime behavior is fully determined by integer values and control flow.
# Float and string LITERAL values are opaque in the self-hosted pipeline's canonical
# syntax-tree form (a float literal is the atom (flt)); programs whose output or control
# flow depends on a specific float/string literal value are therefore outside this
# representation and are covered by the reference's own native-backend tests. The IR
# structure for float arithmetic is still generated and exercised via integer-to-float
# coercion in mixed expressions below.
CASES = [
    "fn main():\n    print(2 + 3 * 4)\n",
    "fn main():\n    print(10 / 3)\n    print(10 % 3)\n",
    "fn main():\n    var s = 0\n    for i in range(0, 10):\n        s += i\n    print(s)\n",
    "fn main():\n    var n = 5\n    while n > 0:\n        print(n)\n        n -= 1\n",
    "fn f(n: int) -> int:\n    if n < 0:\n        return 0\n    elif n == 0:\n        return 1\n    else:\n        return 2\nfn main():\n    print(f(-3))\n    print(f(0))\n    print(f(9))\n",
    "fn main():\n    print(true and false)\n    print(true or false)\n    print(not true)\n",
    "fn main():\n    let x = 7 if 2 < 3 else 9\n    print(x)\n",
    "fn is_prime(n: int) -> bool:\n    if n < 2:\n        return false\n    var i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return false\n        i += 1\n    return true\nfn main():\n    var c = 0\n    for n in range(2, 100):\n        if is_prime(n):\n            c += 1\n    print(c)\n",
    "fn fib(n: int) -> int:\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\nfn main():\n    for i in range(0, 12):\n        print(fib(i))\n",
    "fn main():\n    var total = 0\n    for i in range(1, 6):\n        for j in range(1, 6):\n            total += i * j\n    print(total)\n",
    "fn main():\n    var i = 0\n    while true:\n        i += 1\n        if i == 3:\n            continue\n        if i > 5:\n            break\n        print(i)\n",
    "fn main():\n    print(-5 + 3)\n    print(-(2 * 4))\n",
    "fn scale(n: int) -> int:\n    return n * 2 + 1\nfn main():\n    var acc = 0\n    for i in range(0, 20):\n        acc += scale(i)\n    print(acc)\n",
    "fn gcd(a: int, b: int) -> int:\n    var x = a\n    var y = b\n    while y != 0:\n        let t = x % y\n        x = y\n        y = t\n    return x\nfn main():\n    print(gcd(48, 36))\n",
    "fn to_f(n: int) -> float:\n    return n\nfn main():\n    let x = to_f(5)\n    if x > 3.0:\n        print(1)\n    else:\n        print(0)\n",
]

NATIVE_FILES = ["fib", "primes"]


def run():
    if not _have_toolchain():
        print("skip: no C compiler / llvmlite")
        print("\n0/0 passed (skipped)")
        return 0

    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "codegen.ul"), os.path.join(workdir, "codegen.ul"))
    bindir = tempfile.mkdtemp()
    failed = 0
    checked = 0

    def check(name, src, ref_out):
        nonlocal failed, checked
        try:
            ir = selfhosted_ir(src, workdir)
            exe = compile_ir_to_binary(ir, os.path.join(bindir, "sh_" + name))
            got = subprocess.run([exe], capture_output=True, text=True, timeout=30).stdout
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: self-hosted binary timed out")
            failed += 1
            return
        except (RuntimeError, Exception) as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            return
        checked += 1
        if got == ref_out:
            print(f"ok   {name}: native output matches reference")
        else:
            print(f"FAIL {name}: reference {ref_out!r}, self-hosted {got!r}")
            failed += 1

    for idx, src in enumerate(CASES):
        with open(os.path.join(workdir, "ref.ul"), "w") as f:
            f.write(src)
        ref_out = reference_output(os.path.join(workdir, "ref.ul"),
                                   os.path.join(bindir, f"ref_{idx}"))
        check(f"case[{idx}]", src, ref_out)

    for name in NATIVE_FILES:
        path = os.path.join(NATIVE_EX, name + ".ul")
        src = open(path).read()
        ref_out = reference_output(path, os.path.join(bindir, "ref_" + name))
        check(name, src, ref_out)

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 3 (native codegen): native output matches the reference")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
