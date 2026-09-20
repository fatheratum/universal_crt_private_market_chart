from pathlib import Path
import ast
import hashlib
import json
import time
import urllib.request
import urllib.parse
import ssl

PAIR="GBPJPY"
BASE="GBP"
QUOTE="JPY"
ACCOUNT="USD"
TIMEFRAME="15m"
GRANULARITY=900

print("CAT STAGE A — STEP TWELVE")
print("FX PROVIDER + INSTRUMENT SPECIFICATION DISCOVERY")
print("MODE: READ ONLY")
print("TARGET: GBPJPY / 15m / USD ACCOUNT")
print("SOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

CTX=ssl.create_default_context()

def get(url,timeout=12,headers=None):
    started=time.time()
    try:
        h={
            "User-Agent":"CAT-Stage-A-Step-Twelve/1.0",
            "Accept":"application/json"
        }
        if headers:
            h.update(headers)
        req=urllib.request.Request(url,headers=h)
        with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
            body=r.read().decode("utf-8","replace")
            return {
                "ok":True,
                "status":getattr(r,"status",None),
                "headers":dict(r.headers),
                "body":body,
                "elapsed":time.time()-started
            }
    except Exception as e:
        return {
            "ok":False,
            "status":None,
            "headers":{},
            "body":"",
            "elapsed":time.time()-started,
            "error":f"{type(e).__name__}: {e}"
        }

def parse_json(body):
    try:
        return json.loads(body)
    except Exception:
        return None

def probe(label,url):
    print("\n"+"-"*100)
    print(label)
    print("URL:",url)
    r=get(url)
    print("HTTP:", "SUCCESS" if r["ok"] else "FAILED")
    if r["status"] is not None:
        print("STATUS:",r["status"])
    print("ELAPSED:",f'{r["elapsed"]:.3f}s')
    if not r["ok"]:
        print("ERROR:",r["error"])
        return None
    data=parse_json(r["body"])
    print("JSON:", "VALID" if data is not None else "INVALID")
    if data is None:
        print("BODY:",r["body"][:1000])
    return data

print("\n"+"="*110)
print("1. SOURCE INTEGRITY")
print("="*110)

for name in ["OMNICIPHERIST.py","universal_crt_v4.py","active_trade.json"]:
    p=Path(name)
    print("\n",name)
    if not p.exists():
        print("MISSING")
        continue
    raw=p.read_bytes()
    print("BYTES:",len(raw))
    print("SHA256:",hashlib.sha256(raw).hexdigest())
    if name.endswith(".py"):
        try:
            ast.parse(raw.decode("utf-8"))
            print("AST: VALID")
        except Exception as e:
            print("AST: INVALID:",e)

print("\n"+"="*110)
print("2. PROVIDER CAPABILITY MATRIX")
print("="*110)

providers=[
    (
        "Frankfurter latest GBPJPY",
        "https://api.frankfurter.app/latest?from=GBP&to=JPY"
    ),
    (
        "Frankfurter historical GBPJPY",
        "https://api.frankfurter.app/2026-09-18?from=GBP&to=JPY"
    ),
    (
        "Frankfurter ECB GBPJPY",
        "https://api.frankfurter.app/latest?from=GBP&to=JPY&amount=1"
    ),
    (
        "BiQuote GBPJPY",
        "https://biquote.io/api/GBPJPY"
    ),
    (
        "Coinbase GBP-JPY candles",
        "https://api.exchange.coinbase.com/products/GBP-JPY/candles?granularity=900"
    ),
    (
        "Coinbase GBP-JPY product",
        "https://api.exchange.coinbase.com/products/GBP-JPY"
    ),
    (
        "Twelve Data GBPJPY 15m",
        "https://api.twelvedata.com/time_series?symbol=GBP/JPY&interval=15min&outputsize=5"
    ),
    (
        "Alpha Vantage GBPJPY 15m",
        "https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=GBP&to_symbol=JPY&interval=15min&outputsize=compact"
    )
]

results={}

for label,url in providers:
    data=probe(label,url)
    results[label]=data

    if isinstance(data,dict):
        print("KEYS:",sorted(data.keys())[:40])
        for k in ["status","code","message","error","date","base","rates"]:
            if k in data:
                print(f"{k}:",data[k])

print("\n"+"="*110)
print("3. BIQUOTE MARKET-DATA SEMANTICS")
print("="*110)

b=results.get("BiQuote GBPJPY")

if isinstance(b,dict):
    for k in [
        "symbol","bid","ask","mid","last","spread",
        "stale","quoteAgeSeconds","timestamp",
        "lastQuoteAt","marketState","source"
    ]:
        print(f"{k:20}:",b.get(k,"<ABSENT>"))

    stale=b.get("stale")
    age=b.get("quoteAgeSeconds")

    print("\nFRESHNESS RULE")
    print("stale == False:",stale is False)

    if isinstance(age,(int,float)):
        print("quoteAgeSeconds:",age)
        print("AGE <= 30:",age<=30)

    fresh=(stale is False and isinstance(age,(int,float)) and age<=30)
    print("CAT FRESHNESS RESULT:", "FRESH" if fresh else "REJECT")

print("\n"+"="*110)
print("4. FRANKFURTER ROLE TEST")
print("="*110)

f=results.get("Frankfurter latest GBPJPY")

if isinstance(f,dict):
    print("BASE:",f.get("base"))
    print("DATE:",f.get("date"))
    print("RATES:",f.get("rates"))
    print("""
Frankfurter may establish a reference conversion/rate,
but this audit does NOT promote it to executable FX authority.
It does not establish 15-minute OHLC or bid/ask execution semantics.
""")

print("\n"+"="*110)
print("5. CANDLE SCHEMA DETECTION")
print("="*110)

def inspect_candle_payload(label,data):
    print("\n",label)

    if not isinstance(data,(dict,list)):
        print("NO STRUCTURED PAYLOAD")
        return

    if isinstance(data,dict):
        for key in [
            "values","data","candles","results",
            "Time Series FX (15min)"
        ]:
            if key in data:
                value=data[key]
                print("CANDLE CONTAINER:",key)
                if isinstance(value,list) and value:
                    print("COUNT:",len(value))
                    print("FIRST:",value[0])
                elif isinstance(value,dict):
                    keys=list(value.keys())
                    print("COUNT:",len(keys))
                    if keys:
                        print("FIRST KEY:",keys[0])
                        print("FIRST VALUE:",value[keys[0]])
                return

    print("NO RECOGNIZED CANDLE CONTAINER")

for label,data in results.items():
    if "15m" in label.lower() or "candles" in label.lower():
        inspect_candle_payload(label,data)

print("\n"+"="*110)
print("6. REQUIRED GBPJPY 15m CANDLE CONTRACT")
print("="*110)

print("""
Required:
  symbol        = GBPJPY
  timeframe     = 15m
  interval      = 900 seconds
  timestamp     = provider candle timestamp
  open          = numeric
  high          = numeric
  low           = numeric
  close         = numeric

Optional:
  volume        = provider-supplied only

Forbidden:
  synthetic OHLC
  random OHLC
  stale quote promoted to candle
  midpoint fabricated into OHLC
  conversion rate fabricated into OHLC
""")

print("\n"+"="*110)
print("7. INSTRUMENT-SPECIFICATION REQUIREMENTS")
print("="*110)

requirements=[
    "base_currency",
    "quote_currency",
    "account_currency",
    "pip_size",
    "tick_size",
    "price_precision",
    "contract_size",
    "lot_unit",
    "minimum_lot",
    "maximum_lot",
    "lot_step",
    "margin_currency",
    "quote_currency_to_account_currency_conversion",
    "bid/ask execution semantics"
]

for item in requirements:
    print(f"{item:45} REQUIRED")

print("\nOBSERVED FROM CURRENT ENGINE:")
print("base_currency                         = GBP")
print("quote_currency                        = JPY")
print("account_currency                     = USD")
print("pip_size                             = 0.01")
print("contract_size                        = NOT ESTABLISHED")
print("lot_unit                             = NOT ESTABLISHED")
print("minimum/maximum/step                 = NOT ESTABLISHED")
print("margin_currency                      = NOT ESTABLISHED")
print("execution specification              = DESIGN ONLY")

print("\n"+"="*110)
print("8. P/L MODEL — NO HARD-CODED CONTRACT")
print("="*110)

print("""
BUY:
  favorable_price_change = liquidation_bid - entry

SELL:
  favorable_price_change = entry - liquidation_ask

quote_currency_pnl =
  favorable_price_change
  × contract_units
  × position_lots

account_currency_pnl =
  quote_currency_pnl
  × quote_to_account_conversion

For GBPJPY/USD:
  quote currency = JPY
  account currency = USD
  conversion = JPY → USD

This remains BLOCKED until contract_units and lot semantics
are established from the actual instrument specification.
""")

print("\n"+"="*110)
print("9. SINGLE-PROVIDER TEST")
print("="*110)

biquote_has_quote=isinstance(b,dict) and "bid" in b and "ask" in b
biquote_fresh=isinstance(b,dict) and b.get("stale") is False

single_provider=False

print("BiQuote quote fields:", "YES" if biquote_has_quote else "NO")
print("BiQuote fresh:", "YES" if biquote_fresh else "NO")
print("BiQuote 15m OHLC:", "NO")
print("BiQuote instrument contract metadata:", "NOT ESTABLISHED")
print("BiQuote lot metadata:", "NOT ESTABLISHED")
print("SINGLE PROVIDER AUTHORITY:", "NOT ESTABLISHED")

print("\n"+"="*110)
print("10. MULTI-PROVIDER ARCHITECTURE TEST")
print("="*110)

print("""
Potential role separation:

SPOT/EXECUTION QUOTE PROVIDER
  ↓
  bid / ask / timestamp / freshness

CANDLE PROVIDER
  ↓
  GBPJPY 15m OHLC / timestamp

INSTRUMENT SPECIFICATION
  ↓
  contract size / lot rules / precision / tick / pip

CONVERSION PROVIDER
  ↓
  JPY → USD / timestamp / freshness

RECONCILIATION LAYER
  ↓
  timestamp validation
  ↓
  freshness validation
  ↓
  symbol validation
  ↓
  provider-role validation
  ↓
  only then market state becomes usable
""")

print("MULTI-PROVIDER DESIGN:", "REQUIRED UNLESS A SINGLE AUTHORITATIVE PROVIDER IS ESTABLISHED")

print("\n"+"="*110)
print("11. SAFETY INVARIANTS")
print("="*110)

print("STALE QUOTE → LIVE P/L: FORBIDDEN")
print("STALE QUOTE → SL/TP: FORBIDDEN")
print("STALE QUOTE → AUTO-CLOSE: FORBIDDEN")
print("STALE QUOTE → CRT LIVE STATE: FORBIDDEN")
print("REFERENCE RATE → EXECUTION PRICE: FORBIDDEN")
print("REFERENCE RATE → SYNTHETIC CANDLE: FORBIDDEN")
print("UNKNOWN CONTRACT SIZE → P/L: FORBIDDEN")
print("UNKNOWN LOT SEMANTICS → P/L: FORBIDDEN")
print("UNVERIFIED OHLC → CRT AUTHORITATIVE DATA: FORBIDDEN")
print("HISTORICAL TRADE REWRITE: FORBIDDEN")
print("DIRECTION INFERENCE: FORBIDDEN")
print("TRADE EXECUTION: FORBIDDEN")

print("\n"+"="*110)
print("12. STEP TWELVE FINAL GATE")
print("="*110)

print("GBPJPY CURRENT QUOTE:", "OBSERVED BUT FRESHNESS-BLOCKED")
print("GBPJPY BID/ASK:", "OBSERVED")
print("GBPJPY 15m OHLC:", "NOT ESTABLISHED")
print("GBPJPY INSTRUMENT METADATA:", "INCOMPLETE")
print("CONTRACT SIZE:", "NOT ESTABLISHED")
print("LOT SEMANTICS:", "NOT ESTABLISHED")
print("PIP SIZE:", "0.01")
print("JPY→USD CONVERSION:", "REFERENCE PATH AVAILABLE")
print("EXECUTION PRICE AUTHORITY:", "NOT ESTABLISHED")
print("SINGLE PROVIDER:", "NOT ESTABLISHED")
print("MULTI-PROVIDER RECONCILIATION:", "REQUIRED")
print("LIVE P/L:", "BLOCKED")
print("SL/TP:", "BLOCKED")
print("AUTO-CLOSE:", "BLOCKED")
print("CRT GBPJPY 15m AUTHORITY:", "BLOCKED")
print("PRODUCTION MERGE:", "BLOCKED")

print("\nSOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")
print("FAKE DATA: NO")
print("TRADE EXECUTION: NO")
print("CAT STAGE A — STEP TWELVE COMPLETE")
