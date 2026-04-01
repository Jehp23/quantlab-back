"""
Métricas cuantitativas de riesgo y retorno para portafolios.

Todas las funciones operan sobre retornos logarítmicos y precios históricos.
Los docstrings explican la fórmula y la intuición financiera, no el código.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm


def calculate_log_returns(prices: pd.Series) -> pd.Series:
    """
    r_t = ln(P_t / P_{t-1})

    Los retornos logarítmicos son preferidos en finanzas cuantitativas porque:
    1. Son aditivos en el tiempo: r(0,T) = sum r(t,t+1)
    2. Distribución más simétrica que retornos simples (acotados en -100%)
    3. Son el logaritmo del factor de crecimiento — base del GBM (Black-Scholes)
    """
    return np.log(prices / prices.shift(1)).dropna()


def annualized_return(log_returns: pd.Series) -> float:
    """
    R_anual = (1 + R_total)^(252/n) - 1
    donde R_total = exp(sum(log_returns)) - 1

    Retorno geométrico anualizado: captura el efecto compuesto real.
    252 = días de trading anuales (NYSE/NASDAQ).
    No usar la media aritmética de retornos diarios — sobreestima el rendimiento
    real porque no captura la volatility drag: E[R_aritmético] > E[R_geométrico].
    """
    n = len(log_returns)
    if n == 0:
        return 0.0
    total_return = float(np.exp(log_returns.sum()) - 1)
    return float((1 + total_return) ** (252 / n) - 1)


def annualized_volatility(log_returns: pd.Series) -> float:
    """
    σ_anual = std(r_log) * sqrt(252)

    "Regla de la raíz del tiempo": si los retornos diarios son i.i.d.,
    la varianza escala linealmente con el tiempo → desviación escala con sqrt(T).
    Uso de retornos log porque su distribución se aproxima mejor a la normal.
    """
    if len(log_returns) < 2:
        return 0.0
    return float(log_returns.std() * np.sqrt(252))


def sharpe_ratio(annual_return: float, annual_vol: float, risk_free: float = 0.05) -> float:
    """
    Sharpe Ratio = (Rp - Rf) / σp

    Retorno excedente por unidad de riesgo total.
    Rf = tasa libre de riesgo (benchmark: BIL ≈ 5% anual, 2024).
    Interpretación: >1 aceptable, >2 bueno, >3 excelente (raro).
    Limitación: penaliza igualmente la volatilidad al alza y a la baja.
    """
    if annual_vol == 0:
        return 0.0
    return float((annual_return - risk_free) / annual_vol)


def sortino_ratio(log_returns: pd.Series, annual_return: float, risk_free: float = 0.05) -> float:
    """
    Sortino Ratio = (Rp - Rf) / σ_downside
    σ_downside = std(retornos negativos) * sqrt(252)

    Mejora sobre el Sharpe: solo penaliza la volatilidad a la baja (drawdowns).
    Un inversor racional no debería ser penalizado por retornos positivamente volátiles.
    Sortino > Sharpe sugiere que la volatilidad del portafolio es predominantemente alcista.
    """
    downside = log_returns[log_returns < 0]
    if len(downside) < 2:
        return 0.0
    sigma_downside = float(downside.std() * np.sqrt(252))
    if sigma_downside == 0:
        return 0.0
    return float((annual_return - risk_free) / sigma_downside)


def max_drawdown(prices: pd.Series) -> float:
    """
    MDD = min((P_t - peak_t) / peak_t)  donde peak_t = max(P_0 ... P_t)

    La mayor caída desde un pico hasta un valle en toda la historia.
    Métrica intuitiva de riesgo "de cola": ¿cuánto podrías haber perdido
    si comprabas en el peor momento posible?
    Retorna un número negativo (ej: -0.35 = caída del 35%).
    """
    rolling_peak = prices.cummax()
    drawdown = (prices - rolling_peak) / rolling_peak
    return float(drawdown.min())


def calmar_ratio(annual_return: float, max_dd: float) -> float:
    """
    Calmar Ratio = retorno anualizado / |max drawdown|

    Retorno obtenido por cada unidad de riesgo máximo experimentado.
    Útil para comparar estrategias con perfiles de drawdown muy distintos.
    Un fondo hedge con Calmar > 1 se considera bueno.
    """
    if max_dd == 0:
        return 0.0
    return float(annual_return / abs(max_dd))


def var_parametric(annual_return: float, annual_vol: float, confidence: float = 0.95) -> float:
    """
    VaR Paramétrico (diario) = -(μ_d + z * σ_d)
    donde z = norm.ppf(1 - confidence) ≈ -1.645 para 95%

    Supone retornos normalmente distribuidos (simplificación —
    los mercados tienen "fat tails" que este VaR subestima).
    Retorna el VaR diario como número positivo.
    Interpretación: "En el 95% de los días, la pérdida no superará este %."
    μ_d = annual_return / 252  (retorno diario esperado)
    σ_d = annual_vol / sqrt(252)  (volatilidad diaria)
    """
    mu_daily = annual_return / 252
    sigma_daily = annual_vol / np.sqrt(252)
    z = norm.ppf(1 - confidence)  # ≈ -1.645 para confidence=0.95
    return float(-(mu_daily + z * sigma_daily))


def rolling_volatility(prices: pd.Series, window: int = 21) -> list[dict]:
    """
    sigma_rolling[t] = std(log_r[t-window:t]) * sqrt(252)

    Captura cómo varía el riesgo a lo largo del tiempo — fundamental para
    detectar regímenes de alta/baja volatilidad. Ventana de 21d ≈ 1 mes de trading.
    La volatilidad no es constante (fenómeno de "volatility clustering"):
    períodos de alta vol tienden a seguir a períodos de alta vol (ARCH effects).
    """
    log_r = np.log(prices / prices.shift(1)).dropna()
    rolling_std = log_r.rolling(window=window).std().dropna() * np.sqrt(252)
    return [
        {"date": date.strftime("%Y-%m-%d"), "volatility": round(float(vol), 6)}
        for date, vol in rolling_std.items()
        if not np.isnan(vol)
    ]


def beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """
    β = Cov(r_asset, r_market) / Var(r_market)

    Mide la sensibilidad del activo al mercado (SPY como proxy del mercado).
    β = 1: se mueve igual que el mercado.
    β > 1: amplifica los movimientos del mercado (más riesgo sistemático).
    β < 1: amortigua los movimientos (defensivo).
    β < 0: se mueve en contra del mercado (cobertura natural).

    El riesgo sistemático (beta) no puede eliminarse con diversificación.
    El riesgo idiosincrático (alpha) sí.
    """
    cov_matrix = np.cov(asset_returns.values, market_returns.values)
    market_var = cov_matrix[1, 1]
    if market_var == 0:
        return 0.0
    return float(cov_matrix[0, 1] / market_var)


def alpha_jensen(
    asset_return: float,
    beta_val: float,
    market_return: float,
    risk_free: float = 0.05,
) -> float:
    """
    α = r_asset - [Rf + β × (r_market - Rf)]

    Alpha de Jensen: retorno excedente ajustado por riesgo sistemático.
    α > 0: el activo "le ganó" al mercado dado su nivel de riesgo.
    α < 0: el activo no compensó el riesgo asumido.
    α = 0: retorno exactamente en línea con lo esperado por CAPM.

    Interpretación: un gestor activo busca generar alpha positivo sostenido.
    La evidencia empírica sugiere que es extremadamente difícil a largo plazo.
    """
    return float(asset_return - (risk_free + beta_val * (market_return - risk_free)))


def correlation_matrix(prices_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """
    Correlación de Pearson entre los retornos log de los activos.

    Rango: [-1, 1]
    - 1.0: perfectamente correlacionados
    - 0.0: sin correlación lineal (diversificación efectiva)
    - -1.0: anticorrelacionados (cobertura perfecta)

    Principio de Markowitz: añadir activos con correlación < 1 reduce el riesgo
    del portafolio sin necesariamente reducir el retorno esperado (diversificación).
    """
    log_r = np.log(prices_df / prices_df.shift(1)).dropna()
    corr = log_r.corr()
    return {
        col: {idx: round(float(corr.loc[idx, col]), 4) for idx in corr.index}
        for col in corr.columns
    }


def portfolio_metrics(prices_df: pd.DataFrame, weights: list[float]) -> dict:
    """
    Métricas completas de riesgo/retorno para un portafolio multi-activo.

    Método: retorno del portafolio = suma ponderada de retornos log individuales.
    r_p = Σ w_i * r_i  (aproximación válida para retornos diarios pequeños)

    La serie de precios del portafolio normalizada (base = 1.0) se construye como:
    P_t = exp(Σ_{s=1}^{t} r_p_s)  — suma acumulada de log-retornos.
    """
    w = np.array(weights, dtype=float)

    # Retornos log individuales (una columna por ticker)
    log_r_ind = np.log(prices_df / prices_df.shift(1)).dropna()

    # Retorno log diario del portafolio (suma ponderada)
    port_log_r = pd.Series(
        log_r_ind.values @ w,
        index=log_r_ind.index,
        name="portfolio",
    )

    # Serie de precios del portafolio normalizada a 1.0 en el origen
    cumulative = np.exp(port_log_r.cumsum()).values
    port_prices = pd.Series(np.concatenate([[1.0], cumulative]))

    mu = annualized_return(port_log_r)
    sigma = annualized_volatility(port_log_r)
    mdd = max_drawdown(port_prices)

    return {
        "annual_return": round(mu, 6),
        "sigma": round(sigma, 6),
        "sharpe": round(sharpe_ratio(mu, sigma), 4),
        "sortino": round(sortino_ratio(port_log_r, mu), 4),
        "calmar": round(calmar_ratio(mu, mdd), 4),
        "max_drawdown": round(mdd, 6),
        "var_95": round(var_parametric(mu, sigma), 6),
        "correlation": correlation_matrix(prices_df),
    }
