import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import tokenize, LexError, TokenType
from parser import parse, ParseError
from interpreter import Interpreter
from checker import check as type_check
from compiler import compile_module
from vm import VM
from builtins_mod import UlangPanic
import ast_nodes as ast

VERSION = "1.8.1"


def _optimize(tree):
    if os.environ.get("ULANG_NO_OPT"):
        return tree
    from optimizer import optimize_module
    return optimize_module(tree)


def _dump(node, indent=0):
    pad = "  " * indent
    if isinstance(node, ast.Node):
        lines = [f"{type(node).__name__}"]
        for field in node._fields:
            value = getattr(node, field, None)
            lines.append(f"{pad}  {field}: {_dump(value, indent + 2)}")
        return "\n".join(lines)
    if isinstance(node, list):
        if not node:
            return "[]"
        items = [f"\n{pad}  - {_dump(v, indent + 2)}" for v in node]
        return "".join(items)
    return repr(node)


def cmd_lex(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tokens = tokenize(source)
    except LexError as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    for tok in tokens:
        if tok.type == TokenType.EOF:
            print("EOF")
        else:
            print(f"{tok.type.name:12} {tok.value!r}")
    return 0


def cmd_parse(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    print(_dump(tree))
    return 0


def _project_roots(path):
    roots = []
    d = os.path.dirname(os.path.abspath(path))
    roots.append(d)
    parent = os.path.dirname(d)
    if parent and parent != d:
        roots.append(parent)
    cwd = os.getcwd()
    if cwd not in roots:
        roots.append(cwd)
    return roots


def cmd_run(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    try:
        interp = Interpreter()
        interp.search_roots = _project_roots(path)
        interp.run(_optimize(tree))
    except UlangPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    return 0


def cmd_gc_stats(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    interp = Interpreter()
    interp.search_roots = _project_roots(path)
    interp.memory.enabled = True
    try:
        interp.run(_optimize(tree))
    except UlangPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    interp.memory.collect(full=True)
    stats = interp.memory.stats()
    print("gc statistics:")
    for key in ("total_allocated", "live_objects", "young", "old",
                "minor_collections", "major_collections",
                "objects_reclaimed", "promotions", "max_pause_ms"):
        print(f"  {key}: {stats[key]}")
    return 0


def cmd_check(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    errors = type_check(tree)
    if errors:
        for e in errors:
            print(f"{path}:{e}", file=sys.stderr)
        return 1
    print(f"{path}: ok")
    return 0


def cmd_runvm(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    try:
        VM(compile_module(_optimize(tree))).run()
    except UlangPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    return 0


def cmd_build(path, output=None):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from native import build_executable
    from codegen import CodegenError
    if output is None:
        output = os.path.splitext(os.path.basename(path))[0]
    try:
        build_executable(_optimize(tree), output, keep_ir=True)
    except CodegenError as e:
        print(f"error: {path}: native backend: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    print(f"built {output}")
    return 0


def cmd_emit_ir(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from native import emit_ir
    from codegen import CodegenError
    try:
        print(emit_ir(_optimize(tree)))
    except CodegenError as e:
        print(f"error: {path}: native backend: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_escape(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from escape import analyze
    results = analyze(tree)
    for fn_name, fe in results.items():
        decisions = fe.decisions()
        if not decisions:
            continue
        print(f"fn {fn_name}:")
        for var, where in decisions:
            print(f"    {var}: {where}")
    return 0


def cmd_fmt(path, write=False):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        from formatter import format_source
        formatted = format_source(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    if write:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(formatted)
        print(f"formatted {path}")
    else:
        sys.stdout.write(formatted)
    return 0


def _project(path):
    from packages import Project
    return Project(path)


def cmd_install(path):
    from packages import Project, PackageError
    try:
        lock, installed = Project(path).install()
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not installed:
        print("no dependencies")
    for name, version in installed:
        print(f"installed {name} {version}")
    return 0


def cmd_add(path, name, constraint):
    from packages import Project, PackageError
    try:
        Project(path).add(name, constraint)
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"added {name}")
    return 0


def cmd_remove(path, name):
    from packages import Project, PackageError
    try:
        Project(path).remove(name)
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"removed {name}")
    return 0


def cmd_update(path):
    from packages import Project, PackageError
    try:
        lock, installed = Project(path).update()
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for name, version in installed:
        print(f"{name} {version}")
    return 0


def cmd_publish(path):
    from packages import Project, PackageError
    try:
        name, version, checksum = Project(path).publish()
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"published {name} {version}")
    print(f"checksum {checksum}")
    return 0


def cmd_search(query):
    from registry import Registry
    results = Registry().search(query)
    if not results:
        print("no packages found")
        return 0
    for r in results:
        desc = f" - {r['description']}" if r["description"] else ""
        print(f"{r['name']} {r['version']}{desc}")
    return 0


def cmd_list(path):
    from packages import Project
    for name, version in Project(path).installed():
        print(f"{name} {version}")
    return 0


def cmd_platform():
    import platform_abi
    host = platform_abi.HOST
    info = host.as_dict()
    print("ulang platform:")
    for key in ("os", "arch", "exe_ext", "dll_ext", "obj_ext", "path_sep", "line_sep"):
        print(f"  {key}: {info[key]!r}" if key == "exe_ext" else f"  {key}: {info[key]}")
    return 0


def cmd_doctor():
    import platform_abi
    host = platform_abi.HOST
    ok = True
    print(f"ulang {VERSION}")
    print(f"platform: {host.os}/{host.arch}")

    py = sys.version_info
    py_ok = py >= (3, 10)
    print(f"[{'ok' if py_ok else '!!'}] python {py.major}.{py.minor}")
    ok = ok and py_ok

    cc = platform_abi.find_c_compiler(host)
    print(f"[{'ok' if cc else '--'}] C compiler: {cc or 'not found (needed for ulang build)'}")

    try:
        import llvmlite  # noqa: F401
        print("[ok] llvmlite (native backend available)")
    except ImportError:
        print("[--] llvmlite not installed (needed for ulang build/jit)")

    print("interpreter and VM: available on all platforms")
    return 0 if ok else 1


def cmd_init(name):
    manifest = f"""[package]
name = "{name}"
version = "0.1.0"

[dependencies]
"""
    with open("ulang.toml", "w", encoding="utf-8") as f:
        f.write(manifest)
    os.makedirs("src", exist_ok=True)
    main_path = os.path.join("src", "main.ul")
    if not os.path.exists(main_path):
        with open(main_path, "w", encoding="utf-8") as f:
            f.write('fn main():\n    print("hello from ' + name + '")\n')
    print(f"created ulang.toml and src/main.ul for '{name}'")
    return 0


def cmd_jit(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = parse(source)
    except (LexError, ParseError) as e:
        print(f"error: {path}: {e}", file=sys.stderr)
        return 1
    from tiered import JITInterpreter
    interp = JITInterpreter(threshold=1)
    try:
        interp.run(_optimize(tree))
    except UlangPanic as e:
        print(f"panic: {e.message}", file=sys.stderr)
        return 1
    stats = interp.jit_stats
    if stats["compiled"]:
        print(f"[jit] native calls: {stats['native_calls']}, compiled: {', '.join(sorted(stats['compiled']))}",
              file=sys.stderr)
    return 0


def _dispatch_add(args):
    if os.path.exists(os.path.join(args[0], "ulang.toml")) and len(args) >= 2:
        path = args[0]
        name = args[1]
        constraint = args[2] if len(args) > 2 else None
    else:
        path = "."
        name = args[0]
        constraint = args[1] if len(args) > 1 else None
    return cmd_add(path, name, constraint)


def _dispatch_remove(args):
    if os.path.exists(os.path.join(args[0], "ulang.toml")) and len(args) >= 2:
        return cmd_remove(args[0], args[1])
    return cmd_remove(".", args[0])


def main(argv):
    if len(argv) < 2:
        print("usage: ulang <run|build|check|install|add|remove|update|publish|search|list|fmt|init|lsp|repl|...> ...", file=sys.stderr)
        return 2
    command = argv[1]
    if command in ("version", "--version", "-v"):
        print(f"ulang {VERSION}")
        return 0
    if command == "repl":
        from repl import repl
        return repl()
    if command == "platform":
        return cmd_platform()
    if command == "doctor":
        return cmd_doctor()
    if command == "lsp":
        from lsp import main as lsp_main
        return lsp_main()
    if command == "init":
        name = argv[2] if len(argv) > 2 else "app"
        return cmd_init(name)
    if command == "install":
        return cmd_install(argv[2] if len(argv) > 2 else ".")
    if command == "add":
        if len(argv) < 3:
            print("usage: ulang add [project] <package> [constraint]", file=sys.stderr)
            return 2
        return _dispatch_add(argv[2:])
    if command == "remove":
        if len(argv) < 3:
            print("usage: ulang remove [project] <package>", file=sys.stderr)
            return 2
        return _dispatch_remove(argv[2:])
    if command == "update":
        return cmd_update(argv[2] if len(argv) > 2 else ".")
    if command == "publish":
        return cmd_publish(argv[2] if len(argv) > 2 else ".")
    if command == "search":
        if len(argv) < 3:
            print("usage: ulang search <query>", file=sys.stderr)
            return 2
        return cmd_search(argv[2])
    if command == "list":
        return cmd_list(argv[2] if len(argv) > 2 else ".")
    if len(argv) < 3:
        print(f"usage: ulang {command} <file.ul>", file=sys.stderr)
        return 2
    if command == "lex":
        return cmd_lex(argv[2])
    if command == "parse":
        return cmd_parse(argv[2])
    if command == "check":
        return cmd_check(argv[2])
    if command == "run":
        return cmd_run(argv[2])
    if command == "runvm":
        return cmd_runvm(argv[2])
    if command == "jit":
        return cmd_jit(argv[2])
    if command == "build":
        output = argv[4] if len(argv) > 4 and argv[3] == "-o" else None
        return cmd_build(argv[2], output)
    if command == "emit-ir":
        return cmd_emit_ir(argv[2])
    if command == "escape":
        return cmd_escape(argv[2])
    if command == "gc-stats":
        return cmd_gc_stats(argv[2])
    if command == "fmt":
        write = "-w" in argv[3:]
        return cmd_fmt(argv[2], write)
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
