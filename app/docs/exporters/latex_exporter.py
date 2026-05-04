from typing import Any
from app.docs.models import PRDResult
from app.docs.utils.evidence_sanitizer import sanitize_text
from app.intelligence.consistency_validator import OutputConsistencyValidator

def escape_latex(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    mapping = {
        '\\': r'\textbackslash{}',
        '^': r'\textasciicircum{}',
        '~': r'\textasciitilde{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
    }
    return "".join(mapping.get(c, c) for c in text)

class LatexExporter:
    def __init__(self):
        self.validator = OutputConsistencyValidator()

    def export(self, prd_result: PRDResult) -> str:
        prd_result = self.validator.validate_export_prd(prd_result)
        lines = []
        lines.append(r"\documentclass{article}")
        lines.append(r"\usepackage[utf8]{inputenc}")
        lines.append(r"\usepackage{longtable}")
        lines.append(r"\usepackage{hyperref}")
        lines.append(r"\title{Project Requirement Document}")
        lines.append(r"\author{AHAL AI}")
        lines.append(r"\date{\today}")
        lines.append(r"\begin{document}")
        lines.append(r"\maketitle")
        lines.append(r"\tableofcontents")
        lines.append(r"\newpage")
        
        # 1. Project Overview
        lines.append(self._format_section("1. Project Overview", prd_result.overview))
        
        # 1.5 Project Intelligence Brief
        if getattr(prd_result, "project_brief", None):
            pb = prd_result.project_brief
            lines.append(r"\section{Project Intelligence Brief}")
            lines.append(r"\subsection{Project Goal}")
            lines.append(escape_latex(sanitize_text(pb.goal.content)) + r"\\")
            lines.append(r"\subsection{What This Project Is}")
            lines.append(escape_latex(sanitize_text(pb.what.content)) + r"\\")
            lines.append(r"\subsection{Why This Project Exists}")
            lines.append(escape_latex(sanitize_text(pb.why.content)) + r"\\")
            
            lines.append(r"\subsection{What Is Already Built}")
            lines.append(r"\begin{itemize}")
            for item in pb.completed:
                lines.append(f"\\item \\textbf{{{escape_latex(item.title)}}}: {escape_latex(item.description)}")
            lines.append(r"\end{itemize}")
                
            lines.append(r"\subsection{What Is Remaining}")
            lines.append(r"\begin{itemize}")
            for item in pb.remaining:
                lines.append(f"\\item \\textbf{{{escape_latex(item.title)}}}: {escape_latex(item.description)}")
            lines.append(r"\end{itemize}")
            
            lines.append(r"\subsection{Current Issues}")
            if not pb.issues:
                lines.append("No critical issues detected." + r"\\")
            else:
                lines.append(r"\begin{itemize}")
                for issue in pb.issues:
                    lines.append(f"\\item \\textbf{{{escape_latex(issue.title)}}} ({escape_latex(issue.severity)}): {escape_latex(issue.description)}")
                lines.append(r"\end{itemize}")
                    
            lines.append(r"\subsection{Recommended Next Steps}")
            lines.append(r"\begin{itemize}")
            for step in pb.next_steps:
                lines.append(f"\\item {escape_latex(step)}")
            lines.append(r"\end{itemize}")
        
        # 2. Architecture
        lines.append(self._format_section("2. Architecture", prd_result.architecture))
        
        # 3. Tech Stack
        lines.append(self._format_section("3. Tech Stack", prd_result.tech_stack))
        
        # 4. Core Modules
        lines.append(r"\section{4. Core Modules}")
        if not prd_result.modules:
            lines.append("Insufficient evidence from codebase.")
        else:
            lines.append(r"\begin{longtable}{|p{3cm}|p{2cm}|p{5cm}|p{3cm}|p{2cm}|}")
            lines.append(r"\hline")
            lines.append(r"\textbf{Module} & \textbf{Category} & \textbf{Description} & \textbf{Files} & \textbf{Confidence} \\")
            lines.append(r"\hline")
            for mod in prd_result.modules:
                files_str = ", ".join(mod.files) if mod.files else "None"
                files_str = escape_latex(files_str)
                name = escape_latex(mod.name)
                cat = escape_latex(mod.category)
                desc = escape_latex(mod.description)
                conf = escape_latex(mod.confidence)
                lines.append(f"{name} & {cat} & {desc} & {files_str} & {conf} \\\\")
                lines.append(r"\hline")
            lines.append(r"\end{longtable}")
            
        # 5. API Surface
        lines.append(r"\section{5. API Surface}")
        if not prd_result.api_endpoints:
            lines.append("Insufficient evidence from codebase.")
        else:
            lines.append(r"\begin{longtable}{|p{1.5cm}|p{4cm}|p{2cm}|p{4cm}|p{2cm}|}")
            lines.append(r"\hline")
            lines.append(r"\textbf{Method} & \textbf{Path} & \textbf{Framework} & \textbf{Source File} & \textbf{Confidence} \\")
            lines.append(r"\hline")
            for api in prd_result.api_endpoints:
                method = escape_latex(api.method)
                path = escape_latex(api.path)
                fw = escape_latex(api.framework)
                src = escape_latex(api.source_file or "Unknown")
                conf = escape_latex(api.confidence)
                lines.append(f"{method} & {path} & {fw} & {src} & {conf} \\\\")
                lines.append(r"\hline")
            lines.append(r"\end{longtable}")
            
        # 6. Workflow
        lines.append(r"\section{6. Workflow}")
        if not prd_result.workflow:
            lines.append("Insufficient evidence from codebase.")
        else:
            lines.append(r"\begin{enumerate}")
            for wf in sorted(prd_result.workflow, key=lambda x: x.order):
                target = f" $\\rightarrow$ {escape_latex(wf.target)}" if wf.target else ""
                source = escape_latex(wf.source)
                action = escape_latex(wf.action)
                conf = escape_latex(wf.confidence)
                lines.append(f"\\item \\textbf{{{source}}} {action}{target} \\textit{{(Confidence: {conf})}}")
            lines.append(r"\end{enumerate}")
            
        # 7. Database / Storage
        lines.append(self._format_section("7. Database / Storage", prd_result.databases))
        
        # 8. Setup & Run Notes
        lines.append(self._format_section("8. Setup \& Run Notes", prd_result.setup_notes))
        
        # 9. Risks & Gaps
        lines.append(r"\section{9. Risks \& Gaps}")
        if not prd_result.risks:
            lines.append("No critical risks detected.")
        else:
            lines.append(r"\begin{longtable}{|p{3cm}|p{2cm}|p{5cm}|p{4cm}|}")
            lines.append(r"\hline")
            lines.append(r"\textbf{Title} & \textbf{Severity} & \textbf{Description} & \textbf{Recommendation} \\")
            lines.append(r"\hline")
            for risk in prd_result.risks:
                title = escape_latex(risk.title)
                sev = escape_latex(risk.severity)
                desc = escape_latex(risk.description)
                rec = escape_latex(risk.recommendation)
                lines.append(f"{title} & {sev} & {desc} & {rec} \\\\")
                lines.append(r"\hline")
            lines.append(r"\end{longtable}")
            
        # 10. Evidence Summary
        lines.append(r"\section{10. Evidence Summary}")
        lines.append(r"\begin{itemize}")
        lines.append(f"\\item \\textbf{{Overall Confidence}}: {escape_latex(prd_result.confidence.title())}")
        lines.append(f"\\item \\textbf{{Total Evidence Items}}: {prd_result.evidence_count}")
        if prd_result.warnings:
            lines.append(r"\item \textbf{Warnings}:")
            lines.append(r"\begin{itemize}")
            for w in prd_result.warnings:
                lines.append(f"\\item {escape_latex(w)}")
            lines.append(r"\end{itemize}")
        lines.append(r"\end{itemize}")
        
        lines.append(r"\end{document}")
        return "\n".join(lines)

    def _format_section(self, title: str, section) -> str:
        lines = []
        lines.append(f"\\section{{{title}}}")
        
        if not section or not section.content:
            lines.append("Insufficient evidence from codebase.")
            return "\n".join(lines)
            
        lines.append(f"\\textit{{(Confidence: {escape_latex(section.confidence.title())})}}\n")
        
        if section.warnings:
            for w in section.warnings:
                lines.append(f"\\textbf{{Warning}}: {escape_latex(w)}\n")
            lines.append("")
            
        # Basic newline to latex newline
        content = escape_latex(sanitize_text(section.content)).replace("\n", " \\\\\n")
        lines.append(content)
        lines.append("")
        return "\n".join(lines)
