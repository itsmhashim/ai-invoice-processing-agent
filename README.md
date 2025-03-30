# 🤖 AI Invoice Processing Agent (RAG)

An AI-powered document automation system built with `Python`, designed to parse, summarize, extract, and log data from invoices using Retrieval-Augmented Generation (RAG) and Google Sheets integration.

___

## ✨ Features

- ✉️ **Smart Uploads**: Upload PDFs (invoices/receipts) and extract embedded text.
- 🧰 **Invoice Summarization**: Get concise, LLM-powered summaries.
- 🔢 **Structured Field Extraction**: Pull key invoice data like `invoice number`, `amount`, `due date`, `buyer`, `supplier`, etc.
- 📊 **Google Sheets Logging**: Append structured invoice data to a spreadsheet with duplication checks.
- ⚠️ **Non-Invoice Detection**: Automatically detects and handles non-invoice documents.
- 📁 **Local SQLite Caching**: Responses and summaries are cached to prevent duplicate processing and saving costs with `API` calls.

___


## ⚙️ Tech Stack

| Layer          | Tech          |
|----------------|---------------|
| LLM API        | `Gemini Flash 2.0` |
|  RAG Framework | `LangChain`   |
| Embeddings     | sentence-transformers/`all-MiniLM-L6-v2` |
| Vector DB      | `Qdrant` (local instance) |
| Backend        | `FastAPI`     |
| Storage        | `SQLite`      |
| Logging        | Google Sheets |

___

## ⛏️ Core Workflow

1. **Upload PDF:** Extracts invoice text from the uploaded `PDF` and generates embeddings using a sentence-transformers model. The data is stored in a `Qdrant` vector database, managed through LangChain’s vectorstore interface.

2. **Ask Questions:** Checks for **cached responses** using query similarity. If not found, uses LangChain to retrieve similar documents and send a query to Gemini Flash 2.0.

3. **Summarize Invoice:** If the document is a valid invoice, a brief summary is generated using the `Gemini` model. Summaries are cached per document to avoid redundant `API` calls.

4. **Extract Fields:** Key structured fields (like `invoice number`, `amount`, `due date`) are extracted as `JSON` and logged into a connected Google Sheet. Non-invoice documents are automatically rejected.

___

## 📂 Example Extracted Fields

```json
{
  "Invoice Number": "6A22L94B5901",
  "Supplier": "OpenRouter, Inc",
  "Buyer": "MUHAMMAD HASHIM",
  "Amount": "$10.95",
  "Due Date": "March 8, 2025",
  "Status": "Paid",
  "Filename": "Invoice-8A5DG97B-0001"
}
```
___

## 🖥️ Demo & Showcase
[🚀 Watch Demo Video](https://vimeo.com/1070716391/31bcdd7f41?share=copy)

---

## 📜 License
This project is licensed under the `MIT License`. See the [LICENSE](./LICENSE) file for details.

---

## 🤝 Contributing
Contributions are welcome! Feel free to fork this repo, create a new branch, and submit a Pull Request.

---

## 📬 Contact
📧 [muhammad.hashim40@ee.ceme.edu.pk](muhammad.hashim40@ee.ceme.edu.pk)

___