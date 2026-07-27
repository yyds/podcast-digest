import os
import json
import time
import requests
from datetime import date, timedelta

MAX_RETRIES = 3


def http_get_with_retry(url, **kwargs):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[WARN] Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
    raise last_exc


def load_processed(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.load(f)
    return {}


def save_processed(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def filter_consecutive(items, id_key, processed_file):
    processed = load_processed(processed_file)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today_key = date.today().isoformat()

    filtered = []
    new_processed = {today_key: [str(it[id_key]) for it in items]}
    yesterday_ids = set(processed.get(yesterday, []))

    for item in items:
        if str(item[id_key]) in yesterday_ids:
            label = item.get("repo") or item.get("title") or str(item[id_key])
            print(f"[INFO] Skipping consecutive: {label[:60]}")
            continue
        filtered.append(item)

    save_processed(processed_file, new_processed)
    return filtered
