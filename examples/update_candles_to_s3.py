"""Example script to fetch intraday candle data at the end of the day.

This script demonstrates how to use the ``dhanhq`` client library to retrieve
intraday minute candles for multiple indices and store them on S3. It is
intended to be run **once at the end of the trading day** so that only a single
set of API calls is made. Credentials and security ids are expected to be
supplied via environment variables.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Iterable

import pandas as pd
import boto3

from dhanhq import DhanContext, dhanhq

# Environment variables for dhan credentials
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")

# Security identifiers for the indices
NIFTY50_ID = os.environ.get("NIFTY50_SECURITY_ID", "13")
NIFTYBANK_ID = os.environ.get("NIFTYBANK_SECURITY_ID", "12")
SENSEX_ID = os.environ.get("SENSEX_SECURITY_ID", "100000000")

# S3 bucket name
BUCKET = os.environ.get("S3_BUCKET", "algobymarti-indian-stock-market-data")

# Mapping from index name to its security id and S3 prefix
INDEX_CONFIG = {
    "01-Nifty50": NIFTY50_ID,
    "02-NiftyBank": NIFTYBANK_ID,
    "03-Sensex": SENSEX_ID,
}

# Timeframes in minutes and their folder names
TIMEFRAMES = {
    1: "1-Minutes-Candles/",
    5: "5-Minutes-Candles/",
    15: "15-Minutes-Candles/",
    25: "25-minute-candle/",
    60: "60-minute-Candle/",
}

def fetch_candles(client: dhanhq, security_id: str, interval: int) -> pd.DataFrame:
    """Fetch intraday candle data for a single trading day."""
    trading_day = date.today()
    from_date = trading_day.isoformat()
    to_date = trading_day.isoformat()
    response = client.intraday_minute_data(
        security_id,
        client.INDEX,
        "INDEX",
        from_date,
        to_date,
        interval=interval,
    )
    if response["status"] != "success":
        raise RuntimeError(f"Request failed: {response['remarks']}")
    return pd.DataFrame(response["data"])

def upload_dataframe(s3, df: pd.DataFrame, key: str) -> None:
    """Upload dataframe as CSV to S3."""
    csv_data = df.to_csv(index=False).encode()
    s3.put_object(Bucket=BUCKET, Key=key, Body=csv_data)


def update_index_data(index_name: str, security_id: str, client: dhanhq, s3) -> None:
    """Fetch candles for all intervals and upload them to S3."""
    for interval, prefix in TIMEFRAMES.items():
        df = fetch_candles(client, security_id, interval)
        key = f"{index_name}/{prefix}{date.today().isoformat()}.csv"
        upload_dataframe(s3, df, key)
        print(f"Uploaded {key}")


def main(indices: Iterable[str] | None = None) -> None:
    if CLIENT_ID is None or ACCESS_TOKEN is None:
        raise RuntimeError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set")

    context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
    client = dhanhq(context)
    s3 = boto3.client("s3")

    indices = indices or INDEX_CONFIG.keys()
    for name in indices:
        security_id = INDEX_CONFIG[name]
        update_index_data(name, security_id, client, s3)

if __name__ == "__main__":
    main()
