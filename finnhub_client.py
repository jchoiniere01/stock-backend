import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"

PROFILE_CACHE: dict[str, dict] = {}
FINANCIALS_CACHE: dict[str, dict] = {}
QUOTE_CACHE: dict[str, tuple[dict, float]] = {}
CANDLES_CACHE: dict[tuple[str, str], dict] = {}  # (symbol, resolution) -> candles



class FinnhubError(Exception):
    pass


def _get(path: str, params: dict):
    if not FINNHUB_API_KEY:
        raise FinnhubError("Missing FINNHUB_API_KEY in environment/.env")
    params = {**params, "token": FINNHUB_API_KEY}
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Turn HTTP errors (including 429 Too Many Requests) into FinnhubError
        raise FinnhubError(f"HTTP error {e}") from e
    except requests.exceptions.RequestException as e:
        # Network or other request issues
        raise FinnhubError(f"Request error {e}") from e

    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        # Finnhub sometimes returns {'error': '...'}
        raise FinnhubError(data["error"])
    return data


def get_company_profile(symbol: str) -> dict:
    symbol = symbol.upper()
    if symbol in PROFILE_CACHE:
        return PROFILE_CACHE[symbol]
    data = _get("/stock/profile2", {"symbol": symbol})
    PROFILE_CACHE[symbol] = data
    return data


def get_financials(symbol: str) -> dict:
    symbol = symbol.upper()
    if symbol in FINANCIALS_CACHE:
        return FINANCIALS_CACHE[symbol]
    data = _get("/stock/metric", {"symbol": symbol, "metric": "all"})
    FINANCIALS_CACHE[symbol] = data
    return data


QUOTE_TTL_SECONDS = 5 * 60  # 5 minutes

def get_quote(symbol: str) -> dict:
    symbol = symbol.upper()
    now = time.time()

    # If we have a recent quote, return it
    cached = QUOTE_CACHE.get(symbol)
    if cached is not None:
        data, fetched_at = cached
        if now - fetched_at < QUOTE_TTL_SECONDS:
            print(f"QUOTE CACHE HIT")
            return data

    # Otherwise fetch a fresh quote
    print(f"QUOTE API CALL: {symbol}")
    data = _get("/quote", {"symbol": symbol})
    QUOTE_CACHE[symbol] = (data, now)
    return data


import time

def get_daily_candles(symbol: str, days: int = 365) -> dict:
    symbol = symbol.upper()
    resolution = "D"
    cache_key = (symbol, resolution)

    if cache_key in CANDLES_CACHE:
        return CANDLES_CACHE[cache_key]

    now = int(time.time())
    frm = now - days * 24 * 60 * 60

    data = _get(
        "/stock/candle",
        {
            "symbol": symbol,
            "resolution": resolution,
            "from": frm,
            "to": now,
        },
    )

    # Finnhub returns {'s': 'no_data'} when empty
    if isinstance(data, dict) and data.get("s") == "no_data":
        raise FinnhubError(f"No candle data for {symbol}")

    CANDLES_CACHE[cache_key] = data
    return data

