import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import platform_abi
from lexer import tokenize, TokenType as T
from parser import parse
from interpreter import Interpreter
from compiler import compile_module
from vm import VM


def _toks(src):
    return [(t.type.name, t.value) for t in tokenize(src) if t.type != T.EOF]


def _run_interp(src):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(parse(src))
    return buf.getvalue()


def _run_vm(src):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        VM(compile_module(parse(src))).run()
    return buf.getvalue()


def test_platform_matrix():
    lin = platform_abi.make_platform("Linux", "x86_64")
    mac = platform_abi.make_platform("Darwin", "arm64")
    win = platform_abi.make_platform("Windows", "AMD64")
    assert lin.executable_name("app") == "app"
    assert win.executable_name("app") == "app.exe"
    assert mac.executable_name("app") == "app"
    assert lin.shared_library_name("z") == "libz.so"
    assert mac.shared_library_name("z") == "libz.dylib"
    assert win.shared_library_name("z") == "z.dll"
    assert platform_abi.reloc_model(win) == "default"
    assert platform_abi.reloc_model(lin) == "pic"
    return "platform matrix: exe/dll names and reloc for linux, macos, windows"


def test_arch_normalization():
    assert platform_abi.normalize_arch("amd64") == "x86_64"
    assert platform_abi.normalize_arch("arm64") == "aarch64"
    assert platform_abi.normalize_arch("AArch64") == "aarch64"
    assert platform_abi.normalize_os("Darwin") == platform_abi.MACOS
    assert platform_abi.normalize_os("MINGW64_NT") == platform_abi.WINDOWS
    return "normalization: arch and os aliases mapped consistently"


def test_library_candidates():
    lin = platform_abi.make_platform("Linux", "x86_64")
    mac = platform_abi.make_platform("Darwin", "x86_64")
    win = platform_abi.make_platform("Windows", "AMD64")
    assert "libm.so.6" in lin.library_candidates("m")
    assert any("dylib" in c or "System" in c for c in mac.library_candidates("m"))
    assert any(c.endswith(".dll") for c in win.library_candidates("c"))
    return "ffi: platform-specific library resolution candidates"


def test_line_ending_equivalence():
    lf = "fn main():\n    let x = 21\n    print(x + x)\n"
    crlf = lf.replace("\n", "\r\n")
    cr = lf.replace("\n", "\r")
    assert _toks(lf) == _toks(crlf) == _toks(cr)
    assert _run_interp(lf) == _run_interp(crlf) == _run_interp(cr) == "42\n"
    return "line endings: LF, CRLF, and CR produce identical tokens and output"


def test_engine_consistency_cross_platform():
    programs = [
        "fn main():\n    let xs = [1, 2, 3]\n    var s = 0\n    for x in xs:\n        s += x\n    print(s)\n",
        "enum C:\n    A\n    B\nfn main():\n    match B:\n        A => print(1)\n        B => print(2)\n",
        "fn main():\n    print(\"hi ${2 * 21}\")\n",
    ]
    for src in programs:
        crlf = src.replace("\n", "\r\n")
        i1 = _run_interp(src)
        v1 = _run_vm(src)
        i2 = _run_interp(crlf)
        assert i1 == v1 == i2, (i1, v1, i2)
    return "engines: interpreter and VM agree, independent of line endings"


def test_host_platform_valid():
    host = platform_abi.HOST
    assert host.os in (platform_abi.LINUX, platform_abi.MACOS, platform_abi.WINDOWS)
    assert host.arch
    d = host.as_dict()
    assert set(d) >= {"os", "arch", "exe_ext", "dll_ext", "obj_ext", "path_sep", "line_sep"}
    return f"host detection: {host.os}/{host.arch} recognized"


def test_compiler_discovery():
    host = platform_abi.HOST
    cc = platform_abi.find_c_compiler(host)
    assert cc is None or os.path.basename(cc)
    os.environ["ULANG_CC"] = "my-custom-cc"
    try:
        assert platform_abi.find_c_compiler(host) == "my-custom-cc"
    finally:
        os.environ.pop("ULANG_CC")
    return "toolchain: C compiler discovery honors ULANG_CC override"


def test_platform_module_from_ulang():
    out = _run_interp(
        "import platform\n"
        "fn main():\n"
        "    print(platform.os)\n"
        "    print(platform.is_windows())\n"
    )
    lines = out.strip().split("\n")
    assert lines[0] in ("linux", "macos", "windows")
    assert lines[1] in ("true", "false")
    return "stdlib: platform module exposes os and predicates to programs"


TESTS = [
    test_platform_matrix,
    test_arch_normalization,
    test_library_candidates,
    test_line_ending_equivalence,
    test_engine_consistency_cross_platform,
    test_host_platform_valid,
    test_compiler_discovery,
    test_platform_module_from_ulang,
]


def run():
    failed = 0
    for t in TESTS:
        try:
            print("ok   " + t())
        except Exception as e:
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    total = len(TESTS)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
