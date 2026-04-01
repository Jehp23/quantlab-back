"""
Perfiles de riesgo del Robo Advisor.

Cada perfil define la allocation estratégica (asset allocation) por clase de activo
y los ETFs sugeridos con sus pesos objetivo. El score viene del cuestionario de onboarding.
"""

from typing import TypedDict


class AssetAllocation(TypedDict):
    renta_variable: float  # % en acciones/ETFs equity
    renta_fija: float      # % en bonos
    alternativo: float     # % en commodities, REITs, etc.


class RiskProfile(TypedDict):
    name: str
    score_min: int
    score_max: int
    description: str
    allocation: AssetAllocation
    etf_weights: dict[str, float]  # ticker -> peso (suma = 1.0)


RISK_PROFILES: dict[str, RiskProfile] = {
    "conservador": {
        "name": "Conservador",
        "score_min": 0,
        "score_max": 20,
        "description": "Preservación del capital. Prioriza estabilidad sobre crecimiento. "
                       "Alta exposición a renta fija y activos de bajo riesgo.",
        "allocation": {
            "renta_variable": 0.20,
            "renta_fija": 0.65,
            "alternativo": 0.15,
        },
        "etf_weights": {
            "SPY": 0.10,
            "EFA": 0.10,
            "AGG": 0.40,
            "LQD": 0.15,
            "TLT": 0.10,
            "GLD": 0.10,
            "BIL": 0.05,
        },
    },
    "moderado_conservador": {
        "name": "Moderado-Conservador",
        "score_min": 21,
        "score_max": 40,
        "description": "Balance inclinado hacia la preservación. Algo de crecimiento "
                       "con volatilidad controlada.",
        "allocation": {
            "renta_variable": 0.40,
            "renta_fija": 0.45,
            "alternativo": 0.15,
        },
        "etf_weights": {
            "SPY": 0.20,
            "QQQ": 0.05,
            "EFA": 0.10,
            "EEM": 0.05,
            "AGG": 0.25,
            "LQD": 0.10,
            "TLT": 0.10,
            "GLD": 0.10,
            "VNQ": 0.05,
        },
    },
    "moderado": {
        "name": "Moderado",
        "score_min": 41,
        "score_max": 60,
        "description": "Balance equitativo entre crecimiento y estabilidad. "
                       "Portafolio diversificado globalmente.",
        "allocation": {
            "renta_variable": 0.60,
            "renta_fija": 0.30,
            "alternativo": 0.10,
        },
        "etf_weights": {
            "SPY": 0.25,
            "QQQ": 0.10,
            "EFA": 0.15,
            "EEM": 0.10,
            "AGG": 0.20,
            "LQD": 0.10,
            "GLD": 0.05,
            "VNQ": 0.05,
        },
    },
    "moderado_agresivo": {
        "name": "Moderado-Agresivo",
        "score_min": 61,
        "score_max": 80,
        "description": "Orientado al crecimiento con tolerancia moderada a la volatilidad. "
                       "Alta exposición equity, algo de cobertura.",
        "allocation": {
            "renta_variable": 0.75,
            "renta_fija": 0.15,
            "alternativo": 0.10,
        },
        "etf_weights": {
            "SPY": 0.30,
            "QQQ": 0.15,
            "EFA": 0.15,
            "EEM": 0.15,
            "AGG": 0.10,
            "LQD": 0.05,
            "GLD": 0.05,
            "DJP": 0.05,
        },
    },
    "agresivo": {
        "name": "Agresivo",
        "score_min": 81,
        "score_max": 100,
        "description": "Máximo crecimiento a largo plazo. Alta volatilidad aceptada. "
                       "Dominado por renta variable global.",
        "allocation": {
            "renta_variable": 0.90,
            "renta_fija": 0.05,
            "alternativo": 0.05,
        },
        "etf_weights": {
            "SPY": 0.35,
            "QQQ": 0.20,
            "EFA": 0.15,
            "EEM": 0.20,
            "AGG": 0.05,
            "GLD": 0.05,
        },
    },
}


def get_profile_by_score(score: int) -> RiskProfile:
    """Retorna el perfil correspondiente al score del cuestionario (0-100)."""
    for profile in RISK_PROFILES.values():
        if profile["score_min"] <= score <= profile["score_max"]:
            return profile
    raise ValueError(f"Score {score} fuera de rango válido (0-100)")
