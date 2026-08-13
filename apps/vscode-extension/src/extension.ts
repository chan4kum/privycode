import * as vscode from "vscode";
import { apiClient } from "./apiClient";
import { PrivyCodeChatViewProvider } from "./chatViewProvider";
import { handleEditSelectionCommand } from "./editProvider";
import { PrivyCodeInlineCompletionProvider } from "./inlineCompletion";
import { SymbolGraph } from "./symbolGraph";

let statusBarItem: vscode.StatusBarItem;
const symbolGraph = new SymbolGraph();

export async function activate(context: vscode.ExtensionContext) {
  console.log("PrivyCode Extension is activating with in-memory SymbolGraph...");

  // 1. Status Bar Item setup
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = "privycode.checkConnection";
  statusBarItem.text = "$(sync~spin) PrivyCode: Connecting...";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Initial status bar check
  await updateConnectionStatus();

  // 2. Index open workspace documents into SymbolGraph
  indexOpenWorkspaceDocuments();

  // 3. Register Inline Completion Provider (Ghost text FIM)
  const inlineProvider = new PrivyCodeInlineCompletionProvider();
  const inlineDisposable = vscode.languages.registerInlineCompletionItemProvider(
    { pattern: "**" },
    inlineProvider
  );
  context.subscriptions.push(inlineDisposable);

  // 4. Register Sidebar Chat Webview with SymbolGraph
  const chatProvider = new PrivyCodeChatViewProvider(symbolGraph);
  const chatDisposable = vscode.window.registerWebviewViewProvider(
    PrivyCodeChatViewProvider.viewType,
    chatProvider
  );
  context.subscriptions.push(chatDisposable);

  // 5. Register Edit Selection Command (Cmd+I)
  const editDisposable = vscode.commands.registerCommand(
    "privycode.editSelection",
    handleEditSelectionCommand
  );
  context.subscriptions.push(editDisposable);

  // 6. Register Connection Check Command
  const checkDisposable = vscode.commands.registerCommand(
    "privycode.checkConnection",
    async () => {
      await updateConnectionStatus();
    }
  );
  context.subscriptions.push(checkDisposable);

  // 7. Workspace File Event Listeners for Live In-Memory Symbol Indexing
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      symbolGraph.indexFile(vscode.workspace.asRelativePath(doc.uri), doc.getText());
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidDeleteFiles((e) => {
      for (const uri of e.files) {
        symbolGraph.removeFile(vscode.workspace.asRelativePath(uri));
      }
    })
  );

  // 8. Listen for configuration changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (e) => {
      if (e.affectsConfiguration("privycode")) {
        await updateConnectionStatus();
      }
    })
  );

  // 9. Periodic health check every 60 seconds
  const interval = setInterval(async () => {
    await updateConnectionStatus();
  }, 60000);

  context.subscriptions.push({
    dispose: () => clearInterval(interval),
  });

  console.log("PrivyCode Extension successfully activated with AST SymbolGraph!");
}

async function indexOpenWorkspaceDocuments() {
  try {
    for (const doc of vscode.workspace.textDocuments) {
      if (!doc.isUntitled) {
        symbolGraph.indexFile(vscode.workspace.asRelativePath(doc.uri), doc.getText());
      }
    }
    // Scan up to 50 workspace files
    const files = await vscode.workspace.findFiles("**/*.{ts,js,py,go,rs}", "**/node_modules/**", 50);
    for (const file of files) {
      try {
        const bytes = await vscode.workspace.fs.readFile(file);
        const content = Buffer.from(bytes).toString("utf-8");
        symbolGraph.indexFile(vscode.workspace.asRelativePath(file), content);
      } catch {
        // Skip unreadable files
      }
    }
  } catch (err) {
    console.warn("Workspace indexing standby:", err);
  }
}

async function updateConnectionStatus() {
  const status = await apiClient.checkHealth();
  if (status.connected) {
    statusBarItem.text = `$(lock) PrivyCode: Connected`;
    statusBarItem.tooltip = `Connected to SovereignForge Gateway as ${status.user || "Developer"}`;
    statusBarItem.backgroundColor = undefined;
  } else {
    statusBarItem.text = `$(warning) PrivyCode: Disconnected`;
    statusBarItem.tooltip = `Cannot reach SovereignForge Gateway: ${status.error}. Click to retry.`;
    statusBarItem.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
  }
}

export function deactivate() {
  console.log("PrivyCode Extension deactivated.");
}
