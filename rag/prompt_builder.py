def build_analysis_prompt(summary):
    return f"""
You are a satellite data analyst.

Analyze the vegetation and moisture trends based on the summary below.

Summary:
{summary}

Return JSON:
{{
  "trend": "",
  "key_events": [],
  "summary": ""
}}
"""


def build_chat_prompt(context, question):
    return f"""
You are analyzing satellite time-series data.

Context:
{context}

User Question:
{question}

Answer clearly with reasoning.
"""