import os
import requests
from dotenv import load_dotenv
import json

# Load env
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "google/gemini-2.0-flash-exp:free"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer " + OPENROUTER_API_KEY,
    "Content-Type": "application/json"
}

# -------- QUERY RESPONSE --------
def generate_ai_response(query, retrieved_docs):
    context = "\n".join([doc.payload["text"] for doc in retrieved_docs])

    prompt = f"""
You are an AI assistant that processes invoices.
ONLY answer based on the provided invoice text. Do NOT make assumptions. Do NOT invent invoices on your own.
If the information is not available in the invoice, reply: "The requested information is not present in this invoice."

- DO NOT invent extra details.
- If asked for a total amount, return only the number.

Invoice:
{context}

User Query:
{query}
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 150
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f" Error from OpenRouter: {response.text}"

# -------- INVOICE SUMMARY --------
def generate_summary(invoice_id, retrieved_docs):
    context = "\n".join([doc.payload["text"] for doc in retrieved_docs])

    #  Sanity check: Reject if it doesn’t seem to be an invoice
    if "invoice" not in context.lower():
        return {
            "text": "The uploaded document does not appear to be an invoice.",
            "context": context,
            "query": "Summarize this invoice."
        }

    prompt = f"""
Summarize the following invoice in 2-3 sentences. Highlight:
- Invoice number
- Supplier and recipient
- Total amount due
- Any key payment details (if available)

Invoice:
{context}
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 150
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"]
        return {
            "text": summary.strip(),
            "context": context,
            "query": "Summarize this invoice."
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f" OpenRouter API call failed: {str(e)}"
        }


def generate_structured_fields(filename, retrieved_docs):
    context = "\n".join([doc.payload["text"] for doc in retrieved_docs])

    #  Sanity check to ensure the document is actually an invoice
    if "invoice" not in context.lower():
        return {"error": "The uploaded document does not appear to be an invoice."}

    prompt = f"""
    Extract the following structured fields from the invoice below:

    - Invoice number
    - Supplier name
    - Buyer/Client
    - Total amount
    - Due date
    - Payment status

    IMPORTANT:
    Return ONLY a valid **raw JSON object**. Do NOT use triple backticks, markdown formatting, or explanations. Just return JSON in this exact format:

    {{
      "Invoice Number": "...",
      "Supplier": "...",
      "Buyer": "...",
      "Amount": "...",
      "Due Date": "...",
      "Status": "Paid/Unpaid/Overdue/Unknown"
    }}

    If any field is not available in the invoice, use "Unknown".
    Do NOT guess or infer anything.
    Do NOT assume the invoice is paid unless its specifically mentioned that it's paid.
    Do not wrap the response in markdown or triple backticks. Return a pure JSON object only.
    
    Invoice:
    {context}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 150,
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()

        json_data = response.json()
        raw_content = json_data["choices"][0]["message"]["content"]

        print(" Raw AI Response:\n", raw_content)

        #  Strip markdown-style backticks and label if present
        #  Remove triple backticks and optional "json" language tag
        if raw_content.strip().startswith("```"):
            raw_content = raw_content.strip().strip("```").strip()
            if raw_content.lower().startswith("json"):
                raw_content = raw_content[4:].strip()

        extracted_fields = json.loads(raw_content)

        extracted_fields["Filename"] = filename
        return extracted_fields

    except requests.exceptions.RequestException as e:
        return {"error": f" OpenRouter API failed: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"error": f" Failed to parse JSON response from AI model.\nReason: {str(e)}"}  # Add reason
