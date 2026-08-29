import requests
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from itertools import repeat
import asyncio

def get_transactions(api_key, merchant_code, history=0, limit=0, _start = None, _end = None):
    url = f"https://api.sumup.com/v2.1/merchants/{merchant_code}/transactions/history"

    if _start is not None:
        date_string = _start + "T12:00:00Z"
        today = datetime.fromisoformat(date_string)
    else:
        today = datetime.now(ZoneInfo("Europe/Stockholm"))

    if _end is not None:
        date_string = _end + "T12:00:00Z"
        end = datetime.fromisoformat(date_string)
    else:
        end = datetime.now(ZoneInfo("Europe/Stockholm"))
    if history and _start is not None:
        today = datetime.now() - timedelta(days=history)
    start = datetime.combine(today, time.min, tzinfo=ZoneInfo("Europe/Stockholm"))
    if limit == 0:
        limit = 5000
    params = {
        "oldest_time": start.isoformat(),
        "newest_time": end.isoformat(),
        "order": "descending",
        "limit": limit,
        "statuses[]": "SUCCESSFUL"
    }

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["items"]

def get_transaction(api_key, merchant_code, transaction_id):
    url = f"https://api.sumup.com/v2.1/merchants/{merchant_code}/transactions"

    params = {
        "id": transaction_id
    }

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def get_transaction_details(api_key, merchant_code, mode=None, history=0, limit=0, start=None, end=None):
    products = {}
    transactions = get_transactions(api_key, merchant_code, history, limit, start, end)
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_transaction, repeat(api_key), repeat(merchant_code), (transaction["transaction_id"] for transaction in transactions))
        for transaction, details in tqdm(zip(transactions, results), total=len(transactions), desc=f"Heidrun || Bearbetar SumUP transaktioner för {merchant_code}"):
            if transaction.get("status") != "SUCCESSFUL":
                continue
            for product in details.get("products", []):
                if mode is not None:
                    filtered = product["name"].split("-")
                    if len(filtered) <= 1:
                        continue

                    if mode.strip().lower() not in filtered[0].strip().lower():
                        continue

                if product["name"] in products:
                    products[product["name"]][1] += int(product["quantity"])
                else:
                    products[product["name"]] = [product["name"], int(product["quantity"]), float(product["price"])]
    return products
