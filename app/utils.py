import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID")
EBAY_OAUTH_TOKEN = os.getenv("EBAY_OAUTH_TOKEN")   # For Buy API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# -----------------------------------------------------------
# LOGGING HELPER
# -----------------------------------------------------------
def log(msg):
    print(f"[watch-finder] {msg}", flush=True)

# -----------------------------------------------------------
# GET LISTINGS FROM SPECIFIC EBAY SELLER
# -----------------------------------------------------------
def fetch_ebay_listings(seller_username, limit=50):
    """
    Fetch active listings from a specific seller using eBay Buy API.
    """

    url = (
        "https://api.ebay.com/buy/browse/v1/item_summary/search?"
        f"q=rolex&filter=sellers:{seller_username}&limit={limit}"
    )

    headers = {
        "Authorization": f"Bearer {EBAY_OAUTH_TOKEN}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Type": "application/json"
    }

    log(f"Fetching eBay listings for seller: {seller_username}")

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        log(f"Error from eBay API: {response.status_code} {response.text}")
        return []

    data = response.json()
    return data.get("itemSummaries", [])

# -----------------------------------------------------------
# NORMALIZE LISTINGS
# -----------------------------------------------------------
def normalize_listing(item):
    """
    Convert eBay item fields into a clean structure for LLM analysis.
    """

    return {
        "title": item.get("title", ""),
        "price": item.get("price", {}).get("value"),
        "currency": item.get("price", {}).get("currency"),
        "condition": item.get("condition"),
        "seller_item_url": item.get("itemWebUrl"),
        "image": item.get("image", {}).get("imageUrl"),
        "item_id": item.get("itemId"),
    }

# -----------------------------------------------------------
# CHATGPT INVESTMENT SCORE ENGINE
# -----------------------------------------------------------
def score_watch_with_ai(listing_data):
    """
    Sends a single normalized listing to ChatGPT and returns
    an investment rating + summary.
    """

    prompt = f"""
You are a Rolex investment expert. Analyze the following watch and return ONLY structured JSON.

Listing:
{listing_data}

Return JSON with EXACTLY these fields:
{{
  "score": float (0-10),
  "model_rating": float,
  "rarity_rating": float,
  "condition_rating": float,
  "price_fairness": float,
  "investment_comment": "short explanation"
}}
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    response = requests.post(OPENAI_URL, json=payload, headers=headers)

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return eval(content)  # safe because response is JSON-like
    except Exception as e:
        log(f"AI scoring error: {e} | Raw: {response.text}")
        return None

# -----------------------------------------------------------
# FILTER ONLY TOP INVESTMENT WATCHES
# -----------------------------------------------------------
def filter_top_watches(listings, min_score=8.5):
    """
    Given a list of normalized listings with AI scores,
    return only watches scoring above required threshold.
    """
    return [w for w in listings if w.get("score", 0) >= min_score]

# -----------------------------------------------------------
# MAIN SCAN FUNCTION
# -----------------------------------------------------------
def scan_seller(seller_username):
    """
    1. Pull listings from eBay seller  
    2. Normalize  
    3. Score with ChatGPT  
    4. Keep only > 8.5  
    """

    raw_items = fetch_ebay_listings(seller_username)
    results = []

    for item in raw_items:
        normalized = normalize_listing(item)
        score = score_watch_with_ai(normalized)
        if not score:
            continue

        entry = {**normalized, **score}
        results.append(entry)

        # Avoid rate limit spikes
        time.sleep(1.2)

    return filter_top_watches(results)
