from pathlib import Path
import json
import time
import urllib.request
import urllib.parse
import ssl
import socket

PAIR="GBPJPY"
TIMEFRAME="15m"
GRANULARITY=900
ACCOUNT_CURRENCY="USD"

print("CAT STAGE A — STEP TEN")
print("LIVE PROVIDER RESPONSE + GBPJPY INSTRUMENT SPECIFICATION AUDIT")
print("MODE: READ ONLY")
print("TARGET: GBPJPY / 15m / USD ACCOUNT")
print("SOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

ctx=ssl.create_default_context()

def http_get(url,timeout=8):
    started=time.time()
    try:
        req=urllib.request.Request(
            url,
            headers={
                "User-Agent":"CAT-Stage-A-Step-Ten/1.0",
                "Accept":"application/json"
            }
        )
        with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
            raw=r.read()
            elapsed=time.time()-started
            return {
                "ok":True,
                "status":getattr(r,"status",None),
                "headers":dict(r.headers),
                "body":raw.decode("utf-8","replace"),
                "elapsed":elapsed
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
        return json.loads(body),None
    except Exception as e:
        return None,f"{type(e).__name__}: {e}"

def inspect_keys(obj):
    if isinstance(obj,dict):
        return sorted(obj.keys())
    if isinstance(obj,list) and obj and isinstance(obj[0],dict):
        return sorted(obj[0].keys())
    return []

def show_result(label,result):
    print(f"\n[{label}]")
    print("HTTP:", "SUCCESS" if result["ok"] else "FAILED")
    if result["status"] is not None:
        print("STATUS:",result["status"])
    print("ELAPSED:",f'{result["elapsed"]:.3f}s')
    if not result["ok"]:
        print("ERROR:",result["error"])
        return None
    data,error=parse_json(result["body"])
    if error:
        print("JSON:",f"INVALID ({error})")
        print("BODY:",result["body"][:1000])
        return None
    print("JSON: VALID")
    print("TOP LEVEL TYPE:",type(data).__name__)
    print("KEYS:",inspect_keys(data))
    return data

print("\n"+"="*110)
print("1. BIQUOTE LIVE GBPJPY TEST")
print("="*110)

biquote_url=f"https://biquote.io/api/{PAIR}"
biquote=http_get(biquote_url)
biquote_data=show_result("biquote.io/api/GBPJPY",biquote)

if isinstance(biquote_data,dict):
    print("\nBIQUOTE MARKET FIELDS")
    for key in ["bid","ask","mid","stale","timestamp","time","symbol","pair"]:
        print(f"{key:12}:",biquote_data.get(key,"<ABSENT>"))

    numeric=[]
    for key in ["bid","ask","mid"]:
        value=biquote_data.get(key)
        try:
            numeric.append((key,float(value)))
        except Exception:
            pass

    if numeric:
        print("\nNUMERIC PRICE FIELDS:")
        for key,value in numeric:
            print(f"{key:12}: {value:.10f}")

    if "bid" in biquote_data and "ask" in biquote_data:
        try:
            bid=float(biquote_data["bid"])
            ask=float(biquote_data["ask"])
            print("SPREAD:",f"{ask-bid:.10f}")
        except Exception:
            print("SPREAD: UNCALCULABLE")

    stale=biquote_data.get("stale","<ABSENT>")
    print("STALE FIELD:",stale)

print("\n"+"="*110)
print("2. ER-API GBPJPY CONVERSION TEST")
print("="*110)

er_url="https://open.er-api.com/v6/latest/USD"
er=http_get(er_url)
er_data=show_result("open.er-api.com/v6/latest/USD",er)

if isinstance(er_data,dict):
    rates=er_data.get("rates")
    print("\nRATE OBJECT:", "PRESENT" if isinstance(rates,dict) else "ABSENT")

    if isinstance(rates,dict):
        for currency in ["GBP","JPY","USD"]:
            print(f"USD->{currency:3}:",rates.get(currency,"<ABSENT>"))

        jpy=rates.get("JPY")
        usd=rates.get("USD")

        try:
            jpy=float(jpy)
            usd=float(usd)
            print("USD→JPY:",jpy)
            print("JPY→USD:",1.0/jpy)
        except Exception:
            print("JPY→USD: UNCALCULABLE")

print("\n"+"="*110)
print("3. COINBASE GBP-JPY 15m TEST")
print("="*110)

coinbase_url=(
    "https://api.exchange.coinbase.com/products/"
    +urllib.parse.quote("GBP-JPY",safe="")
    +"/candles?granularity=900"
)

coinbase=http_get(coinbase_url)
coinbase_data=show_result("Coinbase GBP-JPY candles",coinbase)

if isinstance(coinbase_data,list):
    print("\nCOINBASE CANDLE COUNT:",len(coinbase_data))

    if coinbase_data:
        print("FIRST RAW CANDLE:",coinbase_data[0])

        valid=0
        for row in coinbase_data:
            if isinstance(row,list) and len(row)>=6:
                try:
                    [float(x) for x in row[:6]]
                    valid+=1
                except Exception:
                    pass

        print("VALID OHLCV ROWS:",valid)

print("\n"+"="*110)
print("4. COINBASE PRODUCT METADATA TEST")
print("="*110)

product_url="https://api.exchange.coinbase.com/products/GBP-JPY"
product=http_get(product_url)
product_data=show_result("Coinbase GBP-JPY product metadata",product)

if isinstance(product_data,dict):
    print("\nPRODUCT FIELDS")
    for key in [
        "id","base_currency","quote_currency",
        "base_min_size","base_max_size",
        "quote_increment","base_increment",
        "status","trading_disabled"
    ]:
        print(f"{key:20}:",product_data.get(key,"<ABSENT>"))

print("\n"+"="*110)
print("5. GBPJPY INSTRUMENT-SPECIFICATION TEST")
print("="*110)

print("PAIR:",PAIR)
print("BASE CURRENCY: GBP")
print("QUOTE CURRENCY: JPY")
print("ACCOUNT CURRENCY:",ACCOUNT_CURRENCY)
print("STANDARD FX PIP SIZE: 0.01")
print("STANDARD JPY PRICE DECIMAL: 0.01")
print("PIP SIZE SOURCE: FX convention; provider-specific tick precision still requires verification")
print("CONTRACT SIZE: NOT ESTABLISHED FROM CURRENT ENGINE")
print("ACCOUNT-CURRENCY P/L CONVERSION: REQUIRES LIVE JPY/USD RATE")

if isinstance(product_data,dict):
    qi=product_data.get("quote_increment")
    bi=product_data.get("base_increment")
    if qi is not None:
        print("PROVIDER QUOTE INCREMENT:",qi)
    if bi is not None:
        print("PROVIDER BASE INCREMENT:",bi)

print("\n"+"="*110)
print("6. PROVIDER ROLE MATRIX")
print("="*110)

print("BIQUOTE")
print("  Spot/current price:", "OBSERVED" if isinstance(biquote_data,dict) else "UNVERIFIED")
print("  Bid/ask:", "OBSERVED" if isinstance(biquote_data,dict) and "bid" in biquote_data and "ask" in biquote_data else "NOT VERIFIED")
print("  15m candles: NOT ESTABLISHED")

print("\nER-API")
print("  Currency conversion:", "OBSERVED" if isinstance(er_data,dict) and isinstance(er_data.get("rates"),dict) else "UNVERIFIED")
print("  GBPJPY spot feed: NOT ITS PRIMARY ROLE")

print("\nCOINBASE")
print("  GBP-JPY candles:", "OBSERVED RESPONSE" if isinstance(coinbase_data,list) else "NOT ESTABLISHED")
print("  GBP-JPY product:", "OBSERVED RESPONSE" if isinstance(product_data,dict) else "NOT ESTABLISHED")

print("\n"+"="*110)
print("7. LIVE P/L FORMULA SAFETY")
print("="*110)

print("""
For a GBPJPY position quoted in JPY, monetary P/L cannot safely be
derived from the existing universal PIP_VALUE=10 constant.

For a standard FX contract:

price_change = current_price - entry_price

For BUY:
    favorable price_change > 0

For SELL:
    favorable price_change < 0

P/L in quote currency depends on:
    price_change
    × contract_size
    × lot_size

For GBPJPY:
    quote currency = JPY

Therefore USD P/L requires:
    JPY P/L × (JPY→USD conversion rate)

The exact contract size must be established before production
monitoring is implemented.
""")

print("\n"+"="*110)
print("8. AUTHORITATIVE MARKET-DATA GATE")
print("="*110)

biquote_live=(
    isinstance(biquote_data,dict)
    and (
        "mid" in biquote_data
        or ("bid" in biquote_data and "ask" in biquote_data)
    )
)

coinbase_candles=isinstance(coinbase_data,list) and len(coinbase_data)>0

print("BIQUOTE CURRENT PRICE RESPONSE:", "PASS" if biquote_live else "UNVERIFIED/FAIL")
print("COINBASE GBP-JPY 15m CANDLES:", "PASS" if coinbase_candles else "UNVERIFIED/FAIL")
print("INSTRUMENT CONTRACT SIZE:", "BLOCKED")
print("USD CONVERSION:", "PASS" if isinstance(er_data,dict) and isinstance(er_data.get("rates"),dict) and "JPY" in er_data.get("rates",{}) else "UNVERIFIED/FAIL")
print("COMPLETE AUTHORITATIVE SINGLE PROVIDER:", "NOT ESTABLISHED")

print("\n"+"="*110)
print("STEP TEN FINAL GATE")
print("="*110)

print("SOURCE FILES MODIFIED: NO")
print("ACTIVE_TRADE.JSON MODIFIED: NO")
print("BACKUPS MODIFIED: NO")
print("DIRECTION INFERENCE: NO")
print("TRADE EXECUTION: NO")
print("FAKE MARKET DATA: NO")

if biquote_live and coinbase_candles:
    print("PROVIDER RESPONSE TEST: OBSERVED DATA AVAILABLE")
else:
    print("PROVIDER RESPONSE TEST: INCOMPLETE")

print("INSTRUMENT SPECIFICATION: PARTIALLY ESTABLISHED")
print("CONTRACT SIZE: NOT ESTABLISHED")
print("PRODUCTION P/L ENGINE: BLOCKED")
print("PRODUCTION SL/TP MONITOR: BLOCKED")
print("MERGE GATE: BLOCKED UNTIL CONTRACT/P/L MODEL IS ESTABLISHED")

print("\nCAT STAGE A — STEP TEN READ-ONLY AUDIT COMPLETE")
