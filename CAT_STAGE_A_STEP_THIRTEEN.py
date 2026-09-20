from pathlib import Path
import ast
import hashlib
import json
import time
import urllib.request
import ssl

PAIR="GBPJPY"
TIMEFRAME="15m"
ACCOUNT="USD"

print("CAT STAGE A — STEP THIRTEEN")
print("INSTRUMENT / CONTRACT AUTHORITY DISCOVERY")
print("MODE: READ ONLY")
print("TARGET: GBPJPY / 15m / USD")
print("")

CTX=ssl.create_default_context()

def get(url,timeout=12,headers=None):
    h={"User-Agent":"CAT-Stage-A-Step-Thirteen/1.0","Accept":"application/json"}
    if headers:
        h.update(headers)
    started=time.time()
    try:
        req=urllib.request.Request(url,headers=h)
        with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
            return {
                "ok":True,
                "status":getattr(r,"status",None),
                "body":r.read().decode("utf-8","replace"),
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

def js(body):
    try:
        return json.loads(body)
    except Exception:
        return None

def probe(name,url):
    print("\n"+"="*110)
    print(name)
    print("="*110)
    print("URL:",url)
    r=get(url)
    print("HTTP:", "SUCCESS" if r["ok"] else "FAILED")
    if r["status"] is not None:
        print("STATUS:",r["status"])
    print("ELAPSED:",f'{r["elapsed"]:.3f}s')
    if not r["ok"]:
        print("ERROR:",r["error"])
        return None
    data=js(r["body"])
    print("JSON:", "VALID" if data is not None else "INVALID")
    if data is None:
        print("BODY:",r["body"][:1000])
    else:
        print("TOP KEYS:",list(data.keys())[:40] if isinstance(data,dict) else type(data).__name__)
    return data

print("="*110)
print("1. PRODUCTION SOURCE INTEGRITY")
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
print("2. PUBLIC INSTRUMENT / REFERENCE SOURCES")
print("="*110)

frankfurter=probe(
    "Frankfurter GBPJPY reference",
    "https://api.frankfurter.app/latest?from=GBP&to=JPY"
)

ecb=probe(
    "Frankfurter ECB currencies",
    "https://api.frankfurter.app/currencies"
)

print("\nREFERENCE SOURCE INTERPRETATION:")
print("Frankfurter/ECB = reference exchange-rate data.")
print("It is NOT accepted as executable bid/ask authority.")
print("It is NOT accepted as 15m OHLC authority.")
print("It is NOT accepted as broker contract specification.")

print("\n"+"="*110)
print("3. CURRENT BROKER-LIKE QUOTE SOURCE")
print("="*110)

biquote=probe(
    "BiQuote GBPJPY",
    "https://biquote.io/api/GBPJPY"
)

if isinstance(biquote,dict):
    for k in [
        "symbol","bid","ask","mid","spread",
        "stale","quoteAgeSeconds","timestamp",
        "lastQuoteAt","marketState","source"
    ]:
        print(f"{k:20}:",biquote.get(k,"<ABSENT>"))

    fresh=(
        biquote.get("stale") is False
        and isinstance(biquote.get("quoteAgeSeconds"),(int,float))
        and biquote.get("quoteAgeSeconds")<=30
    )

    print("CAT FRESH:",fresh)

print("\n"+"="*110)
print("4. CANDLE AUTHORITY")
print("="*110)

candle_tests=[
    (
        "Coinbase",
        "https://api.exchange.coinbase.com/products/GBP-JPY/candles?granularity=900"
    ),
    (
        "Twelve Data",
        "https://api.twelvedata.com/time_series?symbol=GBP/JPY&interval=15min&outputsize=5"
    ),
    (
        "Alpha Vantage",
        "https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=GBP&to_symbol=JPY&interval=15min&outputsize=compact"
    )
]

for name,url in candle_tests:
    data=probe(name+" GBPJPY 15m",url)
    if isinstance(data,dict):
        if "Error Message" in data:
            print("PROVIDER ERROR:",data["Error Message"])
        if "code" in data:
            print("CODE:",data["code"])
        if "message" in data:
            print("MESSAGE:",data["message"])

print("\n"+"="*110)
print("5. INSTRUMENT SPECIFICATION — REQUIRED VS ESTABLISHED")
print("="*110)

fields=[
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
    "margin_requirement",
    "quote_to_account_conversion",
    "bid_execution_side",
    "ask_execution_side"
]

established={
    "base_currency":"GBP",
    "quote_currency":"JPY",
    "account_currency":"USD",
    "pip_size":"0.01",
    "tick_size":"NOT ESTABLISHED",
    "price_precision":"NOT ESTABLISHED",
    "contract_size":"NOT ESTABLISHED",
    "lot_unit":"NOT ESTABLISHED",
    "minimum_lot":"NOT ESTABLISHED",
    "maximum_lot":"NOT ESTABLISHED",
    "lot_step":"NOT ESTABLISHED",
    "margin_currency":"NOT ESTABLISHED",
    "margin_requirement":"NOT ESTABLISHED",
    "quote_to_account_conversion":"REFERENCE PATH AVAILABLE",
    "bid_execution_side":"BUY ENTRY / SELL LIQUIDATION",
    "ask_execution_side":"SELL ENTRY / BUY LIQUIDATION"
}

for f in fields:
    print(f"{f:35} {established[f]}")

print("\n"+"="*110)
print("6. CONTRACT / LOT MATHEMATICS")
print("="*110)

print("""
A position-size model requires an explicit mapping:

lots
  ↓
contract_units_per_lot
  ↓
base-currency exposure

For GBPJPY:

base = GBP
quote = JPY

quote P/L:

  quote_pnl =
      favorable_price_change
      × contract_units
      × lots

USD P/L:

  usd_pnl =
      quote_pnl
      × JPY_to_USD

The following are NOT equivalent:

  pip_value = 10
  contract_size = 100000
  lot_size = 1

They represent different concepts and must not be substituted
for one another.
""")

print("\n"+"="*110)
print("7. FRESHNESS + TIMESTAMP RECONCILIATION")
print("="*110)

print("""
Every market-data observation entering the bridge must carry:

  provider
  symbol
  timestamp
  received_at
  freshness
  market_state
  price_side / OHLC role

A quote is usable only if:

  symbol == GBPJPY
  AND provider_role == EXECUTION_QUOTE
  AND stale == False
  AND quote_age <= configured threshold
  AND market_state permits the intended operation

A candle is usable only if:

  symbol == GBPJPY
  AND timeframe == 15m
  AND OHLC fields are provider-supplied
  AND candle timestamp is valid
  AND candle is not fabricated from a spot quote

Conversion data must have its own timestamp/freshness validation.
""")

print("\n"+"="*110)
print("8. SINGLE PROVIDER AUTHORITY")
print("="*110)

print("EXECUTION BID/ASK:", "OBSERVED" if isinstance(biquote,dict) else "NO")
print("FRESH EXECUTION BID/ASK:", "NO" if not isinstance(biquote,dict) else "CHECKED ABOVE")
print("15m GBPJPY OHLC:", "NOT ESTABLISHED")
print("CONTRACT SPEC:", "NOT ESTABLISHED")
print("LOT SPEC:", "NOT ESTABLISHED")
print("SINGLE PROVIDER:", "NOT ESTABLISHED")

print("\n"+"="*110)
print("9. MULTI-PROVIDER REQUIREMENT")
print("="*110)

print("""
ROLE A — EXECUTION QUOTE
  bid / ask
  timestamp
  freshness
  market state

ROLE B — 15m CANDLES
  timestamp
  open/high/low/close
  provider identity

ROLE C — INSTRUMENT SPEC
  contract units
  lot rules
  precision
  tick/pip

ROLE D — ACCOUNT CONVERSION
  JPY → USD
  timestamp
  freshness

ROLE E — RECONCILIATION
  symbol validation
  timestamp validation
  freshness validation
  provider-role validation
  instrument validation
""")

print("\n"+"="*110)
print("10. STEP THIRTEEN FINAL GATE")
print("="*110)

print("BROKER-SPECIFIC CONTRACT AUTHORITY:", "NOT ESTABLISHED")
print("GENERIC FX CONVENTION:", "PARTIALLY ESTABLISHED")
print("GBPJPY PIP SIZE:", "0.01")
print("CONTRACT SIZE:", "BLOCKED")
print("LOT SEMANTICS:", "BLOCKED")
print("MIN/MAX/STEP:", "BLOCKED")
print("MARGIN SPEC:", "BLOCKED")
print("FRESH EXECUTION QUOTE:", "BLOCKED")
print("GBPJPY 15m OHLC:", "BLOCKED")
print("REFERENCE FX RATE:", "AVAILABLE")
print("EXECUTION PRICE AUTHORITY:", "BLOCKED")
print("SINGLE PROVIDER:", "NOT ESTABLISHED")
print("MULTI-PROVIDER RECONCILIATION:", "REQUIRED")
print("LIVE P/L:", "BLOCKED")
print("SL/TP:", "BLOCKED")
print("AUTO-CLOSE:", "BLOCKED")
print("CRT GBPJPY 15m:", "BLOCKED")
print("PRODUCTION MERGE:", "BLOCKED")

print("\nSAFETY:")
print("SOURCE MODIFICATION: NO")
print("ACTIVE_TRADE.JSON MODIFICATION: NO")
print("BACKUPS MODIFIED: NO")
print("HISTORICAL REWRITE: NO")
print("DIRECTION INFERENCE: NO")
print("FAKE DATA: NO")
print("TRADE EXECUTION: NO")

print("\nCAT STAGE A — STEP THIRTEEN COMPLETE")
