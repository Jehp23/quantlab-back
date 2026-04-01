"""
Universo de ETFs del Robo Advisor.
Cubre las principales clases de activos para construcción de portafolios diversificados.
"""

ETF_UNIVERSE: dict[str, dict] = {
    "SPY": {
        "name": "SPDR S&P 500 ETF Trust",
        "description": "S&P 500 — 500 mayores empresas de USA",
        "asset_class": "renta_variable",
        "region": "usa",
        "sub_class": "large_cap",
    },
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "description": "Nasdaq 100 — Tech / growth USA",
        "asset_class": "renta_variable",
        "region": "usa",
        "sub_class": "tech_growth",
    },
    "EFA": {
        "name": "iShares MSCI EAFE ETF",
        "description": "MSCI EAFE — Europa, Australasia, Lejano Oriente (mercados desarrollados)",
        "asset_class": "renta_variable",
        "region": "internacional_desarrollado",
        "sub_class": "large_cap",
    },
    "EEM": {
        "name": "iShares MSCI Emerging Markets ETF",
        "description": "MSCI Emerging Markets — mercados emergentes",
        "asset_class": "renta_variable",
        "region": "emergentes",
        "sub_class": "large_cap",
    },
    "AGG": {
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "description": "US Aggregate Bond — bonos USA amplio espectro",
        "asset_class": "renta_fija",
        "region": "usa",
        "sub_class": "broad_bond",
    },
    "LQD": {
        "name": "iShares iBoxx $ Investment Grade Corporate Bond ETF",
        "description": "Bonos corporativos investment grade USA",
        "asset_class": "renta_fija",
        "region": "usa",
        "sub_class": "corporate",
    },
    "GLD": {
        "name": "SPDR Gold Shares",
        "description": "Oro físico — cobertura inflación y volatilidad",
        "asset_class": "alternativo",
        "region": "global",
        "sub_class": "commodities_oro",
    },
    "VNQ": {
        "name": "Vanguard Real Estate ETF",
        "description": "REITs USA — sector inmobiliario cotizado",
        "asset_class": "alternativo",
        "region": "usa",
        "sub_class": "real_estate",
    },
    "BIL": {
        "name": "SPDR Bloomberg 1-3 Month T-Bill ETF",
        "description": "T-Bills 1-3 meses — proxy de tasa libre de riesgo",
        "asset_class": "cash",
        "region": "usa",
        "sub_class": "t_bills",
    },
    "TLT": {
        "name": "iShares 20+ Year Treasury Bond ETF",
        "description": "Bonos del Tesoro USA largo plazo (20+ años)",
        "asset_class": "renta_fija",
        "region": "usa",
        "sub_class": "treasury_largo_plazo",
    },
    "DJP": {
        "name": "iPath Bloomberg Commodity Index Total Return ETN",
        "description": "Bloomberg Commodities — commodities diversificados",
        "asset_class": "alternativo",
        "region": "global",
        "sub_class": "commodities_broad",
    },
    "ACWI": {
        "name": "iShares MSCI ACWI ETF",
        "description": "All Country World Index — mercado global en un solo ETF",
        "asset_class": "renta_variable",
        "region": "global",
        "sub_class": "global_all_cap",
    },
}

# Lista de tickers para operaciones que requieren solo los símbolos
ETF_TICKERS: list[str] = list(ETF_UNIVERSE.keys())
