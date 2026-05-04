import json
from app.docs.models import PRDResult

class PRDPromptBuilder:
    def build_polish_prompt(self, prd_result: PRDResult) -> str:
        # We need to construct a deterministic representation. 
        # Using the json() or model_dump() of PRDResult is best, but we should strip raw types if any.
        try:
            prd_json = prd_result.model_dump_json(indent=2)
        except AttributeError:
            # fallback for older pydantic
            prd_json = prd_result.json(indent=2)
            
        prompt = f"""You are AHAL AI documentation writer.

You are given a deterministic, evidence-backed PRD generated from codebase analysis.

Rules:
1. Do not invent features, APIs, databases, modules, workflows, setup commands, risks, or project goals.
2. Do not remove evidence references.
3. Do not remove warnings or uncertainty.
4. Do not make medical, legal, security, or financial guarantees.
5. Improve clarity, grammar, and formatting only.
6. If a section has insufficient evidence, keep that statement.
7. Return polished markdown only.
8. Do not include hidden reasoning.
9. You must include all 10 standard PRD sections.

Input PRD JSON:
{prd_json}

Output:
Polished markdown PRD.
"""
        return prompt

    def build_pdf_polish_prompt(self, payload: dict) -> str:
        payload_json = json.dumps(payload, indent=2)
        prompt = f"""You are polishing wording only for PDF narrative sections in AHAL AI.

Rules:
1. Use only the provided deterministic PRD JSON and narrative payload.
2. Do not add new facts.
3. Preserve warnings.
4. Preserve risks.
5. Preserve evidence references.
6. Do not invent APIs, modules, frameworks, databases, deployment, authentication, compliance, or test coverage.
7. Do not make medical, legal, security, or compliance certainty claims.
8. Keep output concise.
9. Return strict JSON only.
10. Do not return markdown, prose outside JSON, or hidden reasoning.

Input deterministic PDF polish payload:
{payload_json}
"""
        return prompt
