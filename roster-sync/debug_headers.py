"""Throwaway diagnostic: print exactly what the sync reads as headers.
Run:  python3 debug_headers.py    (reads only, changes nothing)
"""
import json, os
import gspread
from google.oauth2.service_account import Credentials
from config import ROSTER_SHEET_ID
from dotenv import load_dotenv
load_dotenv()

creds = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SA_JSON"]),
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
ws = gspread.authorize(creds).open_by_key(ROSTER_SHEET_ID).sheet1
all_values = ws.get_all_values()

# find header row (contains UUID)
hdr_idx = next(i for i, r in enumerate(all_values[:10]) if "UUID" in r)
header = all_values[hdr_idx]
print(f"Header row is row {hdr_idx+1}, and get_all_values returned {len(header)} columns.")
print("Last 6 header cells (with repr so hidden spaces show):")
for name in header[-6:]:
    print(f"   {name!r}")

target = "Actual Tuition"
print(f"\nIs {target!r} an exact match in the header? {target in header}")
# show any near-matches (ignoring case/space)
for h in header:
    if h.strip().lower() == target.lower() and h != target:
        print(f"  Near-match found but NOT exact: {h!r}")