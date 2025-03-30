from services.retrieval import retrieve_similar_docs
from services.ai_response import generate_ai_response, generate_summary
from models.database import get_cached_response, cache_response, qdrant, collection_name, COMMON_QUERIES
from models.database import correct_query_spelling
from models.database import get_invoice_summary, cache_invoice_summary
from services.retrieval import retrieve_exact_doc_by_filename
from services.ai_response import generate_structured_fields


def get_invoice_id_by_filename(filename):
    """
    Retrieve the invoice ID (UUID) from Qdrant by searching with the filename.
    """
    results, _ = qdrant.scroll(collection_name=collection_name, limit=100)

    filename = filename.lower().strip()  # Normalize input filename
    possible_filenames = {filename, f"{filename}.pdf"}  # Check both versions

    for point in results:
        stored_filename = point.payload.get("filename", "").lower().strip()

        if stored_filename in possible_filenames:
            print(" Match found!")
            return point.id  # Extract and return the invoice UUID

    print(" No match found.")
    return None  # Return None if no match is found


def handle_query(invoice_id, user_query, top_k=3):
    """
    Handles a user query:
    - First, check if a cached response exists.
    - If found, return it immediately.
    - Otherwise, retrieve relevant invoices and query the AI.
    """

    #  Step 1: Check if query is already cached
    corrected_query = correct_query_spelling(user_query, COMMON_QUERIES)
    print(f" Corrected Query: '{user_query}' → '{corrected_query}'")

    #  Use the corrected query for similarity checking
    cached_response = get_cached_response(invoice_id, corrected_query)

    if cached_response:
        print(" Cached response found, returning without API call.")
        return {"response": cached_response}  #  Return cached response immediately

    #  Step 2: Retrieve similar invoices from Qdrant
    retrieved_docs = retrieve_similar_docs(corrected_query, top_k=top_k)

    if not retrieved_docs:
        return {"message": "No relevant invoices found."}

    #  Step 3: Generate AI response via LangChain
    ai_response = generate_ai_response(corrected_query, retrieved_docs)

    #  Step 4: Store response ONLY if it's NOT already in cache
    cache_response(invoice_id, corrected_query, ai_response)

    return {"response": ai_response}

def handle_summary(filename: str):
    """
    Handles invoice summarization logic:
    - Checks cache.
    - If not cached, generates and stores summary.
    """

    # Check if already summarized
    # Step 1: Retrieve relevant document chunks first
    retrieved_docs = retrieve_exact_doc_by_filename(filename)
    if not retrieved_docs:
        return {"error": "No relevant document found for summarization."}

    # Step 2: Check if the document seems to be an invoice
    context = "\n".join([doc.payload["text"] for doc in retrieved_docs])
    if "invoice" not in context.lower():
        return {"summary": "The uploaded document does not appear to be an invoice."}

    # Step 3: Check cache (only for invoices)
    cached_summary = get_invoice_summary(filename)
    if cached_summary:
        print(" Cached summary found.")
        return {"summary": cached_summary}

    # Step 4: Generate and store the summary
    summary_response = generate_summary(filename, retrieved_docs)
    summary_text = summary_response["text"] if isinstance(summary_response["text"], str) else summary_response[
        "text"].get("content", "")
    cache_invoice_summary(filename, summary_text)

    return {"summary": summary_text}

    if not retrieved_docs:
        return {"error": "No relevant invoice found for summarization."}

    # Generate summary using LangChain
    summary_response = generate_summary(filename, retrieved_docs)

    # Extract plain text from the response
    summary_text = summary_response["text"] if isinstance(summary_response["text"], str) else summary_response["text"].get("content", "")

    # Cache it
    #  Cache only if it's a valid invoice summary
    if "does not appear to be an invoice" not in summary_text.lower():
        cache_invoice_summary(filename, summary_text)

    return {"summary": summary_text}


def handle_field_extraction(filename: str):
    """
    Handles structured field extraction and validation for invoices.
    """
    retrieved_docs = retrieve_exact_doc_by_filename(filename)

    if not retrieved_docs:
        return {"error": "No document found with that filename."}

    structured_data = generate_structured_fields(filename, retrieved_docs)

    return structured_data