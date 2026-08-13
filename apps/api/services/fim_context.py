import re
from typing import List, Tuple

# FIM Model Formats
FIM_TEMPLATES = {
    "qwen": ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>"),
    "deepseek": ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>"),
    "starcoder": ("<fim_prefix>", "<fim_suffix>", "<fim_middle>"),
    "codellama": ("<PRE> ", " <SUF>", " <MID>"),
    "default": ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>"),
}

IMPORT_REGEX = re.compile(
    r"^(?:import\s+|from\s+|using\s+|#include\s+|package\s+|require\(|const\s+.*=\s*require\()",
    re.MULTILINE,
)

def extract_top_imports(code: str, max_lines: int = 30) -> Tuple[str, str]:
    """Extracts top-of-file import/package statements from the remaining code body."""
    lines = code.splitlines(keepends=True)
    import_lines = []
    other_lines = []

    for idx, line in enumerate(lines[:max_lines]):
        if IMPORT_REGEX.match(line.strip()):
            import_lines.append(line)
        else:
            other_lines.append(line)

    other_lines.extend(lines[max_lines:])
    return "".join(import_lines), "".join(other_lines)

def build_semantic_fim_prompt(
    prefix: str,
    suffix: str,
    model_name: str = "qwen",
    max_prefix_tokens: int = 1500,
    max_suffix_tokens: int = 500,
) -> str:
    """Constructs an AST/syntax-aware Fill-in-the-Middle prompt for open-weights coding LLMs."""
    # 1. Identify model template
    model_lower = model_name.lower()
    tag_prefix, tag_suffix, tag_middle = FIM_TEMPLATES.get("default")
    for key, tpl in FIM_TEMPLATES.items():
        if key in model_lower:
            tag_prefix, tag_suffix, tag_middle = tpl
            break

    # 2. Extract top imports to anchor context
    imports, prefix_body = extract_top_imports(prefix)

    # 3. Approximate token limits (~4 characters per token)
    prefix_char_limit = max_prefix_tokens * 4
    suffix_char_limit = max_suffix_tokens * 4

    # Keep imports + sliding window of immediate prefix
    if len(imports) + len(prefix_body) > prefix_char_limit:
        available_body_chars = max(0, prefix_char_limit - len(imports))
        trimmed_prefix_body = prefix_body[-available_body_chars:] if available_body_chars > 0 else ""
        final_prefix = imports + "\n# ... [prior context trimmed] ...\n" + trimmed_prefix_body
    else:
        final_prefix = prefix

    # Trim suffix from start
    if len(suffix) > suffix_char_limit:
        final_suffix = suffix[:suffix_char_limit] + "\n# ... [following context trimmed] ..."
    else:
        final_suffix = suffix

    # 4. Assemble FIM template
    return f"{tag_prefix}{final_prefix}{tag_suffix}{final_suffix}{tag_middle}"
