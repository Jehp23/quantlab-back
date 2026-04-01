"""
Simulaciones de Monte Carlo usando Geometric Brownian Motion (GBM).

El GBM es el proceso estocástico detrás del modelo de Black-Scholes:
    dS = S (μ dt + σ dW)

Solución exacta (Ito's lemma):
    S(t+1) = S(t) * exp((μ - σ²/2) + σ * Z)
    donde Z ~ N(0,1)

El término (μ - σ²/2) es el "drift corregido" — la corrección de Ito.
Sin ella, la media de las trayectorias sobreestima el retorno esperado:
E[S(T)] = S(0) * exp(μT)  (correcto)
pero exp(μT) ≠ mean(exp((μ - σ²/2)T + σ√T Z)) si no se aplica la corrección.

Limitaciones del GBM:
- No captura fat tails (colas más gruesas que la normal)
- No captura volatility clustering (GARCH)
- No captura mean reversion en tasas de interés
Para uso educativo es el modelo estándar y punto de partida.
"""

import numpy as np
import pandas as pd

from services import yahoo_service


def run_montecarlo(
    tickers: list[str],
    weights: list[float],
    horizon_days: int = 252,
    simulations: int = 1000,
    initial_value: float = 10_000.0,
    period: str = "2y",
    seed: int | None = None,
) -> dict:
    """
    N simulaciones GBM del portafolio ponderado por `weights`.

    Estimación de μ y σ diarios del portafolio a partir de datos históricos.
    Las simulaciones son independientes (no autocorrelacionadas) — el GBM
    asume retornos i.i.d., lo cual es una simplificación.

    Retorna percentiles 5/50/95 en cada paso temporal y distribución de
    valores finales para visualizar el abanico de posibles resultados.
    """
    # Descargar histórico del portafolio
    prices = yahoo_service.get_multiple_historical(tickers, period)
    prices = prices[tickers].dropna(how="any")

    log_r_ind = np.log(prices / prices.shift(1)).dropna()
    w = np.array(weights, dtype=float)

    # Retorno log diario del portafolio ponderado
    port_log_r = log_r_ind.values @ w
    mu_daily    = float(np.mean(port_log_r))   # drift diario
    sigma_daily = float(np.std(port_log_r))    # volatilidad diaria

    # GBM con corrección de Ito
    drift = mu_daily - 0.5 * sigma_daily ** 2

    # seed=None → aleatoriedad real por defecto; int → resultados reproducibles
    rng = np.random.default_rng(seed)

    # paths[i, t] = valor del portafolio en simulación i, día t
    paths = np.zeros((simulations, horizon_days + 1))
    paths[:, 0] = initial_value

    for t in range(1, horizon_days + 1):
        Z = rng.standard_normal(simulations)
        paths[:, t] = paths[:, t - 1] * np.exp(drift + sigma_daily * Z)

    # Percentiles en cada paso temporal (sobre las N simulaciones)
    p5  = np.percentile(paths,  5, axis=0).round(4).tolist()
    p50 = np.percentile(paths, 50, axis=0).round(4).tolist()
    p95 = np.percentile(paths, 95, axis=0).round(4).tolist()

    # Distribución de valores finales (ordenados para histograma)
    final_vals = np.sort(paths[:, -1]).round(4).tolist()

    return {
        "percentile_5":  p5,
        "percentile_50": p50,
        "percentile_95": p95,
        "final_values":  final_vals,
    }
