"""
Stock screener module.
Identifies stocks that have dropped 20-30% from their 52-week high.
"""

import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_stock_data(ticker: str) -> Optional[Dict]:
    """
    Fetch stock data for a single ticker.
    Returns dict with price info or None if failed.
    """
    try:
        stock = yf.Ticker(ticker)

        # Get historical data for 52 weeks
        hist = stock.history(period="1y")

        if hist.empty:
            return None

        # Get current price and 52-week high
        current_price = hist['Close'].iloc[-1]
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()

        # Calculate drop percentage
        drop_pct = ((high_52w - current_price) / high_52w) * 100

        # Get stock info
        info = stock.info

        # Check if drop was sudden (more than 10% in last 5 days)
        if len(hist) >= 5:
            price_5d_ago = hist['Close'].iloc[-5]
            sudden_drop = bool(((price_5d_ago - current_price) / price_5d_ago) * 100 > 10)
        else:
            sudden_drop = False

        return {
            "ticker": ticker,
            "name": info.get("shortName", info.get("longName", ticker)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": float(round(current_price, 2)),
            "high_52w": float(round(high_52w, 2)),
            "low_52w": float(round(low_52w, 2)),
            "drop_pct": float(round(drop_pct, 2)),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
            "sudden_drop": sudden_drop,
            "volume": info.get("averageVolume", 0),
            "pe_ratio": info.get("trailingPE", None),
            "dividend_yield": info.get("dividendYield", None)
        }

    except Exception as e:
        logger.warning(f"Error fetching data for {ticker}: {e}")
        return None


def screen_stocks(
    tickers: List[str],
    min_drop: float = 20.0,
    max_drop: float = 30.0,
    exclude_sudden_drops: bool = True,
    max_workers: int = 5
) -> List[Dict]:
    """
    Screen multiple stocks for price drops.

    Args:
        tickers: List of ticker symbols
        min_drop: Minimum drop percentage (default 20%)
        max_drop: Maximum drop percentage (default 30%)
        exclude_sudden_drops: Exclude stocks with sudden drops (>10% in 5 days)
        max_workers: Number of parallel threads

    Returns:
        List of stocks matching criteria
    """
    results = []
    total = len(tickers)
    processed = 0

    logger.info(f"Screening {total} stocks...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_stock_data, ticker): ticker for ticker in tickers}

        for future in as_completed(futures):
            processed += 1
            ticker = futures[future]

            try:
                data = future.result()

                if data is None:
                    continue

                # Apply filters
                if min_drop <= data["drop_pct"] <= max_drop:
                    if exclude_sudden_drops and data["sudden_drop"]:
                        logger.info(f"Excluding {ticker} - sudden drop detected")
                        continue

                    results.append(data)
                    logger.info(f"Found: {ticker} - Drop: {data['drop_pct']}%")

            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")

            if processed % 20 == 0:
                logger.info(f"Progress: {processed}/{total}")

    # Sort by drop percentage (highest drop first)
    results.sort(key=lambda x: x["drop_pct"], reverse=True)

    logger.info(f"Screening complete. Found {len(results)} stocks matching criteria.")

    return results


def get_stock_details(ticker: str) -> Optional[Dict]:
    """
    Get detailed information for a single stock.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")

        if hist.empty:
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
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", ""),
            "current_price": float(round(current_price, 2)),
            "high_52w": float(round(hist['High'].max(), 2)),
            "low_52w": float(round(hist['Low'].min(), 2)),
            "ma50": float(round(ma50, 2)) if ma50 is not None else None,
            "ma200": float(round(ma200, 2)) if ma200 is not None else None,
            "currency": info.get("currency", "USD"),
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
