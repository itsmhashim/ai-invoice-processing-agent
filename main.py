from fastapi import FastAPI, UploadFile, File, Query
from services.document_parser import extract_text_from_pdf
from models.database import qdrant, collection_name
from models.embeddings import get_text_embedding
from services.query_handler import handle_query, get_invoice_id_by_filename,handle_summary
import uuid
from services.gsheets_logger import append_invoice_data
from services.query_handler import handle_field_extraction

app = FastAPI(title="AI Invoice Parser & RAG Agent")


@app.get("/")
def home():
    return {"message": "Welcome to the AI Invoice Parser & RAG System!"}


@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Handles invoice file uploads, extracts text, and avoids duplicates."""

    # Check if invoice already exists
    existing_invoice_id = get_invoice_id_by_filename(file.filename)
    if existing_invoice_id:
        return {
            "message": f"Invoice '{file.filename}' already exists in Qdrant.",
            "invoice_id": existing_invoice_id,
        }

    file_bytes = await file.read()
    extracted_text = extract_text_from_pdf(file_bytes)

    # Generate embeddings
    embedding_vector = get_text_embedding(extracted_text)

    # Generate a unique UUID
    invoice_id = str(uuid.uuid4())  # Qdrant requires int or UUID

    # Store in Qdrant
    qdrant.upsert(
        collection_name=collection_name,
        points=[
            {
                "id": invoice_id,
                "vector": embedding_vector,
                "payload": {"text": extracted_text, "filename": file.filename.lower()},
            }
        ],
    )

    return {"message": "Invoice uploaded successfully.", "filename": file.filename, "invoice_id": invoice_id}


@app.get("/ask")
def ask_ai(
    filename: str = Query(..., description="Filename of the invoice"),
    query: str = Query(..., description="Ask a question about an invoice"),
):
    """
    API endpoint to process user queries using filename instead of invoice ID.
    """
    response = handle_query(filename, query)
    return response


@app.get("/summarize")
def summarize_invoice(filename: str):
    return handle_summary(filename)

@app.get("/extract-fields")
def extract_fields(filename: str, sheet: str = "Invoice Logs"):
    """
    Extract structured invoice fields and log them into a Google Sheet.
    """
    result = handle_field_extraction(filename)

    if "error" in result:
        return result

    #  Log to Google Sheet
    append_invoice_data(sheet, result)

    return {"message": "Structured fields extracted and logged successfully.", "fields": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
