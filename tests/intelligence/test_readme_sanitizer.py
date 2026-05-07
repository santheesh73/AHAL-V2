from app.intelligence.readme_sanitizer import sanitize_readme_for_identity


def test_readme_sanitizer_removes_html_logo_block():
    text = """
<p align="center">
  <img src="public/branding/ahal-logo-chatgpt-transparent.png" alt="AHAL AI Logo" width="280" />
</p>
"""

    sanitized = sanitize_readme_for_identity(text)
    lowered = sanitized.lower()

    assert "<p" not in lowered
    assert "<img" not in lowered
    assert "src=" not in lowered
    assert "alt=" not in lowered
    assert "width=" not in lowered
    assert "logo" not in lowered


def test_readme_sanitizer_keeps_meaningful_description():
    text = """
# Demo Project

<p align="center"><img src="assets/logo.svg" alt="Logo" /></p>

Demo Project is a frontend application for reviewing repository analysis results and project summaries.
"""

    sanitized = sanitize_readme_for_identity(text)

    assert "Demo Project is a frontend application" in sanitized
    assert "assets/logo" not in sanitized
