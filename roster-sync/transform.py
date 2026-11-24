"""Step 2: turn each joined Close record into a roster row."""
from config import CF, cf

# --- Phrasing translations: Close's wording -> the roster's exact dropdown wording ---
# Right-hand values match the roster dropdown EXACTLY (including capitalization).
# Maps both old Close names ("... Program") and new short names onto the roster
# values. Anything not listed passes through unchanged, so no student is dropped.

PROGRAM_MAP = {
    # old Close spellings (with "Program") -> roster dropdown names
    "Software Engineering Full-Time Program":          "Software Engineering Full-Time",
    "Software Engineering Part-Time Program":          "Software Engineering Part-Time",
    "AI & Data Science Part-Time Program":             "AI & Data Science Part-Time",
    "Cybersecurity Part-Time Program":                 "Cybersecurity Part-time",
    "AI Engineering Immersive Program":                "AI Engineering Immersive",
    "Cyber Engineering Immersive Program":             "Cyber Engineering Immersive",
    "Accelerated AI Engineering Immersive Program":    "Accelerated AI Engineering Immersive",
    "Accelerated Cyber Engineering Immersive Program": "Accelerated Cyber Engineering Immersive",

    # new Close spellings (now that Close is renamed) -> roster dropdown names
    "Software Engineering Full-time":          "Software Engineering Full-Time",
    "Software Engineering Part-time":          "Software Engineering Part-Time",
    "AI & Data Science Part-time":             "AI & Data Science Part-Time",
    "Cybersecurity Part-time":                 "Cybersecurity Part-time",
    "AI Engineering Immersive":                "AI Engineering Immersive",
    "Cyber Engineering Immersive":             "Cyber Engineering Immersive",
    "Accelerated AI Engineering Immersive":    "Accelerated AI Engineering Immersive",
    "Accelerated Cyber Engineering Immersive": "Accelerated Cyber Engineering Immersive",
}

INSTITUTION_MAP = {
    "Partner":          "Partner College",
    "Flatiron School": "Flatiron School",
}


def translate(value, mapping):
    """Convert Close's wording to the roster's wording; leave unknowns as-is."""
    return mapping.get(value, value)


def as_text(v):
    """Close dropdown fields come back as lists (e.g. ['Partner']).
    Google Sheets needs plain text, so flatten lists and handle None."""
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return v


def split_name(full):
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def iso_to_mdy(iso):
    """'2026-09-07' -> '9/7/26'"""
    iso = as_text(iso)
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return f"{int(m)}/{int(d)}/{y[2:]}"


def to_row(rec):
    opp = rec["opp"]
    full = rec["contact"].get("name", "")
    first, last = split_name(full)
    emails = rec["contact"].get("emails", [])
    phones = rec["contact"].get("phones", [])

    program = translate(as_text(cf(opp, CF["program_pacing"])), PROGRAM_MAP)
    institution = translate(as_text(cf(opp, CF["institution"])), INSTITUTION_MAP)

    return {
        "UUID": rec["lead_id"],                      # the unique key (no duplicates)
        "Full Name": full,
        "First Name": first,
        "Last Name": last,
        "Email": emails[0]["email"] if emails else "",
        "State": as_text(rec.get("state")),
        "Phone": phones[0]["phone"] if phones else "",
        "Program Name": program,
        "Institution": institution,
        "Program Start Date": iso_to_mdy(cf(opp, CF["actual_start"])),
        "Enrollment Status": "Enrolled",
        "Finance Type": as_text(rec["ledger"].get("pay_source")),
        "Actual Tuition": as_text(rec["ledger"].get("ledger_total")),
    }


def to_rows(records):
    return [to_row(r) for r in records]