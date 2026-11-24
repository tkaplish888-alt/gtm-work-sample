"""Step 1: get enrolled students out of Close and stitch their pieces together."""
import requests
from config import (CLOSE_API_KEY, CLOSE_BASE, CF, APPLICATION_COTYPE,
                    LEDGER_TYPE_ID, ENROLLED_STATUS, START_DATE_FLOOR, cf)

AUTH = (CLOSE_API_KEY, "")


def _get(path, params=None):
    r = requests.get(f"{CLOSE_BASE}{path}", auth=AUTH, params=params or {})
    r.raise_for_status()
    return r.json()


def enrolled_opportunities():
    """Every opportunity in 'Enrolled' that started on/after the cutoff.

    We page through all opportunities and filter by status in code, rather
    than trusting a search-query string. It's a little more work but reliable.
    """
    results, skip = [], 0
    while True:
        page = _get("/opportunity/", {"_limit": 100, "_skip": skip})
        for opp in page["data"]:
            if (opp.get("status_label") or "") != ENROLLED_STATUS:
                continue
            start = cf(opp, CF["actual_start"])
            if start and start.startswith("2099"):
                continue          # skip the 12/31/2099 placeholder date
            if start and start >= START_DATE_FLOOR:
                results.append(opp)
        if not page.get("has_more"):
            break
        skip += 100
    return results


def most_recent_per_lead(opps):
    """Keep one opportunity per student: the most recent by start date."""
    best = {}
    for o in opps:
        lid = o["lead_id"]
        cur = best.get(lid)
        this_start = cf(o, CF["actual_start"]) or ""
        if not cur or this_start > (cf(cur, CF["actual_start"]) or ""):
            best[lid] = o
    return best


def lead(lead_id):
    return _get(f"/lead/{lead_id}/")


def application_state(lead_id):
    # CONFIRM the custom-object endpoint path against Close's API docs.
    data = _get("/custom_object/", {
        "lead_id": lead_id,
        "custom_object_type_id": APPLICATION_COTYPE,
    })
    insts = data.get("data", [])
    if not insts:
        return None
    return cf(insts[0], CF["state"])


def latest_ledger(lead_id):
    data = _get("/activity/custom/", {
        "lead_id": lead_id,
        "custom_activity_type_id": LEDGER_TYPE_ID,
    })
    rows = data.get("data", [])
    if not rows:
        return {}
    rows.sort(key=lambda a: a.get("date_created", ""))
    latest = rows[-1]
    return {"pay_source": cf(latest, CF["pay_source"]),
            "ledger_total": cf(latest, CF["ledger_total"])}


def collect():
    """Returns one joined record per enrolled student."""
    best = most_recent_per_lead(enrolled_opportunities())
    out = []
    for lead_id, opp in best.items():
        ld = lead(lead_id)
        contact = (ld.get("contacts") or [{}])[0]
        out.append({
            "lead_id": lead_id,
            "opp": opp,
            "contact": contact,
            "state": application_state(lead_id),
            "ledger": latest_ledger(lead_id),
        })
    return out