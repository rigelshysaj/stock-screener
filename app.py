"""
Stock Screener Web Application
Flask backend for screening stocks with 20-30% price drops and news sentiment analysis.
"""

from flask import Flask, render_template, jsonify, request
from screener import screen_stocks, get_stock_details
from news_analyzer import analyze_stock_news, is_safe_drop
from stock_lists import MARKETS, get_tickers_by_markets
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for scan results (simple in-memory cache)
scan_cache = {}
CACHE_DURATION = 300  # 5 minutes


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
        "price_provider": "auto",         // auto, yfinance, stooq, alphavantage
        "include_info": true,             // Fetch Yahoo metadata for matched tickers
        "batch": 0,                       // Batch number (0-indexed)
        "batch_size": 100                 // Stocks per batch
    }
    """
    data = request.get_json() or {}

    # Get parameters with defaults
    market_keys = data.get('markets', ['sp500'])
    min_drop = float(data.get('min_drop', 20))
    max_drop = float(data.get('max_drop', 30))
    lookback_days = int(data.get('lookback_days', 2))
    price_provider = data.get('price_provider')
    include_info = bool(data.get('include_info', True))
    batch = int(data.get('batch', 0))
    batch_size = int(data.get('batch_size', 100))

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
            "price_provider": price_provider or "auto",
            "include_info": include_info
        },
        "stocks": stocks,
        # Batch metadata for frontend
        "batch": batch,
        "batch_size": batch_size,
        "total_tickers": total_tickers,
        "has_more": has_more
    }

    return jsonify(result)


@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    """Get detailed information for a specific stock."""
    try:
        price_provider = request.args.get('price_provider')
        details = get_stock_details(ticker.upper(), price_provider=price_provider)

        if not details:
            return jsonify({"error": f"Stock {ticker} not found"}), 404

        # Add news analysis
        is_safe, analysis = is_safe_drop(ticker.upper(), details.get('name'))
        details['news_analysis'] = analysis
        details['is_safe'] = is_safe

        return jsonify(details)

    except Exception as e:
        logger.error(f"Error fetching stock {ticker}: {e}")
        return jsonify({"error": "Failed to fetch stock details"}), 500


@app.route('/api/stock/<ticker>/news')
def get_stock_news(ticker):
    """Get news analysis for a specific stock."""
    try:
        analysis = analyze_stock_news(ticker.upper())
        return jsonify(analysis)

    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return jsonify({"error": "Failed to fetch news"}), 500


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
