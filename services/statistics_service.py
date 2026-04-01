"""
Análisis estadístico completo de un activo.

Implementa los tests estadísticos del Laboratorio Cuantitativo:
- Performance: retorno acumulado, drawdown, ratios
- Riesgo: VaR histórico/paramétrico, CVaR (Expected Shortfall)
- Normalidad: test Jarque-Bera, skewness, kurtosis, Q-Q plot
- Volatilidad: rolling vol (21d, 63d, 252d), detección efecto ARCH
- Tests: T-test, test de rachas (independencia serial)
- Autocorrelación: ACF, test de Ljung-Box
- Heatmap: retornos mensuales calendario
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from services import yahoo_service, quant_service


def full_analysis(ticker: str, period: str = "2y") -> dict:
    """
    Análisis estadístico completo de un ticker.

    Descarga precios, calcula retornos log y ejecuta todos los módulos
    estadísticos en una sola llamada para que el frontend no necesite
    múltiples requests.
    """
    # ── Datos históricos ────────────────────────────────────────────────────
    prices_list = yahoo_service.get_historical(ticker, period)
    if not prices_list or len(prices_list) < 30:
        raise ValueError(f"Datos insuficientes para '{ticker}' en período '{period}'.")

    prices = pd.Series(
        [d["close"] for d in prices_list],
        index=pd.to_datetime([d["date"] for d in prices_list]),
        name=ticker,
    ).sort_index()

    # Retornos logarítmicos
    log_r = quant_service.calculate_log_returns(prices)
    r = log_r.values                                  # numpy 1-D array
    dates = log_r.index.strftime("%Y-%m-%d").tolist() # alineado con r
    n = len(r)

    # ── PERFORMANCE ─────────────────────────────────────────────────────────
    mu     = quant_service.annualized_return(log_r)
    sigma  = quant_service.annualized_volatility(log_r)
    mdd    = quant_service.max_drawdown(prices)
    sharpe = quant_service.sharpe_ratio(mu, sigma)
    sortino = quant_service.sortino_ratio(log_r, mu)
    calmar  = quant_service.calmar_ratio(mu, mdd)
    var_95  = quant_service.var_parametric(mu, sigma)

    # Retorno acumulado (base 0 = no ganancia)
    cum_sum  = np.cumsum(r)
    cum_pct  = ((np.exp(cum_sum) - 1) * 100).round(4).tolist()
    total_return = float((np.exp(cum_sum[-1]) - 1) * 100)

    # Drawdown series (caída desde pico)
    prices_aligned = prices.loc[log_r.index]
    rolling_peak   = prices_aligned.cummax()
    dd_pct         = ((prices_aligned - rolling_peak) / rolling_peak * 100).round(4).tolist()

    performance = {
        "annual_return": round(mu, 6),
        "annual_vol":    round(sigma, 6),
        "sharpe":        round(sharpe, 4),
        "sortino":       round(sortino, 4),
        "calmar":        round(calmar, 4),
        "max_drawdown":  round(mdd, 6),
        "var_95":        round(var_95, 6),
        "total_return":  round(total_return, 4),
        "cum_returns":   [{"date": d, "value": v} for d, v in zip(dates, cum_pct)],
        "drawdown_series": [{"date": d, "value": v} for d, v in zip(dates, dd_pct)],
    }

    # ── RIESGO: VaR / CVaR ──────────────────────────────────────────────────
    pct = lambda q: float(np.percentile(r, q))

    var_h95 = pct(5);  var_h99 = pct(1)
    var_p95 = float(np.mean(r) + sp_stats.norm.ppf(0.05) * np.std(r))
    var_p99 = float(np.mean(r) + sp_stats.norm.ppf(0.01) * np.std(r))

    tail95 = r[r <= var_h95];  cvar_95 = float(np.mean(tail95)) if len(tail95) else var_h95
    tail99 = r[r <= var_h99];  cvar_99 = float(np.mean(tail99)) if len(tail99) else var_h99

    # Histograma de retornos (30 bins, en %)
    r_pct = r * 100
    hist_counts, bin_edges = np.histogram(r_pct, bins=40)
    histogram = [
        {
            "x": round(float((bin_edges[i] + bin_edges[i + 1]) / 2), 4),
            "count": int(hist_counts[i]),
        }
        for i in range(len(hist_counts))
    ]

    risk = {
        "var_hist_95":  round(var_h95 * 100, 4),
        "var_hist_99":  round(var_h99 * 100, 4),
        "var_param_95": round(var_p95 * 100, 4),
        "var_param_99": round(var_p99 * 100, 4),
        "cvar_95":      round(cvar_95 * 100, 4),
        "cvar_99":      round(cvar_99 * 100, 4),
        "best_day":     round(float(np.max(r) * 100), 4),
        "worst_day":    round(float(np.min(r) * 100), 4),
        "mean_daily":   round(float(np.mean(r) * 100), 6),
        "std_daily":    round(float(np.std(r) * 100), 6),
        "histogram":    histogram,
    }

    # ── NORMALIDAD: Jarque-Bera, skewness, kurtosis, Q-Q plot ───────────────
    skewness   = float(sp_stats.skew(r))
    kurt_excess = float(sp_stats.kurtosis(r))  # exceso (ya resta 3)
    jb_stat, jb_pvalue = sp_stats.jarque_bera(r)

    # Q-Q plot: cuantiles teóricos vs observados (normalizados)
    r_std   = (r - np.mean(r)) / np.std(r)
    sorted_r_std = np.sort(r_std)
    probs   = (np.arange(1, n + 1) - 0.5) / n       # formula de Blom
    theor_q = sp_stats.norm.ppf(probs)
    step    = max(1, n // 200)                        # downsample para performance
    qq_plot = [
        {"theoretical": round(float(t), 4), "actual": round(float(a), 4)}
        for t, a in zip(theor_q[::step], sorted_r_std[::step])
    ]

    normality = {
        "skewness":         round(skewness, 4),
        "kurtosis":         round(kurt_excess, 4),
        "jb_stat":          round(float(jb_stat), 4),
        "jb_pvalue":        round(float(jb_pvalue), 6),
        "reject_normality": bool(jb_pvalue < 0.05),
        "qq_plot":          qq_plot,
    }

    # ── VOLATILIDAD: rolling vol 3 ventanas + ARCH detection ────────────────
    def _rolling_std(arr: np.ndarray, w: int) -> list[float]:
        """Std anualizada en ventana móvil."""
        return [
            float(np.std(arr[i - w : i]) * np.sqrt(252))
            for i in range(w, len(arr) + 1)
        ]

    rv21  = _rolling_std(r, 21);   dates21  = dates[20:]
    rv63  = _rolling_std(r, 63);   dates63  = dates[62:]
    rv252 = _rolling_std(r, 252) if n > 252 else []; dates252 = dates[251:] if n > 252 else []

    current_vol = rv21[-1] if rv21 else sigma
    mean_vol    = float(np.mean(rv21)) if rv21 else sigma
    vol_regime  = (
        "alto" if current_vol > mean_vol * 1.25
        else "bajo" if current_vol < mean_vol * 0.75
        else "medio"
    )

    # Efecto ARCH: autocorrelación de retornos al cuadrado
    r_sq = r ** 2
    if n > 2:
        arch_corr = float(np.corrcoef(r_sq[1:], r_sq[:-1])[0, 1])
        arch_detected = abs(arch_corr) > 2 / np.sqrt(n)
    else:
        arch_corr = 0.0; arch_detected = False

    volatility = {
        "rolling_21d":     [{"date": d, "vol": round(v, 6)} for d, v in zip(dates21, rv21)],
        "rolling_63d":     [{"date": d, "vol": round(v, 6)} for d, v in zip(dates63, rv63)],
        "rolling_252d":    [{"date": d, "vol": round(v, 6)} for d, v in zip(dates252, rv252)],
        "current_vol_21d": round(current_vol, 6),
        "mean_vol_21d":    round(mean_vol, 6),
        "vol_regime":      vol_regime,
        "arch_detected":   arch_detected,
        "arch_corr":       round(arch_corr, 4),
    }

    # ── T-TEST: μ = 0 ────────────────────────────────────────────────────────
    t_stat, t_pvalue = sp_stats.ttest_1samp(r, popmean=0)
    t_mean = float(np.mean(r));  t_std = float(np.std(r, ddof=1))
    t_se   = t_std / np.sqrt(n)
    t_crit = float(sp_stats.t.ppf(0.975, df=n - 1))
    margin = t_crit * t_se

    evidence = "Sin evidencia"
    evidence_level = "none"
    if float(t_pvalue) < 0.01:   evidence = "Evidencia fuerte";   evidence_level = "strong"
    elif float(t_pvalue) < 0.05: evidence = "Evidencia moderada"; evidence_level = "moderate"
    elif float(t_pvalue) < 0.10: evidence = "Evidencia débil";    evidence_level = "weak"

    # ── TEST DE RACHAS (independencia serial) ────────────────────────────────
    signs  = np.where(r >= 0, 1, -1)
    n_pos  = int(np.sum(signs > 0));  n_neg = int(np.sum(signs < 0))
    runs   = 1 + int(np.sum(signs[1:] != signs[:-1]))
    mean_runs = 2.0 * n_pos * n_neg / n + 1
    var_runs  = max(0.0, 2.0 * n_pos * n_neg * (2.0 * n_pos * n_neg - n) / (n * n * (n - 1)))
    std_runs  = float(np.sqrt(var_runs)) if var_runs > 0 else 1.0
    z_runs    = float((runs - mean_runs) / std_runs)
    p_runs    = float(2 * (1 - sp_stats.norm.cdf(abs(z_runs))))

    tests = {
        "ttest": {
            "n":            n,
            "mean_daily":   round(t_mean * 100, 6),
            "std_daily":    round(t_std * 100, 6),
            "t_stat":       round(float(t_stat), 4),
            "p_value":      round(float(t_pvalue), 6),
            "ci_low":       round((t_mean - margin) * 100, 6),
            "ci_high":      round((t_mean + margin) * 100, 6),
            "reject_h0":    bool(float(t_pvalue) < 0.05),
            "evidence":     evidence,
            "evidence_level": evidence_level,
        },
        "runs_test": {
            "runs":                runs,
            "n_pos":               n_pos,
            "n_neg":               n_neg,
            "mean_runs":           round(mean_runs, 2),
            "z_stat":              round(z_runs, 4),
            "p_value":             round(p_runs, 6),
            "reject_random_walk":  bool(p_runs < 0.05),
        },
    }

    # ── ACF + LJUNG-BOX ─────────────────────────────────────────────────────
    mean_r  = np.mean(r)
    denom   = np.sum((r - mean_r) ** 2)
    max_lag = 20
    ci_95   = 1.96 / np.sqrt(n)
    acf_vals = []

    for lag in range(1, max_lag + 1):
        num  = np.sum((r[lag:] - mean_r) * (r[:-lag] - mean_r))
        rho  = float(num / denom)
        acf_vals.append({
            "lag": lag,
            "acf": round(rho, 4),
            "significant": bool(abs(rho) > ci_95),
        })

    lj_q      = float(n * (n + 2) * sum(d["acf"] ** 2 / (n - d["lag"]) for d in acf_vals))
    lj_pvalue = float(1 - sp_stats.chi2.cdf(lj_q, df=max_lag))

    acf = {
        "values":              acf_vals,
        "ci_95":               round(ci_95, 4),
        "ljung_box_q":         round(lj_q, 4),
        "ljung_box_pvalue":    round(lj_pvalue, 6),
        "n_significant":       int(sum(1 for d in acf_vals if d["significant"])),
        "reject_independence": bool(lj_pvalue < 0.05),
    }

    # ── HEATMAP MENSUAL ──────────────────────────────────────────────────────
    log_r_series = pd.Series(r, index=pd.to_datetime(dates))
    monthly_groups = log_r_series.groupby([
        log_r_series.index.year,
        log_r_series.index.month,
    ]).sum()

    monthly_returns = [
        {
            "year":  str(year),
            "month": int(month),
            "ret":   round(float((np.exp(val) - 1) * 100), 2),
        }
        for (year, month), val in monthly_groups.items()
    ]

    return {
        "ticker":         ticker.upper(),
        "period":         period,
        "n_obs":          n,
        "performance":    performance,
        "risk":           risk,
        "normality":      normality,
        "volatility":     volatility,
        "tests":          tests,
        "acf":            acf,
        "monthly_returns": monthly_returns,
    }
