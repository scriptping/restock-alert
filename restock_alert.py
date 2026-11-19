#!/usr/bin/env python3
"""restock-alert: Check if a sold-out product is back in stock. Alert via ntfy.sh."""

import requests
from bs4 import BeautifulSoup
import schedule
import time
import json
import os
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "targets": [
        {
            "name": "Example Product",
            "url": "https://example.com/product",
            "in_stock_selector": "button.add-to-cart",
            "out_of_stock_text": "Sold Out",
        }
    ],
    "interval_min": 2,
    "ntfy_topic": "scriptping",
    "ntfy_server": "https://ntfy.sh",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Created {CONFIG_FILE}. Edit it, then re-run.")
    sys.exit(0)


def check_stock(t):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    r = requests.get(t["url"], headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Method 1: look for the in-stock element
    if t.get("in_stock_selector"):
        el = soup.select_one(t["in_stock_selector"])
        if el:
            # Check it's not disabled
            disabled = el.has_attr("disabled") or "disabled" in str(el)
            if not disabled:
                return True

    # Method 2: check that out-of-stock text is NOT on the page
    if t.get("out_of_stock_text"):
        if t["out_of_stock_text"].lower() not in r.text.lower():
            return True

    return False


def send_alert(cfg, name, url):
    msg = f"BACK IN STOCK: {name}\n{url}"
    try:
        requests.post(
            f"{cfg['ntfy_server']}/{cfg['ntfy_topic']}",
            data=msg.encode(),
            headers={"Title": "RESTOCK", "Priority": "max", "Tags": "package"},
            timeout=10,
        )
        print(f"[RESTOCK] {name}")
    except Exception as e:
        print(f"[ERROR] ntfy: {e}")


def check_all(cfg):
    for t in cfg["targets"]:
        try:
            if check_stock(t):
                if not t.get("was_in_stock"):
                    send_alert(cfg, t["name"], t["url"])
                    t["was_in_stock"] = True
            else:
                t["was_in_stock"] = False
                print(f"[OOS]  {t['name']}: out of stock")
        except Exception as e:
            print(f"[ERR]  {t['name']}: {e}")


def main():
    cfg = load_config()
    interval = cfg["interval_min"]
    print(f"restock-alert: {len(cfg['targets'])} target(s), every {interval} min")
    print(f"Alerts → {cfg['ntfy_server']}/{cfg['ntfy_topic']}")
    print("Ctrl+C to stop\n")
    check_all(cfg)
    schedule.every(interval).minutes.do(lambda: check_all(cfg))
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
