import * as vscode from "vscode";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface FileContext {
  path: string;
  content: string;
  selection_range?: { start_line: number; end_line: number };
}

export interface ChatRequest {
  model: string;
  mode?: "cheap" | "balanced" | "strong";
  messages: ChatMessage[];
  context_files?: FileContext[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface EditRequest {
  model: string;
  mode?: "cheap" | "balanced" | "strong";
  input: string;
  instruction: string;
  file_path?: string;
  language?: string;
  temperature?: number;
  stream?: boolean;
}

export interface CompletionRequest {
  model: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  stop?: string[];
  stream?: boolean;
}

export class SovereignForgeClient {
  private getApiUrl(): string {
    const config = vscode.workspace.getConfiguration("privycode");
    return config.get<string>("apiUrl", "http://localhost:8000").replace(/\/+$/, "");
  }

  private getApiKey(): string {
    const config = vscode.workspace.getConfiguration("privycode");
    return config.get<string>("apiKey", "sk_live_dev_test_12345").trim();
  }

  public async checkHealth(): Promise<{ connected: boolean; user?: string; error?: string }> {
    try {
      const url = `${this.getApiUrl()}/v1/me`;
      const response = await fetch(url, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${this.getApiKey()}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = (await response.json()) as { email: string; role: string };
        return { connected: true, user: data.email };
      } else {
        const err = await response.text();
        return { connected: false, error: `HTTP ${response.status}: ${err}` };
      }
    } catch (e: any) {
      return { connected: false, error: e.message || "Connection refused" };
    }
  }

  public async streamChat(
    req: ChatRequest,
    onChunk: (text: string) => void,
    onComplete: () => void,
    onError: (err: string) => void,
    signal?: AbortSignal
  ): Promise<void> {
    try {
      const response = await fetch(`${this.getApiUrl()}/v1/chat`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.getApiKey()}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ ...req, stream: true }),
        signal,
      });

      if (!response.ok) {
        const err = await response.text();
        onError(`Server returned ${response.status}: ${err}`);
        return;
      }

      if (!response.body) {
        onError("No response stream received from gateway.");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(":")) continue;

          if (trimmed === "data: [DONE]") {
            onComplete();
            return;
          }

          if (trimmed.startsWith("data: ")) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              const delta = data.choices?.[0]?.delta?.content;
              if (delta) {
                onChunk(delta);
              }
            } catch {
              // Non-JSON or partial chunk pass-through
            }
          }
        }
      }
      onComplete();
    } catch (e: any) {
      if (e.name === "AbortError") {
        onComplete();
      } else {
        onError(e.message || "Network error occurred.");
      }
    }
  }

  public async editCode(req: EditRequest): Promise<string> {
    const response = await fetch(`${this.getApiUrl()}/v1/edits`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.getApiKey()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ...req, stream: false }),
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Failed to generate edit (${response.status}): ${err}`);
    }

    const data = (await response.json()) as any;
    return (
      data.choices?.[0]?.message?.content ||
      data.choices?.[0]?.delta?.content ||
      "// No edits returned"
    );
  }

  public async getCompletion(req: CompletionRequest, signal?: AbortSignal): Promise<string> {
    const response = await fetch(`${this.getApiUrl()}/v1/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.getApiKey()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ...req, stream: false }),
      signal,
    });

    if (!response.ok) return "";

    const data = (await response.json()) as any;
    return (
      data.choices?.[0]?.message?.content ||
      data.choices?.[0]?.delta?.content ||
      ""
    );
  }
}

export const apiClient = new SovereignForgeClient();
