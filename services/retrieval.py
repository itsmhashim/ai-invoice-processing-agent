from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Load the same embedding model used for storing
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Connect to the running Qdrant instance
qdrant = QdrantClient(url="http://localhost:6333")
collection_name = "invoice_embeddings"


def retrieve_similar_docs(query, top_k=3):
    """
    Retrieve the most relevant invoices from Qdrant.

    :param query: The user query.
    :param top_k: Number of similar documents to retrieve.
    :return: List of retrieved documents or an empty list.
    """

    try:
        # Convert query into an embedding
        query_vector = embedding_model.encode(query, normalize_embeddings=True).tolist()

        # Search for top-k similar vectors in Qdrant
        search_results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
        )

        if not search_results:
            return []

        return search_results

    except Exception as e:
        print(f"Error retrieving documents from Qdrant: {str(e)}")
        return []


def retrieve_exact_doc_by_filename(filename: str):
    filename = filename.lower().strip()
    variants = {filename, f"{filename}.pdf"}

    try:
        results, _ = qdrant.scroll(
            collection_name=collection_name,
            limit=1000
        )

        for point in results:
            stored_filename = point.payload.get("filename", "").lower().strip()
            if stored_filename in variants:
                return [point]

    except Exception as e:
        print(f" Error during exact filename match: {e}")

    return []
