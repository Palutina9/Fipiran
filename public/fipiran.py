# -*- coding: utf-8 -*-
"""
Created on Mon Sep 14 08:58:42 2026

@author: p.mahmoudi
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jdatetime

fundcompare_url = "https://fipiran.ir/services/fund/fundcompare"
fundtype_url = "https://fipiran.ir/services/fund/fundtype"

current_date = datetime(2026, 9, 14).date()
end_date = datetime.today().date()
date = current_date.strftime("%Y-%m-%dT07:56:00.000Z")

fundcompare_payload = {
    "regNos": [],
    "showMarketMakers": "false",
    "date": date
    }

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://codal.ir/",
}

doreha = {
    "roozaneh": "dailyEfficiency",
    "haftegi": "weeklyEfficiency",
    "mahaneh": "monthlyEfficiency",
    "fasli": "quarterlyEfficiency",
    "sheshmah": "sixMonthEfficiency",
    "salaneh": "annualEfficiency"
    }


HISTORY_FILE = Path("fund_data.json")
 
TARGET_REG_NO = 10787
 
 
def safe_get(url, timeout=15):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"GET {url} failed: {e}")
        return None
 
 
def safe_post(url, payload, timeout=15):
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"POST {url} failed: {e}")
        return None
 
 
def fetch_fund_types():
    data = safe_get(fundtype_url)
    if not data:
        return {}
    return {item["fundType"]: item["name"] for item in data.get("items", [])}
 
 
def fetch_funds():
    data = safe_post(fundcompare_url, fundcompare_payload)
    if not data:
        return []
    return data.get("items", [])
 
 
def compute_ranks(funds, target_reg_no):
    target = next((f for f in funds if str(f.get("regNo")) == str(target_reg_no)), None)
    if target is None:
        print(f"Fund with regNo {target_reg_no} not found in response.")
        return None
 
    peer_group = [f for f in funds if f.get("fundType") == target.get("fundType")]
 
    ranks = {}
    values = {}
    for label, field in doreha.items():
        # sort peer group descending by this period's return; ties keep stable order
        sorted_group = sorted(peer_group, key=lambda f: f.get(field, float("-inf")), reverse=True)
        for idx, f in enumerate(sorted_group, start=1):
            if str(f.get("regNo")) == str(target_reg_no):
                ranks[label] = idx
                values[label] = f.get(field)
                break
 
    return {
        "date": current_date.isoformat(),
        "tarikh": jdatetime.date.fromgregorian(date=current_date).isoformat(),
        "regNo": target.get("regNo"),
        "name": target.get("name"),
        "fundType": target.get("fundType"),
        "peerGroupSize": len(peer_group),
        "ranks": ranks,
        "values": values,
    }
 
 
def append_history(snapshot):
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"{HISTORY_FILE} was unreadable/corrupt, starting a new history list.")
            history = []
 
    snapshot_with_date = {
        "date": datetime.now(timezone.utc).astimezone().date().isoformat(),
        **snapshot,
    }
    already_exists = any(entry["date"] == snapshot_with_date["date"] for entry in history)

    if not already_exists:
        history.append(snapshot_with_date)
    else:
        print(f"{snapshot_with_date['date']} already in history, skipping.")
        
 
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Appended snapshot for {snapshot['name']} (regNo {snapshot['regNo']}) to {HISTORY_FILE}")
 
 
def main():
    if not TARGET_REG_NO:
        print("Set TARGET_REG_NO near the top of this file before running.")
        return
 
    fund_types = fetch_fund_types()
    funds = fetch_funds()
    if not funds:
        print("No fund data fetched — check FUNDCOMPARE_PAYLOAD / URL.")
        return
 
    snapshot = compute_ranks(funds, TARGET_REG_NO)
    if snapshot is None:
        return
 
    snapshot["fundTypeName"] = fund_types.get(snapshot["fundType"], "unknown")
    append_history(snapshot)
 
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
 
 
if __name__ == "__main__":
    while current_date <= end_date:
        date = current_date.strftime("%Y-%m-%dT07:56:00.000Z")
        main()
        current_date +=timedelta(days=1)
