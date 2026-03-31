import os
import requests
from dotenv import load_dotenv

load_dotenv()

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageError(Exception):
    pass


def _get(params):
    if not ALPHAVANTAGE_API_KEY:
        raise AlphaVantageError("Missing ALPHAVANTAGE_API_KEY in environment/.env")
    params["apikey"] = ALPHAVANTAGE_API_KEY
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "Note" in data:
        # Rate limit or similar
        raise AlphaVantageError(data["Note"])
    if "Error Message" in data:
        raise AlphaVantageError(data["Error Message"])
    return data


def get_company_overview(symbol: str) -> dict:
    """Basic fundamentals like PE, dividend yield, payout, etc."""
    params = {
        "function": "OVERVIEW",
        "symbol": symbol.upper(),
    }
    return _get(params)


def get_daily_adjusted(symbol: str) -> dict:
    """Daily adjusted prices (for trend/drawdown later)."""
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol.upper(),
        "outputsize": "compact",  # last ~100 days for now
    }
    return _get(params)
