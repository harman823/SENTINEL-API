# Sentinel API for Antigravity

Antigravity is VS Code-compatible for extension APIs, so Sentinel ships one
extension package for both VS Code and Antigravity.

## Install from a VSIX

1. Build the extension from `vscode-extension`:

   ```powershell
   npm install
   npm run compile
   ```

2. Package the folder with your VSIX toolchain, then install it in Antigravity:

   ```powershell
   antigravity --install-extension .\autoapi-vscode-0.1.0.vsix
   ```

## Settings

The Antigravity extension uses the same settings as VS Code:

- `sentinel.specPath`: OpenAPI YAML/JSON spec path.
- `sentinel.pythonPath`: Python executable for the Sentinel CLI.
- `sentinel.liveLint.enabled`: Enables live diagnostics.
- `sentinel.liveLint.debounceMs`: Change debounce delay.

## Features

- Live API contract diagnostics while editing backend handlers.
- Red underlines via `vscode.Diagnostic`.
- Quick Fix: "Update OpenAPI spec to match this code".
- Full Sentinel graph analysis command for OpenAPI files.
