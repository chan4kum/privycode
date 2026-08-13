import * as vscode from "vscode";
import { apiClient } from "./apiClient";

export class PrivyCodeInlineCompletionProvider implements vscode.InlineCompletionItemProvider {
  private debounceTimer: NodeJS.Timeout | null = null;
  private abortController: AbortController | null = null;

  public async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionList | undefined> {
    const config = vscode.workspace.getConfiguration("privycode");
    const enabled = config.get<boolean>("enableAutocomplete", true);
    if (!enabled) return undefined;

    const debounceMs = config.get<number>("debounceMs", 250);

    // Cancel in-flight requests on new keystrokes
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    // Debounce keystrokes
    await new Promise((resolve) => {
      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(resolve, debounceMs);
    });

    if (token.isCancellationRequested) return undefined;

    // 1. Extract Prefix and Suffix context
    const fullText = document.getText();
    const offset = document.offsetAt(position);

    // Slice ~2,000 characters of prefix and ~500 characters of suffix
    const prefixStart = Math.max(0, offset - 2000);
    const prefix = fullText.slice(prefixStart, offset);
    const suffixEnd = Math.min(fullText.length, offset + 500);
    const suffix = fullText.slice(offset, suffixEnd);

    // Format Qwen Fill-In-The-Middle (FIM) prompt
    const fimPrompt = `<|fim_prefix|>${prefix}<|fim_suffix|>${suffix}<|fim_middle|>`;

    try {
      const completionText = await apiClient.getCompletion(
        {
          model: config.get<string>("model", "mock-qwen-7b"),
          prompt: fimPrompt,
          max_tokens: 128,
          temperature: 0.0,
          stop: ["\n\n", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>", "<|file_separator|>"],
        },
        this.abortController.signal
      );

      if (!completionText || token.isCancellationRequested) return undefined;

      const item = new vscode.InlineCompletionItem(
        completionText,
        new vscode.Range(position, position)
      );

      return new vscode.InlineCompletionList([item]);
    } catch {
      return undefined;
    }
  }
}
