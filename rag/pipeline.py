from rag.chunking import chunk_time_series
from rag.summarizer import summarize_chunks
from rag.prompt_builder import build_analysis_prompt, build_chat_prompt
from rag.memory import set_memory, get_memory


def run_analysis_pipeline(data):
    # Step 1: chunk
    chunks = chunk_time_series(data)

    # Step 2: summarize
    summary = summarize_chunks(chunks)

    # Step 3: build prompt
    prompt = build_analysis_prompt(summary)

    # store in memory
    set_memory(summary)

    return prompt


def run_chat_pipeline(question):
    context = get_memory()

    if not context:
        return None

    prompt = build_chat_prompt(context, question)
    return prompt