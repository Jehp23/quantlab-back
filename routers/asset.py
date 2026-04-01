"""
Router de análisis de activos individuales — /asset/*

Endpoints:
- GET /asset/analyze?ticker=AAPL&period=2y&benchmark=SPY
- POST /asset/compare   Body: {tickers: [...], period: "2y"}
"""

import logging

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field

from services import asset_service
from models.schemas import AssetAnalysisResponse, AssetCompareResponse

router = APIRouter(prefix="/asset", tags=["asset"])


class CompareRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=8)
    period: str = "2y"


@router.get("/analyze", response_model=AssetAnalysisResponse)
async def analyze_asset(
    ticker: str = Query(..., description="Ticker del activo (ej: AAPL, SPY, GGAL)"),
    period: str = Query("2y", description="Período histórico: 1y, 2y, 5y, max"),
    benchmark: str = Query("SPY", description="Benchmark para beta/alpha"),
):
    """
    Métricas completas de un activo individual.

    Retorna: quote, OHLC histórico, métricas de riesgo/retorno,
    beta y alpha de Jensen vs el benchmark, y rolling volatility.
    """
    try:
        result = asset_service.analyze_asset(
            ticker=ticker.upper(),
            period=period,
            benchmark=benchmark.upper(),
        )
        return result
    except KeyError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=404,
            detail="Ticker no encontrado o sin datos suficientes.",
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Error al analizar el activo. Verificá el ticker e intentá de nuevo.")


@router.post("/compare", response_model=AssetCompareResponse)
async def compare_assets(body: CompareRequest):
    """
    Compara múltiples activos normalizados a base 100.

    Útil para visualizar performance relativa entre activos con precios
    nominales muy distintos. Máximo 8 tickers por request.
    """
    try:
        result = asset_service.compare_assets(
            tickers=[t.upper() for t in body.tickers],
            period=body.period,
        )
        if not result["tickers"]:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos para los tickers solicitados.",
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
