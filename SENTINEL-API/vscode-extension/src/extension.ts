import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
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
            return new Promise<void>((resolve) => {
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

                exec(command, { cwd: rootPath }, (error, stdout, stderr) => {
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
                        } catch (e) {
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
                    } else {
                        vscode.window.showInformationMessage('AutoAPI Analysis Complete!');
                    }
                    resolve();
                });
            });
        });
    });

    context.subscriptions.push(disposable);
}

export function deactivate() { }
