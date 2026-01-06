"""
Stock lists for global markets.
Contains ticker symbols for major indices worldwide.
"""

# S&P 500 - Full list (all 500 stocks)
SP500 = [
    # Top 100
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "JPM", "V", "PG", "XOM", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
    "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO", "ABT",
    "DHR", "VZ", "ADBE", "CRM", "CMCSA", "NKE", "INTC", "WFC", "TXN", "PM",
    "NEE", "UPS", "RTX", "HON", "QCOM", "BMY", "LOW", "MS", "ORCL", "UNP",
    "AMGN", "IBM", "SPGI", "GE", "CAT", "BA", "SBUX", "AMD", "GS", "BLK",
    "INTU", "MDLZ", "DE", "GILD", "ADP", "ISRG", "ADI", "TJX", "CVS", "SYK",
    "BKNG", "VRTX", "MMC", "PLD", "REGN", "CI", "LMT", "SCHW", "NOW", "ZTS",
    "MO", "BDX", "TMUS", "CB", "EOG", "SO", "CME", "DUK", "PNC", "CL",
    "EQIX", "ITW", "SLB", "AON", "NOC", "APD", "FISV", "CSX", "WM", "ICE",
    # 101-200
    "NSC", "EMR", "MCK", "FCX", "PXD", "EL", "GM", "OXY", "CCI", "GD",
    "SHW", "HUM", "PSX", "MPC", "MAR", "ORLY", "EW", "MCO", "ADM", "AEP",
    "MET", "TRV", "COP", "FDX", "DOW", "F", "KMB", "AIG", "AFL", "D",
    "DLR", "A", "NEM", "PSA", "PRU", "KHC", "O", "JCI", "TGT", "CTVA",
    "SPG", "PEG", "BIIB", "MNST", "HAL", "PAYX", "WMB", "HSY", "GIS", "IQV",
    "ALL", "YUM", "TEL", "DD", "IDXX", "BK", "WELL", "STZ", "CTAS", "MSCI",
    "DVN", "AME", "ED", "WEC", "PPG", "ROP", "PCAR", "DLTR", "CMG", "HLT",
    "APTV", "MTD", "RSG", "EA", "FAST", "KEYS", "AZO", "OTIS", "VRSK", "AWK",
    "GWW", "ALB", "ILMN", "ROK", "CTSH", "EXC", "ES", "LHX", "ODFL", "XEL",
    "CBRE", "CHD", "EBAY", "HPQ", "FTV", "VRSN", "ANSS", "MLM", "VMC", "DFS",
    # 201-300
    "WST", "DOV", "FANG", "URI", "PWR", "DHI", "LEN", "PHM", "NVR", "TSCO",
    "EFX", "STT", "SYF", "CFG", "HIG", "FITB", "KEY", "MTB", "RF", "HBAN",
    "NTRS", "CMA", "ZION", "SIVB", "SBNY", "CINF", "GL", "L", "WRB", "AIZ",
    "TFC", "USB", "PFG", "LNC", "UNM", "TROW", "AMP", "BEN", "IVZ", "NTAP",
    "JNPR", "AKAM", "FFIV", "WDC", "HPE", "LDOS", "IT", "FIS", "GPN", "FLT",
    "BR", "PAYC", "CPRT", "CHRW", "EXPD", "JBHT", "XPO", "LSTR", "KNX", "SAIA",
    "WAB", "GPC", "LKQ", "AAP", "ULTA", "BBY", "DG", "COST", "KR", "WBA",
    "SYY", "SYSCO", "MKC", "HRL", "K", "CPB", "CAG", "GIS", "SJM", "CLX",
    "CHD", "CL", "PG", "KMB", "NWL", "RVTY", "HAS", "MAT", "POOL", "PENN",
    "WYNN", "LVS", "MGM", "CZR", "DKNG", "NKE", "VFC", "PVH", "TPR", "RL",
    # 301-400
    "HBI", "UAA", "LEVI", "GPS", "ANF", "AEO", "URBN", "EXPR", "FIVE", "OLLI",
    "TJX", "ROST", "BURL", "RH", "WSM", "WMG", "PARA", "DIS", "NFLX", "WBD",
    "FOXA", "FOX", "VIAC", "DISCA", "DISCB", "DISCK", "CMCSA", "CHTR", "T", "VZ",
    "TMUS", "S", "LUMN", "FYBR", "FTR", "DISH", "SATS", "IRDM", "GILD", "REGN",
    "VRTX", "BIIB", "ALXN", "BMRN", "INCY", "SGEN", "SRPT", "BLUE", "RARE", "EXEL",
    "UTHR", "TECH", "BIO", "A", "TMO", "DHR", "PKI", "MTD", "WAT", "BRKR",
    "TER", "LRCX", "KLAC", "AMAT", "ASML", "NVDA", "AMD", "INTC", "TXN", "QCOM",
    "AVGO", "MRVL", "SWKS", "QRVO", "NXPI", "ON", "ADI", "MCHP", "XLNX", "MPWR",
    "ENPH", "SEDG", "FSLR", "RUN", "NOVA", "JKS", "CSIQ", "DQ", "MAXN", "ARRY",
    "NEE", "AES", "AEP", "D", "DUK", "SO", "EXC", "PEG", "ED", "XEL",
    # 401-500
    "WEC", "ES", "ETR", "CMS", "DTE", "AEE", "LNT", "EVRG", "PNW", "PPL",
    "NI", "OGE", "MGEE", "NWE", "AVA", "POR", "SRE", "PCG", "EIX", "AWK",
    "WTR", "AWR", "SJW", "CWT", "YORW", "ARTNA", "MSEX", "WTRG", "AMT", "CCI",
    "SBAC", "UDR", "ESS", "AVB", "EQR", "MAA", "CPT", "AIV", "INVH", "AMH",
    "SUI", "ELS", "LSI", "ACC", "EDR", "IRT", "NNN", "O", "WPC", "STOR",
    "ADC", "EPRT", "FCPT", "NTST", "GTY", "PINE", "GOOD", "LTC", "OHI", "SBRA",
    "HR", "PEAK", "DOC", "VTR", "WELL", "HTA", "MPW", "GMRE", "CHCT", "GEO",
    "CXW", "BXP", "SLG", "VNO", "KRC", "DEI", "ARE", "BDN", "ESRT", "PGRE",
    "PDM", "CLI", "OFC", "HIW", "CUZ", "CDP", "EGP", "FR", "STAG", "TRNO",
    "IIPR", "COLD", "LAND", "PLYM", "ILPT", "PEB", "HST", "RHP", "PK", "XHR"
]

# NASDAQ 100 - Tech-heavy
NASDAQ100 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP",
    "COST", "ADBE", "CSCO", "CMCSA", "NFLX", "AMD", "INTC", "QCOM", "TXN", "INTU",
    "AMGN", "HON", "AMAT", "BKNG", "ISRG", "SBUX", "ADI", "MDLZ", "GILD", "ADP",
    "REGN", "VRTX", "PYPL", "LRCX", "MU", "SNPS", "KLAC", "PANW", "CDNS", "MELI",
    "ORLY", "FTNT", "ASML", "MAR", "CTAS", "ABNB", "CSX", "MNST", "NXPI", "PCAR",
    "WDAY", "KDP", "MRVL", "AEP", "ROST", "DXCM", "ADSK", "AZN", "LULU", "KHC",
    "EXC", "PAYX", "CHTR", "CPRT", "CRWD", "IDXX", "CTSH", "MCHP", "ODFL", "FAST",
    "VRSK", "EA", "XEL", "CSGP", "GEHC", "TEAM", "DDOG", "BIIB", "FANG", "DLTR",
    "WBD", "ZS", "ILMN", "ANSS", "EBAY", "WBA", "ALGN", "SIRI", "ENPH", "JD",
    "LCID", "ZM", "RIVN", "DOCU", "OKTA", "MRNA", "SGEN", "SPLK", "SWKS", "MTCH"
]

# DAX 40 - Germany (Frankfurt)
DAX40 = [
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "CON.DE",
    "1COV.DE", "DTG.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE", "FRE.DE",
    "HEI.DE", "HEN3.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE", "PAH3.DE",
    "PUM.DE", "RWE.DE", "SAP.DE", "SRT3.DE", "SIE.DE", "ENR.DE", "SHL.DE", "SY1.DE",
    "VOW3.DE", "VNA.DE", "ZAL.DE", "HNR1.DE", "QGEN.DE", "RHM.DE", "BNR.DE", "HAG.DE"
]

# CAC 40 - France (Paris)
CAC40 = [
    "AI.PA", "AIR.PA", "ALO.PA", "MT.PA", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA",
    "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA", "ERF.PA", "RMS.PA",
    "KER.PA", "LR.PA", "OR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA",
    "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "STLA.PA", "STMPA.PA",
    "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
]

# FTSE 100 - UK (London)
FTSE100 = [
    "AAL.L", "ABF.L", "ADM.L", "AHT.L", "ANTO.L", "AV.L", "AZN.L", "BA.L", "BARC.L",
    "BATS.L", "BDEV.L", "BKG.L", "BLND.L", "BP.L", "BRBY.L", "BT-A.L", "CCH.L",
    "CNA.L", "CPG.L", "CRDA.L", "CRH.L", "DCC.L", "DGE.L", "DPLM.L", "EDV.L",
    "ENT.L", "EXPN.L", "EZJ.L", "FCIT.L", "FRAS.L", "FRES.L", "GLEN.L", "GSK.L",
    "HIK.L", "HLMA.L", "HSBA.L", "ICAG.L", "IHG.L", "III.L", "IMB.L", "INF.L",
    "ITRK.L", "JD.L", "KGF.L", "LAND.L", "LGEN.L", "LLOY.L", "LSEG.L", "MKS.L",
    "MNDI.L", "MNG.L", "MRO.L", "NG.L", "NWG.L", "NXT.L", "OCDO.L", "PHNX.L",
    "PRU.L", "PSH.L", "PSN.L", "PSON.L", "REL.L", "RIO.L", "RKT.L", "RMV.L",
    "RR.L", "RS1.L", "RTO.L", "SBRY.L", "SDR.L", "SGE.L", "SGRO.L", "SHEL.L",
    "SKG.L", "SMDS.L", "SMIN.L", "SMT.L", "SN.L", "SPX.L", "SSE.L", "STAN.L",
    "SVT.L", "TSCO.L", "TW.L", "ULVR.L", "UU.L", "VOD.L", "WPP.L", "WTB.L"
]

# FTSE MIB - Italy (Milan)
FTSEMIB = [
    "A2A.MI", "AMP.MI", "ATL.MI", "AZM.MI", "BGN.MI", "BMED.MI", "BPER.MI", "BPE.MI",
    "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "FBK.MI", "G.MI", "HER.MI",
    "IGD.MI", "INW.MI", "IP.MI", "ISP.MI", "IVG.MI", "LDO.MI", "MB.MI", "MONC.MI",
    "NEXI.MI", "PIRC.MI", "PRY.MI", "PST.MI", "REC.MI", "RACE.MI", "SPM.MI", "SRG.MI",
    "STM.MI", "TEN.MI", "TIT.MI", "TRN.MI", "UCG.MI", "UNI.MI", "US.MI", "WBD.MI"
]

# Nikkei 225 - Japan (Tokyo) - Top 50
NIKKEI_TOP = [
    "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "6902.T", "7267.T",
    "4063.T", "8035.T", "6501.T", "4502.T", "7974.T", "6098.T", "8058.T", "9433.T",
    "7751.T", "6367.T", "4503.T", "8316.T", "7741.T", "6954.T", "8411.T", "6981.T",
    "9022.T", "8801.T", "2914.T", "3382.T", "4568.T", "7269.T", "6857.T", "4661.T",
    "9020.T", "5108.T", "6503.T", "8031.T", "6702.T", "7201.T", "4519.T", "6752.T",
    "8766.T", "6594.T", "4901.T", "9021.T", "7011.T", "6762.T", "8267.T", "2802.T",
    "8830.T", "6701.T"
]

# Hang Seng Index - Hong Kong - Top 50
HANGSENG = [
    "0700.HK", "9988.HK", "0005.HK", "0939.HK", "1299.HK", "0941.HK", "2318.HK",
    "0388.HK", "0883.HK", "0027.HK", "1398.HK", "3988.HK", "0011.HK", "0016.HK",
    "0001.HK", "0002.HK", "0003.HK", "0006.HK", "0012.HK", "0017.HK", "0019.HK",
    "0066.HK", "0083.HK", "0101.HK", "0175.HK", "0241.HK", "0267.HK", "0288.HK",
    "0386.HK", "0669.HK", "0688.HK", "0762.HK", "0823.HK", "0857.HK", "0868.HK",
    "0881.HK", "0960.HK", "0968.HK", "0992.HK", "1038.HK", "1044.HK", "1093.HK",
    "1109.HK", "1113.HK", "1177.HK", "1211.HK", "1288.HK", "1810.HK", "1876.HK",
    "1928.HK"
]

# All markets combined
MARKETS = {
    "sp500": {
        "name": "S&P 500 (USA)",
        "tickers": SP500,
        "currency": "USD"
    },
    "nasdaq": {
        "name": "NASDAQ 100 (USA)",
        "tickers": NASDAQ100,
        "currency": "USD"
    },
    "dax": {
        "name": "DAX 40 (Germany)",
        "tickers": DAX40,
        "currency": "EUR"
    },
    "cac": {
        "name": "CAC 40 (France)",
        "tickers": CAC40,
        "currency": "EUR"
    },
    "ftse": {
        "name": "FTSE 100 (UK)",
        "tickers": FTSE100,
        "currency": "GBP"
    },
    "mib": {
        "name": "FTSE MIB (Italy)",
        "tickers": FTSEMIB,
        "currency": "EUR"
    },
    "nikkei": {
        "name": "Nikkei 225 (Japan)",
        "tickers": NIKKEI_TOP,
        "currency": "JPY"
    },
    "hangseng": {
        "name": "Hang Seng (Hong Kong)",
        "tickers": HANGSENG,
        "currency": "HKD"
    }
}

def get_all_tickers():
    """Returns all tickers from all markets."""
    all_tickers = []
    for market in MARKETS.values():
        all_tickers.extend(market["tickers"])
    return list(set(all_tickers))  # Remove duplicates

def get_tickers_by_markets(market_keys):
    """Returns tickers for specified markets."""
    tickers = []
    for key in market_keys:
        if key in MARKETS:
            tickers.extend(MARKETS[key]["tickers"])
    return list(set(tickers))  # Remove duplicates
