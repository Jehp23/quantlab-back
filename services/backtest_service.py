"""
Motor de backtesting con rebalanceo periódico.

Simula la performance histórica de un portafolio con rebalanceo.
Sin rebalanceo, los pesos derivan con el tiempo (momentum implícito).
Con rebalanceo, se fuerzan los pesos objetivo en cada fecha — esto vende
los activos ganadores y compra los perdedores (contrarian implícito).

El benchmark es SPY (S&P 500 total return con dividendos reinvertidos).
"""

import numpy as np
import pandas as pd
import yfinance as yf

from services import quant_service


def run_backtest(
    tickers: list[str],
    weights: list[float],
    start: str,
    end: str,
    rebalance_freq: str = "monthly",
) -> dict:
    """
    Simula el portafolio día a día con rebalanceo periódico.

    Algoritmo:
    1. Convertir pesos a número de acciones al precio inicial.
    2. Cada día: valor = sum(shares_i * price_i).
    3. En fechas de rebalanceo: recalcular shares para volver a los pesos objetivo.

    Rebalanceo = N días de trading:
    - monthly  → 21 días  (≈ 1 mes de trading)
    - quarterly → 63 días  (≈ 3 meses)
    - annually  → 252 días (≈ 1 año)
    """
    # Descargar precios incluyendo SPY como benchmark
    all_tickers = list(dict.fromkeys(tickers + ["SPY"]))
    raw = yf.download(all_tickers, start=start, end=end,
                      interval="1d", auto_adjust=True, progress=False)

    # yfinance 1.x siempre retorna MultiIndex (Price, Ticker); data["Close"] da tickers como columnas.
    prices_df = raw["Close"].copy()
    if isinstance(prices_df, pd.Series):
        prices_df = prices_df.to_frame(name=all_tickers[0])

    prices_df = prices_df.ffill().dropna(how="any")
    if prices_df.empty or len(prices_df) < 2:
        raise ValueError("Datos insuficientes para el período especificado.")

    # Verificar que todos los tickers del portafolio estén disponibles
    missing = [t for t in tickers if t not in prices_df.columns]
    if missing:
        raise ValueError(f"No se encontraron datos para los tickers: {missing}. Verificá que existan en yfinance.")

    asset_prices = prices_df[tickers].values        # shape: (n_days, n_assets)
    spy_prices   = prices_df["SPY"].values           # shape: (n_days,)
    n_days       = len(prices_df)
    dates        = prices_df.index

    w = np.array(weights, dtype=float)
    initial_value = 10_000.0

    # Intervalo de rebalanceo en días de trading
    rebal_map = {"monthly": 21, "quarterly": 63, "annually": 252}
    rebal_interval = rebal_map.get(rebalance_freq, 21)

    # Simular portafolio y benchmark
    portfolio_values = np.zeros(n_days)
    benchmark_values = np.zeros(n_days)
    portfolio_values[0] = initial_value
    benchmark_values[0] = initial_value

    # Posiciones iniciales (cantidad de acciones)
    positions  = w * initial_value / asset_prices[0]
    spy_shares = initial_value / spy_prices[0]

    for i in range(1, n_days):
        val = float(np.dot(positions, asset_prices[i]))
        portfolio_values[i] = val
        benchmark_values[i] = float(spy_shares * spy_prices[i])

        # Rebalanceo: restaurar pesos objetivo
        if i % rebal_interval == 0:
            positions = w * val / asset_prices[i]

    # Serie de precios para métricas
    port_series = pd.Series(portfolio_values, index=dates)
    port_log_r  = quant_service.calculate_log_returns(port_series)
    mu    = quant_service.annualized_return(port_log_r)
    sigma = quant_service.annualized_volatility(port_log_r)
    mdd   = quant_service.max_drawdown(port_series)

    data_points = [
        {
            "date":            dates[i].strftime("%Y-%m-%d"),
            "value":           round(float(portfolio_values[i]), 4),
            "benchmark_value": round(float(benchmark_values[i]), 4),
        }
        for i in range(n_days)
    ]

    # Correlación entre activos del portafolio durante el período
    asset_df = pd.DataFrame(asset_prices, index=dates, columns=tickers)
    correlation = quant_service.correlation_matrix(asset_df)

    metrics = {
        "annual_return": round(mu, 6),
        "sigma":         round(sigma, 6),
        "sharpe":        round(quant_service.sharpe_ratio(mu, sigma), 4),
        "sortino":       round(quant_service.sortino_ratio(port_log_r, mu), 4),
        "calmar":        round(quant_service.calmar_ratio(mu, mdd), 4),
        "max_drawdown":  round(mdd, 6),
        "var_95":        round(quant_service.var_parametric(mu, sigma), 6),
        "correlation":   correlation,
    }

    return {"data": data_points, "metrics": metrics}
