"""
Wrapper de yfinance para mercados globales.

yfinance >= 0.2.x usa curl_cffi internamente para evitar el bot detection de Yahoo Finance.
No pasar session externa — yfinance maneja todo solo.
Se agrega retry con backoff para 429 Rate Limit en IPs compartidas (Render, etc.).
"""

import time
import random
import logging

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_DELAY  = 2.0  # segundos, se duplica con cada reintento


def _with_retry(fn, label: str):
    """Ejecuta fn() hasta _MAX_RETRIES veces con backoff exponencial en rate limit."""
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            is_rate_limit = any(k in msg for k in ("too many requests", "rate limit", "429", "no data"))
            if is_rate_limit and attempt < _MAX_RETRIES - 1:
                wait = _BASE_DELAY * (2 ** attempt) + random.uniform(0.5, 1.5)
                logger.warning("yfinance rate limited [%s] — reintento %d/%d en %.1fs",
                               label, attempt + 1, _MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                break
    raise ValueError(
        f"No se encontró el ticker '{label}'. "
        "Verificá que sea válido (ej: AAPL, MSFT, SPY) o intentá de nuevo en unos segundos."
    )


def get_quote(ticker: str) -> dict:
    def _fetch():
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            raise ValueError(f"Sin datos para '{ticker}'.")
        return info

    info = _with_retry(_fetch, ticker)

    price      = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
    change     = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "ticker":              ticker.upper(),
        "name":                info.get("longName") or info.get("shortName") or ticker,
        "price":               round(price, 4),
        "currency":            info.get("currency", "USD"),
        "change":              round(change, 4),
        "change_pct":          round(change_pct, 4),
        "volume":              info.get("regularMarketVolume") or info.get("volume"),
        "market_cap":          info.get("marketCap"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low":  info.get("fiftyTwoWeekLow"),
        "beta":                info.get("beta"),
        "dividend_yield":      info.get("dividendYield"),
    }


def get_historical(ticker: str, period: str = "1y") -> list[dict]:
    def _fetch():
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
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
    def _fetch():
        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if data.empty:
            raise ValueError(f"Sin datos para {tickers}.")
        return data

    data = _with_retry(_fetch, str(tickers))

    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])

    return close.dropna(how="all").ffill()
