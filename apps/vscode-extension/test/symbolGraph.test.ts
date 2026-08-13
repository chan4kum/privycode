import * as assert from 'assert';
import { SymbolGraph } from '../src/symbolGraph';

function runSymbolGraphTests() {
    console.log("=== Starting SymbolGraph & AST Indexer Unit Tests ===");
    const graph = new SymbolGraph();

    // 1. Python extraction
    const pyCode = `
import os
import sys

class ModelRouter:
    def __init__(self):
        self.routes = {}

    async def resolve_route(self, model: str):
        return "http://localhost:8001"

def standalone_helper(x: int) -> int:
    return x * 2
`;
    graph.indexFile("src/router.py", pyCode);

    const pySymbols = graph.findSymbols("ModelRouter");
    assert.strictEqual(pySymbols.length, 1, "ModelRouter class should be indexed");
    assert.strictEqual(pySymbols[0].kind, "class");

    const helperSymbol = graph.resolveDefinition("standalone_helper");
    assert.ok(helperSymbol, "standalone_helper function should be resolved");
    assert.strictEqual(helperSymbol?.kind, "function");

    // 2. TypeScript extraction
    const tsCode = `
export interface FileContext {
    path: string;
    content: string;
}

export class SovereignForgeClient {
    public async checkHealth(): Promise<boolean> {
        return true;
    }
}

export const executePipeline = async () => {
    return true;
};
`;
    graph.indexFile("src/apiClient.ts", tsCode);

    const tsInterface = graph.resolveDefinition("FileContext");
    assert.ok(tsInterface, "FileContext interface should be resolved");
    assert.strictEqual(tsInterface?.kind, "interface");

    const tsClass = graph.resolveDefinition("SovereignForgeClient");
    assert.ok(tsClass, "SovereignForgeClient class should be resolved");
    assert.strictEqual(tsClass?.kind, "class");

    // 3. Remove file
    graph.removeFile("src/router.py");
    assert.strictEqual(graph.resolveDefinition("ModelRouter"), undefined, "ModelRouter should be removed after file deletion");

    console.log("=== ALL SYMBOLGRAPH TESTS PASSED (3/3) ===");
}

runSymbolGraphTests();
