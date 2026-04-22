"""
FinTrack - Mock Bank Simulator
Simulates a bank sending transactions to the FinTrack webhook.

Setup:
    1. Go to http://127.0.0.1:8000/admin/
    2. Dashboard > Webhook Tokens > Add > select your user > Save
    3. Copy the generated token and paste it below as WEBHOOK_SECRET
    4. Run: python mock_bank_simulator.py

Make sure Django server is running first:
    python manage.py runserver
"""
import requests
import random
import time
from datetime import date

# ── Config ────────────────────────────────────────────────
WEBHOOK_URL    = 'http://127.0.0.1:8000/api/webhook/bank/'
WEBHOOK_SECRET = 'paste-your-webhook-token-here'  # from Django admin > Webhook Tokens
INTERVAL       = 8   # seconds between transactions

# ── Simulated transactions ────────────────────────────────
TRANSACTIONS = [
    {'merchant': 'Swiggy',           'category': 'Food',          'amount': 320},
    {'merchant': 'Zomato',           'category': 'Food',          'amount': 280},
    {'merchant': 'Uber',             'category': 'Transport',     'amount': 150},
    {'merchant': 'Ola',              'category': 'Transport',     'amount': 120},
    {'merchant': 'DMart',            'category': 'Shopping',      'amount': 1450},
    {'merchant': 'Amazon',           'category': 'Shopping',      'amount': 899},
    {'merchant': 'Netflix',          'category': 'Subscription',  'amount': 649},
    {'merchant': 'Spotify',          'category': 'Subscription',  'amount': 119},
    {'merchant': 'Electricity Bill', 'category': 'Bills',         'amount': 1200},
    {'merchant': 'Airtel Recharge',  'category': 'Bills',         'amount': 299},
    {'merchant': 'BookMyShow',       'category': 'Entertainment', 'amount': 450},
    {'merchant': 'PVR Cinemas',      'category': 'Entertainment', 'amount': 380},
    {'merchant': 'MakeMyTrip',       'category': 'Travel',        'amount': 3200},
    {'merchant': 'IRCTC',            'category': 'Travel',        'amount': 850},
    {'merchant': 'Apollo Pharmacy',  'category': 'Bills',         'amount': 560},
]

# Category emoji map for nicer output
EMOJI = {
    'Food': '🍔', 'Transport': '🚗', 'Shopping': '🛍️',
    'Bills': '💡', 'Subscription': '📺', 'Entertainment': '🎬',
    'Travel': '✈️', 'Other': '📦',
}


def send_transaction(txn):
    amount = txn['amount'] + random.randint(-50, 50)
    payload = {
        'merchant': txn['merchant'],
        'category': txn['category'],
        'amount':   amount,
        'date':     str(date.today()),
    }
    headers = {'X-Bank-Token': WEBHOOK_SECRET, 'Content-Type': 'application/json'}

    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=5)
        if response.status_code == 201:
            data = response.json()
            emoji = EMOJI.get(data['category'], '📦')
            print(f"  {emoji}  {data['title']:<22} {data['category']:<15} ₹{data['amount']}")
        elif response.status_code == 401:
            print("  [AUTH ERROR] Invalid token. Check WEBHOOK_SECRET in this file.")
            print("               Go to Django admin > Webhook Tokens to get your token.")
        else:
            print(f"  [ERROR] {response.status_code} — {response.text}")
    except requests.exceptions.ConnectionError:
        print("  [CONNECTION ERROR] Could not reach the server.")
        print("  Make sure Django is running: python manage.py runserver")


if __name__ == '__main__':
    # Guard — prevent running with placeholder token
    if WEBHOOK_SECRET == 'paste-your-webhook-token-here':
        print("\n  ERROR: WEBHOOK_SECRET is not set.")
        print("  Steps:")
        print("  1. Go to http://127.0.0.1:8000/admin/")
        print("  2. Dashboard > Webhook Tokens > Add > select your user > Save")
        print("  3. Copy the token and paste it as WEBHOOK_SECRET in this file")
        print()
        exit(1)

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │       FinTrack Mock Bank Simulator          │")
    print("  ├─────────────────────────────────────────────┤")
    print(f"  │  URL:      {WEBHOOK_URL:<33}│")
    print(f"  │  Interval: every {INTERVAL}s{' ' * 26}│")
    print("  └─────────────────────────────────────────────┘")
    print("  Press Ctrl+C to stop\n")

    count = 0
    try:
        while True:
            txn = random.choice(TRANSACTIONS)
            send_transaction(txn)
            count += 1
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n  Simulator stopped. {count} transaction(s) sent.")
