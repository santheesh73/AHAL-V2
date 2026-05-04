from app.docs.models import PRDResult, PRDSection, APISectionItem, ModuleSectionItem, RiskItem, WorkflowSectionItem
from app.docs.exporters.latex_exporter import LatexExporter, escape_latex

def test_latex_escape():
    assert escape_latex("test & % $ # _ { } ~ ^ \\") == r"test \& \% \$ \# \_ \{ \} \textasciitilde{} \textasciicircum{} \textbackslash{}"
    assert escape_latex(None) == ""

def test_latex_exporter():
    res = PRDResult(
        title="Project Requirement Document",
        project_type="backend",
        overview=PRDSection(title="Overview", content="Sample overview_1", confidence="high"),
        architecture=PRDSection(title="Architecture", content="Sample architecture", confidence="high"),
        tech_stack=PRDSection(title="Tech Stack", content="Sample tech stack", confidence="high"),
        databases=PRDSection(title="Databases", content="Sample DB", confidence="high"),
        setup_notes=PRDSection(title="Setup Notes", content="Sample setup", confidence="high"),
        api_endpoints=[
            APISectionItem(method="POST", path="/diagnose", framework="FastAPI", description="diag", confidence="high"),
            APISectionItem(method="GET", path="/health", framework="FastAPI", description="health", confidence="high")
        ],
        modules=[
            ModuleSectionItem(name="Auth_Module", category="auth", description="auth", confidence="high")
        ],
        workflow=[
            WorkflowSectionItem(order=1, source="Client", action="calls", target="API_1", confidence="high")
        ],
        risks=[
            RiskItem(title="No tests", severity="high", description="no tests", recommendation="add tests")
        ],
        confidence="high",
        evidence_count=5
    )
    
    exporter = LatexExporter()
    tex = exporter.export(res)
    
    assert r"\documentclass{article}" in tex
    assert r"\tableofcontents" in tex
    assert r"\section{1. Project Overview}" in tex
    assert r"\section{2. Architecture}" in tex
    assert r"\section{3. Tech Stack}" in tex
    assert r"\section{4. Core Modules}" in tex
    assert r"\section{5. API Surface}" in tex
    assert r"\section{6. Workflow}" in tex
    assert r"\section{7. Database / Storage}" in tex
    assert r"\section{8. Setup \& Run Notes}" in tex
    assert r"\section{9. Risks \& Gaps}" in tex
    assert r"\section{10. Evidence Summary}" in tex
    
    assert "POST" in tex
    assert "/diagnose" in tex
    assert r"Auth\_Module" in tex
    assert r"API\_1" in tex
    assert r"overview\_1" in tex
    assert "type=" not in tex
    assert "node_modules" not in tex
