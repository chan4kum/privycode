import * as path from 'path';

export type SymbolKind = 'function' | 'class' | 'interface' | 'type' | 'variable' | 'constant';

export interface SymbolEntry {
    name: string;
    kind: SymbolKind;
    filePath: string;
    startLine: number;
    endLine: number;
    signature: string;
    snippet: string;
}

export class SymbolGraph {
    private symbolMap: Map<string, SymbolEntry[]> = new Map();
    private fileMap: Map<string, SymbolEntry[]> = new Map();

    /**
     * Extracts and indexes language symbols from a file's content in-memory.
     */
    public indexFile(filePath: string, content: string): void {
        this.removeFile(filePath);

        const ext = path.extname(filePath).toLowerCase();
        const entries: SymbolEntry[] = [];

        if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) {
            entries.push(...this.extractTypeScriptSymbols(filePath, content));
        } else if (ext === '.py') {
            entries.push(...this.extractPythonSymbols(filePath, content));
        } else if (ext === '.go') {
            entries.push(...this.extractGoSymbols(filePath, content));
        } else if (ext === '.rs') {
            entries.push(...this.extractRustSymbols(filePath, content));
        }

        if (entries.length > 0) {
            this.fileMap.set(filePath, entries);
            for (const entry of entries) {
                const lower = entry.name.toLowerCase();
                const list = this.symbolMap.get(lower) || [];
                list.push(entry);
                this.symbolMap.set(lower, list);
            }
        }
    }

    /**
     * Clears indexed symbols for a specific file when deleted or modified.
     */
    public removeFile(filePath: string): void {
        const existing = this.fileMap.get(filePath);
        if (!existing) return;

        this.fileMap.delete(filePath);
        for (const entry of existing) {
            const lower = entry.name.toLowerCase();
            const list = this.symbolMap.get(lower);
            if (list) {
                const filtered = list.filter(e => e.filePath !== filePath);
                if (filtered.length > 0) {
                    this.symbolMap.set(lower, filtered);
                } else {
                    this.symbolMap.delete(lower);
                }
            }
        }
    }

    /**
     * Finds symbols matching a query prefix or keyword.
     */
    public findSymbols(query: string, limit: number = 20): SymbolEntry[] {
        const q = query.toLowerCase().trim();
        if (!q) return this.getAllSymbols().slice(0, limit);

        const results: SymbolEntry[] = [];
        for (const [name, entries] of this.symbolMap.entries()) {
            if (name.includes(q)) {
                results.push(...entries);
                if (results.length >= limit) break;
            }
        }
        return results.slice(0, limit);
    }

    /**
     * Resolves the primary definition for a given symbol name.
     */
    public resolveDefinition(symbolName: string): SymbolEntry | undefined {
        const entries = this.symbolMap.get(symbolName.toLowerCase().trim());
        return entries && entries.length > 0 ? entries[0] : undefined;
    }

    /**
     * Returns all indexed symbols.
     */
    public getAllSymbols(): SymbolEntry[] {
        const all: SymbolEntry[] = [];
        for (const entries of this.symbolMap.values()) {
            all.push(...entries);
        }
        return all;
    }

    /* ---------------- Parsing Heuristics ---------------- */

    private extractTypeScriptSymbols(filePath: string, content: string): SymbolEntry[] {
        const lines = content.split('\n');
        const entries: SymbolEntry[] = [];

        // Match classes, interfaces, types, functions, and arrow constants
        const regexes = [
            { re: /^(?:export\s+)?class\s+([A-Za-z0-9_$]+)/, kind: 'class' as SymbolKind },
            { re: /^(?:export\s+)?interface\s+([A-Za-z0-9_$]+)/, kind: 'interface' as SymbolKind },
            { re: /^(?:export\s+)?type\s+([A-Za-z0-9_$]+)/, kind: 'type' as SymbolKind },
            { re: /^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)/, kind: 'function' as SymbolKind },
            { re: /^(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(/, kind: 'function' as SymbolKind },
        ];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            for (const { re, kind } of regexes) {
                const match = line.match(re);
                if (match && match[1]) {
                    const snippet = lines.slice(i, Math.min(lines.length, i + 15)).join('\n');
                    entries.push({
                        name: match[1],
                        kind,
                        filePath,
                        startLine: i + 1,
                        endLine: Math.min(lines.length, i + 15),
                        signature: line,
                        snippet,
                    });
                    break;
                }
            }
        }
        return entries;
    }

    private extractPythonSymbols(filePath: string, content: string): SymbolEntry[] {
        const lines = content.split('\n');
        const entries: SymbolEntry[] = [];

        const classRe = /^(?:class\s+)([A-Za-z0-9_]+)/;
        const funcRe = /^(?:async\s+)?def\s+([A-Za-z0-9_]+)/;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();

            const classMatch = trimmed.match(classRe);
            if (classMatch && classMatch[1]) {
                const snippet = lines.slice(i, Math.min(lines.length, i + 20)).join('\n');
                entries.push({
                    name: classMatch[1],
                    kind: 'class',
                    filePath,
                    startLine: i + 1,
                    endLine: Math.min(lines.length, i + 20),
                    signature: trimmed,
                    snippet,
                });
                continue;
            }

            const funcMatch = trimmed.match(funcRe);
            if (funcMatch && funcMatch[1]) {
                const snippet = lines.slice(i, Math.min(lines.length, i + 15)).join('\n');
                entries.push({
                    name: funcMatch[1],
                    kind: 'function',
                    filePath,
                    startLine: i + 1,
                    endLine: Math.min(lines.length, i + 15),
                    signature: trimmed,
                    snippet,
                });
            }
        }
        return entries;
    }

    private extractGoSymbols(filePath: string, content: string): SymbolEntry[] {
        const lines = content.split('\n');
        const entries: SymbolEntry[] = [];

        const funcRe = /^func\s+(?:\([A-Za-z0-9_*\s]+\)\s+)?([A-Za-z0-9_]+)/;
        const typeRe = /^type\s+([A-Za-z0-9_]+)\s+(struct|interface)/;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const typeMatch = line.match(typeRe);
            if (typeMatch && typeMatch[1]) {
                entries.push({
                    name: typeMatch[1],
                    kind: typeMatch[2] === 'interface' ? 'interface' : 'class',
                    filePath,
                    startLine: i + 1,
                    endLine: Math.min(lines.length, i + 20),
                    signature: line,
                    snippet: lines.slice(i, Math.min(lines.length, i + 20)).join('\n'),
                });
                continue;
            }

            const funcMatch = line.match(funcRe);
            if (funcMatch && funcMatch[1]) {
                entries.push({
                    name: funcMatch[1],
                    kind: 'function',
                    filePath,
                    startLine: i + 1,
                    endLine: Math.min(lines.length, i + 15),
                    signature: line,
                    snippet: lines.slice(i, Math.min(lines.length, i + 15)).join('\n'),
                });
            }
        }
        return entries;
    }

    private extractRustSymbols(filePath: string, content: string): SymbolEntry[] {
        const lines = content.split('\n');
        const entries: SymbolEntry[] = [];

        const re = /^(?:pub\s+)?(fn|struct|enum|trait|type)\s+([A-Za-z0-9_]+)/;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const match = line.match(re);
            if (match && match[2]) {
                const kindStr = match[1];
                let kind: SymbolKind = 'function';
                if (['struct', 'enum'].includes(kindStr)) kind = 'class';
                else if (kindStr === 'trait') kind = 'interface';
                else if (kindStr === 'type') kind = 'type';

                entries.push({
                    name: match[2],
                    kind,
                    filePath,
                    startLine: i + 1,
                    endLine: Math.min(lines.length, i + 20),
                    signature: line,
                    snippet: lines.slice(i, Math.min(lines.length, i + 20)).join('\n'),
                });
            }
        }
        return entries;
    }
}
