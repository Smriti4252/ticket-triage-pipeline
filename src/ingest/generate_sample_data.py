import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

subjects = [
    "Cannot login to my account",
    "Payment failed but money deducted",
    "App crashes on startup",
    "Need to upgrade my plan",
    "Wrong invoice amount",
    "Feature request: dark mode",
    "Password reset not working",
    "Refund not received yet",
    "Bug in export functionality",
    "How to cancel subscription",
    "API rate limit exceeded",
    "Data not syncing properly",
    "Billing charged twice",
    "New integration request",
    "Dashboard loading slowly",
    "Account suspended wrongly",
    "CSV import failing",
    "Mobile app not responding",
    "Change email address",
    "Need bulk discount pricing",
]

bodies = [
    "I have been trying to login for the past hour but keep getting an error.",
    "My payment failed but Rs 2000 was deducted from my account.",
    "The app crashes immediately after I open it on Android.",
    "I want to upgrade from free to pro plan.",
    "My invoice shows wrong amount, please check.",
    "Please add dark mode to the application.",
    "I requested password reset but never received the email.",
    "I cancelled my order 5 days ago but refund not received.",
    "When I try to export data as CSV, the file is empty.",
    "How do I cancel my monthly subscription?",
    "Getting 429 error when calling your API.",
    "My data from yesterday is not showing in the dashboard.",
    "I was charged twice for the same month.",
    "We need Slack integration for our team.",
    "The dashboard takes more than 30 seconds to load.",
    "My account was suspended without any warning or reason.",
    "CSV import keeps failing with no error message.",
    "The iOS app is not responding after the latest update.",
    "I need to change my registered email address.",
    "We have 50 users, can we get a bulk discount?",
]

tickets = []
base_date = datetime(2026, 1, 1)

for i in range(200):
    ticket = {
        "ticket_id": f"TKT-{1000 + i}",
        "subject": subjects[i % len(subjects)],
        "body": bodies[i % len(bodies)],
        "created_at": (base_date + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": f"customer{i}@example.com",
        "status": "new",
    }
    tickets.append(ticket)

df = pd.DataFrame(tickets)
df.to_csv("data/raw/tickets.csv", index=False)
print(f"Generated {len(df)} sample tickets → data/raw/tickets.csv")