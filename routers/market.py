"""
Router de mercado — /market/*

Expone datos de precios y cotizaciones, tanto globales (yfinance) como argentinos (data912).
Los routers son thin: delegan toda la lógica a los services.
"""

from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    QuoteResponse,
    HistoricalResponse,
    OHLCPoint,
    ARStocksResponse,
    ARCedearsResponse,
    ARStockItem,
)
from services import yahoo_service, data912_service

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(ticker: str = Query(..., description="Ticker de Yahoo Finance, ej: SPY, QQQ, AAPL")):
    """
    Cotización actual de cualquier ticker global disponible en Yahoo Finance.

    Retorna precio, cambio diario, volumen, market cap, 52w high/low, beta, dividend yield.
    """
    try:
        data = yahoo_service.get_quote(ticker.upper())
        return QuoteResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No se encontró el ticker '{ticker}': {str(e)}")


@router.get("/historical", response_model=HistoricalResponse)
async def get_historical(
    ticker: str = Query(..., description="Ticker de Yahoo Finance"),
    period: str = Query("1y", description="Período: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max"),
):
    """
    Datos OHLCV históricos diarios para un ticker global.

    Útil para graficar precios, calcular métricas y alimentar el optimizador.
    """
    valid_periods = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Período inválido. Válidos: {valid_periods}")

    try:
        data = yahoo_service.get_historical(ticker.upper(), period)
        ohlc_points = [OHLCPoint(**point) for point in data]
        return HistoricalResponse(ticker=ticker.upper(), period=period, data=ohlc_points)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error obteniendo histórico de '{ticker}': {str(e)}")


@router.get("/ar/stocks", response_model=ARStocksResponse)
async def get_ar_stocks():
    """
    Acciones argentinas (BYMA) en tiempo real — via data912.com.

    Precios en ARS. Incluye el panel líder y general de la bolsa argentina.
    Delay de ~20 segundos respecto al mercado.
    """
    try:
        data = await data912_service.get_ar_stocks()
        items = [ARStockItem(**item) for item in data]
        return ARStocksResponse(data=items, count=len(items))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error obteniendo acciones AR: {str(e)}")


@router.get("/ar/cedears", response_model=ARCedearsResponse)
async def get_ar_cedears():
    """
    CEDEARs en tiempo real — via data912.com.

    Precios en ARS en BYMA. Para convertir a USD equivalente se necesita el ratio
    de conversión de cada CEDEAR y el tipo de cambio CCL.
    """
    try:
        data = await data912_service.get_ar_cedears()
        items = [ARStockItem(**item) for item in data]
        return ARCedearsResponse(data=items, count=len(items))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error obteniendo CEDEARs: {str(e)}")


@router.get("/ar/historical/{ticker}")
async def get_ar_historical(
    ticker: str,
    asset_type: str = Query("stocks", description="Tipo de activo: stocks | cedears | bonds"),
):
    """
    Datos OHLC históricos para activos del mercado argentino — via data912.com.

    Ejemplos de tickers:
    - stocks: GGAL, YPFD, PAMP, BBAR
    - cedears: AAPL, MSFT, GOOGL, AMZN
    - bonds: AL30, GD30, GD35
    """
    valid_types = {"stocks", "cedears", "bonds"}
    if asset_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"asset_type inválido. Válidos: {valid_types}")

    try:
        data = await data912_service.get_ar_historical(ticker.upper(), asset_type)
        return {"ticker": ticker.upper(), "asset_type": asset_type, "data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error obteniendo histórico AR de '{ticker}': {str(e)}")
