import time
from typing import Any, Dict

import requests
import streamlit as st


import os

API_URL = os.getenv(
    "API_URL",
    "https://store-intelligence-7v85.onrender.com/stores/STORE_BLR_002/metrics",
)

REFRESH_SECONDS = 5


def fetch_metrics() -> Dict[str, Any]:
    response = requests.get(API_URL, timeout=5)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Store Intelligence Dashboard", layout="wide")
st.title("Store Intelligence Dashboard")
st.caption("STORE_BLR_002")

placeholder = st.empty()

try:
    metrics = fetch_metrics()
    error_message = None
except requests.RequestException as exc:
    metrics = {}
    error_message = f"Unable to fetch metrics: {exc}"

with placeholder.container():
    if error_message:
        st.error(error_message)

    columns = st.columns(5)
    columns[0].metric("Total Visitors", metrics.get("unique_visitors", 0))
    columns[1].metric("Entry Count", metrics.get("entry_count", 0))
    columns[2].metric("Exit Count", metrics.get("exit_count", 0))
    columns[3].metric("Average Dwell Time", f"{metrics.get('avg_dwell_seconds', 0.0):.1f}s")
    columns[4].metric("Queue Depth", metrics.get("queue_depth", 0))

st.caption(f"Auto refreshes every {REFRESH_SECONDS} seconds.")
time.sleep(REFRESH_SECONDS)
st.rerun()
