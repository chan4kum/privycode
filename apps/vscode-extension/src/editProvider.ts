import * as vscode from "vscode";
import { apiClient } from "./apiClient";

export async function handleEditSelectionCommand() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("Open a file and select code to edit with PrivyCode.");
    return;
  }

  const selection = editor.selection;
  const selectedText = editor.document.getText(selection);
  if (!selectedText.trim()) {
    vscode.window.showInformationMessage("Highlight code before running PrivyCode Edit (Cmd+I).");
    return;
  }

  // 1. Prompt user for edit instructions
  const instruction = await vscode.window.showInputBox({
    prompt: "What changes would you like PrivyCode to make?",
    placeHolder: "e.g., Refactor to async/await, add error handling, add type annotations...",
  });

  if (!instruction) return;

  const config = vscode.workspace.getConfiguration("privycode");
  const model = config.get<string>("model", "mock-qwen-32b");

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "PrivyCode: Generating refactored code...",
      cancellable: false,
    },
    async () => {
      try {
        const refactoredCode = await apiClient.editCode({
          model,
          input: selectedText,
          instruction,
          file_path: vscode.workspace.asRelativePath(editor.document.uri),
          language: editor.document.languageId,
        });

        // 2. Open native VS Code Diff view using precise selection character offsets
        const fullText = editor.document.getText();
        const startOffset = editor.document.offsetAt(selection.start);
        const endOffset = editor.document.offsetAt(selection.end);
        const modifiedContent =
          fullText.slice(0, startOffset) + refactoredCode + fullText.slice(endOffset);

        const originalDocUri = editor.document.uri;
        const modifiedDoc = await vscode.workspace.openTextDocument({
          content: modifiedContent,
          language: editor.document.languageId,
        });

        await vscode.commands.executeCommand(
          "vscode.diff",
          originalDocUri,
          modifiedDoc.uri,
          `PrivyCode Edit Proposal: ${instruction.slice(0, 30)}...`
        );
      } catch (err: any) {
        vscode.window.showErrorMessage(`PrivyCode Edit Error: ${err.message}`);
      }
    }
  );
}
