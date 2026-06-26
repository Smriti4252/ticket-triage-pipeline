# kaggle_adapter.py
# Adapter: converts Kaggle customer support dataset format
# into our pipeline's standard format (same as generate_sample_data.py output)
#
# Kaggle columns  →  Our pipeline columns
# Ticket ID       →  ticket_id
# Ticket Subject  →  subject
# Ticket Description → body
# Customer Email  →  customer_email
# Date of Purchase → created_at
# Ticket Status   →  status (mapped to our format)
# (rest skipped — not needed for classification)

import pandas as pd
import re


# Map Kaggle ticket status to our status format
STATUS_MAP = {
    'open': 'new',
    'pending customer response': 'in_review',
    'closed': 'resolved',
}


def adapt_kaggle_data(
    input_path: str = "data/raw/customer_support_tickets.csv",
    output_path: str = "data/raw/tickets_real.csv",
    limit: int = None
) -> pd.DataFrame:
    """Load Kaggle dataset and convert to our pipeline format.

    Args:
        input_path: path to Kaggle CSV
        output_path: where to save adapted CSV
        limit: if set, only process first N rows (for testing)

    Returns:
        Adapted DataFrame
    """
    print(f"Loading Kaggle dataset from {input_path}...")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    if limit:
        df = df.head(limit)
        print(f"Limiting to first {limit} rows")

    # ── Build adapted DataFrame ──────────────────────────────────────
    adapted = pd.DataFrame()

    # ticket_id: "Ticket ID" → "TKT-REAL-1", "TKT-REAL-2" etc
    # We prefix with "REAL" to distinguish from dummy data
    adapted['ticket_id'] = df['Ticket ID'].apply(lambda x: f"TKT-REAL-{x}")

    # subject: use Ticket Subject directly
    adapted['subject'] = df['Ticket Subject'].fillna('No subject')

    # body: use Ticket Description — clean template placeholders
    # Kaggle data has placeholders like {product_purchased} in text
    adapted['body'] = df['Ticket Description'].fillna('No description').apply(clean_body)

    # customer_email
    adapted['customer_email'] = df['Customer Email'].fillna('unknown@unknown.com')

    # created_at: use Date of Purchase
    adapted['created_at'] = pd.to_datetime(
        df['Date of Purchase'], errors='coerce'
    ).dt.strftime('%Y-%m-%d %H:%M:%S').fillna('2024-01-01 00:00:00')

    # status: map Kaggle status to our format
    adapted['status'] = df['Ticket Status'].str.lower().map(STATUS_MAP).fillna('new')

    # ── Print summary ────────────────────────────────────────────────
    print(f"\nAdapted {len(adapted)} tickets")
    print(f"Status distribution:\n{adapted['status'].value_counts()}")
    print(f"\nSample ticket:")
    print(f"  ticket_id : {adapted['ticket_id'].iloc[0]}")
    print(f"  subject   : {adapted['subject'].iloc[0]}")
    print(f"  body      : {adapted['body'].iloc[0][:100]}...")
    print(f"  status    : {adapted['status'].iloc[0]}")

    # ── Save ─────────────────────────────────────────────────────────
    adapted.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")

    return adapted


def clean_body(text: str) -> str:
    """Clean Kaggle template placeholders from ticket body.

    Kaggle data has patterns like:
    "I'm having an issue with the {product_purchased}. Please assist."
    We remove these placeholders for cleaner AI classification.
    """
    if not isinstance(text, str):
        return ""
    # Remove {placeholder} patterns
    cleaned = re.sub(r'\{[^}]+\}', '', text)
    # Remove extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


if __name__ == "__main__":
    # Test with 50 tickets first
    adapted = adapt_kaggle_data(
    input_path="data/raw/customer_support_tickets.csv",
    output_path="data/raw/tickets_real.csv",
)
    
    print(f"\nColumns: {adapted.columns.tolist()}")
    print(adapted.head(3).to_string())