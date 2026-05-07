import * as vscode from 'vscode';
import { execFile } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

type LiveLintDiagnostic = {
    code: string;
    severity: string;
    message: string;
    file: string;
    line: number;
    character: number;
    endpoint?: string;
    field?: string;
    remediation_patch?: Record<string, unknown>;
};

type LiveLintResult = {
    diagnostics?: LiveLintDiagnostic[];
    errors?: string[];
};

type QuickFixPayload = {
    specPath: string;
    remediationPatch: Record<string, unknown>;
};

const SUPPORTED_SOURCE_LANGUAGES = ['python', 'javascript', 'typescript'];
const DIAGNOSTIC_SOURCE = 'Sentinel API';
const EXTRA_FIELD_CODE = 'sentinel.extra_response_field';

const quickFixes = new Map<string, QuickFixPayload>();
const lintTimers = new Map<string, NodeJS.Timeout>();

let outputChannel: vscode.OutputChannel;
let diagnosticCollection: vscode.DiagnosticCollection;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('Sentinel API');
    diagnosticCollection = vscode.languages.createDiagnosticCollection('sentinel-api');
    context.subscriptions.push(outputChannel, diagnosticCollection);

    context.subscriptions.push(
        vscode.commands.registerCommand('autoapi.runAnalysis', runAnalysis),
        vscode.commands.registerCommand('sentinel.applyOpenApiQuickFix', applyOpenApiQuickFix),
        vscode.workspace.onDidSaveTextDocument((document) => {
            void runLiveLint(document);
        }),
        vscode.workspace.onDidChangeTextDocument((event) => {
            scheduleLiveLint(event.document);
        }),
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor) {
                void runLiveLint(editor.document);
            }
        }),
        vscode.languages.registerCodeActionsProvider(
            SUPPORTED_SOURCE_LANGUAGES,
            new SentinelCodeActionProvider(),
            { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] },
        ),
    );

    if (vscode.window.activeTextEditor) {
        void runLiveLint(vscode.window.activeTextEditor.document);
    }
}

export function deactivate() {
    diagnosticCollection?.dispose();
}

async function runAnalysis() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active file open.');
        return;
    }

    const document = editor.document;
    const fileName = document.fileName;

    if (!fileName.endsWith('.yaml') && !fileName.endsWith('.yml') && !fileName.endsWith('.json')) {
        vscode.window.showErrorMessage('Sentinel only supports .yaml, .yml, or .json spec files for full analysis.');
        return;
    }

    outputChannel.show();
    outputChannel.appendLine(`Starting analysis for: ${fileName}`);

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Running Sentinel API Analysis...',
            cancellable: false,
        },
        async () => {
            const rootPath = workspaceRoot();
            if (!rootPath) {
                vscode.window.showErrorMessage('Must be inside a workspace.');
                return;
            }

            const cliPath = path.join(rootPath, 'cli', 'main.py');
            const result = await runCli(rootPath, ['run-graph', fileName, '--ci']);
            outputChannel.appendLine('--- Analysis Complete ---');
            outputChannel.appendLine(result.stdout || result.stderr);

            if (result.exitCode === 0) {
                vscode.window.showInformationMessage('Sentinel API analysis complete.');
            } else {
                outputChannel.appendLine(`CLI path: ${cliPath}`);
                vscode.window.showErrorMessage('Sentinel API analysis failed. Check output channel.');
            }
        },
    );
}

function scheduleLiveLint(document: vscode.TextDocument) {
    if (!isSupportedSourceDocument(document) || !liveLintEnabled()) {
        return;
    }

    const key = document.uri.toString();
    const existing = lintTimers.get(key);
    if (existing) {
        clearTimeout(existing);
    }

    const delay = vscode.workspace.getConfiguration('sentinel').get<number>('liveLint.debounceMs', 650);
    const timer = setTimeout(() => {
        lintTimers.delete(key);
        void runLiveLint(document);
    }, delay);
    lintTimers.set(key, timer);
}

async function runLiveLint(document: vscode.TextDocument) {
    if (!isSupportedSourceDocument(document) || !liveLintEnabled()) {
        return;
    }

    const rootPath = workspaceRoot();
    if (!rootPath) {
        return;
    }

    const specPath = await findSpecPath(rootPath);
    if (!specPath) {
        diagnosticCollection.delete(document.uri);
        return;
    }

    const result = await runCli(rootPath, ['live-lint', document.fileName, '--spec', specPath, '--ci']);
    if (result.exitCode !== 0) {
        outputChannel.appendLine(result.stderr || result.stdout);
        return;
    }

    let parsed: LiveLintResult;
    try {
        parsed = JSON.parse(result.stdout) as LiveLintResult;
    } catch {
        outputChannel.appendLine(`Could not parse Sentinel live lint output: ${result.stdout}`);
        return;
    }

    if (parsed.errors?.length) {
        outputChannel.appendLine(parsed.errors.join('\n'));
    }

    const diagnostics = (parsed.diagnostics ?? []).map((item) => toVsCodeDiagnostic(document, item, specPath));
    diagnosticCollection.set(document.uri, diagnostics);
}

function toVsCodeDiagnostic(
    document: vscode.TextDocument,
    item: LiveLintDiagnostic,
    specPath: string,
): vscode.Diagnostic {
    const line = Math.max(0, (item.line ?? 1) - 1);
    const range = document.lineAt(Math.min(line, document.lineCount - 1)).range;
    const diagnostic = new vscode.Diagnostic(range, item.message, vscode.DiagnosticSeverity.Error);
    diagnostic.source = DIAGNOSTIC_SOURCE;
    diagnostic.code = item.code;

    if (item.remediation_patch) {
        quickFixes.set(diagnosticKey(document.uri, diagnostic), {
            specPath,
            remediationPatch: item.remediation_patch,
        });
    }

    return diagnostic;
}

class SentinelCodeActionProvider implements vscode.CodeActionProvider {
    provideCodeActions(
        document: vscode.TextDocument,
        _range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source !== DIAGNOSTIC_SOURCE || diagnostic.code !== EXTRA_FIELD_CODE) {
                continue;
            }

            const payload = quickFixes.get(diagnosticKey(document.uri, diagnostic));
            if (!payload) {
                continue;
            }

            const action = new vscode.CodeAction(
                'Update OpenAPI spec to match this code',
                vscode.CodeActionKind.QuickFix,
            );
            action.diagnostics = [diagnostic];
            action.isPreferred = true;
            action.command = {
                title: action.title,
                command: 'sentinel.applyOpenApiQuickFix',
                arguments: [document.uri, payload],
            };
            actions.push(action);
        }
        return actions;
    }
}

async function applyOpenApiQuickFix(documentUri: vscode.Uri, payload: QuickFixPayload) {
    const rootPath = workspaceRoot();
    if (!rootPath) {
        vscode.window.showErrorMessage('Must be inside a workspace.');
        return;
    }

    const patchJson = JSON.stringify(payload.remediationPatch);
    const result = await runCli(rootPath, [
        'apply-spec-fix',
        '--spec',
        payload.specPath,
        '--patch-json',
        patchJson,
        '--ci',
    ]);

    if (result.exitCode !== 0) {
        outputChannel.appendLine(result.stderr || result.stdout);
        vscode.window.showErrorMessage('Could not update OpenAPI spec. Check Sentinel output.');
        return;
    }

    vscode.window.showInformationMessage(`Updated OpenAPI spec: ${path.basename(payload.specPath)}`);
    const document = vscode.workspace.textDocuments.find((item) => item.uri.toString() === documentUri.toString());
    if (document) {
        await runLiveLint(document);
    }
}

function runCli(rootPath: string, args: string[]): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    const pythonPath = vscode.workspace.getConfiguration('sentinel').get<string>('pythonPath', 'python');
    const cliPath = path.join(rootPath, 'cli', 'main.py');

    return new Promise((resolve) => {
        execFile(pythonPath, [cliPath, ...args], { cwd: rootPath }, (error, stdout, stderr) => {
            resolve({
                stdout,
                stderr,
                exitCode: typeof error?.code === 'number' ? error.code : error ? 1 : 0,
            });
        });
    });
}

async function findSpecPath(rootPath: string): Promise<string | undefined> {
    const configured = vscode.workspace.getConfiguration('sentinel').get<string>('specPath', '');
    if (configured) {
        const absolute = path.isAbsolute(configured) ? configured : path.join(rootPath, configured);
        return fs.existsSync(absolute) ? absolute : undefined;
    }

    const candidates = ['openapi.yaml', 'openapi.yml', 'openapi.json', 'swagger.yaml', 'swagger.yml'];
    for (const candidate of candidates) {
        const absolute = path.join(rootPath, candidate);
        if (fs.existsSync(absolute)) {
            return absolute;
        }
    }

    const files = await vscode.workspace.findFiles('**/{openapi,swagger}.{yaml,yml,json}', '**/{node_modules,.next,dist,build,venv}/**', 1);
    return files[0]?.fsPath;
}

function workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function isSupportedSourceDocument(document: vscode.TextDocument): boolean {
    return document.uri.scheme === 'file' && SUPPORTED_SOURCE_LANGUAGES.includes(document.languageId);
}

function liveLintEnabled(): boolean {
    return vscode.workspace.getConfiguration('sentinel').get<boolean>('liveLint.enabled', true);
}

function diagnosticKey(uri: vscode.Uri, diagnostic: vscode.Diagnostic): string {
    return `${uri.toString()}:${diagnostic.range.start.line}:${diagnostic.message}`;
}
