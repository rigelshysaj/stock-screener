"""
News analyzer module.
Fetches news and performs sentiment analysis to determine if price drops are "safe".
"""

import feedparser
import requests
from textblob import TextBlob
from typing import List, Dict, Tuple
from urllib.parse import quote
import logging
import re
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Critical keywords that indicate serious issues
CRITICAL_KEYWORDS = [
    # Legal/Regulatory
    "fraud", "fraudulent", "sec investigation", "doj investigation", "fbi investigation",
    "securities fraud", "accounting fraud", "lawsuit", "class action", "indictment",
    "charged", "criminal", "violation", "penalty", "fine", "settlement",

    # Financial distress
    "bankruptcy", "chapter 11", "chapter 7", "insolvent", "insolvency",
    "default", "debt crisis", "liquidity crisis", "going concern",
    "delisting", "delisted",

    # Scandals
    "scandal", "misconduct", "corruption", "bribery", "embezzlement",
    "whistleblower", "cover-up", "falsified",

    # Product/Safety issues
    "recall", "safety issue", "defect", "fatality", "death", "injury",
    "contamination", "toxic",

    # Leadership crisis
    "ceo arrested", "cfo arrested", "executive arrested", "resignation scandal",
    "fired for cause",

    # Severe business issues
    "data breach", "hack", "ransomware", "customer data stolen",
    "major contract loss", "lost contract", "terminated partnership"
]

# Moderate concern keywords (lower weight)
MODERATE_KEYWORDS = [
    "downgrade", "underperform", "sell rating", "price target cut",
    "earnings miss", "revenue miss", "guidance cut", "layoffs",
    "restructuring", "cost cutting", "margin pressure"
]

# Positive keywords that indicate good news (override negative TextBlob sentiment)
POSITIVE_KEYWORDS = [
    # Analyst upgrades
    "upgraded to buy", "upgrade to buy", "upgraded to outperform", "upgrade to outperform",
    "upgraded to overweight", "upgrade to overweight", "upgraded to strong buy",
    "buy rating", "outperform rating", "overweight rating", "strong buy",
    "price target raised", "price target increased", "raises price target",
    "increases price target", "bullish", "bull case",

    # Earnings/Revenue
    "earnings beat", "beat earnings", "beats earnings", "revenue beat", "beat revenue",
    "beats revenue", "exceeds expectations", "exceeded expectations", "beat expectations",
    "beats expectations", "better than expected", "above expectations",
    "record revenue", "record earnings", "record profit", "strong earnings",
    "strong revenue", "guidance raised", "raises guidance", "raised guidance",

    # Business positive
    "fda approval", "fda approved", "receives approval", "granted approval",
    "contract win", "wins contract", "won contract", "new contract",
    "partnership", "strategic partnership", "acquisition", "merger approved",
    "dividend increase", "raises dividend", "special dividend", "buyback",
    "share repurchase", "stock buyback"
]

PRICE_MOVE_TERMS = [
    "stock", "stocks", "share", "shares", "price", "prices", "equity"
]

PRICE_MOVE_VERBS = [
    "down", "lower", "fall", "fell", "falls", "drop", "dropped", "drops", "decline",
    "declined", "slump", "slumped", "plunge", "plunged", "tumble", "tumbled",
    "sink", "sank", "slide", "slid", "plummet", "plummeted", "crash", "crashed",
    "tank", "tanked", "selloff", "sell-off"
]


def fetch_news_google(query: str, num_results: int = 10) -> List[Dict]:
    """
    Fetch news from Google News RSS feed.

    Args:
        query: Search query (usually company name or ticker)
        num_results: Maximum number of results

    Returns:
        List of news articles with title, link, date, source
    """
    try:
        # Google News RSS URL
        encoded_query = quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

        feed = feedparser.parse(url)
        news = []

        for entry in feed.entries[:num_results]:
            # Parse the title (Google News format: "Title - Source")
            title_parts = entry.title.rsplit(" - ", 1)
            title = title_parts[0]
            source = title_parts[1] if len(title_parts) > 1 else "Unknown"

            # Parse date
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                pub_date = datetime.now()

            news.append({
                "title": title,
                "source": source,
                "link": entry.link,
                "date": pub_date.strftime("%Y-%m-%d"),
                "summary": entry.get("summary", "")
            })

        return news

    except Exception as e:
        logger.error(f"Error fetching news for '{query}': {e}")
        return []


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of text using TextBlob + financial keyword detection.

    Returns:
        Dict with polarity (-1 to 1), subjectivity (0 to 1), and interpretation
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    # Check for financial keywords that override TextBlob
    has_positive, positive_kw = check_positive_keywords(text)
    has_critical, critical_kw = check_critical_keywords(text)
    has_moderate, moderate_kw = check_moderate_keywords(text)

    # Override polarity based on financial context
    if has_positive and not has_critical:
        # Positive financial news - boost polarity
        polarity = max(polarity, 0.5)
    elif has_critical:
        # Critical issues - force negative
        polarity = min(polarity, -0.5)
    elif has_moderate and not has_positive:
        # Moderate concerns - nudge negative
        polarity = min(polarity, -0.2)

    if polarity > 0.1:
        interpretation = "positive"
    elif polarity < -0.1:
        interpretation = "negative"
    else:
        interpretation = "neutral"

    return {
        "polarity": round(polarity, 3),
        "subjectivity": round(subjectivity, 3),
        "interpretation": interpretation
    }


def is_price_move_only(text: str) -> bool:
    """
    Detect news that only mentions price movement with no other negative signals.
    """
    text_lower = text.lower()

    if not any(term in text_lower for term in PRICE_MOVE_TERMS):
        return False
    if not any(verb in text_lower for verb in PRICE_MOVE_VERBS):
        return False

    has_critical, _ = check_critical_keywords(text_lower)
    has_moderate, _ = check_moderate_keywords(text_lower)
    return not (has_critical or has_moderate)


def check_critical_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains critical keywords.

    Returns:
        Tuple of (has_critical, list of found keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in CRITICAL_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def check_moderate_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains moderate concern keywords.

    Returns:
        Tuple of (has_moderate, list of found keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in MODERATE_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def check_positive_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains positive financial keywords.

    Returns:
        Tuple of (has_positive, list of found keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in POSITIVE_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def analyze_stock_news(ticker: str, company_name: str = None) -> Dict:
    """
    Comprehensive news analysis for a stock.

    Args:
        ticker: Stock ticker symbol
        company_name: Company name (optional, improves search)

    Returns:
        Dict with news items, sentiment analysis, and safety assessment
    """
    # Build search query
    search_terms = [ticker]
    if company_name:
        # Clean company name (remove Inc, Corp, etc.)
        clean_name = re.sub(r'\s+(Inc\.?|Corp\.?|Ltd\.?|LLC|PLC|Co\.?)$', '', company_name, flags=re.IGNORECASE)
        search_terms.append(clean_name)

    # Fetch news
    all_news = []
    for term in search_terms:
        news = fetch_news_google(f"{term} stock", num_results=5)
        all_news.extend(news)

    # Remove duplicates by title
    seen_titles = set()
    unique_news = []
    for item in all_news:
        if item["title"] not in seen_titles:
            seen_titles.add(item["title"])
            unique_news.append(item)

    # Analyze each news item
    analyzed_news = []
    all_text = ""

    for item in unique_news[:10]:  # Limit to 10 articles
        text = f"{item['title']} {item.get('summary', '')}"
        all_text += " " + text

        sentiment = analyze_sentiment(text)
        has_critical, critical_kw = check_critical_keywords(text)
        has_moderate, moderate_kw = check_moderate_keywords(text)
        price_move_only = is_price_move_only(text)

        analyzed_news.append({
            **item,
            "sentiment": sentiment,
            "has_critical_keywords": has_critical,
            "critical_keywords": critical_kw,
            "has_moderate_keywords": has_moderate,
            "moderate_keywords": moderate_kw,
            "price_move_only": price_move_only
        })

    # Overall assessment
    if not analyzed_news:
        return {
            "news": [],
            "overall_sentiment": 0,
            "critical_issues": False,
            "critical_keywords_found": [],
            "moderate_issues": False,
            "moderate_keywords_found": [],
            "safety_score": 50,  # Unknown - neutral score
            "assessment": "unknown",
            "message": "No recent news found"
        }

    # Calculate overall sentiment
    effective_sentiments = [
        n["sentiment"]["polarity"]
        for n in analyzed_news
        if not n.get("price_move_only")
    ]
    overall_sentiment = (
        sum(effective_sentiments) / len(effective_sentiments)
        if effective_sentiments else 0
    )

    # Check for any critical keywords across all news
    all_critical = []
    all_moderate = []
    for n in analyzed_news:
        all_critical.extend(n.get("critical_keywords", []))
        all_moderate.extend(n.get("moderate_keywords", []))

    all_critical = list(set(all_critical))
    all_moderate = list(set(all_moderate))

    # Calculate safety score (0-100)
    # Start at 75, adjust based on factors
    safety_score = 75

    # Sentiment adjustment (-25 to +15)
    safety_score += overall_sentiment * 15

    # Critical keywords: major penalty
    if all_critical:
        safety_score -= min(40, len(all_critical) * 15)

    # Moderate keywords: minor penalty
    if all_moderate:
        safety_score -= min(15, len(all_moderate) * 5)

    safety_score = max(0, min(100, safety_score))

    has_non_price_negative = any(
        n["sentiment"]["polarity"] < -0.1 and not n.get("price_move_only")
        for n in analyzed_news
    )

    # Assessment
    if all_critical:
        assessment = "avoid"
        message = f"Critical issues detected: {', '.join(all_critical[:3])}"
    elif has_non_price_negative:
        assessment = "caution"
        message = "Negative news detected beyond price movement"
        safety_score = min(safety_score, 59)
    elif safety_score >= 60:
        assessment = "safe"
        if all_moderate:
            message = f"Minor concerns ({', '.join(all_moderate[:2])}), but no critical issues"
        else:
            message = "No significant negative news detected"
    elif safety_score >= 40:
        assessment = "caution"
        message = "Some concerns detected, review news carefully"
    else:
        assessment = "avoid"
        message = "Multiple negative signals detected"

    return {
        "news": analyzed_news,
        "overall_sentiment": round(overall_sentiment, 3),
        "critical_issues": len(all_critical) > 0,
        "critical_keywords_found": all_critical,
        "moderate_issues": len(all_moderate) > 0,
        "moderate_keywords_found": all_moderate,
        "safety_score": round(safety_score),
        "assessment": assessment,
        "message": message
    }


def is_safe_drop(ticker: str, company_name: str = None, min_safety_score: int = 50) -> Tuple[bool, Dict]:
    """
    Determine if a stock's price drop is "safe" (not due to critical issues).

    Args:
        ticker: Stock ticker
        company_name: Company name (optional)
        min_safety_score: Minimum safety score to consider safe (default 50)

    Returns:
        Tuple of (is_safe: bool, analysis: Dict)
    """
    analysis = analyze_stock_news(ticker, company_name)

    is_safe = (
        not analysis["critical_issues"] and
        analysis["safety_score"] >= min_safety_score
    )

    return is_safe, analysis


if __name__ == "__main__":
    # Test with a stock
    test_ticker = "AAPL"
    test_name = "Apple Inc"

    print(f"\nAnalyzing news for {test_ticker} ({test_name})...")
    is_safe, analysis = is_safe_drop(test_ticker, test_name)

    print(f"\nSafety Score: {analysis['safety_score']}/100")
    print(f"Assessment: {analysis['assessment']}")
    print(f"Message: {analysis['message']}")
    print(f"\nRecent News:")

    for news in analysis["news"][:5]:
        print(f"  - {news['title']}")
        print(f"    Sentiment: {news['sentiment']['interpretation']} ({news['sentiment']['polarity']})")
        if news["critical_keywords"]:
            print(f"    Critical: {news['critical_keywords']}")
