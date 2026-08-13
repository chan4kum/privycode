import * as vscode from "vscode";
import { apiClient, ChatMessage, ContextFileItem } from "./apiClient";
import { ContextEngine } from "./contextEngine";
import { SymbolGraph } from "./symbolGraph";

export class PrivyCodeChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "privycode.chatView";
  private _view?: vscode.WebviewView;
  private conversationHistory: ChatMessage[] = [];
  private currentAbortController?: AbortController;
  private contextEngine: ContextEngine;

  constructor(private symbolGraph: SymbolGraph) {
    this.contextEngine = new ContextEngine(symbolGraph);
  }

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
        case "searchSymbols":
          const symbols = this.symbolGraph.findSymbols(data.query || "", 10);
          this.postMessageToWebview({
            type: "symbolResults",
            symbols: symbols.map(s => ({ name: s.name, kind: s.kind, signature: s.signature, file: s.filePath })),
          });
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

    // 1. Resolve multi-file and symbol context using ContextEngine
    const extracted = await this.contextEngine.buildContext(userText);

    // Notify UI of attached context chips
    if (extracted.contextFiles.length > 0) {
      this.postMessageToWebview({
        type: "contextAttached",
        files: extracted.contextFiles.map(f => f.path),
        symbols: extracted.attachedSymbols.map(s => s.name),
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
        context_files: extracted.contextFiles,
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
    body { font-family: var(--vscode-font-family); padding: 10px; color: var(--vscode-foreground); background-color: var(--vscode-editor-background); }
    .chat-container { display: flex; flex-direction: column; height: 95vh; }
    .messages-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-bottom: 8px; }
    .message { padding: 8px 12px; border-radius: 6px; max-width: 92%; word-break: break-word; font-size: 13px; line-height: 1.45; }
    .user-msg { align-self: flex-end; background-color: var(--vscode-button-background); color: var(--vscode-button-foreground); }
    .assistant-msg { align-self: flex-start; background-color: var(--vscode-editor-inactiveSelectionBackground); border: 1px solid var(--vscode-widget-border); }
    .context-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
    .chip { font-size: 10px; background: rgba(88, 166, 255, 0.15); border: 1px solid rgba(88, 166, 255, 0.3); color: var(--vscode-textLink-foreground); padding: 2px 6px; border-radius: 4px; }
    .input-area { position: relative; display: flex; flex-direction: column; gap: 6px; padding-top: 8px; border-top: 1px solid var(--vscode-widget-border); }
    textarea { width: 100%; box-sizing: border-box; resize: none; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; padding: 6px 8px; font-family: inherit; font-size: 12px; }
    .autocomplete-box { position: absolute; bottom: 100%; left: 0; right: 0; background: var(--vscode-dropdown-background); border: 1px solid var(--vscode-dropdown-border); border-radius: 4px; max-height: 140px; overflow-y: auto; display: none; z-index: 100; }
    .autocomplete-item { padding: 6px 10px; font-size: 11px; cursor: pointer; display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .autocomplete-item:hover { background: var(--vscode-list-hoverBackground); }
    button { align-self: flex-end; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; padding: 6px 14px; cursor: pointer; font-size: 12px; }
    button:hover { background: var(--vscode-button-hoverBackground); }
  </style>
</head>
<body>
  <div class="chat-container">
    <div id="messages" class="messages-list">
      <div class="message assistant-msg">👋 Hi! I am PrivyCode. Type <code>@symbol</code> or <code>@file</code> to inject repository context with zero data retention.</div>
    </div>
    <div class="input-area">
      <div id="autocomplete" class="autocomplete-box"></div>
      <textarea id="promptInput" rows="2" placeholder="Ask PrivyCode (type @ to search symbols/files)..."></textarea>
      <button id="sendBtn">Send</button>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const messagesEl = document.getElementById("messages");
    const inputEl = document.getElementById("promptInput");
    const sendBtn = document.getElementById("sendBtn");
    const autoBox = document.getElementById("autocomplete");
    let currentAssistantEl = null;

    inputEl.addEventListener("input", () => {
      const val = inputEl.value;
      const atIdx = val.lastIndexOf("@");
      if (atIdx !== -1 && atIdx === val.length - 1 || (atIdx !== -1 && !val.slice(atIdx).includes(" "))) {
        const query = val.slice(atIdx + 1);
        vscode.postMessage({ type: "searchSymbols", query });
      } else {
        autoBox.style.display = "none";
      }
    });

    sendBtn.addEventListener("click", () => {
      const text = inputEl.value;
      if (!text.trim()) return;
      vscode.postMessage({ type: "sendMessage", text });
      inputEl.value = "";
      autoBox.style.display = "none";
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
        case "symbolResults":
          if (msg.symbols && msg.symbols.length > 0) {
            autoBox.innerHTML = msg.symbols.map(s => 
              \`<div class="autocomplete-item" onclick="insertSymbol('@symbol \${s.name}')">
                <span><b>\${s.name}</b> <small style="opacity:0.7">(\${s.kind})</small></span>
                <span style="opacity:0.6">\${s.file.split('/').pop()}</span>
              </div>\`
            ).join('');
            autoBox.style.display = "block";
          } else {
            autoBox.style.display = "none";
          }
          break;
        case "addUserMessage":
          const uDiv = document.createElement("div");
          uDiv.className = "message user-msg";
          uDiv.textContent = msg.text;
          messagesEl.appendChild(uDiv);
          messagesEl.scrollTop = messagesEl.scrollHeight;
          break;
        case "contextAttached":
          const chipDiv = document.createElement("div");
          chipDiv.className = "context-chips";
          msg.files.forEach(f => {
            const c = document.createElement("span");
            c.className = "chip";
            c.textContent = "📄 " + f.split('/').pop();
            chipDiv.appendChild(c);
          });
          msg.symbols.forEach(s => {
            const c = document.createElement("span");
            c.className = "chip";
            c.textContent = "⚡ " + s;
            chipDiv.appendChild(c);
          });
          messagesEl.appendChild(chipDiv);
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

    function insertSymbol(text) {
      const val = inputEl.value;
      const atIdx = val.lastIndexOf("@");
      inputEl.value = val.slice(0, atIdx) + text + " ";
      autoBox.style.display = "none";
      inputEl.focus();
    }
  </script>
</body>
</html>`;
  }
}
