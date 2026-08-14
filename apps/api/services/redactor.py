import re
from typing import Any, Dict, List, Tuple

# Pre-compiled high-speed regexes for enterprise credential & PII redaction
REDACTION_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # 1. AWS Access Keys
    (
        "AWS_ACCESS_KEY",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "<REDACTED_AWS_KEY>",
    ),
    # 2. General API Keys (OpenAI, GitHub, HuggingFace, Anthropic)
    (
        "API_KEY",
        re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,})\b"),
        "<REDACTED_API_KEY>",
    ),
    # 3. Slack Bot & User Tokens
    (
        "SLACK_TOKEN",
        re.compile(r"\b(xox[baprs]-[0-9A-Za-z-]{20,})\b"),
        "<REDACTED_SLACK_TOKEN>",
    ),
    # 4. RSA / SSH / Elliptic Curve Private Keys
    (
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "<REDACTED_PRIVATE_KEY>",
    ),
    # 5. Database Connection URIs with embedded credentials
    (
        "DB_PASSWORD",
        re.compile(r"((?:postgresql|postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_\-\.]+):([^@\s]+)(@)"),
        r"\1:<REDACTED_DB_PASSWORD>\3",
    ),
    # 6. US Social Security Numbers (SSN)
    (
        "US_SSN",
        re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
        "<REDACTED_SSN>",
    ),
    # 7. Credit Card Numbers
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
        "<REDACTED_CREDIT_CARD>",
    ),
]


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """
    Scans and redacts credentials, secrets, and PII in-memory before inference.
    Returns the sanitized text and a list of detected redaction tags.
    """
    if not text:
        return text, []

    redacted_tags = []
    sanitized = text

    for tag, pattern, replacement in REDACTION_PATTERNS:
        if pattern.search(sanitized):
            sanitized = pattern.sub(replacement, sanitized)
            redacted_tags.append(tag)

    return sanitized, redacted_tags


def sanitize_messages(messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[str]]:
    """Sanitizes conversational chat messages in-memory."""
    sanitized_messages = []
    all_tags = []

    for msg in messages:
        content = msg.get("content", "")
        clean_content, tags = sanitize_text(content)
        sanitized_messages.append({
            "role": msg.get("role", "user"),
            "content": clean_content,
        })
        all_tags.extend(tags)

    return sanitized_messages, list(set(all_tags))


def sanitize_context_files(files: List[Any]) -> Tuple[List[Any], List[str]]:
    """Sanitizes repository context files in-memory before prompt construction."""
    if not files:
        return [], []

    all_tags = []
    for f in files:
        if hasattr(f, "content") and f.content:
            clean_content, tags = sanitize_text(f.content)
            f.content = clean_content
            all_tags.extend(tags)

    return files, list(set(all_tags))
