"""
Router de portafolio — /portfolio/*

Endpoints para construir un portafolio por perfil de riesgo y analizar sus métricas.
Thin layer: valida input HTTP y delega toda la lógica a portfolio_service.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import (
    PortfolioBuildRequest,
    PortfolioBuildResponse,
    PortfolioAnalyzeRequest,
    PortfolioAnalyzeResponse,
    PortfolioMetrics,
    EquityCurveResponse,
    EquityCurvePoint,
)
from services import portfolio_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/build", response_model=PortfolioBuildResponse)
async def build_portfolio(body: PortfolioBuildRequest):
    """
    Construye el portafolio sugerido para un perfil de riesgo (score 0-100).

    El score viene del cuestionario de onboarding. No descarga datos de mercado —
    devuelve la allocation y ETFs predefinidos para el perfil correspondiente.
    """
    try:
        result = portfolio_service.build_portfolio(
            risk_score=body.risk_score,
            investment_goal=body.investment_goal,
            horizon_years=body.horizon_years,
            liquidity_need=body.liquidity_need,
            experience_level=body.experience_level,
            monthly_contribution=body.monthly_contribution,
            emergency_buffer_months=body.emergency_buffer_months,
        )
        return PortfolioBuildResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze", response_model=PortfolioAnalyzeResponse)
async def analyze_portfolio(body: PortfolioAnalyzeRequest):
    """
    Analiza un portafolio calculando retorno, volatilidad, Sharpe, VaR y drawdown.

    Descarga precios históricos de yfinance para el período indicado y calcula
    todas las métricas con numpy/pandas. Puede tardar 2-5 segundos.
    """
    if len(body.tickers) != len(body.weights):
        raise HTTPException(
            status_code=400,
            detail=f"tickers ({len(body.tickers)}) y weights ({len(body.weights)}) deben tener la misma longitud",
        )

    total_weight = sum(body.weights)
    if abs(total_weight - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Los pesos deben sumar 1.0 (suma actual: {total_weight:.4f})",
        )

    try:
        result = portfolio_service.analyze_portfolio(
            body.tickers, body.weights, body.period
        )
        return PortfolioAnalyzeResponse(
            tickers=result["tickers"],
            weights=result["weights"],
            period=result["period"],
            metrics=PortfolioMetrics(**result["metrics"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al obtener datos de mercado: {str(e)}",
        )


def _validate_weights(body: PortfolioAnalyzeRequest) -> None:
    """Validaciones comunes para endpoints que reciben tickers + weights."""
    if len(body.tickers) != len(body.weights):
        raise HTTPException(
            status_code=400,
            detail=f"tickers ({len(body.tickers)}) y weights ({len(body.weights)}) deben tener la misma longitud",
        )
    total = sum(body.weights)
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Los pesos deben sumar 1.0 (suma actual: {total:.4f})",
        )


@router.post("/equity-curve", response_model=EquityCurveResponse)
async def equity_curve(body: PortfolioAnalyzeRequest):
    """
    Construye la equity curve del portafolio vs SPY como benchmark.

    Retorna la serie temporal de valores diarios (base $100) para graficar
    la evolución histórica del portafolio comparado con el mercado.
    Descarga portafolio + SPY en una sola request a yfinance.
    """
    _validate_weights(body)
    try:
        result = portfolio_service.get_equity_curve(
            body.tickers, body.weights, body.period
        )
        return EquityCurveResponse(
            tickers=result["tickers"],
            weights=result["weights"],
            period=result["period"],
            initial_value=result["initial_value"],
            data=[EquityCurvePoint(**p) for p in result["data"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al construir equity curve: {str(e)}",
        )
