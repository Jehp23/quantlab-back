"""
Router de análisis estadístico — /statistics/*

GET /statistics/full?ticker=SPY&period=2y
    Análisis completo en un solo endpoint: performance, riesgo, normalidad,
    volatilidad, tests estadísticos, ACF, heatmap mensual.
"""

from fastapi import APIRouter, HTTPException, Query
from services import statistics_service

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/full")
async def full_analysis(
    ticker: str = Query(..., description="Ticker del activo (ej: SPY, AAPL)"),
    period: str = Query("2y", description="Período: 1y, 2y, 5y, max"),
):
    """
    Análisis estadístico completo de un activo.

    Retorna todos los módulos en una sola respuesta:
    performance, riesgo (VaR/CVaR), normalidad (JB),
    volatilidad rolling, tests (t-test, rachas), ACF/Ljung-Box,
    heatmap mensual.
    """
    try:
        return statistics_service.full_analysis(ticker.upper().strip(), period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar {ticker}: {str(e)}")
