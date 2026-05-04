"""
Wrapper de yfinance para mercados globales.

yfinance es un cliente no oficial de Yahoo Finance.
En entornos de servidor con IP compartida (Render, Railway, etc.) Yahoo Finance
aplica rate limiting agresivo. Se mitiga con:
  - Session con headers de browser real
  - Retry con exponential backoff (3 intentos)
"""

import time
import random
import logging

import requests
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

_MAX_RETRIES = 3
_BASE_DELAY  = 1.5   # segundos, se duplica con cada intento


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _with_retry(fn, ticker: str):
    """Ejecuta fn() hasta _MAX_RETRIES veces con backoff exponencial."""
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            result = fn()
            return result
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            if "too many requests" in msg or "rate limit" in msg or "429" in msg:
                wait = _BASE_DELAY * (2 ** attempt) + random.uniform(0.5, 1.5)
                logger.warning("yfinance rate limited for %s — retry %d/%d in %.1fs",
                               ticker, attempt + 1, _MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                break   # error distinto, no reintentar
    raise ValueError(
        f"No se encontró el ticker '{ticker}': {last_err}. "
        "Verificá que el ticker sea válido (ej: AAPL, MSFT, SPY)."
    )


def get_quote(ticker: str) -> dict:
    def _fetch():
        t = yf.Ticker(ticker, session=_session())
        info = t.info
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            raise ValueError(f"Ticker '{ticker}' no encontrado.")
        return info

    info = _with_retry(_fetch, ticker)

    price      = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
    change     = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "ticker":               ticker.upper(),
        "name":                 info.get("longName") or info.get("shortName") or ticker,
        "price":                round(price, 4),
        "currency":             info.get("currency", "USD"),
        "change":               round(change, 4),
        "change_pct":           round(change_pct, 4),
        "volume":               info.get("regularMarketVolume") or info.get("volume"),
        "market_cap":           info.get("marketCap"),
        "fifty_two_week_high":  info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low":   info.get("fiftyTwoWeekLow"),
        "beta":                 info.get("beta"),
        "dividend_yield":       info.get("dividendYield"),
    }


def get_historical(ticker: str, period: str = "1y") -> list[dict]:
    """
    Retorna datos OHLCV históricos para un ticker.
    Period válidos: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    def _fetch():
        t = yf.Ticker(ticker, session=_session())
        hist: pd.DataFrame = t.history(period=period, interval="1d")
        if hist.empty:
            raise ValueError(f"Sin datos para '{ticker}' en período '{period}'.")
        return hist

    hist = _with_retry(_fetch, ticker)

    hist.index = pd.to_datetime(hist.index)
    return [
        {
            "date":   date.strftime("%Y-%m-%d"),
            "open":   round(float(row["Open"]), 4),
            "high":   round(float(row["High"]), 4),
            "low":    round(float(row["Low"]), 4),
            "close":  round(float(row["Close"]), 4),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
        }
        for date, row in hist.iterrows()
    ]


def get_multiple_historical(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """
    Descarga históricos de múltiples tickers simultáneamente.
    Más eficiente que llamar get_historical() N veces.
    """
    def _fetch():
        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            session=_session(),
        )
        return data

    data = _with_retry(_fetch, str(tickers))

    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])

    return close.dropna(how="all").ffill()
