"""
Router de backtesting — /backtest/*
"""

from fastapi import APIRouter, HTTPException

from services import backtest_service
from models.schemas import BacktestRequest, BacktestResponse

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(body: BacktestRequest):
    """
    Simula el portafolio con rebalanceo periódico sobre datos históricos.

    Compara el rendimiento del portafolio vs SPY (benchmark).
    El rebalanceo fuerza los pesos objetivo en cada período.
    """
    if len(body.tickers) != len(body.weights):
        raise HTTPException(status_code=422, detail="tickers y weights deben tener el mismo largo.")
    if abs(sum(body.weights) - 1.0) > 0.02:
        raise HTTPException(status_code=422, detail="Los pesos deben sumar 1.0.")

    try:
        return backtest_service.run_backtest(
            tickers=body.tickers,
            weights=body.weights,
            start=body.start,
            end=body.end,
            rebalance_freq=body.rebalance_freq,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
