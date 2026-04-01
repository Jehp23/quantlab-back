"""
Wrapper de yfinance para mercados globales.

yfinance es un cliente no oficial de Yahoo Finance — perfecto para uso educativo/personal.
Para descarga masiva de históricos, yf.download() es más eficiente que ticker a ticker.
"""

import yfinance as yf
import pandas as pd
from typing import Optional


def get_quote(ticker: str) -> dict:
    """
    Retorna la cotización actual y metadata de un ticker.

    yfinance expone el dict `info` con más de 100 campos.
    Usamos regularMarketPrice para el precio actual (vs previousClose para el cambio).
    """
    t = yf.Ticker(ticker)
    info = t.info

    price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName") or ticker,
        "price": round(price, 4),
        "currency": info.get("currency", "USD"),
        "change": round(change, 4),
        "change_pct": round(change_pct, 4),
        "volume": info.get("regularMarketVolume") or info.get("volume"),
        "market_cap": info.get("marketCap"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
    }


def get_historical(ticker: str, period: str = "1y") -> list[dict]:
    """
    Retorna datos OHLCV históricos para un ticker.

    Period válidos: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    El interval es diario ("1d") — suficiente para todas las métricas quant de la Fase 1.
    """
    t = yf.Ticker(ticker)
    hist: pd.DataFrame = t.history(period=period, interval="1d")

    if hist.empty:
        return []

    hist.index = pd.to_datetime(hist.index)
    result = []
    for date, row in hist.iterrows():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
        })

    return result


def get_multiple_historical(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """
    Descarga históricos de múltiples tickers simultáneamente.

    Retorna un DataFrame con columna 'Close' multi-index (ticker x fecha).
    Más eficiente que llamar get_historical() N veces — usa una sola request HTTP.
    Usado por portfolio_service y optimizer_service para cálculos matriciales.
    """
    data = yf.download(tickers, period=period, interval="1d", auto_adjust=True, progress=False)

    # yfinance 1.x siempre retorna MultiIndex (Price, Ticker) para listas;
    # data["Close"] extrae el nivel "Close" y retorna columnas = tickers en ambos casos.
    close = data["Close"]
    if isinstance(close, pd.Series):
        # Fallback defensivo: si por alguna razón retorna Series, convertir a DataFrame
        close = close.to_frame(name=tickers[0])

    # Eliminar filas con todos NaN y forward-fill gaps menores
    close = close.dropna(how="all").ffill()
    return close
