"""
Lógica de negocio para construcción y análisis de portafolios.

Orquesta yahoo_service (datos) + quant_service (cálculos).
Sin lógica HTTP — eso queda en el router.
"""

import numpy as np
import pandas as pd
from services import yahoo_service, quant_service
from constants import risk_profiles as rp_constants


def _format_goal(goal: str | None) -> str:
    mapping = {
        "capital_preservation": "preservar capital",
        "income": "generar ingresos estables",
        "balanced_growth": "crecimiento balanceado",
        "long_term_growth": "maximizar crecimiento de largo plazo",
        "wealth_building": "acumular patrimonio",
    }
    return mapping.get(goal or "", "invertir con un enfoque diversificado")


def _format_liquidity(liquidity_need: str | None) -> str:
    mapping = {
        "high": "alta necesidad de liquidez",
        "medium": "liquidez intermedia",
        "low": "baja necesidad de liquidez",
    }
    return mapping.get(liquidity_need or "", "liquidez no especificada")


def _format_experience(experience_level: str | None) -> str:
    mapping = {
        "none": "sin experiencia previa",
        "basic": "experiencia inicial",
        "intermediate": "experiencia intermedia",
        "advanced": "experiencia avanzada",
    }
    return mapping.get(experience_level or "", "experiencia no especificada")


def build_portfolio(
    risk_score: int,
    investment_goal: str | None = None,
    horizon_years: int | None = None,
    liquidity_need: str | None = None,
    experience_level: str | None = None,
    monthly_contribution: float | None = None,
    emergency_buffer_months: int | None = None,
) -> dict:
    """
    Construye el portafolio sugerido para un perfil de riesgo dado su score.

    El score (0-100) viene del cuestionario de onboarding. Mapea directamente
    al perfil definido en constants/risk_profiles.py con su allocation estratégica
    y los ETFs con pesos objetivo.
    """
    profile = rp_constants.get_profile_by_score(risk_score)
    goal_text = _format_goal(investment_goal)
    liquidity_text = _format_liquidity(liquidity_need)
    experience_text = _format_experience(experience_level)
    horizon_text = (
        f"horizonte de {horizon_years} años"
        if horizon_years is not None
        else "horizonte no especificado"
    )
    contribution_text = (
        f"aportes mensuales estimados de ${monthly_contribution:,.0f}"
        if monthly_contribution and monthly_contribution > 0
        else "sin aportes periódicos declarados"
    )
    emergency_text = (
        f"colchón de emergencia de {emergency_buffer_months} meses"
        if emergency_buffer_months is not None
        else "colchón de emergencia no informado"
    )

    suitability = [
        f"Tu score de riesgo ({risk_score}/100) encaja con un perfil {profile['name'].lower()}.",
        f"La propuesta prioriza {goal_text} con {horizon_text}.",
        f"Se asume {liquidity_text} y {experience_text}.",
    ]

    rationale = [
        f"La asignación estratégica combina {int(profile['allocation']['renta_variable'] * 100)}% de renta variable, "
        f"{int(profile['allocation']['renta_fija'] * 100)}% de renta fija y "
        f"{int(profile['allocation']['alternativo'] * 100)}% de activos alternativos.",
        "Los ETFs elegidos buscan diversificación global por clase de activo, región y estilo.",
        f"El plan considera {contribution_text} y {emergency_text}.",
    ]

    next_steps = [
        "Revisar si el horizonte y la necesidad de liquidez siguen siendo correctos.",
        "Definir un monto inicial y un esquema de aportes automáticos.",
        "Monitorear desvíos de pesos y rebalancear cuando una clase se aleje demasiado del objetivo.",
    ]

    return {
        "profile_name": profile["name"],
        "description": profile["description"],
        "allocation": dict(profile["allocation"]),
        "etf_weights": dict(profile["etf_weights"]),
        "investor_context": {
            "risk_score": risk_score,
            "investment_goal": investment_goal,
            "horizon_years": horizon_years,
            "liquidity_need": liquidity_need,
            "experience_level": experience_level,
            "monthly_contribution": monthly_contribution,
            "emergency_buffer_months": emergency_buffer_months,
        },
        "suitability": suitability,
        "rationale": rationale,
        "rebalance_policy": "Rebalanceo trimestral o cuando una clase de activo se desvíe más de 5 puntos porcentuales del objetivo.",
        "next_steps": next_steps,
    }


def analyze_portfolio(tickers: list[str], weights: list[float], period: str) -> dict:
    """
    Analiza un portafolio calculando sus métricas históricas de riesgo/retorno.

    Pasos:
    1. Descarga precios históricos de todos los tickers via yfinance (una sola request)
    2. Alinea las series temporales (dropna elimina fechas sin datos en algún ticker)
    3. Delega el cálculo de métricas a quant_service.portfolio_metrics()

    Nota: el período de datos determina el horizonte de análisis. Para 2y se tienen
    ~500 días de trading — suficiente para métricas estables pero insuficiente para
    capturar ciclos económicos completos.
    """
    prices_df = yahoo_service.get_multiple_historical(tickers, period)

    # Verificar que todos los tickers están disponibles
    missing = [t for t in tickers if t not in prices_df.columns]
    if missing:
        raise ValueError(f"Tickers no encontrados: {missing}")

    # Reordenar columnas para que coincidan con el orden de weights
    prices_df = prices_df[tickers]

    # Alinear series: solo fechas donde TODOS los tickers tienen datos
    prices_df = prices_df.dropna(how="any")

    if len(prices_df) < 30:
        raise ValueError(
            f"Datos insuficientes ({len(prices_df)} días). "
            "Verificar que los tickers existan y el período sea válido."
        )

    metrics = quant_service.portfolio_metrics(prices_df, weights)

    return {
        "tickers": tickers,
        "weights": weights,
        "period": period,
        "metrics": metrics,
    }


def get_equity_curve(tickers: list[str], weights: list[float], period: str) -> dict:
    """
    Construye la equity curve del portafolio vs SPY como benchmark.

    Optimización: descarga portafolio + SPY en una sola request a yfinance.
    Ambas curvas parten de base 100 (equivale a $100 invertidos el primer día),
    lo que permite comparar visualmente el rendimiento relativo de forma inmediata.

    Equity curve = 100 * exp(cumsum(log_returns_diarios))
    Esta formulación asume reinversión continua de dividendos (precio ajustado).
    """
    # Descargar portafolio + benchmark en una sola request
    benchmark = "SPY"
    all_tickers = list(dict.fromkeys(tickers + [benchmark]))  # deduplica preservando orden
    prices_df = yahoo_service.get_multiple_historical(all_tickers, period)

    missing = [t for t in tickers if t not in prices_df.columns]
    if missing:
        raise ValueError(f"Tickers no encontrados: {missing}")
    if benchmark not in prices_df.columns:
        raise ValueError("No se pudo obtener datos de SPY (benchmark)")

    # Log returns del portafolio (solo columnas de portfolio tickers)
    port_prices = prices_df[tickers].dropna(how="any")
    log_r_mat = np.log(port_prices / port_prices.shift(1)).dropna()
    w = np.array(weights, dtype=float)
    port_log_r = pd.Series(log_r_mat.values @ w, index=log_r_mat.index)

    # Log returns del benchmark
    spy_prices = prices_df[benchmark].dropna()
    spy_log_r = np.log(spy_prices / spy_prices.shift(1)).dropna()

    # Alinear en fechas donde ambos tienen datos (tras calcular log returns)
    common_idx = port_log_r.index.intersection(spy_log_r.index)
    if len(common_idx) < 2:
        raise ValueError("Datos insuficientes para construir la equity curve")

    port_log_r = port_log_r.loc[common_idx]
    spy_log_r = spy_log_r.loc[common_idx]

    # Equity curves: base 100
    port_equity = 100.0 * np.exp(port_log_r.cumsum())
    spy_equity = 100.0 * np.exp(spy_log_r.cumsum())

    data = [
        {
            "date": date.strftime("%Y-%m-%d"),
            "portfolio_value": round(float(port_equity[date]), 2),
            "benchmark_value": round(float(spy_equity[date]), 2),
        }
        for date in port_equity.index
    ]

    return {
        "tickers": tickers,
        "weights": weights,
        "period": period,
        "initial_value": 100.0,
        "data": data,
    }
