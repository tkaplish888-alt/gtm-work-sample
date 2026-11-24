"""Settings and Close field IDs. No secrets live here."""
import os
from dotenv import load_dotenv

load_dotenv()

CLOSE_API_KEY   = os.environ["CLOSE_API_KEY"]
ROSTER_SHEET_ID = os.environ["ROSTER_SHEET_ID"]
IMMERSIVE_SHEET_ID = os.environ.get("IMMERSIVE_SHEET_ID", "")  # Partner immersive sheet (optional)
DRY_RUN         = os.environ.get("DRY_RUN", "true").lower() == "true"

CLOSE_BASE = "https://api.close.com/api/v1"

# --- Close custom field IDs (verified in your Close account) ---
CF = {
    "institution":    "cf_REDACTED",
    "program_pacing": "cf_REDACTED",
    "actual_start":   "cf_REDACTED",
    "ea_cleared":     "cf_REDACTED",
    "state":          "cf_REDACTED",
    "pay_source":     "cf_REDACTED",
    "ledger_total":   "cf_REDACTED",
}

APPLICATION_COTYPE = "cotype_REDACTED"
LEDGER_TYPE_ID     = "actitype_REDACTED"

ENROLLED_STATUS  = "Enrolled"      # exact status label in Close
START_DATE_FLOOR = "2026-09-07"    # TEMP for testing; set real "91-forward" date later

# The roster columns we fill in Phase 1, in order.
ROSTER_COLUMNS = [
    "UUID", "Full Name", "First Name", "Last Name", "Email", "State",
    "Phone", "Product", "Institution", "Enrollment Start Date",
    "Enrollment Status", "Finance Type", "Actual Tuition",
]


def cf(obj, field_id):
    """Read a Close custom field.

    Close returns custom fields two different ways depending on the endpoint:
    as a flat key named 'custom.cf_xxx', OR nested inside a 'custom' object.
    This checks both so we never miss a value.
    """
    flat = obj.get(f"custom.{field_id}")
    if flat is not None:
        return flat
    return (obj.get("custom") or {}).get(field_id)