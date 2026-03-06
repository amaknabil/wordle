"""
extract_wordle.py
-----------------
Ingestion script for the Wordle Analytics Pipeline.

Source: wordlehints.co.uk API (free, no auth, includes difficulty score)

Two modes (auto-detected):
  1. Historical load  — DB is empty, fetches ALL past answers via pagination
  2. Daily increment  — DB has data, fetches from (latest date in DB + 1) to today

Validation: checks existing puzzle_numbers in date range before inserting
            to prevent any duplicate data

Storage : DuckDB at ../data/wordle.db
Table   : raw_wordle_words
"""

import time
import datetime
import logging
import requests
import duckdb
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL       = "https://wordlehints.co.uk/wp-json/wordlehint/v1/answers"
WORDLE_LAUNCH = datetime.date(2021, 6, 19)   # puzzle #0: CIGAR
DB_PATH       = Path(__file__).parent.parent / "data" / "wordle.db"
PER_PAGE      = 200    # max allowed by wordlehints API
REQUEST_DELAY = 1      # seconds between paginated requests (be polite)
TIMEOUT       = 15     # seconds per request

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_connection() -> duckdb.DuckDBPyConnection:
    """Open (or create) DuckDB and ensure raw table exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_wordle_words (
            puzzle_number  INTEGER PRIMARY KEY,
            answer         VARCHAR NOT NULL,
            date           DATE    NOT NULL,
            day_name       VARCHAR,
            difficulty     FLOAT,
            loaded_at      TIMESTAMP DEFAULT current_timestamp
        )
    """)
    return con


def get_row_count(con: duckdb.DuckDBPyConnection) -> int:
    return con.execute("SELECT COUNT(*) FROM raw_wordle_words").fetchone()[0]


def get_latest_date(con: duckdb.DuckDBPyConnection) -> datetime.date | None:
    """Return the most recent puzzle date in the DB, or None if empty."""
    return con.execute("SELECT MAX(date) FROM raw_wordle_words").fetchone()[0]


def get_existing_puzzle_numbers(
    con: duckdb.DuckDBPyConnection,
    from_date: datetime.date,
    to_date: datetime.date,
) -> set[int]:
    """
    Return puzzle_numbers already in DB for the given date range.
    Used to validate and skip duplicates before inserting.
    """
    rows = con.execute("""
        SELECT puzzle_number FROM raw_wordle_words
        WHERE date BETWEEN ? AND ?
    """, [from_date, to_date]).fetchall()
    return {row[0] for row in rows}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def fetch_page(page: int, from_date: datetime.date = None, to_date: datetime.date = None) -> dict:
    """
    Fetch one page of results from wordlehints API.
    Accepts optional from/to date filters for incremental loads.
    """
    params = {
        "order":    "asc",
        "per_page": PER_PAGE,
        "page":     page,
    }
    if from_date:
        params["from"] = from_date.isoformat()
    if to_date:
        params["to"] = to_date.isoformat()

    resp = requests.get(API_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------

def insert_rows(
    con: duckdb.DuckDBPyConnection,
    rows: list[dict],
    existing: set[int],
) -> tuple[int, int]:
    """
    Insert new rows into raw_wordle_words.
    Validates each row against existing puzzle_numbers before inserting.
    Returns (inserted_count, skipped_count).
    """
    inserted = 0
    skipped  = 0

    for row in rows:
        puzzle_number = row["game"]

        if puzzle_number in existing:
            log.debug(f"  Skipping #{puzzle_number} {row['answer']} — already in database.")
            skipped += 1
            continue

        try:
            con.execute("""
                INSERT INTO raw_wordle_words
                    (puzzle_number, answer, date, day_name, difficulty)
                VALUES (?, ?, ?, ?, ?)
            """, [
                puzzle_number,
                row["answer"].upper().strip(),
                row["date"],
                row.get("day_name"),
                row.get("difficulty"),
            ])
            existing.add(puzzle_number)  # prevent in-batch dupes
            inserted += 1
            log.info(
                f"  Inserted #{puzzle_number}  {row['answer']}  "
                f"{row['date']}  difficulty={row.get('difficulty')}"
            )
        except Exception as e:
            log.error(f"  Failed to insert #{puzzle_number}: {e}")

    return inserted, skipped


# ---------------------------------------------------------------------------
# Mode 1: Historical load
# ---------------------------------------------------------------------------

def historical_load(con: duckdb.DuckDBPyConnection) -> None:
    """
    Fetch ALL historical Wordle answers via pagination (no date filter).
    Runs automatically when DB is empty. Safe to re-run.
    """
    log.info("Starting historical load...")

    page      = 1
    total_new = 0
    has_more  = True
    existing  = set()   # empty DB, nothing to validate against

    while has_more:
        log.info(f"  Fetching page {page}...")

        data     = fetch_page(page)
        results  = data.get("results", [])
        has_more = data.get("has_more", False)
        total    = data.get("total", "?")

        if not results:
            log.warning("  Empty page returned — stopping.")
            break

        inserted, skipped = insert_rows(con, results, existing)
        total_new += inserted

        log.info(
            f"  Page {page}: {len(results)} fetched, "
            f"{inserted} inserted, {skipped} skipped  "
            f"(API total: {total})"
        )

        page += 1
        if has_more:
            time.sleep(REQUEST_DELAY)

    log.info(
        f"Historical load complete — "
        f"{total_new} rows inserted, "
        f"{get_row_count(con)} total in database."
    )


# ---------------------------------------------------------------------------
# Mode 2: Daily increment
# ---------------------------------------------------------------------------

def daily_increment(con: duckdb.DuckDBPyConnection, latest_date: datetime.date) -> None:
    """
    Fetch answers from (latest_date + 1 day) to today using the from/to API params.
    Validates against existing puzzle_numbers before inserting.
    """
    from_date = latest_date + datetime.timedelta(days=1)
    to_date   = datetime.date.today()

    log.info(f"Fetching range: {from_date} → {to_date}")

    if from_date > to_date:
        log.info("Already up to date — nothing to fetch.")
        return

    # Fetch all pages for this date range
    all_results = []
    page        = 1
    has_more    = True

    while has_more:
        data     = fetch_page(page, from_date=from_date, to_date=to_date)
        results  = data.get("results", [])
        has_more = data.get("has_more", False)

        all_results.extend(results)
        page += 1

        if has_more:
            time.sleep(REQUEST_DELAY)

    if not all_results:
        log.info("No new results returned from API — nothing to insert.")
        return

    log.info(f"API returned {len(all_results)} record(s).")

    # Validate against what's already in DB for this date range
    existing          = get_existing_puzzle_numbers(con, from_date, to_date)
    inserted, skipped = insert_rows(con, all_results, existing)

    log.info(
        f"Done — {inserted} inserted, {skipped} skipped, "
        f"{get_row_count(con)} total in database."
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    con         = get_connection()
    latest_date = get_latest_date(con)

    if latest_date is None:
        log.info("Database is empty — running full historical load.")
        historical_load(con)
    else:
        log.info(f"Latest date in DB: {latest_date} — running daily increment.")
        daily_increment(con, latest_date)

    # Preview latest 5 rows
    log.info("Latest 5 rows in database:")
    for row in con.execute("""
        SELECT puzzle_number, answer, date, day_name, difficulty
        FROM raw_wordle_words
        ORDER BY puzzle_number DESC
        LIMIT 5
    """).fetchall():
        log.info(f"  #{row[0]}  {row[1]}  {row[2]}  {row[3]}  difficulty={row[4]}")

    con.close()


if __name__ == "__main__":
    main()