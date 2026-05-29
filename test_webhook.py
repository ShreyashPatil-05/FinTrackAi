"""
Mock Bank Webhook Simulator
Run this while the dev server is running to simulate bank transactions.



Usage:
    python test_webhook.py YOUR_TOKEN_HERE

Get your token from: http://127.0.0.1:8000/settings/upload/
(Settings -> Webhook section)
"""
import sys
import json
import urllib.request
import urllib.error
from datetime import date, timedelta

TOKEN = sys.argv[1] if len(sys.argv) > 1 else input("Paste your webhook token: ").strip()

BASE_URL = "http://127.0.0.1:8000/api/webhook/bank/"

# Sample transactions to simulate
TRANSACTIONS = [
    {"merchant": "Swiggy",          "amount": 450,   "category": "Food",          "date": str(date.today())},
    {"merchant": "Uber",            "amount": 220,   "category": "Transport",     "date": str(date.today())},
    {"merchant": "Netflix",         "amount": 649,   "category": "Subscription",  "date": str(date.today() - timedelta(days=1))},
    {"merchant": "Amazon",          "amount": 1299,  "category": "Shopping",      "date": str(date.today() - timedelta(days=2))},
    {"merchant": "Electricity Bill","amount": 1850,  "category": "Bills",         "date": str(date.today() - timedelta(days=3))},
    {"merchant": "Zomato",          "amount": 380,   "category": "Food",          "date": str(date.today() - timedelta(days=4))},
    {"merchant": "BookMyShow",      "amount": 560,   "category": "Entertainment", "date": str(date.today() - timedelta(days=5))},
]

def send_transaction(txn):
    data = json.dumps(txn).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Bank-Token": TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            print(f"  OK  #{result['expense_id']:>4}  {txn['merchant']:<20} ₹{txn['amount']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERR {e.code}  {txn['merchant']:<20} — {body}")
    except Exception as e:
        print(f"  ERR       {txn['merchant']:<20} — {e}")

print(f"\nSending {len(TRANSACTIONS)} mock bank transactions to {BASE_URL}\n")
for txn in TRANSACTIONS:
    send_transaction(txn)
print("\nDone. Refresh your dashboard to see the new expenses.")
