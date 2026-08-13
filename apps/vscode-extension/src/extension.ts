import * as vscode from "vscode";
import { apiClient } from "./apiClient";
import { PrivyCodeChatViewProvider } from "./chatViewProvider";
import { handleEditSelectionCommand } from "./editProvider";
import { PrivyCodeInlineCompletionProvider } from "./inlineCompletion";

let statusBarItem: vscode.StatusBarItem;

export async function activate(context: vscode.ExtensionContext) {
  console.log("PrivyCode Extension is activating...");

  // 1. Status Bar Item setup
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = "privycode.checkConnection";
  statusBarItem.text = "$(sync~spin) PrivyCode: Connecting...";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Initial status bar check
  await updateConnectionStatus();

  // 2. Register Inline Completion Provider (Ghost text FIM)
  const inlineProvider = new PrivyCodeInlineCompletionProvider();
  const inlineDisposable = vscode.languages.registerInlineCompletionItemProvider(
    { pattern: "**" },
    inlineProvider
  );
  context.subscriptions.push(inlineDisposable);

  // 3. Register Sidebar Chat Webview
  const chatProvider = new PrivyCodeChatViewProvider();
  const chatDisposable = vscode.window.registerWebviewViewProvider(
    PrivyCodeChatViewProvider.viewType,
    chatProvider
  );
  context.subscriptions.push(chatDisposable);

  // 4. Register Edit Selection Command (Cmd+I)
  const editDisposable = vscode.commands.registerCommand(
    "privycode.editSelection",
    handleEditSelectionCommand
  );
  context.subscriptions.push(editDisposable);

  // 5. Register Connection Check Command
  const checkDisposable = vscode.commands.registerCommand(
    "privycode.checkConnection",
    async () => {
      await updateConnectionStatus();
    }
  );
  context.subscriptions.push(checkDisposable);

  // 6. Listen for configuration changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (e) => {
      if (e.affectsConfiguration("privycode")) {
        await updateConnectionStatus();
      }
    })
  );

  // 7. Periodic health check every 60 seconds
  const interval = setInterval(async () => {
    await updateConnectionStatus();
  }, 60000);

  context.subscriptions.push({
    dispose: () => clearInterval(interval),
  });

  console.log("PrivyCode Extension successfully activated!");
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
