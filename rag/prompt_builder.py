def build_chat_prompt(context, question):

    retrieved = context.get(
        "retrieved_context",
        ""
    )

    return f"""
You are an NDVI analysis expert.

Retrieved NDVI Information:

{retrieved}

Question:

{question}

Rules:

1. Answer ONLY from retrieved NDVI information.
2. Answer the exact question.
3. If asked about peak:
   return Peak NDVI value and Peak Date.
4. If asked about minimum:
   return Minimum NDVI value and Minimum Date.
5. If asked about trend:
   describe increasing/decreasing/stable.
6. Never invent NDVI values.
7. Never give a generic graph summary when a specific value is requested.
8. If information is unavailable say:

Insufficient NDVI evidence in retrieved data.

Return JSON:

{{
    "answer":""
}}
"""