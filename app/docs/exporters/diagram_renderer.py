def render_architecture_diagram(pdf, prd_result):
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 10, "Architecture Diagram", ln=True)
    pdf.set_font("helvetica", "", 10)
    
    arch_content = getattr(prd_result.architecture, "content", "")
    if not arch_content or "Architecture details are not available." in arch_content or arch_content == "Unknown":
        pdf.cell(0, 10, "Insufficient architecture relationship evidence from codebase.", ln=True)
        pdf.ln(5)
        return

    arch_label = str(getattr(prd_result, "architecture_label", "") or getattr(prd_result, "project_type", "") or "").lower()
    arch_text = arch_content.lower()
    non_app_repo_types = {
        "documentation", "curriculum", "knowledge_base", "cli_tool", "python_package", "npm_package",
        "component_library", "sdk", "browser_extension", "vscode_extension", "dataset", "ml_model_repo",
        "data_science_notebooks", "template", "infrastructure", "devops_automation", "design_assets",
        "research_code", "monorepo",
    }
    if arch_label in non_app_repo_types or any(token in arch_text for token in (
        "documentation/curriculum content", "package with importable library apis", "dataset and metadata distribution",
        "command-line execution flow", "starter/template structure", "infrastructure-as-code", "automation and pipeline configuration",
    )):
        pdf.cell(0, 10, "No executable application architecture was confirmed from the analyzed evidence.", ln=True)
        pdf.ln(5)
        return
    
    layers = []
    if arch_label in {"frontend", "fullstack"} or ("frontend" in arch_text and arch_label != "backend"):
        layers.append("Frontend")
    else:
        layers.append("Client / API Consumer")
        
    layers.append("API Surface")
    layers.append("Core Modules / Services")
    layers.append("Database / Storage")

    for i, layer in enumerate(layers):
        pdf.set_x(pdf.get_x() + 20)
        pdf.cell(80, 10, layer, border=1, align="C", ln=True)
        if i < len(layers) - 1:
            pdf.set_x(pdf.get_x() + 55)
            pdf.cell(10, 10, "v", align="C", ln=True)  # Using 'v' to safely avoid unicode arrow issues if built-in font
    
    pdf.ln(5)

def _safe(value, default=""):
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default

def render_workflow_diagram(pdf, prd_result):
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 10, "Workflow Diagram", ln=True)
    pdf.set_font("helvetica", "", 10)
    
    items = getattr(prd_result, "workflow", [])
    if not items:
        pdf.cell(0, 10, "Insufficient workflow evidence from codebase.", ln=True)
        pdf.ln(5)
        return
        
    for i, step in enumerate(items):
        pdf.set_x(pdf.get_x() + 20)
        source = _safe(getattr(step, "source", None), "Unknown source")
        order = getattr(step, "order", i+1)
        action = _safe(getattr(step, "action", None), "next")
        target = _safe(getattr(step, "target", None), "Unknown target")
        
        # safely encode
        source = source.encode("latin-1", "replace").decode("latin-1")
        action = action.encode("latin-1", "replace").decode("latin-1")
        target = target.encode("latin-1", "replace").decode("latin-1")

        text = f"[{order}] {source}"
        pdf.cell(100, 10, text, border=1, align="L", ln=True)
        
        pdf.set_x(pdf.get_x() + 65)
        pdf.cell(10, 8, f"v {action}", align="L", ln=True)
        
        if i == len(items) - 1:
            pdf.set_x(pdf.get_x() + 20)
            pdf.cell(100, 10, f"[{order+1}] {target}", border=1, align="L", ln=True)
            
    pdf.ln(5)
