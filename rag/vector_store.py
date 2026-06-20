import faiss
import pickle
import os

INDEX_PATH = "rag/faiss.index"
CHUNKS_PATH = "rag/chunks.pkl"

index = None
stored_chunks = []


def build_index(embeddings, chunks):

    global index
    global stored_chunks

    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)

    index.add(embeddings)

    stored_chunks = chunks
    print("\n========== FAISS BUILD ==========")
    print("Embeddings Shape:", embeddings.shape)
    print("Stored Chunks:", len(chunks))
    print("FAISS Total Vectors:", index.ntotal)
    print("========== END FAISS BUILD ==========\n")


def search(query_embedding, top_k=10):

    global index
    global stored_chunks

    distances, indices = index.search(
        query_embedding,
        top_k
    )

    results = []

    for rank, idx in enumerate(indices[0]):

        if idx >= len(stored_chunks):
            continue

        results.append({
            "text": stored_chunks[idx],
            "score": float(distances[0][rank])
        })
    
    print("\n========== RETRIEVAL ==========")

    for rank, idx in enumerate(indices[0]):

        if idx >= len(stored_chunks):
            continue

        print(f"\nRank {rank+1}",flush=True)
        print("Score:", distances[0][rank],flush=True)
        print(stored_chunks[idx],flush=True)

    print("========== END RETRIEVAL ==========\n")


    return results


def save_index():

    global index

    os.makedirs("rag", exist_ok=True)

    faiss.write_index(
        index,
        INDEX_PATH
    )

    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(stored_chunks, f)

    print("\n========== INDEX SAVED ==========")
    print("Index Path:", INDEX_PATH)
    print("Chunk Path:", CHUNKS_PATH)
    print("========== END SAVE ==========\n")


def load_index():

    global index
    global stored_chunks

    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)

    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, "rb") as f:
            stored_chunks = pickle.load(f)
    

    print("\n========== INDEX LOADED ==========")

    if index:
        print("Vectors:", index.ntotal)

    print("Chunks:", len(stored_chunks))

    print("========== END LOAD ==========\n")