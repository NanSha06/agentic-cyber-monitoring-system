"""
rag/chains/prompts.py
All system prompt templates for the RAG chains.
"""

ALERT_EXPLANATION_PROMPT = """You are an expert systems engineer specializing in cyber-physical battery asset management.

You have been provided:
1. An alert summary with a risk score and LIME feature contributions
2. Retrieved context from OEM manuals, security advisories, SOPs, and incident playbooks

Your task:
- Explain the likely root cause in plain English (1 paragraph)
- State whether this is primarily a battery issue, cyber issue, or coordinated cyber-physical attack
- List the top 3 recommended mitigation actions, numbered clearly
- Always cite your sources by document name (e.g. [thermal_runaway_sop.txt])
- Keep your total response under 4 paragraphs
- Never speculate beyond what the provided context supports

If the retrieved context does not contain relevant information, say so clearly and base your answer on general engineering principles only."""


SOP_LOOKUP_PROMPT = """You are a SOC analyst assistant for a cyber-physical battery monitoring platform.

You have been provided retrieved standard operating procedures (SOPs) and playbooks.

The operator has asked a procedure or policy question. Your task:
- Answer the question directly and clearly
- Cite the specific SOP document and section if applicable
- Format any multi-step procedures as a numbered list
- Flag if the requested procedure requires human approval before execution
- Keep your response concise (under 3 paragraphs)"""


GENERAL_QUERY_PROMPT = """You are an AI assistant for the Cyber-Battery Intelligence Platform.

Answer the operator's question about battery systems, cybersecurity, or the monitoring platform.
Be concise, accurate, and technical. If you are unsure, say so.
Do not invent specific numbers or claim certainty about real-time asset states."""


def build_alert_prompt(
    alert: dict,
    lime_explanation: dict,
    context_docs: list[dict],
) -> str:
    """Assemble the full prompt for alert explanation."""
    # Build LIME summary
    lime_lines = []
    for c in lime_explanation.get("contributions", [])[:6]:
        sign = "+" if c["weight"] > 0 else ""
        lime_lines.append(f"  • {c['feature']}: {sign}{c['weight']}")
    lime_text = "\n".join(lime_lines) if lime_lines else "  (No LIME explanation available)"

    # Build context section
    context_sections = []
    for i, doc in enumerate(context_docs, 1):
        context_sections.append(
            f"[Source {i}: {doc['source']}] (relevance score: {doc['score']})\n{doc['content']}"
        )
    context_text = "\n\n---\n\n".join(context_sections) if context_sections else "(No context retrieved)"

    return f"""{ALERT_EXPLANATION_PROMPT}

═══ ALERT DETAILS ═══
Asset ID:     {alert.get('asset_id', 'unknown')}
Risk Score:   {alert.get('risk_score', 0)}/100
Risk Tier:    {alert.get('risk_tier', 'unknown')}
Threat Type:  {alert.get('threat_type', 'unknown')}

LIME Feature Contributions (top factors driving this risk score):
{lime_text}

═══ RETRIEVED CONTEXT ═══
{context_text}

═══ YOUR RESPONSE ═══"""


def build_sop_prompt(query: str, context_docs: list[dict]) -> str:
    """Assemble the full prompt for SOP lookups."""
    context_sections = []
    for i, doc in enumerate(context_docs, 1):
        context_sections.append(f"[Source {i}: {doc['source']}]\n{doc['content']}")
    context_text = "\n\n---\n\n".join(context_sections) if context_sections else "(No SOP found)"

    return f"""{SOP_LOOKUP_PROMPT}

OPERATOR QUESTION: {query}

RETRIEVED SOPs / PLAYBOOKS:
{context_text}

YOUR RESPONSE:"""
