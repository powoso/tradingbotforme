"""
Live crypto price fetcher for the CounterTrade Bot.
Uses CoinGecko's free API (no API key required).
Caches prices for 60 seconds to avoid rate limiting.
"""

import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# CoinGecko free API base
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map common ticker symbols to CoinGecko IDs
SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "NEAR": "near",
    "ARB": "arbitrum",
    "OP": "optimism",
    "APT": "aptos",
    "SUI": "sui",
    "FIL": "filecoin",
    "INJ": "injective-protocol",
    "TIA": "celestia",
    "SEI": "sei-network",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "SHIB": "shiba-inu",
    "BNB": "binancecoin",
    "TRX": "tron",
    "TON": "the-open-network",
    "HBAR": "hedera-hashgraph",
    "ICP": "internet-computer",
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "AAVE": "aave",
    "MKR": "maker",
    "SNX": "havven",
    "CRV": "curve-dao-token",
    "RUNE": "thorchain",
    "STX": "blockstack",
    "IMX": "immutable-x",
    "RNDR": "render-token",
    "GRT": "the-graph",
    "WLD": "worldcoin-wld",
    "JUP": "jupiter-exchange-solana",
    "PYTH": "pyth-network",
    "JTO": "jito-governance-token",
    "PENDLE": "pendle",
    "ENA": "ethena",
    "W": "wormhole",
}

# Default watchlist
DEFAULT_WATCHLIST = ["BTC", "ETH", "SOL", "DOGE", "XRP", "LINK", "AVAX", "ARB"]

# Price cache
_price_cache: dict[str, Any] = {}
_cache_timestamp: float = 0
CACHE_TTL = 60  # seconds


def _get_coingecko_ids(symbols: list[str]) -> list[str]:
    """Convert ticker symbols to CoinGecko IDs."""
    ids = []
    for s in symbols:
        upper = s.upper().strip()
        if upper in SYMBOL_TO_ID:
            ids.append(SYMBOL_TO_ID[upper])
        else:
            # Try lowercase as fallback (some CoinGecko IDs match)
            ids.append(upper.lower())
    return ids


async def get_prices(symbols: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Fetch current prices for a list of crypto symbols.
    Returns a dict of { symbol: { price, change_24h, change_7d, market_cap, volume_24h, sparkline } }.
    Uses cache to avoid hammering the API.
    """
    global _price_cache, _cache_timestamp

    if symbols is None:
        symbols = DEFAULT_WATCHLIST

    # Check cache
    cache_key = ",".join(sorted(s.upper() for s in symbols))
    now = time.time()
    if _price_cache and (now - _cache_timestamp) < CACHE_TTL:
        # Return cached if same symbols
        if all(s.upper() in _price_cache for s in symbols):
            return {s.upper(): _price_cache[s.upper()] for s in symbols if s.upper() in _price_cache}

    cg_ids = _get_coingecko_ids(symbols)
    ids_str = ",".join(cg_ids)

    try:
        url = (
            f"{COINGECKO_BASE}/coins/markets"
            f"?vs_currency=usd"
            f"&ids={ids_str}"
            f"&order=market_cap_desc"
            f"&sparkline=true"
            f"&price_change_percentage=1h,24h,7d"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("CoinGecko API error: %s", exc)
        # Return cached data if available
        if _price_cache:
            return {s.upper(): _price_cache.get(s.upper(), {}) for s in symbols}
        return {}

    # Build reverse mapping: CoinGecko ID -> symbol
    id_to_symbol = {}
    for sym, cg_id in SYMBOL_TO_ID.items():
        id_to_symbol[cg_id] = sym

    result: dict[str, Any] = {}
    for coin in data:
        cg_id = coin.get("id", "")
        symbol = id_to_symbol.get(cg_id, coin.get("symbol", "").upper())

        sparkline_data = coin.get("sparkline_in_7d", {}).get("price", [])
        # Downsample sparkline to last 24 points for the mini chart
        if len(sparkline_data) > 24:
            step = len(sparkline_data) // 24
            sparkline_data = sparkline_data[::step][-24:]

        result[symbol] = {
            "price": coin.get("current_price", 0),
            "change_1h": coin.get("price_change_percentage_1h_in_currency", 0),
            "change_24h": coin.get("price_change_percentage_24h", 0),
            "change_7d": coin.get("price_change_percentage_7d_in_currency", 0),
            "market_cap": coin.get("market_cap", 0),
            "volume_24h": coin.get("total_volume", 0),
            "high_24h": coin.get("high_24h", 0),
            "low_24h": coin.get("low_24h", 0),
            "image": coin.get("image", ""),
            "sparkline": sparkline_data,
            "name": coin.get("name", symbol),
        }

    # Update cache
    _price_cache.update(result)
    _cache_timestamp = now

    return result


async def get_trending() -> list[dict]:
    """Fetch trending coins from CoinGecko."""
    try:
        url = f"{COINGECKO_BASE}/search/trending"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        coins = data.get("coins", [])
        return [
            {
                "symbol": c["item"].get("symbol", ""),
                "name": c["item"].get("name", ""),
                "market_cap_rank": c["item"].get("market_cap_rank"),
                "thumb": c["item"].get("thumb", ""),
                "price_btc": c["item"].get("price_btc", 0),
            }
            for c in coins[:8]
        ]
    except Exception as exc:
        logger.warning("CoinGecko trending error: %s", exc)
        return []


async def get_fear_greed_index() -> dict:
    """Fetch the Crypto Fear & Greed Index from alternative.me."""
    try:
        url = "https://api.alternative.me/fng/?limit=1&format=json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        entry = data.get("data", [{}])[0]
        return {
            "value": int(entry.get("value", 50)),
            "label": entry.get("value_classification", "Neutral"),
            "timestamp": entry.get("timestamp", ""),
        }
    except Exception as exc:
        logger.warning("Fear & Greed Index error: %s", exc)
        return {"value": 50, "label": "Neutral", "timestamp": ""}
