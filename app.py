"""
Stock Screener Web Application
Flask backend for screening stocks with 20-30% price drops and news sentiment analysis.
"""

from flask import Flask, render_template, jsonify, request
from screener import screen_stocks, get_stock_details
from news_analyzer import analyze_stock_news, is_safe_drop
from stock_lists import MARKETS, get_tickers_by_markets
import logging
from concurrent.futures import ThreadPoolExecutor
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
    Scan stocks for price drops.

    Request body:
    {
        "markets": ["sp500", "nasdaq"],  // Market keys to scan
        "min_drop": 20,                   // Minimum drop percentage
        "max_drop": 30,                   // Maximum drop percentage
        "analyze_news": true              // Whether to analyze news
    }
    """
    data = request.get_json() or {}

    # Get parameters with defaults
    market_keys = data.get('markets', ['sp500'])
    min_drop = float(data.get('min_drop', 20))
    max_drop = float(data.get('max_drop', 30))
    analyze_news = data.get('analyze_news', True)

    # Validate parameters
    if min_drop < 0 or max_drop > 100 or min_drop >= max_drop:
        return jsonify({"error": "Invalid drop range"}), 400

    # Get tickers for selected markets
    tickers = get_tickers_by_markets(market_keys)

    if not tickers:
        return jsonify({"error": "No valid markets selected"}), 400

    # Limit stocks to avoid timeout on free hosting (30s request limit)
    MAX_STOCKS = 150
    if len(tickers) > MAX_STOCKS:
        logger.warning(f"Limiting scan from {len(tickers)} to {MAX_STOCKS} stocks")
        tickers = tickers[:MAX_STOCKS]

    logger.info(f"Scanning {len(tickers)} stocks from markets: {market_keys}")

    # Screen stocks for price drops
    try:
        stocks = screen_stocks(
            tickers,
            min_drop=min_drop,
            max_drop=max_drop,
            exclude_sudden_drops=True
        )
    except Exception as e:
        logger.error(f"Error screening stocks: {e}")
        return jsonify({"error": "Failed to screen stocks"}), 500

    # Analyze news for each stock if requested
    if analyze_news and stocks:
        logger.info(f"Analyzing news for {len(stocks)} stocks...")

        # Process news analysis sequentially to avoid rate limiting
        analyzed_stocks = []
        for i, stock in enumerate(stocks):
            try:
                is_safe, analysis = is_safe_drop(stock['ticker'], stock.get('name'))
                stock['news_analysis'] = {
                    'safety_score': analysis['safety_score'],
                    'assessment': analysis['assessment'],
                    'message': analysis['message'],
                    'overall_sentiment': analysis['overall_sentiment'],
                    'critical_issues': analysis['critical_issues'],
                    'critical_keywords': analysis.get('critical_keywords_found', []),
                    'news_count': len(analysis.get('news', []))
                }
                stock['is_safe'] = is_safe
            except Exception as e:
                logger.warning(f"Error analyzing news for {stock['ticker']}: {e}")
                stock['news_analysis'] = None
                stock['is_safe'] = None

            analyzed_stocks.append(stock)

            # Add small delay between news analyses to avoid rate limiting
            if i < len(stocks) - 1:
                time.sleep(0.5)

        stocks = analyzed_stocks

    # Sort by safety score (safest first), then by drop percentage
    stocks.sort(key=lambda x: (
        -(x.get('news_analysis', {}).get('safety_score', 0) if x.get('news_analysis') else 0),
        -x['drop_pct']
    ))

    # Prepare response
    original_count = len(get_tickers_by_markets(market_keys))
    was_limited = original_count > MAX_STOCKS

    result = {
        "count": len(stocks),
        "markets_scanned": market_keys,
        "tickers_scanned": len(tickers),
        "tickers_total": original_count,
        "was_limited": was_limited,
        "max_stocks": MAX_STOCKS,
        "parameters": {
            "min_drop": min_drop,
            "max_drop": max_drop,
            "analyze_news": analyze_news
        },
        "stocks": stocks
    }

    return jsonify(result)


@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    """Get detailed information for a specific stock."""
    try:
        details = get_stock_details(ticker.upper())

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
