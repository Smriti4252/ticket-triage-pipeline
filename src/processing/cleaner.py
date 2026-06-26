# cleaner.py
# Processing Layer: clean and normalize raw ticket data before sending to AI.
# Real support tickets often have HTML tags, extra spaces, or missing fields —
# this script handles all of that before AI classification.

import pandas as pd
import re


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text.
    Example: '<p>Hello <b>world</b></p>' → 'Hello world'
    """
    if not isinstance(text, str):
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)  # replace HTML tags with space
    clean = re.sub(r'\s+', ' ', clean)     # collapse multiple spaces
    return clean.strip()


def clean_text(text: str) -> str:
    """Lowercase, strip whitespace, remove special characters."""
    if not isinstance(text, str):
        return ""
    text = remove_html_tags(text)
    text = text.lower().strip()
    return text


def combine_subject_body(subject: str, body: str) -> str:
    """Combine subject and body into one field for AI.
    
    Why: AI gets better context when it sees both subject and body together.
    Format: 'Subject: <subject>\nBody: <body>'
    """
    subject = clean_text(subject)
    body = clean_text(body)
    return f"Subject: {subject}\nBody: {body}"


def clean_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """Main function: takes raw DataFrame, returns cleaned DataFrame.
    
    Steps:
    1. Fill missing values
    2. Clean subject and body text
    3. Combine subject + body into 'text_for_ai' column
    4. Add processing timestamp
    """
    df = df.copy()  # never modify original data

    # Step 1: Fill missing values
    df['subject'] = df['subject'].fillna('no subject')
    df['body'] = df['body'].fillna('no description')
    df['customer_email'] = df['customer_email'].fillna('unknown@unknown.com')

    # Step 2: Clean text fields
    df['subject_clean'] = df['subject'].apply(clean_text)
    df['body_clean'] = df['body'].apply(clean_text)

    # Step 3: Combine for AI input
    df['text_for_ai'] = df.apply(
        lambda row: combine_subject_body(row['subject'], row['body']),
        axis=1
    )

    # Step 4: Add processing timestamp
    df['processed_at'] = pd.Timestamp.now().isoformat()

    return df


if __name__ == "__main__":
    # Quick test — load raw tickets and clean them
    raw = pd.read_csv("data/raw/tickets.csv")
    print(f"Raw tickets: {len(raw)}")

    cleaned = clean_tickets(raw)
    print(f"Cleaned tickets: {len(cleaned)}")
    print("\nSample text_for_ai column:")
    print(cleaned['text_for_ai'].iloc[0])
    print("\nColumns after cleaning:")
    print(cleaned.columns.tolist())