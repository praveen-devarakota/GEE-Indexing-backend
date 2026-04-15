def build_analysis_prompt(summary):
    return f"""
You are a satellite data analyst.

You are given processed insights from satellite time-series data.

Data:
{summary}

STRICT RULES:
- DO NOT perform calculations
- DO NOT derive new values
- USE ONLY provided insights
- DO NOT explain reasoning
- DO NOT add extra text

Return ONLY valid JSON:

{{
  "trend": "increasing | decreasing | stable",
  "key_events": ["event 1", "event 2"],
  "summary": "short explanation"
}}
"""


def build_chat_prompt(context, question):
    analysis = context.get("analysis", {})
    start_date = context.get("start_date", "unknown")
    end_date = context.get("end_date", "unknown")
    curve = context.get("curve", "")

    return f"""
You are analyzing an NDVI time-series graph.

Graph Data (NDVI over time):
{curve}

Analysis Summary:
{analysis}

Time Range:
- Start Date: {start_date}
- End Date: {end_date}

User Question:
{question}

STRICT RULES:
- Explain the graph pattern (increase, decrease, fluctuations)
- Mention important phases (growth, decline, recovery)
- Use NDVI values from data
- DO NOT return raw data or analysis
- DO NOT explain your reasoning

RETURN ONLY JSON:

{{
  "answer": "clear explanation of the graph in 3-4 lines"
}}
"""