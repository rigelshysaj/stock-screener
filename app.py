"""
Stock Screener Web Application
Flask backend for screening stocks with 20-30% price drops and news sentiment analysis.
"""

import json
import logging
import os
import sqlite3
import time

from flask import Flask, render_template, jsonify, request

import yfinance as yf

from screener import screen_stocks, get_stock_details
from news_analyzer import analyze_stock_news
from stock_lists import MARKETS, get_tickers_by_markets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Database layer: SQLite (persistent on disk)
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'saved_stocks.db')


def _init_db():
    """Create the saved_stocks table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS saved_stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL UNIQUE,
        name TEXT,
        sector TEXT,
        currency TEXT,
        price_when_saved REAL,
        reference_price REAL,
        high_52w REAL,
        low_52w REAL,
        drop_pct REAL,
        saved_at REAL,
        extra TEXT
    )""")
    conn.commit()
    conn.close()
    logger.info(f"SQLite database ready at {DB_PATH}")


def _db_execute(query, params=None, fetch=False):
    """Execute a query against SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, params or ())
    if fetch:
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    conn.commit()
    conn.close()
    return None


_init_db()

# Cache for responses (simple in-memory cache)
scan_cache = {}
details_cache = {}
news_cache = {}

SCAN_CACHE_DURATION = 300  # seconds
DETAILS_CACHE_DURATION = 300
NEWS_CACHE_DURATION = 600


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "yes", "y", "on"):
            return True
        if normalized in ("0", "false", "no", "n", "off"):
            return False
    return default


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cache_get(cache, key):
    entry = cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        cache.pop(key, None)
        return None
    return value


def _cache_set(cache, key, value, ttl):
    cache[key] = (time.time() + ttl, value)


def _get_news_cached(ticker, company_name=None):
    cache_key = (ticker, company_name or "")
    cached = _cache_get(news_cache, cache_key)
    if cached is not None:
        return cached
    analysis = analyze_stock_news(ticker, company_name)
    _cache_set(news_cache, cache_key, analysis, NEWS_CACHE_DURATION)
    return analysis


@app.route('/')
def index():
    """Serve the main frontend page."""
    return render_template('index.html', markets=MARKETS)


@app.route('/api/markets')
def get_markets():
    """Get available markets."""
    markets_info = {
        key: {
            "name": value["name"],
            "count": len(value["tickers"]),
            "currency": value["currency"]
        }
        for key, value in MARKETS.items()
    }
    return jsonify(markets_info)


@app.route('/api/scan', methods=['POST'])
def scan_stocks():
    """
    Scan stocks for price drops with batch support.

    Request body:
    {
        "markets": ["sp500", "nasdaq"],  // Market keys to scan
        "min_drop": 20,                   // Minimum drop percentage
        "max_drop": 30,                   // Maximum drop percentage
        "lookback_days": 2,               // Days to look back (1 or 2)
        "price_provider": "stooq",        // stooq, yfinance, auto, alphavantage
        "include_info": false,            // Fetch Yahoo metadata for matched tickers
        "batch": 0,                       // Batch number (0-indexed)
        "batch_size": 100                 // Stocks per batch
    }
    """
    data = request.get_json() or {}

    # Get parameters with defaults
    market_keys = data.get('markets', ['sp500'])
    if isinstance(market_keys, str):
        market_keys = [market_keys]
    min_drop = float(data.get('min_drop', 20))
    max_drop = float(data.get('max_drop', 30))
    lookback_days = int(data.get('lookback_days', 2))
    # Default to yfinance - uses efficient batch downloading, avoids rate limits
    price_provider = data.get('price_provider')
    if price_provider is None:
        price_provider = os.getenv('PRICE_PROVIDER', 'yfinance')
    price_provider = str(price_provider).strip().lower()
    if price_provider == "":
        price_provider = "yfinance"
    include_info = _parse_bool(os.getenv('INCLUDE_INFO'), False)
    batch = int(data.get('batch', 0))

    # Respect MAX_BATCH_SIZE from environment (Render has resource limits)
    requested_batch_size = int(data.get('batch_size', 100))
    max_batch_size = _parse_int(os.getenv('MAX_BATCH_SIZE'), 100)
    batch_size = min(requested_batch_size, max_batch_size)
    if batch_size != requested_batch_size:
        logger.info(f"Clamped batch_size to {batch_size} (requested {requested_batch_size})")

    # Validate parameters
    if min_drop < 0 or max_drop > 100 or min_drop >= max_drop:
        return jsonify({"error": "Invalid drop range"}), 400

    # Get tickers for selected markets
    all_tickers = get_tickers_by_markets(market_keys)
    total_tickers = len(all_tickers)

    # Calculate batch slice
    start_idx = batch * batch_size
    end_idx = min(start_idx + batch_size, total_tickers)
    tickers = all_tickers[start_idx:end_idx]

    # Check if this is the last batch
    has_more = end_idx < total_tickers

    if not tickers:
        return jsonify({"error": "No valid market selected"}), 400

    logger.info(f"Scanning {len(tickers)} stocks from markets: {market_keys}")

    cache_key = (
        tuple(sorted(set(market_keys))),
        round(min_drop, 4),
        round(max_drop, 4),
        lookback_days,
        price_provider,
        include_info,
        batch,
        batch_size
    )
    cached = _cache_get(scan_cache, cache_key)
    if cached is not None:
        logger.info("Returning cached scan results.")
        return jsonify(cached)

    # Screen stocks for price drops in last N days
    try:
        stocks = screen_stocks(
            tickers,
            min_drop=min_drop,
            max_drop=max_drop,
            lookback_days=lookback_days,
            include_info=include_info,
            price_provider=price_provider
        )
    except Exception as e:
        logger.error(f"Error screening stocks: {e}")
        return jsonify({"error": "Failed to screen stocks"}), 500

    # Sort by drop percentage (highest first)
    stocks.sort(key=lambda x: -x['drop_pct'])

    # Prepare response with batch metadata
    result = {
        "count": len(stocks),
        "markets_scanned": market_keys,
        "tickers_scanned": len(tickers),
        "parameters": {
            "min_drop": min_drop,
            "max_drop": max_drop,
            "lookback_days": lookback_days,
            "price_provider": price_provider,
            "include_info": include_info
        },
        "stocks": stocks,
        # Batch metadata for frontend
        "batch": batch,
        "batch_size": batch_size,
        "total_tickers": total_tickers,
        "has_more": has_more
    }

    _cache_set(scan_cache, cache_key, result, SCAN_CACHE_DURATION)
    return jsonify(result)


@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    """Get detailed information for a specific stock."""
    try:
        # Default to yfinance for stock details
        price_provider = request.args.get('price_provider')
        if price_provider is None:
            price_provider = os.getenv('PRICE_PROVIDER', 'yfinance')
        price_provider = str(price_provider).strip().lower()
        if price_provider == "":
            price_provider = "yfinance"
        include_info = _parse_bool(os.getenv('INCLUDE_INFO'), False)

        cache_key = (ticker.upper(), price_provider, include_info)
        cached = _cache_get(details_cache, cache_key)
        if cached is not None:
            return jsonify(cached)

        details = get_stock_details(
            ticker.upper(),
            price_provider=price_provider,
            include_info=include_info
        )

        if not details:
            return jsonify({"error": f"Stock {ticker} not found"}), 404

        # Add news analysis
        analysis = _get_news_cached(ticker.upper(), details.get('name'))
        is_safe = (
            not analysis.get("critical_issues") and
            analysis.get("safety_score", 0) >= 50
        )
        details['news_analysis'] = analysis
        details['is_safe'] = is_safe

        _cache_set(details_cache, cache_key, details, DETAILS_CACHE_DURATION)
        return jsonify(details)

    except Exception as e:
        logger.error(f"Error fetching stock {ticker}: {e}")
        return jsonify({"error": "Failed to fetch stock details"}), 500
@app.route('/api/stock/<ticker>/news')
def get_stock_news(ticker):
    """Get news analysis for a specific stock."""
    try:
        cache_key = (ticker.upper(), "")
        cached = _cache_get(news_cache, cache_key)
        if cached is not None:
            return jsonify(cached)

        analysis = analyze_stock_news(ticker.upper())
        _cache_set(news_cache, cache_key, analysis, NEWS_CACHE_DURATION)
        return jsonify(analysis)

    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return jsonify({"error": "Failed to fetch news"}), 500


@app.route('/api/current-prices', methods=['POST'])
def get_current_prices():
    """Fetch current live prices for a list of tickers."""
    data = request.get_json() or {}
    tickers = data.get('tickers', [])
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    prices = {}
    try:
        ticker_str = ' '.join(tickers)
        df = yf.download(ticker_str, period='1d', progress=False)
        if df is not None and not df.empty:
            close = df['Close']
            if isinstance(close, (float, int)):
                # single ticker
                prices[tickers[0]] = round(float(close.iloc[-1]), 2)
            else:
                if close.ndim == 1:
                    prices[tickers[0]] = round(float(close.iloc[-1]), 2)
                else:
                    for t in tickers:
                        if t in close.columns:
                            val = close[t].dropna()
                            if not val.empty:
                                prices[t] = round(float(val.iloc[-1]), 2)
    except Exception as e:
        logger.error(f"Error fetching current prices: {e}")

    return jsonify({"prices": prices})


@app.route('/api/saved-stocks', methods=['GET'])
def get_saved_stocks():
    """Get all saved stocks."""
    rows = _db_execute("SELECT * FROM saved_stocks ORDER BY saved_at DESC", fetch=True)
    result = []
    for r in rows:
        d = {k: r[k] for k in ('ticker', 'name', 'sector', 'currency',
                                'price_when_saved', 'reference_price',
                                'high_52w', 'low_52w', 'drop_pct', 'saved_at')}
        if r.get('extra'):
            try:
                d.update(json.loads(r['extra']))
            except Exception:
                pass
        result.append(d)
    return jsonify(result)


@app.route('/api/saved-stocks', methods=['POST'])
def save_stocks():
    """Save stocks from scan results. Skips tickers already saved."""
    data = request.get_json() or {}
    stocks_to_save = data.get('stocks', [])
    if not stocks_to_save:
        return jsonify({"error": "No stocks provided"}), 400

    existing_rows = _db_execute("SELECT ticker FROM saved_stocks", fetch=True)
    existing = {r['ticker'] for r in existing_rows}
    saved_at = time.time()
    added = 0

    for stock in stocks_to_save:
        t = stock.get('ticker')
        if t in existing:
            continue
        extra = {k: stock[k] for k in stock
                 if k not in ('ticker', 'name', 'sector', 'currency',
                              'current_price', 'reference_price',
                              'high_52w', 'low_52w', 'drop_pct')}
        _db_execute(
            """INSERT INTO saved_stocks
               (ticker, name, sector, currency, price_when_saved,
                reference_price, high_52w, low_52w, drop_pct, saved_at, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t, stock.get('name'), stock.get('sector'),
             stock.get('currency'), stock.get('current_price'),
             stock.get('reference_price'), stock.get('high_52w'),
             stock.get('low_52w'), stock.get('drop_pct'),
             saved_at, json.dumps(extra) if extra else None)
        )
        existing.add(t)
        added += 1

    total_rows = _db_execute("SELECT COUNT(*) as cnt FROM saved_stocks", fetch=True)
    total = total_rows[0]['cnt'] if total_rows else 0
    skipped = len(stocks_to_save) - added
    return jsonify({"saved": added, "skipped": skipped, "total": total})


@app.route('/api/saved-stocks', methods=['DELETE'])
def delete_saved_stocks():
    """Delete saved stocks."""
    data = request.get_json() or {}
    ticker = data.get('ticker')

    if ticker:
        _db_execute("DELETE FROM saved_stocks WHERE ticker = ?", (ticker,))
    else:
        _db_execute("DELETE FROM saved_stocks")

    remaining_rows = _db_execute("SELECT COUNT(*) as cnt FROM saved_stocks", fetch=True)
    remaining = remaining_rows[0]['cnt'] if remaining_rows else 0
    return jsonify({"remaining": remaining})


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": time.time()})


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Stock Screener - Value Opportunity Finder")
    print("  Starting server at http://127.0.0.1:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)
