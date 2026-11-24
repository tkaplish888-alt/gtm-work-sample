"""Second source: read Partner immersive students from their Google Sheet and
turn them into roster rows. Keyed on email (as a deterministic IMM- code), so
this source can share the roster with the Close sync without duplicating people.
"""
import json
import os
import hashlib
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
from config import IMMERSIVE_SHEET_ID, START_DATE_FLOOR

IMMERSIVE_TAB = "Immersive Info"

# Reuse the same institution phrasing the roster expects.
INSTITUTION_MAP = {"Partner": "Partner College"}


def _sheet():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SA_JSON"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    book = gspread.authorize(creds).open_by_key(IMMERSIVE_SHEET_ID)
    return book.worksheet(IMMERSIVE_TAB)


def email_to_uuid(email):
    """Deterministic short code from the email. Same email -> same code, always,
    so re-runs never create duplicates and no counter is needed."""
    h = hashlib.sha1(email.strip().lower().encode()).hexdigest()[:6].upper()
    return f"IMM-{h}"


def _parse_mdy(s):
    """'7/6/26' -> date(2026, 7, 6); returns None if blank/unparseable."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        m, d, y = s.split("/")
        y = int(y)
        if y < 100:
            y += 2000
        return date(y, int(m), int(d))
    except Exception:
        return None


def _floor():
    y, m, d = START_DATE_FLOOR.split("-")
    return date(int(y), int(m), int(d))


def collect_rows():
    """One roster row per eligible immersive student (real email + start >= cutoff)."""
    if not IMMERSIVE_SHEET_ID:
        return []  # source not configured yet

    ws = _sheet()
    all_values = ws.get_all_values()
    # Header row = the one containing "Preferred Email".
    hdr_idx = next(i for i, r in enumerate(all_values[:6]) if "Preferred Email" in r)
    header = all_values[hdr_idx]
    col = {name.strip(): i for i, name in enumerate(header) if name.strip()}

    def g(row, name):
        i = col.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    floor = _floor()
    rows = []
    for row in all_values[hdr_idx + 1:]:
        email = g(row, "Preferred Email")
        if not email:
            continue  # no key -> cannot dedupe, skip
        start = _parse_mdy(g(row, "Start Date"))
        if not start or start < floor:
            continue  # apply the same 9/07 cutoff; skip blanks/earlier
        first, last = g(row, "First Name"), g(row, "Last Name")
        institution = g(row, "Institution")
        rows.append({
            "UUID": email_to_uuid(email),
            "Full Name": f"{first} {last}".strip(),
            "First Name": first,
            "Last Name": last,
            "Email": email.lower(),
            "State": g(row, "State"),
            "Phone": g(row, "Phone Number"),
            "Program Name": g(row, "Program"),
            "Institution": INSTITUTION_MAP.get(institution, institution),
            "Program Start Date": f"{start.month}/{start.day}/{str(start.year)[2:]}",
            "Enrollment Status": "Enrolled",
            "Finance Type": g(row, "Payment Type"),
            "Actual Tuition": g(row, "Tuition"),
        })
    return rows