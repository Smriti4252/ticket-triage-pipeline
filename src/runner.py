# runner.py
# Main orchestrator: runs the full ticket triage pipeline
# Ingest -> Clean -> AI Classify -> Store in DuckDB

import sys
import os
import logging
import pandas as pd
from datetime import datetime

# Add src to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processing.cleaner import clean_tickets
from ai.classifier import classify_batch
from storage.db import create_tables, insert_classified_tickets, get_stats

# Setup logging — console + file both
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"pipeline_{datetime.now().strftime('%Y%m%dT%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
        ),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger("ticket_triage_runner")

RAW_DATA_PATH = "data/raw/tickets_real.csv"


def run(limit: int = None):
    """Run the full ticket triage pipeline.

    Args:
        limit: if set, only process first N tickets (useful for testing)
    """
    logger.info("=" * 50)
    logger.info("Starting Ticket Triage Pipeline")
    logger.info("=" * 50)

    # Step 1: Ingest
    logger.info("Step 1: Loading raw tickets from CSV")
    try:
        df = pd.read_csv(RAW_DATA_PATH)
        if limit:
            df = df.head(limit)
            logger.info(f"  Limit set: processing first {limit} tickets")
        logger.info(f"  Loaded {len(df)} tickets from {RAW_DATA_PATH}")
    except FileNotFoundError:
        logger.error(f"  File not found: {RAW_DATA_PATH}")
        logger.error("  Run generate_sample_data.py first!")
        return

    # Step 2: Clean
    logger.info("Step 2: Cleaning and normalizing ticket text")
    cleaned = clean_tickets(df)
    logger.info(f"  Cleaned {len(cleaned)} tickets successfully")

    # Step 3: AI Classify
    logger.info("Step 3: AI Classification using Groq API (LLaMA 3.3)")
    tickets_for_ai = cleaned[['ticket_id', 'text_for_ai']].to_dict('records')
    classifications = classify_batch(tickets_for_ai, delay=0.5)
    logger.info(f"  Classified {len(classifications)} tickets")

    # Step 4: Store
    logger.info("Step 4: Storing results in DuckDB")
    create_tables()
    inserted = insert_classified_tickets(cleaned, classifications)
    logger.info(f"  Inserted/updated {inserted} tickets in DuckDB")

    # Step 5: Summary
    stats = get_stats()
    logger.info("=" * 50)
    logger.info("Pipeline Complete! Summary:")
    logger.info(f"  Total tickets in DB : {stats['total']}")
    logger.info(f"  By Category         : {stats['by_category']}")
    logger.info(f"  By Priority         : {stats['by_priority']}")
    logger.info("=" * 50)
    logger.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    run()