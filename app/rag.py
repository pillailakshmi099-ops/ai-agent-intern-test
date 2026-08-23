from pathlib import Path
import json

import frontmatter
import numpy as np
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_BASE = PROJECT_ROOT / "knowledge-base"
STORAGE = PROJECT_ROOT / "storage"

CHUNKS_FILE = STORAGE / "chunks.json"
EMBEDDINGS_FILE = STORAGE / "embeddings.npy"


# --------------------------------------------------
# Local embedding model
# --------------------------------------------------

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# Load Markdown documents
# --------------------------------------------------

def load_documents():

    documents = []

    for filepath in sorted(KNOWLEDGE_BASE.glob("*.md")):

        post = frontmatter.load(filepath)

        document = {
            "filename": filepath.name,
            "metadata": dict(post.metadata),
            "content": post.content.strip()
        }

        documents.append(document)

    return documents


# --------------------------------------------------
# Create chunks using Markdown headings
# --------------------------------------------------

def create_chunks(document):

    lines = document["content"].splitlines()

    chunks = []

    current_heading = None
    current_text = []

    for line in lines:

        # A "##" heading starts a new chunk
        if line.startswith("## "):

            # Save previous chunk
            if current_heading and current_text:

                chunks.append({
                    "filename": document["filename"],
                    "heading": current_heading,
                    "text": "\n".join(current_text).strip(),
                    "metadata": document["metadata"]
                })

            current_heading = line[3:].strip()
            current_text = []

        elif current_heading:

            current_text.append(line)

    # Save final chunk
    if current_heading and current_text:

        chunks.append({
            "filename": document["filename"],
            "heading": current_heading,
            "text": "\n".join(current_text).strip(),
            "metadata": document["metadata"]
        })

    return chunks


# --------------------------------------------------
# Create embeddings
# --------------------------------------------------

def create_embeddings(chunks):

    # Include heading and content so the embedding
    # captures the meaning of the complete section.
    texts = [
        f"{chunk['heading']}\n{chunk['text']}"
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings


# --------------------------------------------------
# Save chunks and embeddings
# --------------------------------------------------

def save_index(chunks, embeddings):

    STORAGE.mkdir(exist_ok=True)

    with open(CHUNKS_FILE, "w", encoding="utf-8") as file:

        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False,
            default=str
        )

    np.save(EMBEDDINGS_FILE, embeddings)

    print()
    print("Index saved successfully!")
    print(f"Chunks saved to: {CHUNKS_FILE}")
    print(f"Embeddings saved to: {EMBEDDINGS_FILE}")


# --------------------------------------------------
# Retrieve relevant chunks with hybrid ranking
# --------------------------------------------------

def retrieve(query, chunks, embeddings, top_k=3):

    # Create embedding for the user's question
    query_embedding = embedding_model.encode(
        query,
        normalize_embeddings=True
    )

    # Calculate semantic similarity
    similarity_scores = np.dot(
        embeddings,
        query_embedding
    )

    # Normalize query words
    query_words = set(
        word.lower().strip(".,?!")
        for word in query.split()
        if len(word) > 2
    )

    ranked_results = []

    for index, similarity in enumerate(similarity_scores):

        chunk = chunks[index]
        metadata = chunk.get("metadata", {})

        # ------------------------------------------
        # Heading keyword relevance
        # ------------------------------------------

        heading_words = set(
            word.lower().strip(".,?!")
            for word in chunk["heading"].split()
            if len(word) > 2
        )

        heading_overlap = query_words.intersection(
            heading_words
        )

        heading_bonus = 0.10 * len(heading_overlap)

        # ------------------------------------------
        # Metadata-aware ranking
        # ------------------------------------------

        status = str(
            metadata.get("status", "")
        ).lower()

        authority = str(
            metadata.get("policy_authority", "")
        ).lower()

        metadata_bonus = 0.0

        # Prefer active documents
        if status == "active":
            metadata_bonus += 0.08

        # Prefer official documents
        if authority == "official":
            metadata_bonus += 0.05

        # Penalize superseded documents
        if status == "superseded":
            metadata_bonus -= 0.15

        # ------------------------------------------
        # Final score
        # ------------------------------------------

        final_score = (
            float(similarity)
            + heading_bonus
            + metadata_bonus
        )

        ranked_results.append({
            "chunk": chunk,
            "similarity": float(similarity),
            "heading_bonus": heading_bonus,
            "score": final_score
        })

    # Sort by highest final score
    ranked_results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    results = []

    for item in ranked_results[:top_k]:

        result = item["chunk"].copy()

        result["similarity"] = item["similarity"]
        result["heading_bonus"] = item["heading_bonus"]
        result["score"] = item["score"]

        results.append(result)

    return results


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    # Load documents
    documents = load_documents()

    print(f"Loaded {len(documents)} documents.")
    print()

    # Create chunks
    all_chunks = []

    for document in documents:

        chunks = create_chunks(document)
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} chunks.")
    print()

    # Create embeddings
    embeddings = create_embeddings(all_chunks)

    print("Embeddings created successfully!")
    print(
        "Number of embeddings:",
        len(embeddings)
    )

    print(
        "Embedding dimensions:",
        len(embeddings[0])
    )

    # Save index
    save_index(
        all_chunks,
        embeddings
    )

   