"""Step 3: write ONLY the sync-owned columns into the sheet.

Every other column (end date, course columns, grades, onboarding, etc.) is left
completely untouched, so formulas and manual entries there are never overwritten.
Columns are matched by header name; if a header was renamed and no longer matches,
that column is skipped safely (never guessed, never clobbered) and reported.
"""
import json
import os
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
from config import ROSTER_SHEET_ID, DRY_RUN

KEY_COLUMN = "UUID"

# The only columns the sync writes. Names must match the sheet's header row exactly.
SYNC_COLUMNS = [
    "UUID", "Full Name", "First Name", "Last Name", "Email", "State", "Phone",
    "Program Name", "Institution", "Program Start Date",
    "Enrollment Status", "Finance Type", "Actual Tuition",
]


def _sheet():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SA_JSON"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds).open_by_key(ROSTER_SHEET_ID).sheet1


def _find_header_row(all_values):
    """Header row = whichever of the first rows contains the UUID column."""
    for i, row in enumerate(all_values[:10]):
        if KEY_COLUMN in row:
            return i  # 0-based
    raise SystemExit(f"Could not find a '{KEY_COLUMN}' header in the first rows of the sheet.")


def upsert(rows):
    ws = _sheet()
    all_values = ws.get_all_values()
    if not all_values:
        raise SystemExit("Sheet appears empty.")

    header_idx = _find_header_row(all_values)      # 0-based
    header = all_values[header_idx]
    header_row_num = header_idx + 1                # 1-based sheet row
    first_data_row = header_row_num + 1
    key_col_idx = header.index(KEY_COLUMN)         # 0-based

    # Map each owned column name -> its 1-based column number; skip renamed/missing ones.
    # Match on the trimmed header text so stray leading/trailing spaces in a header
    # cell (e.g. " Actual Tuition ") don't cause a column to be missed.
    stripped_to_col = {}
    for i, h in enumerate(header):
        key = h.strip()
        if key and key not in stripped_to_col:
            stripped_to_col[key] = i + 1
    colnum, missing = {}, []
    for name in SYNC_COLUMNS:
        if name in stripped_to_col:
            colnum[name] = stripped_to_col[name]
        else:
            missing.append(name)

    # Existing students: key value -> sheet row number
    index, last_used_row = {}, header_row_num
    for offset, row in enumerate(all_values[first_data_row - 1:]):
        rownum = first_data_row + offset
        if key_col_idx < len(row) and row[key_col_idx]:
            index[str(row[key_col_idx])] = rownum
            last_used_row = rownum
    next_empty_row = last_used_row + 1

    # Build cell-level updates for owned columns only.
    updates, added, updated = [], 0, 0
    for row in rows:
        key = str(row[KEY_COLUMN])
        rownum = index.get(key)
        if rownum:
            updated += 1
        else:
            rownum = next_empty_row
            next_empty_row += 1
            added += 1
        for name, cnum in colnum.items():
            updates.append({"range": rowcol_to_a1(rownum, cnum),
                            "values": [[row.get(name, "")]]})

    if DRY_RUN:
        print(f"[DRY] would write {added} new + {updated} existing, "
              f"touching only columns: {list(colnum)}")
        if missing:
            print(f"[DRY] WARNING: these sync columns were not found in the sheet "
                  f"(check for renames): {missing}")
        return {"added": added, "updated": updated, "dry_run": True, "skipped_columns": missing}

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
    if missing:
        print(f"WARNING: sync columns not found in sheet (skipped): {missing}")
    return {"added": added, "updated": updated, "dry_run": False, "skipped_columns": missing}