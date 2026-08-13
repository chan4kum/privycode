import pytest
from apps.api.services.fim_context import build_semantic_fim_prompt, extract_top_imports

def test_extract_top_imports():
    code = (
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        "def compute():\n"
        "    return 42\n"
    )
    imports, body = extract_top_imports(code)
    assert "import os" in imports
    assert "from pathlib import Path" in imports
    assert "def compute():" in body
    assert "import os" not in body

def test_build_semantic_fim_prompt_qwen():
    prefix = "import math\n\ndef circle_area(r):\n"
    suffix = "\n    return area"
    prompt = build_semantic_fim_prompt(prefix, suffix, model_name="qwen-2.5-coder-7b")

    assert prompt.startswith("<|fim_prefix|>")
    assert "<|fim_suffix|>" in prompt
    assert "<|fim_middle|>" in prompt
    assert "import math" in prompt
    assert "return area" in prompt

def test_build_semantic_fim_prompt_starcoder():
    prefix = "const fs = require('fs');\nfunction read() {"
    suffix = "\n}"
    prompt = build_semantic_fim_prompt(prefix, suffix, model_name="starcoder2-15b")

    assert "<fim_prefix>" in prompt
    assert "<fim_suffix>" in prompt
    assert "<fim_middle>" in prompt

def test_build_semantic_fim_prompt_sliding_window():
    large_prefix = "import math\n" + "x = 1\n" * 2000
    prompt = build_semantic_fim_prompt(large_prefix, "return x", model_name="qwen", max_prefix_tokens=200)

    assert "import math" in prompt  # Top imports preserved
    assert "# ... [prior context trimmed] ..." in prompt  # Trimming occurred
    assert len(prompt) < len(large_prefix)  # Token bounded
