"""
Stock screener module.
Identifies stocks that have dropped 20-30% in the last 1-2 days.
"""

import io
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Iterable, Tuple

import pandas as pd
import requests
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUFFIX_CURRENCY = {
    ".DE": "EUR",
    ".PA": "EUR",
    ".MI": "EUR",
    ".L": "GBP",
    ".HK": "HKD",
    ".T": "JPY",
}

STOOQ_SUFFIX_MAP = {
    ".DE": "de",
    ".PA": "fr",
    ".MI": "it",
    ".L": "uk",
    ".HK": "hk",
    ".T": "jp",
}

SUPPORTED_PRICE_PROVIDERS = {"auto", "yfinance", "stooq", "alphavantage"}

PRICE_PROVIDER_ENV = "PRICE_PROVIDER"
ALPHAVANTAGE_API_KEY_ENV = "ALPHAVANTAGE_API_KEY"
ALPHAVANTAGE_MIN_SECONDS_ENV = "ALPHAVANTAGE_MIN_SECONDS"

def _infer_currency(ticker: str) -> str:
    for suffix, currency in SUFFIX_CURRENCY.items():
        if ticker.endswith(suffix):
            return currency
    return "USD"


def _normalize_provider(provider: Optional[str]) -> str:
    if not provider:
        provider = os.getenv(PRICE_PROVIDER_ENV, "auto")
    provider = provider.strip().lower()
    if provider not in SUPPORTED_PRICE_PROVIDERS:
        logger.warning(f"Unknown price provider '{provider}', falling back to auto.")
        return "auto"
    return provider


def _period_to_rows(period: str) -> int:
    period = (period or "").strip().lower()
    try:
        if period.endswith("d"):
            return int(period[:-1])
        if period.endswith("mo"):
            return int(period[:-2]) * 21
        if period.endswith("y"):
            return int(period[:-1]) * 252
    except ValueError:
        return 0
    return 0


def _to_stooq_symbol(ticker: str) -> Optional[str]:
    upper = ticker.upper()
    if "." in upper:
        root, suffix = upper.rsplit(".", 1)
        mapped = STOOQ_SUFFIX_MAP.get(f".{suffix}")
        if not mapped:
            return None
        return f"{root.replace('-', '.').lower()}.{mapped}"
    return f"{upper.replace('-', '.').lower()}.us"


def _fetch_stooq_history(ticker: str, period: str) -> Optional[pd.DataFrame]:
    symbol = _to_stooq_symbol(ticker)
    if not symbol:
        return None

    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logger.warning(f"Error fetching Stooq data for {ticker}: {e}")
        return None

    if response.status_code != 200:
        logger.warning(f"Stooq HTTP {response.status_code} for {ticker}")
        return None

    text = response.text.strip()
    if not text or text.startswith("No data"):
        return None

    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        logger.warning(f"Error parsing Stooq data for {ticker}: {e}")
        return None

    required_cols = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(df.columns):
        return None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.set_index("Date").sort_index()

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Close", "High"])

    rows = _period_to_rows(period)
    if rows and len(df) > rows:
        df = df.tail(rows)

    return df


def _fetch_yfinance_history(ticker: str, period: str) -> Optional[pd.DataFrame]:
    try:
        return yf.Ticker(ticker).history(period=period)
    except Exception as e:
        logger.warning(f"Error fetching Yahoo history for {ticker}: {e}")
        return None


def _fetch_alphavantage_history(ticker: str, period: str) -> Optional[pd.DataFrame]:
    api_key = os.getenv(ALPHAVANTAGE_API_KEY_ENV)
    if not api_key:
        return None

    rows = _period_to_rows(period)
    outputsize = "compact" if rows and rows <= 100 else "full"
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "apikey": api_key,
        "outputsize": outputsize
    }

    try:
        response = requests.get(url, params=params, timeout=15)
    except requests.RequestException as e:
        logger.warning(f"Error fetching Alpha Vantage data for {ticker}: {e}")
        return None

    if response.status_code != 200:
        logger.warning(f"Alpha Vantage HTTP {response.status_code} for {ticker}")
        return None

    data = response.json()
    if "Error Message" in data or "Note" in data:
        logger.warning(f"Alpha Vantage error for {ticker}: {data.get('Note') or data.get('Error Message')}")
        return None

    series = data.get("Time Series (Daily)")
    if not series:
        return None

    df = pd.DataFrame.from_dict(series, orient="index")
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.rename(columns={
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    })

    required_cols = {"Open", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        return None

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df.sort_index()

    if rows and len(df) > rows:
        df = df.tail(rows)

    return df


def _fetch_history(ticker: str, period: str, provider: Optional[str]) -> Optional[pd.DataFrame]:
    provider = _normalize_provider(provider)
    if provider == "yfinance":
        return _fetch_yfinance_history(ticker, period)
    if provider == "stooq":
        return _fetch_stooq_history(ticker, period)
    if provider == "alphavantage":
        return _fetch_alphavantage_history(ticker, period)

    hist = _fetch_yfinance_history(ticker, period)
    if hist is None or hist.empty:
        hist = _fetch_stooq_history(ticker, period)
    return hist


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _safe_get_info(stock: yf.Ticker, ticker: str) -> Dict:
    try:
        info = stock.get_info()
        return info or {}
    except Exception as e:
        logger.warning(f"Error fetching info for {ticker}: {e}")
        return {}


def _get_history_for_ticker(hist: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    if hist is None or hist.empty:
        return None
    if isinstance(hist.columns, pd.MultiIndex):
        if ticker not in hist.columns.levels[0]:
            return None
        return hist[ticker]
    return hist


def _calculate_drop(hist: pd.DataFrame, lookback_days: int) -> Optional[Tuple[float, float, float]]:
    hist = hist.dropna(subset=["Close", "High"])
    if len(hist) < 2:
        return None

    current_price = float(hist["Close"].iloc[-1])

    if lookback_days == 1 and len(hist) >= 2:
        reference_high = float(hist["High"].iloc[-2])
    elif lookback_days == 2 and len(hist) >= 3:
        reference_high = float(max(hist["High"].iloc[-3], hist["High"].iloc[-2]))
    else:
        reference_high = float(hist["High"].iloc[-2])

    if reference_high <= 0:
        return None

    drop_pct = ((reference_high - current_price) / reference_high) * 100
    return current_price, reference_high, drop_pct


def get_stock_data(
    ticker: str,
    lookback_days: int = 2,
    hist: Optional[pd.DataFrame] = None,
    info: Optional[Dict] = None,
    include_info: bool = True
) -> Optional[Dict]:
    """
    Fetch stock data for a single ticker.
    Looks for price drops in the last 1-2 days.

    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to look back (1 or 2)
        hist: Optional pre-fetched price history (10d)
        info: Optional pre-fetched stock info
        include_info: Whether to fetch info if not provided

    Returns dict with price info or None if failed.
    """
    try:
        stock = None
        if hist is None:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="10d")

        if hist is None or hist.empty:
            return None

        drop_data = _calculate_drop(hist, lookback_days)
        if drop_data is None:
            return None

        current_price, reference_high, drop_pct = drop_data

        if include_info:
            if info is None:
                if stock is None:
                    stock = yf.Ticker(ticker)
                info = _safe_get_info(stock, ticker)
        else:
            info = info or {}

        info = info or {}

        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")
        if high_52w is None or pd.isna(high_52w):
            high_52w = reference_high
        if low_52w is None or pd.isna(low_52w):
            low_52w = current_price

        currency = info.get("currency") or _infer_currency(ticker)

        return {
            "ticker": ticker,
            "name": info.get("shortName", info.get("longName", ticker)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": float(round(current_price, 2)),
            "reference_price": float(round(reference_high, 2)),
            "high_52w": float(round(high_52w, 2)),
            "low_52w": float(round(low_52w, 2)),
            "drop_pct": float(round(drop_pct, 2)),
            "currency": currency,
            "market_cap": info.get("marketCap", 0),
            "volume": info.get("averageVolume", 0),
            "pe_ratio": info.get("trailingPE", None),
            "dividend_yield": info.get("dividendYield", None),
            "lookback_days": lookback_days
        }

    except Exception as e:
        logger.warning(f"Error fetching data for {ticker}: {e}")
        return None


def _screen_with_stooq(
    tickers: List[str],
    min_drop: float,
    max_drop: float,
    lookback_days: int,
    max_workers: int
) -> List[Dict]:
    results = []
    total = len(tickers)
    processed = 0

    if total == 0:
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_stooq_history, ticker, "10d"): ticker
            for ticker in tickers
        }

        for future in as_completed(futures):
            processed += 1
            ticker = futures[future]
            try:
                hist = future.result()
            except Exception as e:
                logger.warning(f"Error fetching Stooq history for {ticker}: {e}")
                continue

            if hist is None or hist.empty:
                continue

            data = get_stock_data(
                ticker,
                lookback_days=lookback_days,
                hist=hist,
                include_info=False
            )

            if data is None:
                continue

            if min_drop <= data["drop_pct"] <= max_drop:
                results.append(data)
                logger.info(f"Found: {ticker} - Drop: {data['drop_pct']}% in last {lookback_days} days")

            if processed % 20 == 0:
                logger.info(f"Progress: {processed}/{total}")

    return results


def _screen_with_alphavantage(
    tickers: List[str],
    min_drop: float,
    max_drop: float,
    lookback_days: int
) -> List[Dict]:
    results = []
    total = len(tickers)

    if total == 0:
        return results

    if not os.getenv(ALPHAVANTAGE_API_KEY_ENV):
        logger.warning("ALPHAVANTAGE_API_KEY not set; skipping Alpha Vantage scan.")
        return results

    if total > 10:
        logger.warning("Alpha Vantage is rate-limited; large scans will be slow.")

    min_seconds = float(os.getenv(ALPHAVANTAGE_MIN_SECONDS_ENV, "12"))

    for idx, ticker in enumerate(tickers, start=1):
        hist = _fetch_alphavantage_history(ticker, "10d")

        if hist is None or hist.empty:
            continue

        data = get_stock_data(
            ticker,
            lookback_days=lookback_days,
            hist=hist,
            include_info=False
        )

        if data is None:
            continue

        if min_drop <= data["drop_pct"] <= max_drop:
            results.append(data)
            logger.info(f"Found: {ticker} - Drop: {data['drop_pct']}% in last {lookback_days} days")

        if idx % 20 == 0:
            logger.info(f"Progress: {idx}/{total}")

        if idx < total:
            time.sleep(min_seconds)

    return results


def screen_stocks(
    tickers: List[str],
    min_drop: float = 20.0,
    max_drop: float = 30.0,
    lookback_days: int = 2,
    max_workers: int = 5,
    batch_size: int = 100,
    include_info: bool = True,
    price_provider: Optional[str] = None
) -> List[Dict]:
    """
    Screen multiple stocks for price drops in the last 1-2 days.

    Args:
        tickers: List of ticker symbols
        min_drop: Minimum drop percentage (default 20%)
        max_drop: Maximum drop percentage (default 30%)
        lookback_days: Number of days to look back (1 or 2)
        max_workers: Deprecated, kept for backward compatibility
        batch_size: Number of tickers per price-history request
        include_info: Whether to fetch metadata for matched tickers
        price_provider: auto, yfinance, stooq, or alphavantage

    Returns:
        List of stocks matching criteria
    """
    results = []
    total = len(tickers)
    processed = 0
    provider = _normalize_provider(price_provider)

    logger.info(f"Screening {total} stocks for drops in last {lookback_days} days...")
    logger.info(f"Using price provider: {provider}")

    if provider in ("yfinance", "auto"):
        missing = set() if provider == "auto" else None

        for batch in _chunked(tickers, batch_size):
            try:
                hist = yf.download(
                    tickers=" ".join(batch),
                    period="10d",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=False,
                    threads=False,
                    progress=False
                )
            except Exception as e:
                logger.warning(f"Error fetching batch history: {e}")
                if missing is not None:
                    missing.update(batch)
                processed += len(batch)
                continue

            if hist is None or hist.empty:
                if missing is not None:
                    missing.update(batch)
                processed += len(batch)
                continue

            for ticker in batch:
                processed += 1
                ticker_hist = _get_history_for_ticker(hist, ticker)
                if ticker_hist is None or ticker_hist.empty:
                    if missing is not None:
                        missing.add(ticker)
                    continue

                data = get_stock_data(
                    ticker,
                    lookback_days=lookback_days,
                    hist=ticker_hist,
                    include_info=False
                )

                if data is None:
                    continue

                if min_drop <= data["drop_pct"] <= max_drop:
                    results.append(data)
                    logger.info(f"Found: {ticker} - Drop: {data['drop_pct']}% in last {lookback_days} days")

                if processed % 20 == 0:
                    logger.info(f"Progress: {processed}/{total}")

        if provider == "auto" and missing:
            logger.info(f"Falling back to Stooq for {len(missing)} tickers.")
            fallback_results = _screen_with_stooq(
                sorted(missing),
                min_drop=min_drop,
                max_drop=max_drop,
                lookback_days=lookback_days,
                max_workers=max_workers
            )
            results.extend(fallback_results)
    elif provider == "stooq":
        results = _screen_with_stooq(
            tickers,
            min_drop=min_drop,
            max_drop=max_drop,
            lookback_days=lookback_days,
            max_workers=max_workers
        )
    elif provider == "alphavantage":
        results = _screen_with_alphavantage(
            tickers,
            min_drop=min_drop,
            max_drop=max_drop,
            lookback_days=lookback_days
        )
    else:
        logger.warning(f"Unknown provider '{provider}', defaulting to yfinance.")

    if include_info and results:
        for stock in results:
            info = _safe_get_info(yf.Ticker(stock["ticker"]), stock["ticker"])
            if not info:
                continue
            if info.get("shortName") or info.get("longName"):
                stock["name"] = info.get("shortName", info.get("longName", stock["ticker"]))
            if info.get("sector"):
                stock["sector"] = info.get("sector")
            if info.get("industry"):
                stock["industry"] = info.get("industry")
            if info.get("currency"):
                stock["currency"] = info.get("currency")
            if info.get("marketCap") is not None and not pd.isna(info.get("marketCap")):
                stock["market_cap"] = info.get("marketCap")
            if info.get("averageVolume") is not None and not pd.isna(info.get("averageVolume")):
                stock["volume"] = info.get("averageVolume")
            if info.get("trailingPE") is not None and not pd.isna(info.get("trailingPE")):
                stock["pe_ratio"] = info.get("trailingPE")
            if info.get("dividendYield") is not None and not pd.isna(info.get("dividendYield")):
                stock["dividend_yield"] = info.get("dividendYield")
            if info.get("fiftyTwoWeekHigh") is not None and not pd.isna(info.get("fiftyTwoWeekHigh")):
                stock["high_52w"] = float(round(info.get("fiftyTwoWeekHigh"), 2))
            if info.get("fiftyTwoWeekLow") is not None and not pd.isna(info.get("fiftyTwoWeekLow")):
                stock["low_52w"] = float(round(info.get("fiftyTwoWeekLow"), 2))

    # Sort by drop percentage (highest drop first)
    results.sort(key=lambda x: x["drop_pct"], reverse=True)

    logger.info(f"Screening complete. Found {len(results)} stocks matching criteria.")

    return results


def get_stock_details(ticker: str, price_provider: Optional[str] = None) -> Optional[Dict]:
    """
    Get detailed information for a single stock.

    Args:
        price_provider: auto, yfinance, stooq, or alphavantage
    """
    try:
        stock = yf.Ticker(ticker)
        info = _safe_get_info(stock, ticker)
        hist = _fetch_history(ticker, "1y", price_provider)

        if hist is None or hist.empty:
            return None

        # Calculate moving averages
        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        hist['MA200'] = hist['Close'].rolling(window=200).mean()

        current_price = hist['Close'].iloc[-1]
        ma50 = hist['MA50'].iloc[-1] if len(hist) >= 50 else None
        ma200 = hist['MA200'].iloc[-1] if len(hist) >= 200 else None

        # Get price history for chart
        price_history = [
            {"date": str(date.date()), "price": round(price, 2)}
            for date, price in hist['Close'].items()
        ]

        return {
            "ticker": ticker,
            "name": info.get("shortName", info.get("longName", ticker)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", ""),
            "current_price": float(round(current_price, 2)),
            "high_52w": float(round(hist['High'].max(), 2)),
            "low_52w": float(round(hist['Low'].min(), 2)),
            "ma50": float(round(ma50, 2)) if ma50 is not None else None,
            "ma200": float(round(ma200, 2)) if ma200 is not None else None,
            "currency": info.get("currency") or _infer_currency(ticker),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": float(info["trailingPE"]) if info.get("trailingPE") else None,
            "forward_pe": float(info["forwardPE"]) if info.get("forwardPE") else None,
            "pb_ratio": float(info["priceToBook"]) if info.get("priceToBook") else None,
            "dividend_yield": float(info["dividendYield"]) if info.get("dividendYield") else None,
            "beta": float(info["beta"]) if info.get("beta") else None,
            "eps": float(info["trailingEps"]) if info.get("trailingEps") else None,
            "revenue": int(info["totalRevenue"]) if info.get("totalRevenue") else None,
            "profit_margin": float(info["profitMargins"]) if info.get("profitMargins") else None,
            "debt_to_equity": float(info["debtToEquity"]) if info.get("debtToEquity") else None,
            "price_history": price_history[-90:]  # Last 90 days
        }

    except Exception as e:
        logger.error(f"Error fetching details for {ticker}: {e}")
        return None


if __name__ == "__main__":
    # Test with a few stocks
    test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    results = screen_stocks(test_tickers, min_drop=5, max_drop=50)

    for stock in results:
        print(f"{stock['ticker']}: {stock['name']} - Drop: {stock['drop_pct']}%")
