import sys
import json

from lsp_analysis import Analyzer


class LSPServer:
    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin or sys.stdin.buffer
        self.stdout = stdout or sys.stdout.buffer
        self.documents = {}
        self.shutdown_requested = False
        self.running = True

    def read_message(self):
        headers = {}
        while True:
            line = self.stdin.readline()
            if not line:
                return None
            line = line.decode("ascii").rstrip("\r\n")
            if line == "":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        length = int(headers.get("content-length", 0))
        if length == 0:
            return None
        body = self.stdin.read(length)
        return json.loads(body.decode("utf-8"))

    def write_message(self, message):
        data = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
        self.stdout.write(header)
        self.stdout.write(data)
        self.stdout.flush()

    def respond(self, request_id, result):
        self.write_message({"jsonrpc": "2.0", "id": request_id, "result": result})

    def respond_error(self, request_id, code, message):
        self.write_message({
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message},
        })

    def notify(self, method, params):
        self.write_message({"jsonrpc": "2.0", "method": method, "params": params})

    def serve(self):
        while self.running:
            message = self.read_message()
            if message is None:
                break
            self.handle(message)

    def handle(self, message):
        method = message.get("method")
        request_id = message.get("id")
        if method is None:
            return
        handler = getattr(self, "on_" + method.replace("/", "_").replace("$", "dollar"), None)
        if handler is None:
            if request_id is not None:
                self.respond(request_id, None)
            return
        result = handler(message.get("params") or {}, request_id)
        if request_id is not None and result is not _NO_RESPONSE:
            self.respond(request_id, result)

    def on_initialize(self, params, request_id):
        return {
            "capabilities": {
                "textDocumentSync": 1,
                "hoverProvider": True,
                "completionProvider": {"triggerCharacters": ["."]},
                "definitionProvider": True,
                "documentSymbolProvider": True,
                "documentFormattingProvider": True,
            },
            "serverInfo": {"name": "ulang-lsp", "version": "1.5.0"},
        }

    def on_initialized(self, params, request_id):
        return _NO_RESPONSE

    def on_shutdown(self, params, request_id):
        self.shutdown_requested = True
        return None

    def on_exit(self, params, request_id):
        self.running = False
        return _NO_RESPONSE

    def on_textDocument_didOpen(self, params, request_id):
        doc = params["textDocument"]
        uri = doc["uri"]
        self.documents[uri] = doc["text"]
        self.publish_diagnostics(uri)
        return _NO_RESPONSE

    def on_textDocument_didChange(self, params, request_id):
        uri = params["textDocument"]["uri"]
        changes = params.get("contentChanges", [])
        if changes:
            self.documents[uri] = changes[-1]["text"]
        self.publish_diagnostics(uri)
        return _NO_RESPONSE

    def on_textDocument_didClose(self, params, request_id):
        uri = params["textDocument"]["uri"]
        self.documents.pop(uri, None)
        self.notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})
        return _NO_RESPONSE

    def on_textDocument_didSave(self, params, request_id):
        uri = params["textDocument"]["uri"]
        self.publish_diagnostics(uri)
        return _NO_RESPONSE

    def on_textDocument_hover(self, params, request_id):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        text = self.documents.get(uri)
        if text is None:
            return None
        return Analyzer(text).hover(pos["line"], pos["character"])

    def on_textDocument_completion(self, params, request_id):
        uri = params["textDocument"]["uri"]
        text = self.documents.get(uri, "")
        analyzer = Analyzer(text)
        return {"isIncomplete": False, "items": analyzer.completions()}

    def on_textDocument_definition(self, params, request_id):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        text = self.documents.get(uri)
        if text is None:
            return None
        loc = Analyzer(text).definition(pos["line"], pos["character"])
        if loc is None:
            return None
        return {
            "uri": uri,
            "range": {
                "start": {"line": loc["line"], "character": loc["character"]},
                "end": {"line": loc["line"], "character": loc["character"] + loc["length"]},
            },
        }

    def on_textDocument_documentSymbol(self, params, request_id):
        uri = params["textDocument"]["uri"]
        text = self.documents.get(uri, "")
        return Analyzer(text).symbols()

    def on_textDocument_formatting(self, params, request_id):
        uri = params["textDocument"]["uri"]
        text = self.documents.get(uri)
        if text is None:
            return None
        formatted = Analyzer(text).formatted()
        if formatted is None:
            return None
        lines = text.count("\n") + 1
        return [{
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": lines + 1, "character": 0},
            },
            "newText": formatted,
        }]

    def publish_diagnostics(self, uri):
        text = self.documents.get(uri, "")
        diagnostics = Analyzer(text).diagnostics()
        self.notify("textDocument/publishDiagnostics", {
            "uri": uri, "diagnostics": diagnostics,
        })


_NO_RESPONSE = object()


def main():
    LSPServer().serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
