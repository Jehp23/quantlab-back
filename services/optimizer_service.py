"""
Optimizador de portafolios — Markowitz, Min Variance, Risk Parity.

PyPortfolioOpt implementa los algoritmos de Markowitz usando optimización cuadrática convexa.
Ledoit-Wolf shrinkage para la covarianza: contrae la matriz muestral hacia la identidad
para reducir el error de estimación (fundamental con n activos cercano a n observaciones).

S_shrunk = (1-α) * S_sample + α * F
donde F = identidad escalada, α se elige óptimamente (Ledoit-Wolf 2004).

Risk Parity resuelto con SLSQP para no depender de la API interna de pypfopt
(más robusto entre versiones).
"""

import logging
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from pypfopt import EfficientFrontier, risk_models, expected_returns, objective_functions
from pypfopt.risk_models import CovarianceShrinkage

from constants.rates import RISK_FREE_RATE
from services import yahoo_service

logger = logging.getLogger(__name__)


def _load_data(tickers: list[str], period: str):
    """
    Descarga precios y calcula retornos esperados + covarianza con Ledoit-Wolf shrinkage.

    Retorna (prices, mu, S):
    - prices: DataFrame de precios de cierre, tickers como columnas
    - mu: pd.Series de retornos esperados anualizados (media histórica)
    - S: pd.DataFrame de covarianza anualizada (Ledoit-Wolf)
    """
    prices = yahoo_service.get_multiple_historical(tickers, period)
    prices = prices[tickers].dropna(how="any")

    mu = expected_returns.mean_historical_return(prices)
    S = CovarianceShrinkage(prices).ledoit_wolf()

    return prices, mu, S


def optimize_max_sharpe(
    tickers: list[str],
    period: str = "5y",
    risk_free_rate: float = RISK_FREE_RATE,
) -> dict:
    """
    Portafolio de Máximo Sharpe Ratio — Tangency Portfolio.

    Maximiza (μ_p − Rf) / σ_p sobre el simplex de pesos.
    Es el portafolio óptimo de la CML (Capital Market Line) cuando se puede
    invertir en el activo libre de riesgo.

    L2 regularization (γ=0.1) penaliza concentración: agrega γ * ‖w‖² al objetivo.
    Sin esto, la solución tiende a concentrarse en uno o dos activos.
    """
    prices, mu, S = _load_data(tickers, period)

    ef = EfficientFrontier(mu, S)
    ef.add_objective(objective_functions.L2_reg, gamma=0.1)
    ef.max_sharpe(risk_free_rate=risk_free_rate)
    clean_w = ef.clean_weights()
    ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate, verbose=False)

    return {
        "method": "max_sharpe",
        "weights": dict(clean_w),
        "expected_return": round(float(ret), 6),
        "expected_volatility": round(float(vol), 6),
        "sharpe": round(float(sharpe), 4),
    }


def optimize_min_variance(
    tickers: list[str],
    period: str = "5y",
    risk_free_rate: float = RISK_FREE_RATE,
) -> dict:
    """
    Portafolio de Mínima Varianza — punto más a la izquierda de la frontera.

    Minimiza σ_p = √(w^T Σ w) sin restricción de retorno objetivo.
    Solo depende de la covarianza — no de las estimaciones de retorno esperado.
    Más robusto que Max Sharpe porque los retornos históricos son mejores
    predictores de la volatilidad futura que del retorno futuro.
    """
    prices, mu, S = _load_data(tickers, period)

    ef = EfficientFrontier(mu, S)
    ef.add_objective(objective_functions.L2_reg, gamma=0.1)
    ef.min_volatility()
    clean_w = ef.clean_weights()
    ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate, verbose=False)

    return {
        "method": "min_variance",
        "weights": dict(clean_w),
        "expected_return": round(float(ret), 6),
        "expected_volatility": round(float(vol), 6),
        "sharpe": round(float(sharpe), 4),
    }


def optimize_risk_parity(
    tickers: list[str],
    period: str = "5y",
    risk_free_rate: float = RISK_FREE_RATE,
) -> dict:
    """
    Portafolio de Risk Parity — Equal Risk Contribution (ERC).

    Cada activo contribuye igual al riesgo total del portafolio:
    RC_i = w_i * (Σw)_i = σ_p / n  para todo i

    donde RC_i es la contribución marginal al riesgo del activo i.

    Popularizado por Ray Dalio (All Weather). No maximiza retorno:
    diversifica el riesgo. Más robusto a errores de estimación que Markowitz
    porque no depende de estimaciones de retorno esperado.
    """
    prices, mu, S = _load_data(tickers, period)
    S_arr = S.values
    mu_arr = mu.values
    n = len(tickers)

    def erc_objective(w: np.ndarray) -> float:
        port_var = float(w @ S_arr @ w)
        if port_var <= 1e-10:
            return 1e10
        rc = w * (S_arr @ w)          # contribuciones de riesgo no normalizadas
        target = port_var / n          # contribución objetivo igual para todos
        return float(np.sum((rc - target) ** 2))

    x0 = np.ones(n) / n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bounds = [(0.01, 0.99)] * n

    result = minimize(erc_objective, x0, method="SLSQP", bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-12, "maxiter": 500})
    w = result.x / result.x.sum()

    w_dict = {t: round(float(v), 6) for t, v in zip(tickers, w)}
    exp_ret = float(np.dot(w, mu_arr))
    exp_vol = float(np.sqrt(w @ S_arr @ w))
    sharpe = (exp_ret - risk_free_rate) / exp_vol if exp_vol > 0 else 0.0

    return {
        "method": "risk_parity",
        "weights": w_dict,
        "expected_return": round(exp_ret, 6),
        "expected_volatility": round(exp_vol, 6),
        "sharpe": round(sharpe, 4),
    }


def compute_efficient_frontier(
    tickers: list[str],
    period: str = "5y",
    risk_free_rate: float = RISK_FREE_RATE,
    points: int = 40,
) -> list[dict]:
    """
    Frontera eficiente de Markowitz — curva de portafolios óptimos.

    Para cada retorno objetivo entre min_vol y max_sharpe, encuentra el
    portafolio de menor varianza (efficient frontier superior).

    La frontera muestra el trade-off fundamental retorno/riesgo:
    no se puede mejorar el retorno sin aumentar el riesgo.
    Todo portafolio por debajo de la frontera es subóptimo (dominado).
    """
    prices, mu, S = _load_data(tickers, period)

    # Rango de retornos factibles (con margen para evitar infeasibility)
    min_ret = float(mu.min()) + 0.005
    max_ret = float(mu.max()) - 0.005
    if min_ret >= max_ret:
        return []

    target_returns = np.linspace(min_ret, max_ret, points)
    frontier: list[dict] = []

    for target in target_returns:
        try:
            ef = EfficientFrontier(mu, S, weight_bounds=(0, 1))
            ef.efficient_return(target_return=float(target))
            ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate, verbose=False)
            frontier.append({
                "return": round(float(ret), 6),
                "volatility": round(float(vol), 6),
                "sharpe": round(float(sharpe), 4),
            })
        except Exception as e:
            logger.warning(f"Skipping frontier point at target={target:.4f}: {e}")

    return frontier
