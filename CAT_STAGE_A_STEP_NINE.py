from pathlib import Path
import ast
import re
from collections import Counter

FILES=["OMNICIPHERIST.py","universal_crt_v4.py"]

print("CAT STAGE A — STEP NINE")
print("AUTHORITATIVE MARKET-DATA + INSTRUMENT SPECIFICATION AUDIT")
print("MODE: READ ONLY")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

def read_file(name):
    p=Path(name)
    if not p.exists():
        print(f"\nERROR: {name} NOT FOUND")
        return ""
    return p.read_text(encoding="utf-8",errors="replace")

def parse(name,src):
    try:
        return ast.parse(src),None
    except Exception as e:
        return None,e

def functions(tree):
    if tree is None:
        return []
    return [
        (n.name,n.lineno)
        for n in ast.walk(tree)
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
    ]

def urls(src):
    return sorted(set(re.findall(r'https?://[^"\']+',src)))

def imports(src):
    try:
        tree=ast.parse(src)
    except Exception:
        return []
    result=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            result.extend(a.name for a in n.names)
        elif isinstance(n,ast.ImportFrom):
            result.append(n.module or "")
    return result

sources={name:read_file(name) for name in FILES}
trees={name:parse(name,sources[name]) for name in FILES}

print("\n"+"="*110)
print("SOURCE INVENTORY")
print("="*110)

for name in FILES:
    src=sources[name]
    tree,err=trees[name]
    print(f"\n{name}")
    print("LINES:",len(src.splitlines()))
    print("AST:", "VALID" if err is None else f"INVALID: {err}")
    print("FUNCTIONS:",len(functions(tree)))
    print("IMPORTS:",len(imports(src)))

print("\n"+"="*110)
print("OMNICIPHERIST MARKET-DATA PATH")
print("="*110)

src=sources["OMNICIPHERIST.py"]

patterns=[
    "fetch_live_price",
    "biquote.io",
    "requests.get",
    "FOREX_API_URL",
    "FOREX_API_KEY",
    "COINGECKO_API_URL",
    "simple/price",
    "bid",
    "ask",
    "mid",
    "stale",
    "current_price",
    "timeframe",
    "trading_pair",
]

for p in patterns:
    lines=[
        (i+1,line.strip())
        for i,line in enumerate(src.splitlines())
        if p.lower() in line.lower()
    ]
    print(f"\n[{p}] {len(lines)} match(es)")
    for no,line in lines[:20]:
        print(f"{no}: {line}")

print("\nOMNICIPHERIST URLS:")
for u in urls(src):
    print(" ",u)

print("\nOMNICIPHERIST IMPORTS:")
for x in imports(src):
    print(" ",x)

print("\n"+"="*110)
print("UNIVERSAL_CRT_V4 MARKET-DATA PATH")
print("="*110)

src=sources["universal_crt_v4.py"]

patterns=[
    "api_url",
    "fetch_candles",
    "_pair_url",
    "_fetch_pair",
    "exchange.coinbase.com",
    "urllib.request",
    "Coinbase",
    "candles",
    "granularity",
    "TF",
    "state[\"tf\"]",
    "_multi_refresh",
    "last_refresh",
]

for p in patterns:
    lines=[
        (i+1,line.strip())
        for i,line in enumerate(src.splitlines())
        if p.lower() in line.lower()
    ]
    print(f"\n[{p}] {len(lines)} match(es)")
    for no,line in lines[:25]:
        print(f"{no}: {line}")

print("\nV4 URLS:")
for u in urls(src):
    print(" ",u)

print("\nV4 IMPORTS:")
for x in imports(src):
    print(" ",x)

print("\n"+"="*110)
print("CURRENT-TICK / BID-ASK CAPABILITY")
print("="*110)

for name,src in sources.items():
    low=src.lower()

    print(f"\n{name}")

    checks={
        "HTTP request":("requests.get" in src or "urllib.request.urlopen" in src),
        "Bid field":bool(re.search(r'["\']bid["\']',src,re.I)),
        "Ask field":bool(re.search(r'["\']ask["\']',src,re.I)),
        "Mid field":bool(re.search(r'["\']mid["\']',src,re.I)),
        "Current price field":("current_price" in src),
        "Timestamp handling":("time.time" in src or "datetime" in src),
        "WebSocket":("websocket" in low or "ws://" in low or "wss://" in low),
        "Candle data":("candles" in low or "ohlc" in low),
    }

    for k,v in checks.items():
        print(f"{k:24}: {'PRESENT' if v else 'ABSENT'}")

print("\n"+"="*110)
print("TIMEFRAME AUTHORITY")
print("="*110)

v4=sources["universal_crt_v4.py"]
omni=sources["OMNICIPHERIST.py"]

print("\nV4 TF definitions:")
for i,line in enumerate(v4.splitlines(),1):
    if "TF=" in line or "TF_ORDER" in line:
        print(f"{i}: {line.strip()}")

print("\nOMNICIPHERIST timeframe references:")
for i,line in enumerate(omni.splitlines(),1):
    if "timeframe" in line.lower():
        print(f"{i}: {line.strip()}")

print("\n"+"="*110)
print("INSTRUMENT SPECIFICATION AUDIT")
print("="*110)

spec_terms={
    "pip_size":r'\bpip[_ ]?size\b|\bpip_size\b',
    "pip_value":r'\bpip[_ ]?value\b|\bpip_value\b',
    "contract_size":r'\bcontract[_ ]?size\b|\bcontract_size\b',
    "price_precision":r'\bprice[_ ]?precision\b|\bprecision\b',
    "tick_size":r'\btick[_ ]?size\b|\btick_size\b',
    "quote_currency":r'\bquote[_ ]?currency\b|\bquote_currency\b',
    "base_currency":r'\bbase[_ ]?currency\b|\bbase_currency\b',
    "account_currency":r'\baccount[_ ]?currency\b|\baccount_currency\b',
    "currency_conversion":r'bconversionb|bconvertb',
}

for name,src in sources.items():
    print(f"\n{name}")
    for label,pattern in spec_terms.items():
        found=bool(re.search(pattern,src,re.I))
        print(f"{label:22}: {'PRESENT' if found else 'ABSENT'}")

print("\n"+"="*110)
print("PIP / P/L CONSTANT AUDIT")
print("="*110)

for name,src in sources.items():
    print(f"\n{name}")

    for key in [
        "PIP_DISTANCE",
        "PIP_TO_PRICE_RATIO",
        "PIP_VALUE",
        "TARGET_GROWTH",
        "contract_size",
        "pip_size",
        "lot_size",
    ]:
        matches=[]
        for i,line in enumerate(src.splitlines(),1):
            if key.lower() in line.lower():
                matches.append((i,line.strip()))
        if matches:
            print(f"\n{key}:")
            for no,line in matches[:15]:
                print(f"  {no}: {line}")

print("\n"+"="*110)
print("GBPJPY / 15MIN ARCHITECTURE TEST")
print("="*110)

print("\nRequired normalized identity:")
print("PAIR      = GBPJPY")
print("TIMEFRAME = 15m / 900 seconds")

print("\nV4 supported timeframe mapping:")
for i,line in enumerate(v4.splitlines(),1):
    if "15m" in line or "15MIN" in line or "900" in line:
        print(f"{i}: {line.strip()}")

print("\nV4 pair normalization:")
for i,line in enumerate(v4.splitlines(),1):
    if "_pair_normalize" in line or "_pair_url" in line:
        print(f"{i}: {line.strip()}")

print("\nV4 market endpoint construction:")
for i,line in enumerate(v4.splitlines(),1):
    if "exchange.coinbase.com" in line or "candles?granularity" in line:
        print(f"{i}: {line.strip()}")

print("\nOMNICIPHERIST GBPJPY handling:")
for i,line in enumerate(omni.splitlines(),1):
    if "JPY" in line or "fetch_live_price" in line:
        print(f"{i}: {line.strip()}")

print("\n"+"="*110)
print("AUTHORITATIVE-SOURCE DETERMINATION")
print("="*110)

print("""
A market source qualifies as authoritative for the merge only if the
source path is explicitly identifiable and supplies the market fields
required by the lifecycle.

Required minimum:
  1. instrument-specific market source
  2. current market price
  3. timestamp
  4. candle/OHLC data where chart candles are required
  5. bid/ask or clearly defined trade/mid price
  6. instrument specification
  7. currency conversion when account currency differs from quote currency

This audit does NOT declare a provider authoritative merely because
the source code calls it "real-time" or "MT5".
""")

print("\n"+"="*110)
print("ARCHITECTURE MATRIX")
print("="*110)

matrix=[
    ("OMNICIPHERIST live price path","PRESENT" if "fetch_live_price" in omni else "ABSENT"),
    ("OMNICIPHERIST bid/ask path","PRESENT" if ('"bid"' in omni and '"ask"' in omni) else "ABSENT"),
    ("OMNICIPHERIST instrument specification","ABSENT"),
    ("OMNICIPHERIST account-currency conversion","ABSENT"),
    ("V4 candle source","PRESENT" if "exchange.coinbase.com" in v4 else "ABSENT"),
    ("V4 Forex-authoritative source","ABSENT"),
    ("V4 active-trade consumer","PRESENT" if "active_trade.json" in v4 else "ABSENT"),
    ("V4 live P/L engine","PRESENT" if "unrealized_pl" in v4 else "ABSENT"),
    ("V4 drawdown engine","PRESENT" if "drawdown" in v4.lower() else "ABSENT"),
    ("V4 SL/TP monitor","PRESENT" if ("take_profit" in v4 and "stop_loss" in v4) else "ABSENT"),
    ("Instrument-aware pip model","PRESENT" if "pip_size" in (omni+v4) else "ABSENT"),
    ("Contract-size model","PRESENT" if "contract_size" in (omni+v4) else "ABSENT"),
    ("Account-currency conversion model","ABSENT"),
]

for label,result in matrix:
    print(f"{label:42}: {result}")

print("\n"+"="*110)
print("STEP NINE GATE")
print("="*110)

print("MARKET-DATA ARCHITECTURE: REQUIRES BRIDGE")
print("INSTRUMENT SPECIFICATION: REQUIRES BRIDGE")
print("GBPJPY/15MIN AUTHORITATIVE V4 FEED: NOT ESTABLISHED")
print("LIVE P/L MODEL: NOT YET SAFE TO IMPLEMENT")
print("SL/TP MONITOR: NOT YET SAFE TO IMPLEMENT")
print("SOURCE MODIFICATION: NO")
print("BACKUP MODIFICATION: NO")
print("ACTIVE_TRADE.JSON MODIFICATION: NO")

print("\nCAT STAGE A — STEP NINE READ-ONLY AUDIT COMPLETE")
