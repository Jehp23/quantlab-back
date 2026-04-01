"""
Wrapper httpx async para data912.com — mercado argentino.

data912.com es una API gratuita con datos de BYMA (Bolsa y Mercados Argentinos).
Rate limit: 120 req/min. Refresh: cada 20 segundos (precios live), diario (opciones/EOD).
Sin autenticación requerida. Licencia: "Do whatever you want with the data".

IMPORTANTE: API de un individuo, puede tener downtime ocasional.
Los precios son con 20s de delay — no son estrictamente real-time.
"""

import httpx
from typing import Any

BASE_URL = "https://data912.com"

# Timeout generoso dado que la API puede ser lenta en horario de mercado
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


async def _get(path: str) -> Any:
    """Helper interno: realiza GET a data912.com y retorna el JSON parseado."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}{path}")
        response.raise_for_status()
        return response.json()


def _normalize_stock(item: dict) -> dict:
    """
    Normaliza un item de la respuesta live de data912 al formato interno.

    Campos originales: symbol, c (close/precio), v (volumen), px_bid, px_ask,
    q_bid, q_ask, pct_change, q_op (operaciones).
    """
    return {
        "symbol": item.get("symbol", ""),
        "price": float(item.get("c", 0) or 0),
        "change_pct": float(item.get("pct_change", 0) or 0),
        "bid": float(item.get("px_bid", 0) or 0) or None,
        "ask": float(item.get("px_ask", 0) or 0) or None,
        "volume": int(item.get("v", 0) or 0) or None,
    }


async def get_ar_stocks() -> list[dict]:
    """
    Acciones argentinas (BYMA) en tiempo real.

    Retorna todas las acciones del panel BYMA con precios en ARS.
    Incluye líderes, panel general y SME.
    """
    data = await _get("/live/arg_stocks")
    if isinstance(data, list):
        return [_normalize_stock(item) for item in data]
    return []


async def get_ar_cedears() -> list[dict]:
    """
    CEDEARs en tiempo real — precio en ARS en BYMA.

    IMPORTANTE: El precio de un CEDEAR en ARS ≠ precio del subyacente en USD.
    La relación es: precio_cedear_ARS = precio_subyacente_USD × tipo_cambio_ccl / ratio_cedear.
    Para comparar con yfinance se debe aplicar esta conversión.
    """
    data = await _get("/live/arg_cedears")
    if isinstance(data, list):
        return [_normalize_stock(item) for item in data]
    return []


async def get_ar_historical(ticker: str, asset_type: str = "stocks") -> list[dict]:
    """
    Datos OHLC históricos para activos argentinos.

    asset_type: "stocks" (acciones BYMA) | "cedears" | "bonds"

    Campos originales: date, o (open), h (high), l (low), c (close),
    v (volume), dr (daily return), sa (sigma anualizado).
    """
    path = f"/historical/{asset_type}/{ticker.upper()}"
    data = await _get(path)

    if not isinstance(data, list):
        return []

    result = []
    for item in data:
        result.append({
            "date": item.get("date", ""),
            "open": float(item.get("o", 0) or 0),
            "high": float(item.get("h", 0) or 0),
            "low": float(item.get("l", 0) or 0),
            "close": float(item.get("c", 0) or 0),
            "volume": int(item.get("v", 0) or 0) or None,
        })

    return result


async def get_mep() -> dict:
    """
    Dólar MEP (Mercado Electrónico de Pagos).

    Retorna bid/ask en ARS y USD, con volúmenes.
    El MEP es el tipo de cambio implícito AL30 ARS / AL30 USD (o bonos similares).
    """
    return await _get("/live/mep")


async def get_ccl() -> dict:
    """
    Dólar CCL (Contado con Liquidación).

    Similar al MEP pero usando activos que cotizan en el exterior (ADRs).
    Generalmente cotiza levemente por encima del MEP.
    """
    return await _get("/live/ccl")


async def get_option_chain(ticker: str) -> dict:
    """
    Cadena de opciones completa con Greeks para un ticker argentino.

    Greeks disponibles: delta, gamma, theta, vega, rho, fair_value, itm_prob (probabilidad ITM).
    Datos EOD (end of day) — actualizados al cierre del mercado.
    """
    return await _get(f"/eod/option_chain/{ticker.upper()}")


async def get_volatilities(ticker: str) -> dict:
    """
    Volatilidades implícitas y históricas para análisis de opciones.

    IV (implied volatility) vs HV (historical volatility) en tres plazos:
    - Short: ~30 días
    - Medium: ~60 días
    - Long: ~90 días

    iv_percentile: posición de la IV actual en el rango del último año (0-100%).
    Ratio IV/HV > 1 indica que las opciones son "caras" vs historia — oportunidad de venta de vol.
    """
    return await _get(f"/eod/volatilities/{ticker.upper()}")
