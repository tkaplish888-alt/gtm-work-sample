"""Run the sync: Close students + Partner immersive students -> roster.
Both sources feed the same upsert, so no duplicates across them.
"""
import logging
from extract import collect
from transform import to_rows
from immersive import collect_rows as collect_immersive
from load import upsert

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("roster-sync")


def run():
    log.info("Fetching enrolled students from Close...")
    records = collect()
    close_rows = to_rows(records)
    log.info("Close: %d student(s).", len(close_rows))

    log.info("Fetching immersive students from Partner sheet...")
    immersive_rows = collect_immersive()
    log.info("Immersive: %d student(s) past cutoff.", len(immersive_rows))

    all_rows = close_rows + immersive_rows
    result = upsert(all_rows)
    log.info("Done: %s", result)


if __name__ == "__main__":
    run()