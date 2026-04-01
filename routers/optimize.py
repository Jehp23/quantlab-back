"""
Router de optimización de portafolios — /optimize/*

Endpoints:
- POST /optimize/max-sharpe
- POST /optimize/min-variance
- POST /optimize/risk-parity
- GET  /optimize/frontier?tickers=SPY,QQQ,...&period=5y
"""

from fastapi import APIRouter, HTTPException, Query

from services import optimizer_service
from models.schemas import OptimizeRequest, OptimizeResponse

router = APIRouter(prefix="/optimize", tags=["optimize"])


def _handle(fn, *args, **kwargs):
    """Wrapper de manejo de errores común a todos los endpoints."""
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/max-sharpe", response_model=OptimizeResponse)
async def max_sharpe(body: OptimizeRequest):
    """
    Portafolio de Máximo Sharpe Ratio (Tangency Portfolio).

    Maximiza el retorno excedente por unidad de riesgo.
    Usa Ledoit-Wolf shrinkage + L2 regularization para mayor robustez.
    """
    return _handle(
        optimizer_service.optimize_max_sharpe,
        body.tickers,
        body.period,
        body.risk_free_rate,
    )


@router.post("/min-variance", response_model=OptimizeResponse)
async def min_variance(body: OptimizeRequest):
    """
    Portafolio de Mínima Varianza.

    Punto más a la izquierda de la frontera eficiente.
    No depende de estimaciones de retorno — solo de la covarianza.
    """
    return _handle(
        optimizer_service.optimize_min_variance,
        body.tickers,
        body.period,
        body.risk_free_rate,
    )


@router.post("/risk-parity", response_model=OptimizeResponse)
async def risk_parity(body: OptimizeRequest):
    """
    Portafolio de Risk Parity (Equal Risk Contribution).

    Cada activo contribuye igual al riesgo total.
    Más robusto a errores de estimación que Markowitz.
    """
    return _handle(
        optimizer_service.optimize_risk_parity,
        body.tickers,
        body.period,
        body.risk_free_rate,
    )


@router.get("/frontier")
async def efficient_frontier(
    tickers: str = Query(..., description="Tickers separados por coma: SPY,QQQ,AGG"),
    period: str = Query("5y", description="Período histórico: 3y, 5y, 10y"),
    risk_free_rate: float = Query(0.05, description="Tasa libre de riesgo anual"),
    points: int = Query(40, ge=10, le=80, description="Número de puntos en la frontera"),
):
    """
    Frontera eficiente de Markowitz.

    Retorna una lista de {return, volatility, sharpe} para visualizar la
    curva completa de portafolios óptimos en el espacio retorno-riesgo.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 tickers.")
    return _handle(
        optimizer_service.compute_efficient_frontier,
        ticker_list,
        period,
        risk_free_rate,
        points,
    )
