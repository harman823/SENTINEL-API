"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
function activate(context) {
    const outputChannel = vscode.window.createOutputChannel('AutoAPI Intelligence');
    context.subscriptions.push(outputChannel);
    let disposable = vscode.commands.registerCommand('autoapi.runAnalysis', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active file open.');
            return;
        }
        const document = editor.document;
        const fileName = document.fileName;
        if (!fileName.endsWith('.yaml') && !fileName.endsWith('.yml') && !fileName.endsWith('.json')) {
            vscode.window.showErrorMessage('AutoAPI only supports .yaml, .yml, or .json files.');
            return;
        }
        outputChannel.show();
        outputChannel.appendLine(`Starting analysis for: ${fileName}`);
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Running AutoAPI Intelligence Analysis...",
            cancellable: false
        }, async (progress) => {
            return new Promise((resolve) => {
                // Find root workspace path
                const workspaceFolders = vscode.workspace.workspaceFolders;
                if (!workspaceFolders) {
                    vscode.window.showErrorMessage('Must be inside a workspace (AutoAPI project root).');
                    resolve();
                    return;
                }
                const rootPath = workspaceFolders[0].uri.fsPath;
                const cliPath = path.join(rootPath, 'cli', 'main.py');
                // Run the CLI
                const command = `python "${cliPath}" run-graph "${fileName}" --ci`;
                outputChannel.appendLine(`> Executing: ${command}`);
                (0, child_process_1.exec)(command, { cwd: rootPath }, (error, stdout, stderr) => {
                    if (stdout) {
                        try {
                            const result = JSON.parse(stdout);
                            outputChannel.appendLine('--- Analysis Complete ---');
                            if (result.summary) {
                                outputChannel.appendLine(`Total Tests: ${result.summary.total_tests}`);
                                outputChannel.appendLine(`Pass Rate: ${result.summary.pass_rate}%`);
                                outputChannel.appendLine(`Validation Passed: ${result.summary.validation_passed}`);
                                outputChannel.appendLine(`Validation Failed: ${result.summary.validation_failed}`);
                            }
                            if (result.errors && result.errors.length > 0) {
                                outputChannel.appendLine(`\nErrors:\n${result.errors.join('\\n')}`);
                            }
                        }
                        catch (e) {
                            // If not JSON, just dump output
                            outputChannel.appendLine(stdout);
                        }
                    }
                    if (stderr) {
                        outputChannel.appendLine(`[STDERR]: ${stderr}`);
                    }
                    if (error) {
                        outputChannel.appendLine(`Execution failed: ${error.message}`);
                        vscode.window.showErrorMessage('AutoAPI Analysis Failed. Check output channel.');
                    }
                    else {
                        vscode.window.showInformationMessage('AutoAPI Analysis Complete!');
                    }
                    resolve();
                });
            });
        });
    });
    context.subscriptions.push(disposable);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map