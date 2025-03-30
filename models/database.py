import sqlite3
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import numpy as np
import re
from rapidfuzz import fuzz, process
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# SQLite Database File
DB_FILE = "invoice_cache.db"

# Initialize Sentence Transformer for embeddings
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Qdrant setup using LangChain's built-in vectorstore retriever
qdrant = QdrantClient(url="http://localhost:6333")
collection_name = "invoice_embeddings"

#  Check if collection exists before creating
existing_collections = [col.name for col in qdrant.get_collections().collections]

if collection_name not in existing_collections:
    print(" Creating collection for the first time...")
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
else:
    print(" Collection already exists, skipping recreation.")

vector_store = Qdrant(
    client=qdrant,
    collection_name=collection_name,
    embeddings=embedding_model
)

# Initialize database connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize SQLite database & tables
def initialize_sqlite():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cache for queries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Dedicated summary table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Store API responses in cache
def cache_response(invoice_id, query, response):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO query_cache (invoice_id, query, response) VALUES (?, ?, ?)",
            (invoice_id, query, response)
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f" Database Lock Error (cache_response): {e}")
    finally:
        cursor.close()
        conn.close()

# Cache invoice summary separately
def cache_invoice_summary(invoice_id, summary):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO invoice_summaries (invoice_id, summary) VALUES (?, ?)",
            (invoice_id, summary)
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f" Database Lock Error (cache_invoice_summary): {e}")
    finally:
        cursor.close()
        conn.close()

# Get cached invoice summary
def get_invoice_summary(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT summary FROM invoice_summaries WHERE invoice_id = ?",
            (invoice_id,)
        )
        result = cursor.fetchone()
        return result["summary"] if result else None
    except sqlite3.OperationalError as e:
        print(f" Database Lock Error (get_invoice_summary): {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# Preprocessing and NLP setup
nltk.download("stopwords")
nltk.download("wordnet")

def preprocess_query(query):
    query = query.lower().strip()
    query = re.sub(r"[^\w\s$]", "", query)
    tokens = query.split()
    stop_words = set(stopwords.words("english"))
    tokens = [word for word in tokens if word not in stop_words]
    lemmatizer = WordNetLemmatizer()
    processed_query = " ".join([lemmatizer.lemmatize(word) for word in tokens])
    return processed_query

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

COMMON_QUERIES = [
    "What is the total amount?",
    "What is the due date?",
    "Who is the recipient of the invoice?",
    "Who should make the payment?",
    "To whom is the invoice addressed?",
    "What is the invoice number?",
    "What is the payment method?"
]

def correct_query_spelling(query, common_queries):
    result = process.extractOne(query, common_queries)
    if result:
        best_match = result[0]
        score = result[1]
        return best_match if score > 85 else query
    return query

def get_cached_response(invoice_id, user_query, similarity_threshold=0.65):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT query, response FROM query_cache WHERE invoice_id = ?", (invoice_id,))
        cached_data = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f" Database Lock Error (get_cached_response): {e}")
        return None
    finally:
        conn.close()

    if not cached_data:
        return None

    query_embedding = embedding_model.embed_query(preprocess_query(user_query))
    best_match = None
    highest_similarity = 0

    for cached_query, response in cached_data:
        cached_query_processed = preprocess_query(cached_query)
        cached_embedding = embedding_model.embed_query(cached_query_processed)

        fuzzy_similarity = fuzz.ratio(user_query.lower(), cached_query.lower()) / 100
        embedding_similarity = cosine_similarity(query_embedding, cached_embedding)

        similarity = (0.7 * fuzzy_similarity) + (0.3 * embedding_similarity)
        print(f" Checking '{user_query}' vs '{cached_query}' | Similarity: {similarity:.2f}")

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = response

    if highest_similarity >= similarity_threshold:
        print(f" Found similar cached query with {highest_similarity:.2f} similarity.")
        return best_match

    return None

# Run init
initialize_sqlite()
