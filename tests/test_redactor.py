import pytest
from apps.api.services.redactor import sanitize_text, sanitize_messages, sanitize_context_files
from apps.api.services.audit import generate_zero_retention_headers
import uuid

def test_sanitize_aws_key():
    code = 'aws_key = "AKIAIOSFODNN7EXAMPLE"'
    sanitized, tags = sanitize_text(code)
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "<REDACTED_AWS_KEY>" in sanitized
    assert "AWS_ACCESS_KEY" in tags

def test_sanitize_api_tokens():
    openai_code = 'openai.api_key = "sk-proj-1234567890abcdefghijklmn"'
    sanitized, tags = sanitize_text(openai_code)
    assert "sk-proj" not in sanitized
    assert "<REDACTED_API_KEY>" in sanitized
    assert "API_KEY" in tags

    github_code = 'git_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"'
    sanitized_gh, tags_gh = sanitize_text(github_code)
    assert "ghp_" not in sanitized_gh
    assert "<REDACTED_API_KEY>" in sanitized_gh
    assert "API_KEY" in tags_gh

def test_sanitize_db_password():
    uri = 'db_url = "postgresql://myuser:SuperSecretPass123!@db.internal:5432/production"'
    sanitized, tags = sanitize_text(uri)
    assert "SuperSecretPass123!" not in sanitized
    assert "<REDACTED_DB_PASSWORD>" in sanitized
    assert "postgresql://myuser:<REDACTED_DB_PASSWORD>@db.internal:5432/production" == sanitized.replace('db_url = "', '').replace('"', '')
    assert "DB_PASSWORD" in tags

def test_sanitize_private_key():
    key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Y8v...
-----END RSA PRIVATE KEY-----
"""
    sanitized, tags = sanitize_text(key)
    assert "MIIEowIBAAKCAQEA" not in sanitized
    assert "<REDACTED_PRIVATE_KEY>" in sanitized
    assert "PRIVATE_KEY" in tags

def test_sanitize_messages():
    messages = [
        {"role": "user", "content": "Connect using postgresql://admin:p@ssword99@localhost/db"},
        {"role": "assistant", "content": "Here is how you connect..."},
    ]
    clean_msgs, tags = sanitize_messages(messages)
    assert len(clean_msgs) == 2
    assert "p@ssword99" not in clean_msgs[0]["content"]
    assert "<REDACTED_DB_PASSWORD>" in clean_msgs[0]["content"]
    assert "DB_PASSWORD" in tags

def test_zero_retention_audit_headers():
    user_id = uuid.uuid4()
    headers = generate_zero_retention_headers(
        user_id=user_id,
        endpoint="/v1/chat",
        redacted_tags=["AWS_ACCESS_KEY", "DB_PASSWORD"],
    )
    assert headers["X-PrivyCode-Zero-Retention"] == "Verified"
    assert headers["X-PrivyCode-Audit-Signature"].startswith("sig_")
    assert "AWS_ACCESS_KEY" in headers["X-PrivyCode-Redacted-Entities"]
