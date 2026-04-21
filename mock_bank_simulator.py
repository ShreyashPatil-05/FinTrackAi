"""
FinTrack - Mock Bank Simulator
Simulates a bank sending transactions to the FinTrack webhook.

Usage:
    python mock_bank_simulator.py

Make sure Django server is running first:
    python manage.py runserver
"""
import requests
import random
import time
from datetime import date

# ── Config ────────────────────────────────────────────────
WEBHOOK_URL    = 'http://127.0.0.1:8000/api/webhook/bank/'
WEBHOOK_SECRET = 'fintrack-mock-bank-secret-2026'
USER_ID        = 2   # Change to your user's ID (check Django admin)
INTERVAL       = 8   # seconds between transactions

# ── Simulated transactions ────────────────────────────────
TRANSACTIONS = [
    {'merchant': 'Swiggy',          'category': 'Food',          'amount': 320},
    {'merchant': 'Zomato',          'category': 'Food',          'amount': 280},
    {'merchant': 'Uber',            'category': 'Transport',     'amount': 150},
    {'merchant': 'Ola',             'category': 'Transport',     'amount': 120},
    {'merchant': 'DMart',           'category': 'Shopping',      'amount': 1450},
    {'merchant': 'Amazon',          'category': 'Shopping',      'amount': 899},
    {'merchant': 'Netflix',         'category': 'Subscription',  'amount': 649},
    {'merchant': 'Spotify',         'category': 'Subscription',  'amount': 119},
    {'merchant': 'Electricity Bill','category': 'Bills',         'amount': 1200},
    {'merchant': 'Airtel Recharge', 'category': 'Bills',         'amount': 299},
    {'merchant': 'BookMyShow',      'category': 'Entertainment', 'amount': 450},
    {'merchant': 'PVR Cinemas',     'category': 'Entertainment', 'amount': 380},
    {'merchant': 'MakeMyTrip',      'category': 'Travel',        'amount': 3200},
    {'merchant': 'IRCTC',           'category': 'Travel',        'amount': 850},
    {'merchant': 'Apollo Pharmacy', 'category': 'Bills',         'amount': 560},
]


def send_transaction(txn):
    payload = {
        'user_id':  USER_ID,
        'merchant': txn['merchant'],
        'category': txn['category'],
        'amount':   txn['amount'] + random.randint(-50, 50),  # slight variation
        'date':     str(date.today()),
    }
    headers = {'X-Bank-Token': WEBHOOK_SECRET, 'Content-Type': 'application/json'}

    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=5)
        if response.status_code == 201:
            data = response.json()
            print(f"[SENT]  {data['title']:<25} {data['category']:<15} Rs.{data['amount']}")
        else:
            print(f"[ERROR] {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect. Is the Django server running?")


if __name__ == '__main__':
    print("=" * 55)
    print("  FinTrack Mock Bank Simulator")
    print(f"  Sending to: {WEBHOOK_URL}")
    print(f"  User ID:    {USER_ID}")
    print(f"  Interval:   {INTERVAL}s")
    print("=" * 55)
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            txn = random.choice(TRANSACTIONS)
            send_transaction(txn)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
