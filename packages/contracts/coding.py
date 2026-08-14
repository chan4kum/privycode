from pydantic import BaseModel, Field
from typing import Literal

RequestMode = Literal["cheap", "balanced", "strong"]

class DiagnosticItem(BaseModel):
    path: str
    message: str
    line: int | None = None

class FileContext(BaseModel):
    path: str
    content: str
    selection_range: dict[str, int] | None = None

class CodeContext(BaseModel):
    repositoryId: str | None = None
    filePath: str | None = None
    languageId: str | None = None
    selectedText: str | None = None
    currentFileContent: str | None = None
    openFiles: list[FileContext] | None = None
    diagnostics: list[DiagnosticItem] | None = None

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    model: str = "mock-qwen-32b"
    mode: RequestMode = "balanced"
    messages: list[ChatMessage] = Field(min_length=1)
    context_files: list[FileContext] | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    stream: bool = True

class EditRequest(BaseModel):
    model: str = "mock-qwen-32b"
    mode: RequestMode = "balanced"
    input: str
    instruction: str
    file_path: str | None = None
    language: str | None = None
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    stream: bool = False

class CompletionRequest(BaseModel):
    model: str = "mock-qwen-7b"
    prompt: str
    max_tokens: int = Field(default=128, ge=1, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    stop: list[str] = Field(default_factory=lambda: ["\n\n", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>", "<|file_separator|>"])
    stream: bool = True
