# db.py
# Storage Layer: DuckDB operations for ticket storage and retrieval.
#
# Why DuckDB?
# - Zero setup (no server needed, embedded like SQLite)
# - Fast analytical queries (perfect for dashboard aggregations)
# - Native Parquet support (future extension possible)
# - Already proven in our Job Aggregation Pipeline

import duckdb
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "data/tickets.duckdb"


def get_connection():
    """Return a DuckDB connection.
    
    DuckDB is file-based — connection automatically creates
    the .duckdb file if it doesn't exist.
    """
    return duckdb.connect(DB_PATH)


def create_tables():
    """Create tickets table if it doesn't exist.
    
    We use CREATE TABLE IF NOT EXISTS so this function
    is safe to call multiple times (idempotent).
    """
    con = get_connection()
    con.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id       VARCHAR PRIMARY KEY,
            subject         VARCHAR,
            body            VARCHAR,
            subject_clean   VARCHAR,
            body_clean      VARCHAR,
            text_for_ai     VARCHAR,
            customer_email  VARCHAR,
            created_at      VARCHAR,
            processed_at    VARCHAR,
            status          VARCHAR DEFAULT 'new',
            category        VARCHAR,
            priority        VARCHAR,
            summary         VARCHAR,
            classified_at   VARCHAR
        )
    """)
    con.close()
    logger.info("Tables created/verified successfully.")


def insert_classified_tickets(cleaned_df: pd.DataFrame, classifications: list):
    """Merge cleaned ticket data with AI classification results and insert to DB.
    
    Args:
        cleaned_df: DataFrame from cleaner.py
        classifications: list of dicts from classifier.py
            each dict has: ticket_id, category, priority, summary
    """
    # Convert classifications list to DataFrame
    class_df = pd.DataFrame(classifications)

    # Merge on ticket_id
    merged = cleaned_df.merge(class_df, on="ticket_id", how="left")

    # Add classification timestamp
    merged["classified_at"] = datetime.now().isoformat()

    # Select only columns that match our table schema
    final = merged[[
        "ticket_id", "subject", "body", "subject_clean", "body_clean",
        "text_for_ai", "customer_email", "created_at", "processed_at",
        "status", "category", "priority", "summary", "classified_at"
    ]]

    con = get_connection()

    # INSERT OR REPLACE — if ticket_id already exists, update it
    # This makes the pipeline idempotent (safe to run multiple times)
    con.execute("""
        INSERT OR REPLACE INTO tickets
        SELECT * FROM final
    """)

    count = con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    con.close()

    logger.info(f"Inserted/updated {len(final)} tickets. Total in DB: {count}")
    return len(final)


def get_all_tickets(status: str = None) -> pd.DataFrame:
    """Fetch all tickets from DB, optionally filtered by status."""
    con = get_connection()
    if status:
        df = con.execute(
            "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC",
            [status]
        ).df()
    else:
        df = con.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        ).df()
    con.close()
    return df


def get_ticket_by_id(ticket_id: str) -> dict:
    """Fetch single ticket by ID."""
    con = get_connection()
    result = con.execute(
        "SELECT * FROM tickets WHERE ticket_id = ?",
        [ticket_id]
    ).df()
    con.close()
    if len(result) == 0:
        return None
    return result.iloc[0].to_dict()


def update_ticket_status(ticket_id: str, new_status: str) -> bool:
    """Update ticket status.
    
    Valid statuses: new → in_review → assigned → resolved
    """
    valid_statuses = ["new", "in_review", "assigned", "resolved"]
    if new_status not in valid_statuses:
        logger.error(f"Invalid status: {new_status}")
        return False

    con = get_connection()
    con.execute(
        "UPDATE tickets SET status = ? WHERE ticket_id = ?",
        [new_status, ticket_id]
    )
    con.close()
    logger.info(f"Ticket {ticket_id} status updated to {new_status}")
    return True


def get_stats() -> dict:
    """Aggregated stats for dashboard.
    
    Returns counts by category, priority, and status.
    """
    con = get_connection()

    total = con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]

    by_category = con.execute("""
        SELECT category, COUNT(*) as count
        FROM tickets
        GROUP BY category
        ORDER BY count DESC
    """).df().to_dict('records')

    by_priority = con.execute("""
        SELECT priority, COUNT(*) as count
        FROM tickets
        GROUP BY priority
        ORDER BY count DESC
    """).df().to_dict('records')

    by_status = con.execute("""
        SELECT status, COUNT(*) as count
        FROM tickets
        GROUP BY status
        ORDER BY count DESC
    """).df().to_dict('records')

    con.close()

    return {
        "total": total,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
    }


if __name__ == "__main__":
    # Quick test
    create_tables()
    print("Tables created successfully.")
    print(f"DB path: {DB_PATH}")

    stats = get_stats()
    print(f"Total tickets in DB: {stats['total']}")