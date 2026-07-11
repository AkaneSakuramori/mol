const { workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const config = workspace.getConfiguration("ulang");
  const command = config.get("serverCommand", ["python3", "src/ulang.py", "lsp"]);

  const serverOptions = {
    command: command[0],
    args: command.slice(1),
    transport: TransportKind.stdio,
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "ulang" }],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.ul"),
    },
  };

  client = new LanguageClient(
    "ulang",
    "Ulang Language Server",
    serverOptions,
    clientOptions
  );

  client.start();
}

function deactivate() {
  if (!client) {
    return undefined;
  }
  return client.stop();
}

module.exports = { activate, deactivate };
