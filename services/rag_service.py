from rag.pipeline import run_analysis_pipeline, run_chat_pipeline


# 🔥 Analyze
def analyze_with_rag(data):
    return run_analysis_pipeline(data)


# 🔥 Chat
def chat_with_rag(question):
    return run_chat_pipeline(question)