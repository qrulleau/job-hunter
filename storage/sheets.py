import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SHEET_ID, CREDENTIALS_FILE

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def log_application(company: str, job_site: str, job_url: str):
    """Ajoute une ligne dans le Google Sheet après candidature."""
    sheet = get_sheet()
    sheet.append_row([
        company,
        datetime.now().strftime("%d/%m/%Y"),
        job_site,
        "",   # Réponse
        "",   # Date réponse
        job_url,
    ])
    print(f"📊 Google Sheet mis à jour : {company}")
