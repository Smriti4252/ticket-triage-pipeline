# classifier.py
# AI Layer: send cleaned ticket text to Groq API (LLaMA 3.3)
# and get back category, priority, and a 2-line summary.
#
# Why Groq? It's free, fast (low latency), and LLaMA 3.3 is strong
# enough for classification tasks like this.

import os
import json
import time
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # load GROQ_API_KEY from .env file

logger = logging.getLogger(__name__)

# Initialize Groq client once (reuse across calls)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Valid categories and priorities — AI must return only these values
VALID_CATEGORIES = ["billing", "bug", "feature_request", "account_issue", "general"]
VALID_PRIORITIES = ["HIGH", "MEDIUM", "LOW"]

# This is the prompt we send to LLM — called "system prompt"
# It tells the AI exactly what to do and what format to return
SYSTEM_PROMPT = """You are a customer support ticket classifier.

Given a support ticket (subject + body), you must return a JSON object with exactly these fields:
- category: one of [billing, bug, feature_request, account_issue, general]
- priority: one of [HIGH, MEDIUM, LOW]
- summary: a 2-line summary of the ticket for support agents

Priority rules:
- HIGH: payment issues, account suspended, data loss, cannot login
- MEDIUM: bugs, errors, performance issues, sync problems
- LOW: feature requests, general questions, how-to queries

Category rules:
- billing: payment, invoice, refund, charge, subscription cost
- bug: crash, error, not working, failing, broken
- feature_request: please add, need, want, suggestion, integration
- account_issue: login, password, account suspended, email change, access
- general: general questions, how-to, cancel subscription

Return ONLY valid JSON. No explanation, no markdown, no extra text.

Example output:
{"category": "account_issue", "priority": "HIGH", "summary": "Customer cannot login for past hour. Getting error on login page."}"""


def classify_ticket(text_for_ai: str, ticket_id: str = "") -> dict:
    """Send one ticket to Groq API and get classification back.
    
    Args:
        text_for_ai: Combined subject + body text (from cleaner.py)
        ticket_id: For logging purposes only
    
    Returns:
        dict with keys: category, priority, summary
        Returns default values if API call fails.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Groq's fast LLaMA 3.3 model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text_for_ai}
            ],
            temperature=0.1,   # low temperature = more consistent/deterministic output
            max_tokens=200,    # we only need a short JSON response
        )

        # Extract the text response from API
        raw_output = response.choices[0].message.content.strip()

        # Parse JSON response
        result = json.loads(raw_output)

        # Validate — make sure AI returned valid values
        if result.get("category") not in VALID_CATEGORIES:
            result["category"] = "general"
        if result.get("priority") not in VALID_PRIORITIES:
            result["priority"] = "MEDIUM"
        if not result.get("summary"):
            result["summary"] = "No summary available."

        logger.info(f"Ticket {ticket_id} -> {result['category']} | {result['priority']}")
        return result

    except json.JSONDecodeError as e:
        # AI returned non-JSON response — use defaults
        logger.error(f"JSON parse error for {ticket_id}: {e}")
        return {"category": "general", "priority": "MEDIUM", "summary": "Classification failed — manual review needed."}

    except Exception as e:
        logger.error(f"API error for {ticket_id}: {e}")
        return {"category": "general", "priority": "MEDIUM", "summary": "Classification failed — manual review needed."}


def classify_batch(tickets: list, delay: float = 0.5) -> list:
    """Classify a list of tickets one by one.
    
    Args:
        tickets: list of dicts with keys: ticket_id, text_for_ai
        delay: seconds to wait between API calls (avoid rate limiting)
    
    Returns:
        list of dicts with classification results added
    """
    results = []
    total = len(tickets)

    for i, ticket in enumerate(tickets):
        print(f"Classifying {i+1}/{total} — {ticket['ticket_id']}...")

        result = classify_ticket(
            text_for_ai=ticket['text_for_ai'],
            ticket_id=ticket['ticket_id']
        )

        results.append({
            "ticket_id": ticket['ticket_id'],
            "category": result["category"],
            "priority": result["priority"],
            "summary": result["summary"],
        })

        # Small delay between API calls to avoid rate limiting
        # Groq free tier: 30 requests/minute
        if i < total - 1:
            time.sleep(delay)

    return results


if __name__ == "__main__":
    # Quick test — classify first 5 tickets only
    import pandas as pd
    import sys
    sys.path.insert(0, "src")
    from processing.cleaner import clean_tickets

    raw = pd.read_csv("data/raw/tickets.csv")
    cleaned = clean_tickets(raw)

    # Test with first 5 tickets only (save API quota)
    sample = cleaned.head(5)[['ticket_id', 'text_for_ai']].to_dict('records')

    print("Testing AI classifier on 5 tickets...\n")
    results = classify_batch(sample, delay=1.0)

    print("\nResults:")
    for r in results:
        print(f"{r['ticket_id']} | {r['category']} | {r['priority']}")
        print(f"  Summary: {r['summary']}\n")