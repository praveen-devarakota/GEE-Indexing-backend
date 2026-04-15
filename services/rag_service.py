from rag.pipeline import run_analysis_pipeline, run_chat_pipeline
from services.groq_service import client

# 🔥 Analyze (main RAG entry)
def analyze_with_rag(data):
    """
    Takes timeseries data → runs RAG pipeline → calls LLM
    """

    # Step 1: Build prompt using RAG pipeline
    prompt = run_analysis_pipeline(data)

    # Step 2: Call LLM
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    # Step 3: Extract response
    content = response.choices[0].message.content

    return content


# 🔥 Chat (uses stored context)
def chat_with_rag(question):
    """
    Takes user question → uses stored RAG context → calls LLM
    """

    # Step 1: Build prompt using memory
    prompt = run_chat_pipeline(question)

    if not prompt:
        return "No analysis found. Please run /api/analyze first."

    # Step 2: Call LLM
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    # Step 3: Extract response
    content = response.choices[0].message.content

    return content