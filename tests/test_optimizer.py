import os
import sys
import io
import glob
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parser import parse
from optimizer import optimize_module
from interpreter import Interpreter
from compiler import compile_module
from vm import VM
from builtins_mod import UlangPanic


EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")

RUNNABLE = [
    "01_hello", "02_functions", "03_interpolation", "04_control_flow",
    "05_loops", "06_higher_order", "08_enums_match", "09_result",
    "10_option", "12_closures", "13_generics", "15_dicts",
    "16_tuples", "18_recursion", "19_const_ternary",
]

FOLD_CASES = [
    ("fn main():\n    print(2 + 3 * 4 - 1)\n", "13"),
    ("fn main():\n    print(\"a\" + \"b\" + \"c\")\n", "abc"),
    ("fn main():\n    print(10 / 2 + 3)\n", "8"),
    ("fn main():\n    if 1 < 2:\n        print(\"yes\")\n    else:\n        print(\"no\")\n", "yes"),
    ("fn main():\n    print(5 if false else 9)\n", "9"),
    ("fn main():\n    print(not false)\n", "true"),
    ("fn main():\n    print(\"n=${2 * 21}\")\n", "n=42"),
    ("fn main():\n    var s = 0\n    while false:\n        s += 1\n    print(s)\n", "0"),
]


def run_interp(tree):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(tree)
    return buf.getvalue()


def run_vm(tree):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        VM(compile_module(tree)).run()
    return buf.getvalue()


def instr_count(tree):
    prog = compile_module(tree)
    return sum(len(c.instrs) for c in prog.functions.values())


def run():
    failed = 0
    total_before = 0
    total_after = 0

    for name in RUNNABLE:
        with open(os.path.join(EXAMPLES, name + ".ul")) as f:
            src = f.read()
        base = run_interp(parse(src))
        opt_tree = optimize_module(parse(src))
        opt_interp = run_interp(opt_tree)
        opt_vm = run_vm(optimize_module(parse(src)))
        before = instr_count(parse(src))
        after = instr_count(optimize_module(parse(src)))
        total_before += before
        total_after += after
        if base == opt_interp == opt_vm:
            delta = before - after
            note = f"(-{delta} instrs)" if delta else "(no change)"
            print(f"ok   {name}: identical output {note}")
        else:
            print(f"FAIL {name}: base={base!r} opt={opt_interp!r} vm={opt_vm!r}")
            failed += 1

    for i, (src, expected) in enumerate(FOLD_CASES):
        opt = optimize_module(parse(src))
        out = run_interp(opt).strip()
        base = run_interp(parse(src)).strip()
        if out == expected == base:
            print(f"ok   fold {i}: {expected}")
        else:
            print(f"FAIL fold {i}: expected {expected!r}, got {out!r} (base {base!r})")
            failed += 1

    pct = 100 * (total_before - total_after) / total_before if total_before else 0
    print(f"\ntotal bytecode: {total_before} -> {total_after} ({pct:.1f}% smaller across examples)")

    if _peephole_checks():
        print("ok   peephole: jump-to-next and unreachable code removed, targets remapped")
    else:
        print("FAIL peephole checks")
        failed += 1

    total = len(RUNNABLE) + len(FOLD_CASES) + 1
    print(f"{total - failed}/{total} passed")
    return 1 if failed else 0


def _peephole_checks():
    from bytecode import Op, Instr, CodeObject
    from peephole import peephole
    code = CodeObject("t")
    code.instrs = [
        Instr(Op.JUMP, 1),
        Instr(Op.LOAD_CONST, 0),
        Instr(Op.RETURN),
        Instr(Op.LOAD_CONST, 1),
        Instr(Op.RETURN),
    ]
    peephole(code)
    ops = [i.op for i in code.instrs]
    if Op.JUMP in ops:
        return False
    if len(code.instrs) != 2:
        return False

    code2 = CodeObject("t2")
    code2.instrs = [
        Instr(Op.LOAD_CONST, 0),
        Instr(Op.JUMP_IF_FALSE, 4),
        Instr(Op.LOAD_CONST, 1),
        Instr(Op.RETURN),
        Instr(Op.LOAD_CONST, 2),
        Instr(Op.RETURN),
    ]
    peephole(code2)
    jif = next(i for i in code2.instrs if i.op == Op.JUMP_IF_FALSE)
    return code2.instrs[jif.arg].op == Op.LOAD_CONST


if __name__ == "__main__":
    sys.exit(run())
