"""
Router de Monte Carlo — /montecarlo/*
"""

from fastapi import APIRouter, HTTPException

from services import montecarlo_service
from models.schemas import MonteCarloRequest, MonteCarloResponse

router = APIRouter(prefix="/montecarlo", tags=["montecarlo"])


@router.post("/run", response_model=MonteCarloResponse)
async def run_montecarlo(body: MonteCarloRequest):
    """
    Simulación GBM del portafolio ponderado.

    Proyecta N trayectorias posibles del portafolio hacia el futuro.
    Retorna percentiles 5/50/95 y distribución de valores finales.
    Los parámetros μ y σ se estiman de los últimos 2 años de datos históricos.
    """
    if len(body.tickers) != len(body.weights):
        raise HTTPException(status_code=422, detail="tickers y weights deben tener el mismo largo.")
    if abs(sum(body.weights) - 1.0) > 0.02:
        raise HTTPException(status_code=422, detail="Los pesos deben sumar 1.0.")

    try:
        return montecarlo_service.run_montecarlo(
            tickers=body.tickers,
            weights=body.weights,
            horizon_days=body.horizon_days,
            simulations=body.simulations,
            initial_value=body.initial_value,
            seed=body.seed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
