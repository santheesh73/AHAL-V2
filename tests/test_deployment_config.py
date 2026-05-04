from __future__ import annotations

from pathlib import Path


def _repo_file(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / name


def test_dockerfile_exists():
    assert _repo_file("Dockerfile").exists()


def test_docker_compose_exists():
    assert _repo_file("docker-compose.yml").exists()


def test_dockerignore_exists():
    assert _repo_file(".dockerignore").exists()


def test_deployment_docs_exist():
    assert _repo_file("docs/deployment.md").exists()


def test_env_example_does_not_contain_real_secret():
    content = _repo_file(".env.example").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=" in content
    assert "GEMINI_API_KEY=AIza" not in content
    assert "GEMINI_API_KEY =AIza" not in content


def test_compose_defaults_to_memory_storage():
    content = _repo_file("docker-compose.yml").read_text(encoding="utf-8")
    assert "AHAL_STORAGE_BACKEND: ${AHAL_STORAGE_BACKEND:-memory}" in content


def test_gemini_disabled_by_default():
    content = _repo_file("docker-compose.yml").read_text(encoding="utf-8")
    assert "AHAL_LLM_ENABLED: ${AHAL_LLM_ENABLED:-false}" in content


def test_no_real_gemini_key_committed():
    compose = _repo_file("docker-compose.yml").read_text(encoding="utf-8")
    env_example = _repo_file(".env.example").read_text(encoding="utf-8")
    assert "AIza" not in compose
    assert "AIza" not in env_example
