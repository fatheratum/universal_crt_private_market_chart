from pathlib import Path
import ast
import hashlib
import json
import re
import ssl
import time
import urllib.request
import urllib.parse

PAIR="GBPJPY"
BASE="GBP"
QUOTE="JPY"
ACCOUNT="USD"
TIMEFRAME="15m"
GRANULARITY=900
FRESH_SECONDS=30
CTX=ssl.create_default_context()

print("CAT STAGE A — STEP FOURTEEN")
print("BLOCKED-DEPENDENCY AUTHORITY DISCOVERY")
print("MODE: READ ONLY")
print("TARGET: GBPJPY / 15m / USD")
print("")

def http_get(url,timeout=12,headers=None):
    h={
        "User-Agent":"CAT-Stage-A-Step-Fourteen/1.0",
        "Accept":"application/json,text/plain,*/*"
    }
    if headers:
        h.update(headers)
    started=time.time()
    try:
        req=urllib.request.Request(url,headers=h)
        with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
            body=r.read().decode("utf-8","replace")
            return {
                "ok":True,
                "status":getattr(r,"status",None),
                "body":body,
                "headers":dict(r.headers),
                "elapsed":time.time()-started
            }
    except Exception as e:
        return {
            "ok":False,
            "status":None,
            "body":"",
            "headers":{},
            "elapsed":time.time()-started,
            "error":f"{type(e).__name__}: {e}"
        }

def parse_json(body):
    try:
        return json.loads(body)
    except Exception:
        return None

def probe(name,url,headers=None):
    print("\n"+"="*110)
    print(name)
    print("="*110)
    print("URL:",url)
    r=http_get(url,headers=headers)
    print("HTTP:",r["status"] if r["status"] is not None else "FAILED")
    print("ELAPSED:",f'{r["elapsed"]:.3f}s')
    if not r["ok"]:
        print("ERROR:",r["error"])
        return None
    data=parse_json(r["body"])
    print("JSON:", "VALID" if data is not None else "INVALID")
    if isinstance(data,dict):
        print("KEYS:",list(data.keys())[:80])
    elif isinstance(data,list):
        print("LIST LENGTH:",len(data))
        if data:
            print("FIRST ITEM TYPE:",type(data[0]).__name__)
    else:
        print("BODY:",r["body"][:1200])
    return data

print("="*110)
print("1. SOURCE INTEGRITY — READ ONLY")
print("="*110)

for name in ["OMNICIPHERIST.py","universal_crt_v4.py","active_trade.json"]:
    p=Path(name)
    if not p.exists():
        print(name,": MISSING")
        continue
    raw=p.read_bytes()
    print(name)
    print("  SHA256:",hashlib.sha256(raw).hexdigest())
    if name.endswith(".py"):
        try:
            ast.parse(raw.decode("utf-8"))
            print("  AST: VALID")
        except Exception as e:
            print("  AST: INVALID:",e)

print("\n"+"="*110)
print("2. BLOCKER A — EXECUTION QUOTE AUTHORITY")
print("="*110)

biquote=probe(
    "BiQuote GBPJPY",
    "https://biquote.io/api/GBPJPY"
)

biquote_fresh=False

if isinstance(biquote,dict):
    print("")
    for key in [
        "symbol","bid","ask","mid","last",
        "spread","timestamp","lastQuoteAt",
        "quoteAgeSeconds","stale",
        "marketState","source"
    ]:
        print(f"{key:20}:",biquote.get(key,"<ABSENT>"))

    biquote_fresh=(
        biquote.get("symbol")=="GBPJPY"
        and isinstance(biquote.get("bid"),(int,float))
        and isinstance(biquote.get("ask"),(int,float))
        and biquote.get("stale") is False
        and isinstance(biquote.get("quoteAgeSeconds"),(int,float))
        and biquote.get("quoteAgeSeconds")<=FRESH_SECONDS
    )

print("")
print("EXECUTION QUOTE AUTHORITY:", "PASS" if biquote_fresh else "BLOCKED")

print("\nREQUIRED EXECUTION FIELDS:")
for field in [
    "symbol",
    "bid",
    "ask",
    "timestamp",
    "received_at",
    "quote_age",
    "stale",
    "market_state",
    "provider_identity"
]:
    print(" ",field)

print("\nRULE:")
print("No fresh bid/ask = no live P/L, no SL/TP trigger, no auto-close.")

print("\n"+"="*110)
print("3. BLOCKER B — 15m OHLC AUTHORITY")
print("="*110)

providers=[
    (
        "Coinbase",
        "https://api.exchange.coinbase.com/products/GBP-JPY/candles?granularity=900"
    ),
    (
        "TwelveData",
        "https://api.twelvedata.com/time_series?symbol=GBP/JPY&interval=15min&outputsize=5"
    ),
    (
        "AlphaVantage",
        "https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=GBP&to_symbol=JPY&interval=15min&outputsize=compact"
    ),
    (
        "Frankfurter",
        "https://api.frankfurter.app/latest?from=GBP&to=JPY"
    )
]

ohlc_authority=False

for name,url in providers:
    data=probe(name+" GBPJPY",url)

    if name=="Coinbase" and isinstance(data,list) and data:
        sample=data[0]
        if isinstance(sample,list) and len(sample)>=6:
            ohlc_authority=True

    if name=="TwelveData" and isinstance(data,dict):
        values=data.get("values")
        if isinstance(values,list) and values:
            item=values[0]
            if all(k in item for k in ["datetime","open","high","low","close"]):
                ohlc_authority=True

    if name=="AlphaVantage" and isinstance(data,dict):
        for key,value in data.items():
            if "Time Series FX" in key and isinstance(value,dict) and value:
                ohlc_authority=True

print("")
print("PROVIDER-SUPPLIED GBPJPY 15m OHLC:", "PASS" if ohlc_authority else "BLOCKED")

print("\nCANDLE REQUIREMENTS:")
for field in [
    "provider",
    "symbol",
    "timeframe",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume-if-provider-supplied"
]:
    print(" ",field)

print("\nRULE:")
print("A spot/reference price cannot be transformed into synthetic 15m OHLC.")

print("\n"+"="*110)
print("4. BLOCKER C — CONTRACT SIZE AUTHORITY")
print("="*110)

print("""
SEARCH TARGETS:

contract_size
contractSize
contract_units
contractUnits
units_per_lot
unitsPerLot
base_units
lot_size
lotSize
position_size
positionSize
""")

source_texts={}

for name in ["OMNICIPHERIST.py","universal_crt_v4.py"]:
    p=Path(name)
    if p.exists():
        source_texts[name]=p.read_text(errors="replace")

contract_patterns=[
    r"contract[_A-Za-z]*size",
    r"contract[_A-Za-z]*units?",
    r"units?[_A-Za-z]*per[_A-Za-z]*lot",
    r"units[_A-Za-z]*per[_A-Za-z]*lot",
    r"contractSize",
    r"contractUnits"
]

for name,text in source_texts.items():
    print("\n",name)
    found=[]
    for pattern in contract_patterns:
        matches=re.findall(pattern,text,re.I)
        if matches:
            found.extend(matches)
    print("CONTRACT SYMBOLS:",sorted(set(found)) if found else "NONE")

print("""
CAT RESULT:
Source presence of a variable is NOT contract authority.
A numeric contract size is accepted only when tied to an
identified authoritative instrument specification.
""")

print("CONTRACT SIZE:", "BLOCKED")

print("\n"+"="*110)
print("5. BLOCKER D — LOT SEMANTICS")
print("="*110)

lot_fields=[
    "lot_unit",
    "units_per_lot",
    "minimum_lot",
    "maximum_lot",
    "lot_step",
    "min_volume",
    "max_volume",
    "volume_step",
    "position_size"
]

for name,text in source_texts.items():
    print("\n",name)
    for field in lot_fields:
        hits=re.findall(r".{0,45}"+re.escape(field)+r".{0,80}",text,re.I)
        if hits:
            print(field,":",hits[:5])

print("""
REQUIRED:

1 lot = ? base units
minimum lot = ?
maximum lot = ?
lot increment = ?
broker volume unit = ?
fractional-lot behavior = ?

The engine must not assume these values.
""")

print("LOT SEMANTICS: BLOCKED")
print("MIN LOT: BLOCKED")
print("MAX LOT: BLOCKED")
print("LOT STEP: BLOCKED")

print("\n"+"="*110)
print("6. BLOCKER E — PRICE / INSTRUMENT SPECIFICATION")
print("="*110)

spec=[
    ("base_currency","GBP","ESTABLISHED"),
    ("quote_currency","JPY","ESTABLISHED"),
    ("account_currency","USD","ESTABLISHED"),
    ("pip_size","0.01","ESTABLISHED"),
    ("tick_size","UNKNOWN","BLOCKED"),
    ("price_precision","UNKNOWN","BLOCKED"),
    ("contract_size","UNKNOWN","BLOCKED"),
    ("lot_unit","UNKNOWN","BLOCKED"),
    ("minimum_lot","UNKNOWN","BLOCKED"),
    ("maximum_lot","UNKNOWN","BLOCKED"),
    ("lot_step","UNKNOWN","BLOCKED"),
    ("margin_currency","UNKNOWN","BLOCKED"),
    ("margin_requirement","UNKNOWN","BLOCKED")
]

for field,value,status in spec:
    print(f"{field:25} {value:15} {status}")

print("\n"+"="*110)
print("7. BLOCKER F — ACCOUNT-CURRENCY CONVERSION")
print("="*110)

fx=probe(
    "Frankfurter JPY/USD reference",
    "https://api.frankfurter.app/latest?from=JPY&to=USD"
)

conversion_available=False

if isinstance(fx,dict):
    rates=fx.get("rates")
    if isinstance(rates,dict) and isinstance(rates.get("USD"),(int,float)):
        conversion_available=True
        print("JPY→USD:",rates["USD"])
        print("DATE:",fx.get("date"))

print("")
print("JPY→USD REFERENCE PATH:", "AVAILABLE" if conversion_available else "BLOCKED")
print("EXECUTABLE CONVERSION:", "BLOCKED")

print("""
A reference conversion may support valuation only after the
engine explicitly defines its valuation policy.

It does not establish broker execution or margin semantics.
""")

print("\n"+"="*110)
print("8. PRICE-SIDE MATHEMATICS")
print("="*110)

print("""
BUY:

entry_price = ASK
liquidation_price = BID

favorable_change = liquidation_price - entry_price

SELL:

entry_price = BID
liquidation_price = ASK

favorable_change = entry_price - liquidation_price

quote_pnl =
    favorable_change
    × contract_units_per_lot
    × lots

account_pnl =
    quote_pnl
    × quote_to_account_rate

For GBPJPY:

quote_currency = JPY
account_currency = USD

Therefore:

JPY P/L → JPY/USD → USD P/L

No universal pip-value shortcut is permitted until the
instrument and lot specification is authoritative.
""")

print("\n"+"="*110)
print("9. BLOCKER MATRIX")
print("="*110)

matrix=[
    ("Fresh execution quote",biquote_fresh),
    ("GBPJPY 15m OHLC",ohlc_authority),
    ("Contract size",False),
    ("Lot unit",False),
    ("Minimum lot",False),
    ("Maximum lot",False),
    ("Lot step",False),
    ("Tick size",False),
    ("Price precision",False),
    ("Margin currency",False),
    ("Executable conversion",False)
]

for name,ok in matrix:
    print(f"{name:35} {'PASS' if ok else 'BLOCKED'}")

print("\n"+"="*110)
print("10. CAT SAFETY INVARIANTS")
print("="*110)

print("STALE QUOTE → LIVE P/L: FORBIDDEN")
print("STALE QUOTE → SL/TP: FORBIDDEN")
print("STALE QUOTE → AUTO-CLOSE: FORBIDDEN")
print("REFERENCE RATE → EXECUTION: FORBIDDEN")
print("REFERENCE RATE → SYNTHETIC OHLC: FORBIDDEN")
print("UNKNOWN CONTRACT → P/L: FORBIDDEN")
print("UNKNOWN LOT SEMANTICS → P/L: FORBIDDEN")
print("UNVERIFIED 15m OHLC → CRT AUTHORITY: FORBIDDEN")
print("HISTORICAL RECORD REWRITE: FORBIDDEN")
print("DIRECTION INFERENCE: FORBIDDEN")
print("TRADE EXECUTION: FORBIDDEN")

print("\n"+"="*110)
print("11. STEP FOURTEEN FINAL GATE")
print("="*110)

all_required=[
    biquote_fresh,
    ohlc_authority,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False
]

if all(all_required):
    print("STEP FOURTEEN: PASS")
    print("BLOCKED DEPENDENCIES RESOLVED")
else:
    print("STEP FOURTEEN: BLOCKED")
    print("ONE OR MORE REQUIRED AUTHORITIES REMAIN UNRESOLVED")

print("\nSOURCE MODIFICATION: NO")
print("ACTIVE_TRADE.JSON MODIFICATION: NO")
print("BACKUPS MODIFIED: NO")
print("PRODUCTION MERGE: BLOCKED")
print("TRADE EXECUTION: NO")
print("FAKE DATA: NO")

print("\nCAT STAGE A — STEP FOURTEEN COMPLETE")
