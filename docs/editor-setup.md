# Editor Setup

Ulang ships a Language Server that gives editors a first-class experience:
diagnostics, hover, completion, go-to-definition, document symbols, and formatting.

The server speaks the [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
over stdin/stdout. Any LSP-capable editor can use it.

## The language server

Start it with:

```sh
ulang lsp
```

It reads LSP JSON-RPC messages on stdin and writes responses on stdout. You normally do
not run this by hand; your editor launches it.

### Features

| Feature | LSP method |
|---------|------------|
| Diagnostics (errors as you type) | `textDocument/publishDiagnostics` |
| Hover information | `textDocument/hover` |
| Completion | `textDocument/completion` |
| Go to definition | `textDocument/definition` |
| Document symbols (outline) | `textDocument/documentSymbol` |
| Formatting | `textDocument/formatting` |

## VS Code

A ready-to-use extension is in [`editors/vscode`](../editors/vscode).

1. Install its dependencies and open it:

   ```sh
   cd editors/vscode
   npm install
   ```

2. Point the extension at your checkout. In VS Code settings (`ulang.serverCommand`),
   set the absolute path to `src/ulang.py`:

   ```json
   "ulang.serverCommand": ["python3", "/absolute/path/to/mol/src/ulang.py", "lsp"]
   ```

3. Press F5 in the extension folder to launch an Extension Development Host, then open a
   `.ul` file. You get syntax highlighting, live diagnostics, hover, completion, symbols,
   and formatting.

The extension also provides a TextMate grammar for syntax highlighting, so keywords,
strings, numbers, and types are colored even before the server connects.

## Neovim

With the built-in LSP client (`nvim` 0.8+):

```lua
vim.filetype.add({ extension = { ul = "ulang" } })

vim.api.nvim_create_autocmd("FileType", {
  pattern = "ulang",
  callback = function(args)
    vim.lsp.start({
      name = "ulang",
      cmd = { "python3", "/absolute/path/to/mol/src/ulang.py", "lsp" },
      root_dir = vim.fs.dirname(vim.fs.find({ "ulang.toml", ".git" }, { upward = true })[1]),
    })
  end,
})
```

Then `gd` (go to definition), `K` (hover), and `<C-x><C-o>` (completion) work in `.ul`
files, with diagnostics shown inline.

## Other editors

Any editor with an LSP client works. Configure it to:

- Launch `python3 /path/to/mol/src/ulang.py lsp`.
- Associate the `.ul` extension with a language id of `ulang`.
- Use stdio transport.

## Troubleshooting

- **No diagnostics appear.** Confirm the server starts: `echo '' | ulang lsp` should not
  error. Check the editor's LSP log for the launch command.
- **Server not found.** Use an absolute path to `src/ulang.py` in the server command.
- **`llvmlite` errors.** The language server itself does not need `llvmlite`; only
  `ulang build` and `ulang jit` do.
