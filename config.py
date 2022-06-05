import pytz
import datetime

tz = pytz.timezone("Asia/Kuala_Lumpur")
now = datetime.datetime.now(tz)
today = now.date()
curr_year, curr_week, _ = today.isocalendar()

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_ID = "1169xArmlcu-erc02F9RTFWtLUWgvOru15hHn4JOLI4Q"
SHEET_NAME = "dB"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
TAB_RANGE = "A:J"
