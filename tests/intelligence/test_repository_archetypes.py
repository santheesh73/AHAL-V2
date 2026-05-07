from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.intelligence_engine import IntelligenceEngine
from app.intelligence.repository_type_classifier import RepositoryTypeClassifier
from tests.intelligence.conftest import make_scan_result, python_fastapi_scan
from tests.intelligence.test_repository_type_classifier import _coding_interview_university_scan


def _cli_scan():
    return make_scan_result(
        files=[
            {"path": "pyproject.toml", "extension": ".toml"},
            {"path": "src/tool/main.py", "extension": ".py"},
            {"path": "README.md", "extension": ".md"},
        ],
        contents={
            "pyproject.toml": """
[project]
name = "repo-tool"
version = "0.1.0"
description = "Command-line tool for repository analysis"
[project.scripts]
repo-tool = "tool.main:main"
""",
            "src/tool/main.py": "import click\n\n@click.command()\ndef main():\n    print('ok')\n",
            "README.md": "# Repo Tool\n\nA command-line tool for repository analysis.\n",
        },
    )


def _python_package_scan():
    return make_scan_result(
        files=[
            {"path": "pyproject.toml", "extension": ".toml"},
            {"path": "src/mypkg/__init__.py", "extension": ".py"},
            {"path": "README.md", "extension": ".md"},
        ],
        contents={
            "pyproject.toml": """
[project]
name = "mypkg"
version = "0.1.0"
description = "Reusable Python package for data normalization"
""",
            "src/mypkg/__init__.py": "def normalize(value):\n    return value.strip()\n",
            "README.md": "# mypkg\n\nReusable Python package for data normalization.\n",
        },
    )


def _npm_package_scan():
    return make_scan_result(
        files=[
            {"path": "package.json", "extension": ".json"},
            {"path": "src/index.ts", "extension": ".ts"},
            {"path": "README.md", "extension": ".md"},
        ],
        contents={
            "package.json": '{"name":"pkg","version":"1.0.0","description":"Reusable npm package for parsing logs","main":"dist/index.js","types":"dist/index.d.ts"}',
            "src/index.ts": "export function parseLog(input: string) { return input.trim() }\n",
            "README.md": "# pkg\n\nReusable npm package for parsing logs.\n",
        },
    )


def _vscode_extension_scan():
    return make_scan_result(
        files=[
            {"path": "package.json", "extension": ".json"},
            {"path": "src/extension.ts", "extension": ".ts"},
        ],
        contents={
            "package.json": '{"name":"repo-helper","engines":{"vscode":"^1.80.0"},"main":"./dist/extension.js","contributes":{"commands":[{"command":"repoHelper.scan","title":"Scan Repository"}]}}',
            "src/extension.ts": "export function activate() {}\n",
        },
    )


def _browser_extension_scan():
    return make_scan_result(
        files=[
            {"path": "manifest.json", "extension": ".json"},
            {"path": "background.js", "extension": ".js"},
        ],
        contents={
            "manifest.json": '{"manifest_version":3,"name":"Capture","background":{"service_worker":"background.js"},"permissions":["storage"],"content_scripts":[{"matches":["<all_urls>"],"js":["content.js"]}]}',
            "background.js": "chrome.runtime.onInstalled.addListener(() => console.log('installed'))\n",
        },
    )


def _dataset_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "data/train.csv", "extension": ".csv"},
            {"path": "schema.json", "extension": ".json"},
            {"path": "LICENSE", "extension": ""},
        ],
        contents={
            "README.md": "# Sample Dataset\n\nDataset repository for customer churn analysis with schema notes and metadata.\n",
            "data/train.csv": "id,label\n1,0\n",
            "schema.json": '{"fields":[{"name":"id"},{"name":"label"}]}',
            "LICENSE": "MIT",
        },
    )


def _terraform_scan():
    return make_scan_result(
        files=[
            {"path": "main.tf", "extension": ".tf"},
            {"path": "variables.tf", "extension": ".tf"},
            {"path": "README.md", "extension": ".md"},
        ],
        contents={
            "main.tf": 'resource "aws_s3_bucket" "logs" { bucket = "ahal-logs" }\n',
            "variables.tf": 'variable "region" { type = string }\n',
            "README.md": "# Infra\n\nTerraform infrastructure for provisioning environments.\n",
        },
    )


def _template_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "package.json", "extension": ".json"},
            {"path": "template.config.json", "extension": ".json"},
        ],
        contents={
            "README.md": "# Starter\n\nStarter template for bootstrapping a SaaS app.\n",
            "package.json": '{"name":"starter","private":true,"workspaces":["apps/*","packages/*"]}',
            "template.config.json": '{"name":"starter"}',
        },
    )


def _design_assets_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "branding/logo.fig", "extension": ".fig"},
            {"path": "exports/logo.png", "extension": ".png"},
        ],
        contents={
            "README.md": "# Brand Assets\n\nDesign system asset pack with source files and exports.\n",
            "branding/logo.fig": "figma-binary-placeholder",
            "exports/logo.png": "png",
        },
    )


def _assert_repo_type(scan, expected: str):
    intelligence = IntelligenceEngine().analyze(scan)
    result = RepositoryTypeClassifier().classify(scan_result=scan, intelligence_result=intelligence)
    assert result.repo_type == expected
    return intelligence


def test_repository_archetypes_are_classified():
    assert RepositoryTypeClassifier().classify(scan_result=python_fastapi_scan(), intelligence_result=IntelligenceEngine().analyze(python_fastapi_scan())).repo_type == "backend_service"
    assert RepositoryTypeClassifier().classify(scan_result=_coding_interview_university_scan(), intelligence_result=IntelligenceEngine().analyze(_coding_interview_university_scan())).repo_type == "curriculum"
    assert RepositoryTypeClassifier().classify(scan_result=_cli_scan(), intelligence_result=IntelligenceEngine().analyze(_cli_scan())).repo_type == "cli_tool"
    assert RepositoryTypeClassifier().classify(scan_result=_python_package_scan(), intelligence_result=IntelligenceEngine().analyze(_python_package_scan())).repo_type == "python_package"
    assert RepositoryTypeClassifier().classify(scan_result=_npm_package_scan(), intelligence_result=IntelligenceEngine().analyze(_npm_package_scan())).repo_type == "npm_package"
    assert RepositoryTypeClassifier().classify(scan_result=_vscode_extension_scan(), intelligence_result=IntelligenceEngine().analyze(_vscode_extension_scan())).repo_type == "vscode_extension"
    assert RepositoryTypeClassifier().classify(scan_result=_browser_extension_scan(), intelligence_result=IntelligenceEngine().analyze(_browser_extension_scan())).repo_type == "browser_extension"
    assert RepositoryTypeClassifier().classify(scan_result=_dataset_scan(), intelligence_result=IntelligenceEngine().analyze(_dataset_scan())).repo_type == "dataset"
    assert RepositoryTypeClassifier().classify(scan_result=_terraform_scan(), intelligence_result=IntelligenceEngine().analyze(_terraform_scan())).repo_type == "infrastructure"
    assert RepositoryTypeClassifier().classify(scan_result=_template_scan(), intelligence_result=IntelligenceEngine().analyze(_template_scan())).repo_type == "template"
    assert RepositoryTypeClassifier().classify(scan_result=_design_assets_scan(), intelligence_result=IntelligenceEngine().analyze(_design_assets_scan())).repo_type == "design_assets"


def test_package_canonical_output_is_not_treated_as_backend():
    scan = _python_package_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("pkg-session", scan, intelligence)

    assert canonical.repo_type == "python_package"
    assert canonical.project_type == "python_package"
    assert "python package" in canonical.what.lower() or "library" in canonical.what.lower()
    assert "backend api" not in canonical.product_summary.lower()
    assert "devops" not in canonical.product_summary.lower()


def test_dataset_canonical_output_is_not_treated_as_app():
    scan = _dataset_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("dataset-session", scan, intelligence)

    assert canonical.repo_type == "dataset"
    assert "dataset repository" in canonical.product_summary.lower()
    assert "api service" not in canonical.product_summary.lower()
    assert "frontend" not in canonical.product_summary.lower()
