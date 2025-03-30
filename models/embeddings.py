from sentence_transformers import SentenceTransformer
import numpy as np

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_text_embedding(text: str) -> np.ndarray:
    """Generate embeddings for invoice text."""
    return embedding_model.encode(text).tolist()
