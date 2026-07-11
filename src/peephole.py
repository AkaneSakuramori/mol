from bytecode import Op, Instr


_UNCONDITIONAL = (Op.JUMP, Op.RETURN)


def peephole(code):
    changed = True
    while changed:
        changed = False
        if _remove_jump_to_next(code):
            changed = True
        if _remove_unreachable(code):
            changed = True
    return code


def _jump_targets(instrs):
    targets = set()
    for ins in instrs:
        if ins.op in (Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_IF_TRUE):
            targets.add(ins.arg)
    return targets


def _rebuild(code, keep):
    old_to_new = {}
    new_instrs = []
    for i, ins in enumerate(code.instrs):
        if keep[i]:
            old_to_new[i] = len(new_instrs)
            new_instrs.append(ins)
    end = len(new_instrs)
    for i in range(len(code.instrs)):
        if i not in old_to_new:
            j = i
            while j < len(code.instrs) and j not in old_to_new:
                j += 1
            old_to_new[i] = old_to_new.get(j, end)
    for ins in new_instrs:
        if ins.op in (Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_IF_TRUE):
            ins.arg = old_to_new.get(ins.arg, end)
    code.instrs = new_instrs


def _remove_jump_to_next(code):
    instrs = code.instrs
    keep = [True] * len(instrs)
    removed = False
    for i, ins in enumerate(instrs):
        if ins.op == Op.JUMP and ins.arg == i + 1:
            keep[i] = False
            removed = True
    if removed:
        _rebuild(code, keep)
    return removed


def _remove_unreachable(code):
    instrs = code.instrs
    if not instrs:
        return False
    targets = _jump_targets(instrs)
    keep = [True] * len(instrs)
    reachable = True
    removed = False
    for i, ins in enumerate(instrs):
        if i in targets:
            reachable = True
        if not reachable:
            keep[i] = False
            removed = True
            continue
        if ins.op in _UNCONDITIONAL:
            reachable = False
    if removed:
        _rebuild(code, keep)
    return removed
