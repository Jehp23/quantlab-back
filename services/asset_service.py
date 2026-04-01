"""
Análisis individual de un activo (ticker).
Combina datos de yfinance con métricas de quant_service.

Dos operaciones principales:
- analyze_asset: descarga OHLC + quote + métricas completas vs benchmark
- compare_assets: normaliza múltiples activos a base 100 y compara métricas
"""

import pandas as pd

from services import yahoo_service, quant_service


def analyze_asset(
    ticker: str,
    period: str = "2y",
    benchmark: str = "SPY",
) -> dict:
    """
    Métricas completas de un activo individual vs benchmark.

    Descarga precios del activo y el benchmark juntos (una sola request HTTP),
    alinea en fechas comunes, y calcula:
    - Métricas absolutas: retorno, volatilidad, ratios, drawdown, VaR
    - Métricas relativas al benchmark: beta, alpha de Jensen
    - Rolling volatility (ventana 21d) para el gráfico temporal
    - Datos OHLC y quote para la cabecera de la página
    """
    # Descarga precios de cierre en una sola request
    tickers_dl = list(dict.fromkeys([ticker.upper(), benchmark.upper()]))
    prices_df = yahoo_service.get_multiple_historical(tickers_dl, period)

    # Datos OHLC y quote del activo
    ohlc = yahoo_service.get_historical(ticker, period)
    quote = yahoo_service.get_quote(ticker)

    # Series de precios alineadas en fechas comunes
    asset_prices = prices_df[ticker.upper()].dropna()
    market_prices = prices_df[benchmark.upper()].dropna()
    common_idx = asset_prices.index.intersection(market_prices.index)
    asset_prices = asset_prices.loc[common_idx]
    market_prices = market_prices.loc[common_idx]

    # Retornos log
    asset_log_r = quant_service.calculate_log_returns(asset_prices)
    market_log_r = quant_service.calculate_log_returns(market_prices)

    # Métricas
    mu = quant_service.annualized_return(asset_log_r)
    sigma = quant_service.annualized_volatility(asset_log_r)
    mdd = quant_service.max_drawdown(asset_prices)
    mu_market = quant_service.annualized_return(market_log_r)
    b = quant_service.beta(asset_log_r, market_log_r)
    alpha = quant_service.alpha_jensen(mu, b, mu_market)

    return {
        "ticker": ticker.upper(),
        "benchmark": benchmark.upper(),
        "period": period,
        "quote": quote,
        "ohlc": ohlc,
        "metrics": {
            "annual_return": round(mu, 6),
            "sigma": round(sigma, 6),
            "sharpe": round(quant_service.sharpe_ratio(mu, sigma), 4),
            "sortino": round(quant_service.sortino_ratio(asset_log_r, mu), 4),
            "calmar": round(quant_service.calmar_ratio(mu, mdd), 4),
            "max_drawdown": round(mdd, 6),
            "var_95": round(quant_service.var_parametric(mu, sigma), 6),
            "beta": round(b, 4),
            "alpha": round(alpha, 4),
        },
        "rolling_vol": quant_service.rolling_volatility(asset_prices),
    }


def compare_assets(tickers: list[str], period: str = "2y") -> dict:
    """
    Compara múltiples activos normalizados a base 100.

    Normalizar a base 100 permite comparar activos con precios absolutos muy
    distintos (ej: AMZN ~$180 vs BRK.A ~$600k) en el mismo eje Y.
    P_norm(t) = 100 * P(t) / P(0)

    Retorna:
    - series: lista de puntos [{date, values: {ticker: valor_normalizado}}]
    - metrics: métricas por ticker (sin beta/alpha — no hay benchmark común)
    """
    prices_df = yahoo_service.get_multiple_historical(tickers, period)
    if prices_df.empty:
        raise ValueError("No se encontraron precios históricos para los tickers solicitados.")

    # Solo tickers disponibles y con al menos 2 observaciones válidas
    available = [
        t for t in tickers
        if t in prices_df.columns and prices_df[t].dropna().shape[0] >= 2
    ]
    if len(available) < 2:
        raise ValueError("Se necesitan al menos 2 tickers con histórico suficiente para comparar.")

    prices_df = prices_df[available].dropna(how="any")
    if prices_df.empty:
        raise ValueError("No hay suficientes fechas en común entre los tickers seleccionados.")
    if len(prices_df) < 2:
        raise ValueError("No hay suficientes observaciones comunes para calcular la comparación.")

    # Normalizar a base 100
    normalized = (prices_df / prices_df.iloc[0]) * 100

    # Serie temporal para el gráfico
    series = []
    for date, row in normalized.iterrows():
        series.append({
            "date": date.strftime("%Y-%m-%d"),
            "values": {t: round(float(row[t]), 4) for t in available},
        })

    # Métricas individuales
    metrics = []
    for t in available:
        t_prices = prices_df[t]
        log_r = quant_service.calculate_log_returns(t_prices)
        mu = quant_service.annualized_return(log_r)
        sigma = quant_service.annualized_volatility(log_r)
        mdd = quant_service.max_drawdown(t_prices)
        metrics.append({
            "ticker": t,
            "metrics": {
                "annual_return": round(mu, 6),
                "sigma": round(sigma, 6),
                "sharpe": round(quant_service.sharpe_ratio(mu, sigma), 4),
                "sortino": round(quant_service.sortino_ratio(log_r, mu), 4),
                "calmar": round(quant_service.calmar_ratio(mu, mdd), 4),
                "max_drawdown": round(mdd, 6),
                "var_95": round(quant_service.var_parametric(mu, sigma), 6),
                "beta": None,
                "alpha": None,
            },
        })

    return {
        "tickers": available,
        "period": period,
        "series": series,
        "metrics": metrics,
    }
