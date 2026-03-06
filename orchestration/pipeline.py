"""
pipeline.py
-----------
Orchestration script for the Wordle Analytics Pipeline.

Runs the full pipeline in order:
  1. extract_wordle.py  — ingest new data into DuckDB
  2. dbt seed           — load reference word list
  3. dbt run            — execute all transformation models
  4. dbt test           — validate data quality

Can be run:
  - Manually        : uv run python orchestration/pipeline.py
  - On a schedule   : uv run python orchestration/pipeline.py --schedule
                      (runs daily at 08:00 by default)
"""

import sys
import logging
import argparse
import subprocess
import schedule
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT  = Path(__file__).parent.parent
INGESTION_DIR = PROJECT_ROOT / "ingestion"
DBT_DIR       = PROJECT_ROOT / "dbt_wordle"
RUN_HOUR      = 8     # daily run time (24h format)
RUN_MINUTE    = 0

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
# Steps
# ---------------------------------------------------------------------------

def run_command(cmd: list[str], cwd: Path, step_name: str) -> bool:
    """
    Run a shell command, stream output live, return True if successful.
    """
    log.info(f"{'─' * 50}")
    log.info(f"STEP: {step_name}")
    log.info(f"CMD : {' '.join(cmd)}")
    log.info(f"CWD : {cwd}")
    log.info(f"{'─' * 50}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=False,   # stream stdout/stderr live to terminal
    )

    if result.returncode != 0:
        log.error(f"FAILED: {step_name} (exit code {result.returncode})")
        return False

    log.info(f"OK: {step_name}")
    return True


def step_ingest() -> bool:
    return run_command(
        cmd=["uv", "run", "python", "ingestion/extract_wordle.py"],
        cwd=PROJECT_ROOT,
        step_name="Ingest — extract_wordle.py",
    )


def step_dbt_seed() -> bool:
    return run_command(
        cmd=["uv", "run", "dbt", "seed", "--profiles-dir", "."],
        cwd=DBT_DIR,
        step_name="dbt seed — load reference word list",
    )


def step_dbt_run() -> bool:
    return run_command(
        cmd=["uv", "run", "dbt", "run", "--profiles-dir", "."],
        cwd=DBT_DIR,
        step_name="dbt run — execute transformation models",
    )


def step_dbt_test() -> bool:
    return run_command(
        cmd=["uv", "run", "dbt", "test", "--profiles-dir", "."],
        cwd=DBT_DIR,
        step_name="dbt test — validate data quality",
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> bool:
    """
    Execute the full pipeline in order.
    Stops immediately if any step fails.
    Returns True if all steps passed.
    """
    log.info("=" * 50)
    log.info("WORDLE ANALYTICS PIPELINE — START")
    log.info("=" * 50)

    steps = [
        step_ingest,
        step_dbt_seed,
        step_dbt_run,
        step_dbt_test,
    ]

    for step in steps:
        success = step()
        if not success:
            log.error("Pipeline stopped due to failure.")
            log.error("Fix the error above and re-run.")
            return False

    log.info("=" * 50)
    log.info("WORDLE ANALYTICS PIPELINE — COMPLETE")
    log.info("=" * 50)
    return True


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

def run_scheduled():
    """Run pipeline on a daily schedule."""
    run_time = f"{RUN_HOUR:02d}:{RUN_MINUTE:02d}"
    log.info(f"Scheduler started — pipeline will run daily at {run_time}.")
    log.info("Press Ctrl+C to stop.")

    schedule.every().day.at(run_time).do(run_pipeline)

    # Run once immediately on start so you don't wait until tomorrow
    log.info("Running pipeline now (initial run)...")
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Wordle Analytics Pipeline orchestrator."
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help=f"Run on a daily schedule at {RUN_HOUR:02d}:{RUN_MINUTE:02d}.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.schedule:
        run_scheduled()
    else:
        success = run_pipeline()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()