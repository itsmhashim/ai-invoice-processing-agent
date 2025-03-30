import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load credentials
GOOGLE_CREDS_FILE = "C://Users/DELL/JupyterProjects/ai_invoice_rag_agent/n8n-gmail-integration-451120-0e00b6af9e09.json"  # place in project root or secure location

# Setup connection
scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
client = gspread.authorize(creds)

# Access sheet
def get_sheet(sheet_name: str, worksheet_name: str = "Sheet1"):
    sheet = client.open(sheet_name)
    return sheet.worksheet(worksheet_name)

# Append invoice data
def append_invoice_data(sheet_name: str, data: dict):
    sheet = get_sheet(sheet_name)
    sheet.append_row(list(data.values()))


# append_invoice_data("Invoice Logs",
#     {
#     "Invoice Number": "INV-001",
#     "Supplier": "ABC Corp",
#     "Buyer": "XYZ Ltd",
#     "Amount": "$1299",
#     "Date": "2024-03-20",
#     "Due Date": "2024-04-01",
#     "Status": "Paid"
# }
# )
