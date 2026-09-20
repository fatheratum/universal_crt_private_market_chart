from pathlib import Path
import ast
import json
import time
import urllib.request
import urllib.parse
import ssl
from datetime import datetime,timezone

PAIR="GBPJPY"
TIMEFRAME="15m"
GRANULARITY=900
ACCOUNT_CURRENCY="USD"

print("CAT STAGE A — STEP ELEVEN")
print("AUTHORITATIVE FX INSTRUMENT + CONTRACT/LOT + CANDLE ARCHITECTURE AUDIT")
print("MODE: READ ONLY")
print("TARGET: GBPJPY / 15m / USD ACCOUNT")
print("SOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

CTX=ssl.create_default_context()

def get(url,timeout=10):
    started=time.time()
    try:
        req=urllib.request.Request(
            url,
            headers={
                "User-Agent":"CAT-Stage-A-Step-Eleven/1.0",
                "Accept":"application/json"
            }
        )
        with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
            body=r.read().decode("utf-8","replace")
            return {
                "ok":True,
                "status":getattr(r,"status",None),
                "body":body,
                "elapsed":time.time()-started
            }
    except Exception as e:
        return {
            "ok":False,
            "status":None,
            "body":"",
            "elapsed":time.time()-started,
            "error":f"{type(e).__name__}: {e}"
        }

def js(body):
    try:
        return json.loads(body)
    except Exception:
        return None

def test(label,url):
    print(f"\n[{label}]")
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
    return data

print("\n"+"="*110)
print("1. EXISTING SOURCE ARCHITECTURE")
print("="*110)

for name in ["OMNICIPHERIST.py","universal_crt_v4.py"]:
    p=Path(name)
    print(f"\n{name}")
    if not p.exists():
        print("MISSING")
        continue
    src=p.read_text(encoding="utf-8",errors="replace")
    print("LINES:",len(src.splitlines()))
    print("SHA256:",__import__("hashlib").sha256(src.encode()).hexdigest())

    try:
        tree=ast.parse(src)
        print("AST: VALID")
    except Exception as e:
        print("AST: INVALID",e)

print("\n"+"="*110)
print("2. BIQUOTE FRESHNESS RE-TEST")
print("="*110)

biquote=test(
    "BiQuote GBPJPY",
    "https://biquote.io/api/GBPJPY"
)

if isinstance(biquote,dict):
    print("\nFIELDS")
    for k in [
        "symbol","bid","ask","mid","last",
        "spread","stale","quoteAgeSeconds",
        "timestamp","time","lastQuoteAt",
        "marketState","source"
    ]:
        print(f"{k:18}:",biquote.get(k,"<ABSENT>"))

    age=biquote.get("quoteAgeSeconds")
    if isinstance(age,(int,float)):
        print("QUOTE AGE SECONDS:",age)
        print("FRESHNESS:", "FRESH" if age <= 30 else "STALE/OLD")

print("\n"+"="*110)
print("3. FX CANDLE PROVIDER DISCOVERY")
print("="*110)

urls=[
    (
        "Frankfurter GBPJPY",
        "https://api.frankfurter.app/latest?from=GBP&to=JPY"
    ),
    (
        "Twelve Data GBPJPY 15m metadata",
        "https://api.twelvedata.com/time_series?symbol=GBP/JPY&interval=15min&outputsize=5"
    ),
    (
        "Alpha Vantage GBPJPY 15m",
        "https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=GBP&to_symbol=JPY&interval=15min&outputsize=compact"
    )
]

for label,url in urls:
    data=test(label,url)
    if isinstance(data,dict):
        print("TOP KEYS:",sorted(data.keys())[:30])
        if "status" in data:
            print("API STATUS:",data.get("status"))
        if "code" in data:
            print("API CODE:",data.get("code"))
        if "message" in data:
            print("API MESSAGE:",data.get("message"))

print("\n"+"="*110)
print("4. INSTRUMENT SPECIFICATION — SOURCE CODE")
print("="*110)

for name in ["OMNICIPHERIST.py","universal_crt_v4.py"]:
    p=Path(name)
    src=p.read_text(encoding="utf-8",errors="replace") if p.exists() else ""
    print(f"\n{name}")

    terms=[
        "contract_size",
        "pip_size",
        "tick_size",
        "base_currency",
        "quote_currency",
        "account_currency",
        "position_size",
        "units",
        "lot_size",
        "pip_value"
    ]

    for term in terms:
        hits=[
            (i,line.strip())
            for i,line in enumerate(src.splitlines(),1)
            if term.lower() in line.lower()
        ]
        print(f"{term:20}: {len(hits)}")

print("\n"+"="*110)
print("5. STANDARD FX CONTRACT MODEL — EXPLICIT ASSUMPTIONS")
print("="*110)

print("""
GBPJPY:
  base currency  = GBP
  quote currency = JPY
  account        = USD
  standard pip   = 0.01

A standard retail FX lot is commonly 100,000 base-currency units,
but this MUST be treated as a provider/broker contract specification,
not silently hard-coded as an authoritative fact for this system.

If contract_size = 100000 GBP per standard lot:

  quote_pnl_jpy =
      price_change
      × contract_size
      × lot_size

  usd_pnl =
      quote_pnl_jpy
      × JPY_to_USD

For BUY:
  price_change = current_price - entry

For SELL:
  price_change = entry - current_price

This formula is only production-safe after contract_size,
lot semantics, and conversion-rate freshness are established.
""")

print("\n"+"="*110)
print("6. PRICE-SEMANTICS AUDIT")
print("="*110)

print("""
For an open BUY:
  entry execution should use an appropriate ask-side/executable price
  current liquidation valuation should use an appropriate bid-side price

For an open SELL:
  entry execution should use an appropriate bid-side/executable price
  current liquidation valuation should use an appropriate ask-side price

A midpoint can be useful for display/reference but must not automatically
be treated as the executable liquidation price.

SL/TP detection must therefore define which side of the market is used.
""")

if isinstance(biquote,dict):
    bid=biquote.get("bid")
    ask=biquote.get("ask")
    mid=biquote.get("mid")
    print("OBSERVED BID:",bid)
    print("OBSERVED ASK:",ask)
    print("OBSERVED MID:",mid)

print("\n"+"="*110)
print("7. GBPJPY / 15m CANDLE REQUIREMENT")
print("="*110)

print("PAIR:",PAIR)
print("TIMEFRAME:",TIMEFRAME)
print("GRANULARITY:",GRANULARITY)
print("""
Required candle record:
  timestamp
  open
  high
  low
  close
  volume where provider supplies it

Required invariant:
  candle timestamps must identify the 15-minute interval.
  The current spot quote and candle timestamps must not be silently
  treated as the same observation.
""")

print("\n"+"="*110)
print("8. PROVIDER ROLE DECISION")
print("="*110)

fresh=False
if isinstance(biquote,dict):
    stale=biquote.get("stale")
    age=biquote.get("quoteAgeSeconds")
    fresh=(stale is False) and (
        not isinstance(age,(int,float)) or age <= 30
    )

print("BIQUOTE CURRENT QUOTE:", "FRESH OBSERVATION" if fresh else "NOT FRESHLY VERIFIED")
print("BIQUOTE BID/ASK:", "AVAILABLE" if isinstance(biquote,dict) and "bid" in biquote and "ask" in biquote else "UNAVAILABLE")
print("BIQUOTE 15m OHLC:", "NOT ESTABLISHED")

print("""
The merge requires a provider capable of supplying or reliably pairing:

  A. current executable quote
  B. GBPJPY 15m OHLC
  C. timestamps
  D. instrument metadata
  E. sufficient freshness

If no single provider supplies all five, the architecture must use
separate market-data roles with explicit timestamp/freshness rules.
""")

print("\n"+"="*110)
print("9. PRODUCTION-SAFETY GATE")
print("="*110)

print("CURRENT PRICE:", "BLOCKED" if not fresh else "OBSERVED FRESH")
print("BID/ASK:", "AVAILABLE" if isinstance(biquote,dict) and "bid" in biquote and "ask" in biquote else "BLOCKED")
print("15m GBPJPY OHLC:", "NOT ESTABLISHED")
print("CONTRACT SIZE:", "NOT ESTABLISHED")
print("LOT SEMANTICS:", "NOT ESTABLISHED")
print("USD CONVERSION:", "AVAILABLE FROM STEP TEN")
print("EXECUTABLE PRICE SEMANTICS:", "DEFINED FOR DESIGN; PROVIDER IMPLEMENTATION PENDING")
print("LIVE P/L:", "BLOCKED")
print("SL/TP MONITOR:", "BLOCKED")
print("TRADE CLOSE:", "BLOCKED")
print("CRT GBPJPY 15m AUTHORITY:", "BLOCKED")

print("\n"+"="*110)
print("STEP ELEVEN FINAL GATE")
print("="*110)

print("SOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")
print("DIRECTION INFERENCE: NO")
print("PENDING SELECTION: NO")
print("HISTORICAL REWRITE: NO")
print("TRADE EXECUTION: NO")
print("FAKE DATA: NO")
print("CONTRACT SIZE HARD-CODED: NO")
print("PRODUCTION MERGE: BLOCKED")

print("\nCAT STAGE A — STEP ELEVEN READ-ONLY AUDIT COMPLETE")
