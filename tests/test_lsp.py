import os
import sys
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from lsp_analysis import Analyzer

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


SAMPLE = """fn add(a: int, b: int) -> int:
    return a + b

fn main():
    let x = add(2, 3)
    print(x)
"""


def frame(msg):
    data = json.dumps(msg).encode()
    return f"Content-Length: {len(data)}\r\n\r\n".encode() + data


def parse_frames(raw):
    import re
    out = []
    for part in re.split(r"Content-Length: \d+\r\n\r\n", raw)[1:]:
        part = part.strip()
        if part:
            try:
                out.append(json.loads(part))
            except json.JSONDecodeError:
                pass
    return out


def run():
    failed = 0

    a = Analyzer(SAMPLE)

    if a.diagnostics() == []:
        print("ok   clean file has no diagnostics")
    else:
        print(f"FAIL diagnostics not empty: {a.diagnostics()}")
        failed += 1

    names = {s["name"] for s in a.symbols()}
    if names == {"add", "main"}:
        print("ok   document symbols: add, main")
    else:
        print(f"FAIL symbols {names}")
        failed += 1

    d = a.definition(4, 12)
    if d and d["line"] == 0 and d["character"] == 3:
        print("ok   go-to-definition resolves 'add' to its declaration")
    else:
        print(f"FAIL definition {d}")
        failed += 1

    h = a.hover(5, 4)
    if h and "builtin" in h["contents"]["value"]:
        print("ok   hover on 'print' shows builtin")
    else:
        print(f"FAIL hover {h}")
        failed += 1

    comps = {c["label"] for c in a.completions()}
    if {"fn", "print", "add", "fs", "match"} <= comps:
        print("ok   completion offers keywords, builtins, modules, user names")
    else:
        print(f"FAIL completions missing items: {comps}")
        failed += 1

    diags = Analyzer("fn main():\n    let y: int = \"hi\"\n").diagnostics()
    if diags and "mismatch" in diags[0]["message"] and diags[0]["range"]["start"]["line"] == 1:
        print("ok   type error surfaced as a diagnostic at the right line")
    else:
        print(f"FAIL type diagnostic {diags}")
        failed += 1

    fmt = a.formatted()
    if fmt and "fn add(a: int, b: int) -> int:" in fmt:
        print("ok   formatting returns canonical source")
    else:
        print(f"FAIL formatting {fmt!r}")
        failed += 1

    msgs = b""
    msgs += frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    msgs += frame({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    msgs += frame({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
        "textDocument": {"uri": "file:///t.ul", "text": "fn main():\n    let x = bad +\n"}}})
    msgs += frame({"jsonrpc": "2.0", "id": 2, "method": "textDocument/hover", "params": {
        "textDocument": {"uri": "file:///t.ul"}, "position": {"line": 0, "character": 0}}})
    msgs += frame({"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}})
    msgs += frame({"jsonrpc": "2.0", "method": "exit", "params": {}})

    proc = subprocess.run([sys.executable, os.path.join(SRC, "lsp.py")],
                          input=msgs, capture_output=True)
    frames = parse_frames(proc.stdout.decode())
    init = next((f for f in frames if f.get("id") == 1), None)
    diag_note = next((f for f in frames if f.get("method") == "textDocument/publishDiagnostics"), None)
    hover_kw = next((f for f in frames if f.get("id") == 2), None)

    if init and "capabilities" in init.get("result", {}):
        caps = init["result"]["capabilities"]
        needed = ["hoverProvider", "completionProvider", "definitionProvider",
                  "documentSymbolProvider", "documentFormattingProvider"]
        if all(caps.get(c) for c in needed):
            print("ok   server advertises all capabilities over JSON-RPC")
        else:
            print(f"FAIL capabilities {caps}")
            failed += 1
    else:
        print("FAIL no initialize result")
        failed += 1

    if diag_note and diag_note["params"]["diagnostics"]:
        print("ok   server pushed diagnostics for a broken document")
    else:
        print("FAIL no diagnostics pushed")
        failed += 1

    if hover_kw and hover_kw.get("result") and "keyword" in json.dumps(hover_kw["result"]):
        print("ok   hover over 'fn' identifies a keyword")
    else:
        print(f"FAIL keyword hover {hover_kw}")
        failed += 1

    total = 10
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
