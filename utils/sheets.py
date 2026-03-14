"""
Google Sheets read/write logic using gspread + service account.

Three tabs:
  - DailyLog: every meal entry with date, meal type, and all nutrition fields
  - FoodLibrary: saved meals for quick reuse
  - BodyLog: date, weight_kg, body_fat_pct
"""

import json
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from utils.parser import ALL_FIELDS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DAILY_LOG_HEADERS = ["date", "meal_type", "meal_name"] + ALL_FIELDS
FOOD_LIBRARY_HEADERS = ["meal_name"] + ALL_FIELDS
BODY_LOG_HEADERS = ["date", "weight_kg", "body_fat_pct"]


@st.cache_resource(ttl=300)
def _get_client():
    """Return an authorized gspread client using Streamlit secrets."""
    creds_dict = json.loads(st.secrets["gcp"]["credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet():
    """Return the Google Sheet workbook."""
    client = _get_client()
    return client.open_by_key(st.secrets["gcp"]["sheet_id"])


def _ensure_headers(ws, headers: list[str]):
    """If the worksheet is empty, write the header row."""
    if ws.row_count == 0 or not ws.row_values(1):
        ws.append_row(headers, value_input_option="RAW")
    else:
        existing = ws.row_values(1)
        if existing != headers:
            ws.update("A1", [headers], value_input_option="RAW")


def _get_or_create_worksheet(sheet, title: str, headers: list[str]):
    """Get a worksheet by title, creating it if it doesn't exist."""
    try:
        ws = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=1000, cols=len(headers))
    _ensure_headers(ws, headers)
    return ws


# --- DailyLog ---

def load_log() -> pd.DataFrame:
    """Read the DailyLog tab into a DataFrame."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "DailyLog", DAILY_LOG_HEADERS)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=DAILY_LOG_HEADERS)
    df = pd.DataFrame(data)
    for col in ALL_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def save_entry(row: dict):
    """Append a new entry to DailyLog."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "DailyLog", DAILY_LOG_HEADERS)
    values = [row.get(h, 0) for h in DAILY_LOG_HEADERS]
    ws.append_row(values, value_input_option="USER_ENTERED")
    load_log.clear()


def delete_entry(row_index: int):
    """Delete a row from DailyLog by its 1-based sheet row index."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "DailyLog", DAILY_LOG_HEADERS)
    ws.delete_rows(row_index)
    load_log.clear()


# --- FoodLibrary ---

def load_food_library() -> pd.DataFrame:
    """Read the FoodLibrary tab into a DataFrame."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "FoodLibrary", FOOD_LIBRARY_HEADERS)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=FOOD_LIBRARY_HEADERS)
    df = pd.DataFrame(data)
    for col in ALL_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def save_to_library(entry: dict):
    """Save a parsed meal to FoodLibrary."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "FoodLibrary", FOOD_LIBRARY_HEADERS)
    values = [entry.get(h, 0) for h in FOOD_LIBRARY_HEADERS]
    ws.append_row(values, value_input_option="USER_ENTERED")
    load_food_library.clear()


def delete_from_library(row_index: int):
    """Delete a row from FoodLibrary by its 1-based sheet row index."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "FoodLibrary", FOOD_LIBRARY_HEADERS)
    ws.delete_rows(row_index)
    load_food_library.clear()


# --- BodyLog ---

def load_body_log() -> pd.DataFrame:
    """Read the BodyLog tab into a DataFrame."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "BodyLog", BODY_LOG_HEADERS)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=BODY_LOG_HEADERS)
    df = pd.DataFrame(data)
    df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")
    df["body_fat_pct"] = pd.to_numeric(df["body_fat_pct"], errors="coerce")
    return df


def save_body_entry(row: dict):
    """Append a body composition entry."""
    sheet = _get_sheet()
    ws = _get_or_create_worksheet(sheet, "BodyLog", BODY_LOG_HEADERS)
    values = [row.get(h, "") for h in BODY_LOG_HEADERS]
    ws.append_row(values, value_input_option="USER_ENTERED")
    load_body_log.clear()
