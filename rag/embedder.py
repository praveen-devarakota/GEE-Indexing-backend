import os
import requests
import numpy as np
from dotenv import load_dotenv

load_dotenv()

JINA_API_KEY = os.getenv("JINA_API_KEY")

JINA_URL = "https://api.jina.ai/v1/embeddings"


def _normalize(vectors):
    norms = np.linalg.norm(
        vectors,
        axis=1,
        keepdims=True
    )

    return vectors / np.maximum(
        norms,
        1e-12
    )


def embed_texts(texts):

    print(
        "\n========== EMBEDDING START ==========",
        flush=True
    )

    print(
        f"Total Chunks: {len(texts)}",
        flush=True
    )

    response = requests.post(
        JINA_URL,
        headers={
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "jina-embeddings-v3",
            "task": "retrieval.passage",
            "input": texts
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    embeddings = np.array(
        [
            item["embedding"]
            for item in data["data"]
        ],
        dtype=np.float32
    )

    embeddings = _normalize(
        embeddings
    )

    print(
        "Embedding Shape:",
        embeddings.shape,
        flush=True
    )

    print(
        "========== EMBEDDING END ==========\n",
        flush=True
    )

    return embeddings


def embed_query(question):

    print(
        "\n========== QUERY EMBEDDING ==========",
        flush=True
    )

    print(
        question,
        flush=True
    )

    response = requests.post(
        JINA_URL,
        headers={
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "jina-embeddings-v3",
            "task": "retrieval.query",
            "input": [question]
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    vector = np.array(
        [
            data["data"][0]["embedding"]
        ],
        dtype=np.float32
    )

    vector = _normalize(
        vector
    )

    print(
        "Query Shape:",
        vector.shape,
        flush=True
    )

    print(
        "========== END QUERY ==========\n",
        flush=True
    )

    return vector