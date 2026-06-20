from rag.chunking import chunk_time_series
from rag.embedder import embed_texts, embed_query
from rag.vector_store import (
    build_index,
    save_index,
    load_index,
    search
)

def run_analysis_pipeline(data):

    print("\n========== ANALYSIS ==========")
    print("Input Records:", len(data))

    if len(data):
        print("First Record:")
        print(data[0])

    chunks = chunk_time_series(data)

    embeddings = embed_texts(chunks)

    build_index(
        embeddings,
        chunks
    )

    save_index()

    return {
        "status": "success",
        "summary":
        f"""
Indexed {len(chunks)} NDVI periods.

You may ask about:

• vegetation growth
• decline periods
• peak vegetation
• lowest vegetation
• seasonal behaviour
• anomalies
"""
    }


def run_chat_pipeline(context, question):

    print("\n========== CHAT ==========")

    print("Question:")
    print(question)

    print("\nCurve Length:")

    curve = context.get("curve", [])

    if isinstance(curve, list):
        print(len(curve))

    load_index()

    query_embedding = embed_query(question)

    results = search(
        query_embedding,
        top_k=10
    )

    retrieved_context = "\n\n".join(
        [r["text"] for r in results]
    )
    print(
        "\n========== RETRIEVED CONTEXT ==========",
        flush=True
    )

    print(
        retrieved_context,
        flush=True
    )

    print(
        "========== END RETRIEVED CONTEXT ==========\n",
        flush=True
    )

    with open(
        "retrieval_debug.txt",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"QUESTION:\n{question}\n\n"
        )

        f.write(
            "RETRIEVED:\n"
        )

        f.write(
            retrieved_context
        )

        context["retrieved_context"] = retrieved_context

    return context