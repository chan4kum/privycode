import * as vscode from 'vscode';
import * as path from 'path';
import { ContextFileItem } from './apiClient';
import { SymbolGraph, SymbolEntry } from './symbolGraph';

export interface ExtractedContext {
    cleanedPrompt: string;
    contextFiles: ContextFileItem[];
    attachedSymbols: SymbolEntry[];
}

export class ContextEngine {
    constructor(private symbolGraph: SymbolGraph) {}

    /**
     * Parses @file, @symbol, and @folder mentions from prompt and attaches context.
     */
    public async buildContext(prompt: string, maxTokens: number = 3500): Promise<ExtractedContext> {
        const contextFiles: ContextFileItem[] = [];
        const attachedSymbols: SymbolEntry[] = [];
        let cleanedPrompt = prompt;

        // 1. Match @symbol <name>
        const symbolRegex = /@symbol\s+([A-Za-z0-9_$]+)/g;
        let match: RegExpExecArray | null;
        while ((match = symbolRegex.exec(prompt)) !== null) {
            const symName = match[1];
            const entry = this.symbolGraph.resolveDefinition(symName);
            if (entry) {
                attachedSymbols.push(entry);
                contextFiles.push({
                    path: entry.filePath,
                    content: entry.snippet,
                    selection_range: {
                        start_line: entry.startLine,
                        end_line: entry.endLine,
                    },
                });
            }
        }
        cleanedPrompt = cleanedPrompt.replace(symbolRegex, '').trim();

        // 2. Match @file <path>
        const fileRegex = /@file\s+([^\s]+)/g;
        while ((match = fileRegex.exec(prompt)) !== null) {
            const targetPath = match[1];
            const resolvedDoc = await this.readWorkspaceFile(targetPath);
            if (resolvedDoc) {
                contextFiles.push({
                    path: targetPath,
                    content: resolvedDoc.slice(0, 10000), // Cap length
                });
            }
        }
        cleanedPrompt = cleanedPrompt.replace(fileRegex, '').trim();

        // 3. Fallback to active editor context if no specific mentions were provided
        if (contextFiles.length === 0) {
            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor) {
                const doc = activeEditor.document;
                const selection = activeEditor.selection;
                const activeSnippet = !selection.isEmpty
                    ? doc.getText(selection)
                    : doc.getText().slice(0, 6000);

                contextFiles.push({
                    path: vscode.workspace.asRelativePath(doc.uri),
                    content: activeSnippet,
                    selection_range: !selection.isEmpty
                        ? { start_line: selection.start.line + 1, end_line: selection.end.line + 1 }
                        : undefined,
                });
            }
        }

        return {
            cleanedPrompt: cleanedPrompt || prompt,
            contextFiles: this.trimToTokenBudget(contextFiles, maxTokens),
            attachedSymbols,
        };
    }

    private async readWorkspaceFile(relativePath: string): Promise<string | undefined> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) return undefined;

        for (const folder of workspaceFolders) {
            try {
                const uri = vscode.Uri.joinPath(folder.uri, relativePath);
                const bytes = await vscode.workspace.fs.readFile(uri);
                return Buffer.from(bytes).toString('utf-8');
            } catch {
                // Try fuzzy file match
            }
        }
        return undefined;
    }

    private trimToTokenBudget(files: ContextFileItem[], maxTokens: number): ContextFileItem[] {
        const charBudget = maxTokens * 4;
        let currentChars = 0;
        const result: ContextFileItem[] = [];

        for (const file of files) {
            if (currentChars + file.content.length <= charBudget) {
                result.push(file);
                currentChars += file.content.length;
            } else {
                const remaining = Math.max(0, charBudget - currentChars);
                if (remaining > 200) {
                    result.push({
                        ...file,
                        content: file.content.slice(0, remaining) + '\n# ... [context truncated for length]',
                    });
                }
                break;
            }
        }
        return result;
    }
}
