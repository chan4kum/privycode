import * as vscode from "vscode";
import { apiClient, ChatMessage, FileContext } from "./apiClient";

export class PrivyCodeChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "privycode.chatView";
  private _view?: vscode.WebviewView;
  private conversationHistory: ChatMessage[] = [];
  private currentAbortController?: AbortController;

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
    };

    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (data) => {
      switch (data.type) {
        case "sendMessage":
          await this.handleUserMessage(data.text);
          break;
        case "clearChat":
          this.conversationHistory = [];
          this.postMessageToWebview({ type: "chatCleared" });
          break;
        case "applyCode":
          await this.applyCodeToActiveEditor(data.code);
          break;
      }
    });
  }

  private async handleUserMessage(userText: string) {
    if (!userText.trim()) return;

    this.conversationHistory.push({ role: "user", content: userText });
    this.postMessageToWebview({ type: "addUserMessage", text: userText });

    // 1. Gather active IDE context (file & selection)
    const contextFiles: FileContext[] = [];
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      const doc = editor.document;
      const selection = editor.selection;
      contextFiles.push({
        path: vscode.workspace.asRelativePath(doc.uri),
        content: doc.getText(),
        selection_range: selection.isEmpty
          ? undefined
          : { start_line: selection.start.line + 1, end_line: selection.end.line + 1 },
      });
    }

    const config = vscode.workspace.getConfiguration("privycode");
    const model = config.get<string>("model", "mock-qwen-32b");

    this.currentAbortController = new AbortController();
    this.postMessageToWebview({ type: "startAssistantStream" });

    let assistantAccumulatedText = "";

    await apiClient.streamChat(
      {
        model,
        mode: "balanced",
        messages: this.conversationHistory,
        context_files: contextFiles,
      },
      (chunk: string) => {
        assistantAccumulatedText += chunk;
        this.postMessageToWebview({ type: "appendChunk", chunk });
      },
      () => {
        this.conversationHistory.push({ role: "assistant", content: assistantAccumulatedText });
        this.postMessageToWebview({ type: "endAssistantStream" });
      },
      (errorMsg: string) => {
        this.postMessageToWebview({ type: "streamError", error: errorMsg });
      },
      this.currentAbortController.signal
    );
  }

  private async applyCodeToActiveEditor(code: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("No active editor to apply code.");
      return;
    }

    const selection = editor.selection;
    await editor.edit((editBuilder) => {
      if (selection.isEmpty) {
        editBuilder.insert(selection.active, code);
      } else {
        editBuilder.replace(selection, code);
      }
    });
    vscode.window.showInformationMessage("Applied code changes to editor.");
  }

  private postMessageToWebview(msg: any) {
    this._view?.webview.postMessage(msg);
  }

  private getHtmlForWebview(webview: vscode.Webview): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PrivyCode Chat</title>
  <style>
    body { font-family: var(--vscode-font-family); padding: 12px; color: var(--vscode-foreground); background-color: var(--vscode-editor-background); }
    .chat-container { display: flex; flex-direction: column; height: 95vh; }
    .messages-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-bottom: 8px; }
    .message { padding: 8px 12px; border-radius: 6px; max-width: 90%; word-break: break-word; }
    .user-msg { align-self: flex-end; background-color: var(--vscode-button-background); color: var(--vscode-button-foreground); }
    .assistant-msg { align-self: flex-start; background-color: var(--vscode-editor-inactiveSelectionBackground); border: 1px solid var(--vscode-widget-border); }
    .input-area { display: flex; gap: 6px; padding-top: 8px; border-top: 1px solid var(--vscode-widget-border); }
    textarea { flex: 1; resize: none; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; padding: 6px; }
    button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; }
    button:hover { background: var(--vscode-button-hoverBackground); }
    pre { background: var(--vscode-textCodeBlock-background); padding: 8px; border-radius: 4px; overflow-x: auto; position: relative; }
    .apply-btn { position: absolute; top: 4px; right: 4px; font-size: 10px; padding: 2px 6px; }
  </style>
</head>
<body>
  <div class="chat-container">
    <div id="messages" class="messages-list">
      <div class="message assistant-msg">👋 Hi! I am PrivyCode. Ask me questions about your code with zero data retention.</div>
    </div>
    <div class="input-area">
      <textarea id="promptInput" rows="2" placeholder="Ask PrivyCode (e.g. refactor this function)..."></textarea>
      <button id="sendBtn">Send</button>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const messagesEl = document.getElementById("messages");
    const inputEl = document.getElementById("promptInput");
    const sendBtn = document.getElementById("sendBtn");
    let currentAssistantEl = null;

    sendBtn.addEventListener("click", () => {
      const text = inputEl.value;
      if (!text.trim()) return;
      vscode.postMessage({ type: "sendMessage", text });
      inputEl.value = "";
    });

    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
      }
    });

    window.addEventListener("message", (event) => {
      const msg = event.data;
      switch (msg.type) {
        case "addUserMessage":
          const uDiv = document.createElement("div");
          uDiv.className = "message user-msg";
          uDiv.textContent = msg.text;
          messagesEl.appendChild(uDiv);
          messagesEl.scrollTop = messagesEl.scrollHeight;
          break;
        case "startAssistantStream":
          currentAssistantEl = document.createElement("div");
          currentAssistantEl.className = "message assistant-msg";
          messagesEl.appendChild(currentAssistantEl);
          break;
        case "appendChunk":
          if (currentAssistantEl) {
            currentAssistantEl.textContent += msg.chunk;
            messagesEl.scrollTop = messagesEl.scrollHeight;
          }
          break;
        case "endAssistantStream":
          currentAssistantEl = null;
          break;
        case "streamError":
          if (currentAssistantEl) {
            currentAssistantEl.textContent += "\\n⚠️ Error: " + msg.error;
          }
          break;
      }
    });
  </script>
</body>
</html>`;
  }
}
