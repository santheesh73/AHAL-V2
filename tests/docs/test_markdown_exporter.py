from app.docs.models import PRDResult, PRDSection, APISectionItem, ModuleSectionItem, RiskItem, WorkflowSectionItem
from app.docs.exporters.markdown_exporter import MarkdownExporter

def test_markdown_exporter():
    res = PRDResult(
        title="Project Requirement Document",
        project_type="backend",
        overview=PRDSection(title="Overview", content="Sample overview", confidence="high"),
        architecture=PRDSection(title="Architecture", content="Sample architecture", confidence="high"),
        tech_stack=PRDSection(title="Tech Stack", content="Sample tech stack", confidence="high"),
        databases=PRDSection(title="Databases", content="Sample DB", confidence="high"),
        setup_notes=PRDSection(title="Setup Notes", content="Sample setup", confidence="high"),
        api_endpoints=[
            APISectionItem(method="POST", path="/diagnose", framework="FastAPI", description="diag", confidence="high"),
            APISectionItem(method="GET", path="/health", framework="FastAPI", description="health", confidence="high")
        ],
        modules=[
            ModuleSectionItem(name="AuthModule", category="auth", description="auth", confidence="high")
        ],
        workflow=[
            WorkflowSectionItem(order=1, source="Client", action="calls", target="API", confidence="high")
        ],
        risks=[
            RiskItem(title="No tests detected", severity="high", description="no tests", recommendation="add tests")
        ],
        confidence="high",
        evidence_count=5
    )
    
    exporter = MarkdownExporter()
    md = exporter.export(res)
    
    assert "# Project Requirement Document" in md
    assert "1. Project Overview" in md
    assert "2. Architecture" in md
    assert "3. Tech Stack" in md
    assert "4. Core Modules" in md
    assert "5. API Surface" in md
    assert "6. Workflow" in md
    assert "7. Database / Storage" in md
    assert "8. Setup & Run Notes" in md
    assert "9. Risks & Gaps" in md
    assert "10. Evidence Summary" in md
    
    assert "POST" in md
    assert "/diagnose" in md
    assert "AuthModule" in md
    assert "No tests detected" in md
    assert "Evidence Summary" in md
    assert "type=" not in md
    assert "node_modules" not in md
