#!/usr/bin/env python3
import ast
import hashlib
import json
import re
import ssl
import urllib.request
from pathlib import Path
from datetime import datetime,timezone

V4="universal_crt_v4.py"
OMNI="OMNICIPHERIST.py"
ACTIVE="active_trade.json"
CONFIG="omnicipherist_config.json"

PROTECTED={
    V4:"5a9c70027b863477d50dd98bc597345017a1baa94e7a597b1877ad7cca4e010a",
    OMNI:"21923126a630842fe7fc64f3e70a5d549e07cf67170792855d49ef567d63069a",
}

ROOT=Path(".")
LOCAL_SCAN_FILES=(
    "universal_crt_v4.py",
    "OMNICIPHERIST.py",
    "omnicipherist_config.json",
    "active_trade.json",
    "CAT_STAGE_A_STEP_SIXTEEN.py",
    "CAT_STAGE_A_STEP_SEVENTEEN.py",
)

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def ast_ok(path):
    try:
        ast.parse(Path(path).read_text(encoding="utf-8"),filename=str(path))
        return True
    except Exception:
        return False

def get_json(url,timeout=8):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":"CAT-Stage-A-Step-Eighteen/1.0",
            "Accept":"application/json"
        }
    )
    ctx=ssl.create_default_context()
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
        raw=r.read()
        return r.status,json.loads(raw.decode("utf-8")),dict(r.headers)

def number(x):
    return isinstance(x,(int,float)) and x==x

def scan_local():
    print("\n[1] LOCAL PROVIDER DISCOVERY — READ ONLY")
    terms=(
        "oanda","metatrader","mt5","forex","fxcm","interactive brokers",
        "alpaca","twelvedata","alphavantage","finnhub","dukascopy",
        "biquote","gbpjpy","candles","ohlc","contract_size",
        "pip_size","tick_size","lot_step","margin_currency"
    )
    found={}
    for name in LOCAL_SCAN_FILES:
        p=ROOT/name
        if not p.exists():
            continue
        try:
            text=p.read_text(encoding="utf-8",errors="replace")
        except Exception:
            continue
        for term in terms:
            n=len(re.findall(re.escape(term),text,re.I))
            if n:
                found.setdefault(name,{})[term]=n
    if not found:
        print("NO LOCAL PROVIDER REFERENCES FOUND")
    else:
        for name,data in found.items():
            print(name)
            for term,n in sorted(data.items()):
                print(f"  {term}: {n}")

def test_biquote():
    print("\n[2] BIQUOTE — CURRENT QUOTE")
    try:
        status,data,_=get_json("https://biquote.io/api/GBPJPY")
        print("HTTP:",status)
        if isinstance(data,dict):
            for k in ("source","symbol","bid","ask","mid","stale","marketState","timestamp"):
                if k in data:
                    print(f"{k.upper()}:",data[k])
            print("CLASSIFICATION: REFERENCE ONLY IF STALE/CLOSED")
        else:
            print("INVALID JSON OBJECT")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def test_frankfurter():
    print("\n[3] FRANKFURTER — REFERENCE FX")
    try:
        status,data,_=get_json(
            "https://api.frankfurter.app/latest?from=GBP&to=JPY,USD"
        )
        print("HTTP:",status)
        if isinstance(data,dict):
            print("DATE:",data.get("date"))
            print("RATES:",data.get("rates"))
        print("CLASSIFICATION: REFERENCE ONLY")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def test_twelvedata():
    print("\n[4] TWELVEDATA — DISCOVERY")
    url="https://api.twelvedata.com/time_series?symbol=GBP/JPY&interval=15min&outputsize=5"
    try:
        status,data,_=get_json(url)
        print("HTTP:",status)
        if isinstance(data,dict):
            if data.get("status")=="error":
                print("STATUS: ERROR")
                print("MESSAGE:",data.get("message"))
            else:
                print("META:",data.get("meta"))
                values=data.get("values")
                print("15M_ROWS:",len(values) if isinstance(values,list) else 0)
        print("CLASSIFICATION: NOT AUTHORITY WITHOUT VALID CREDENTIAL/TERMS")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def test_alphavantage():
    print("\n[5] ALPHAVANTAGE — DISCOVERY")
    url="https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=GBP&to_symbol=JPY&interval=15min&outputsize=compact"
    try:
        status,data,_=get_json(url)
        print("HTTP:",status)
        if isinstance(data,dict):
            if "Error Message" in data:
                print("ERROR MESSAGE:",data["Error Message"])
            elif "Note" in data:
                print("NOTE:",data["Note"])
            elif "Information" in data:
                print("INFORMATION:",data["Information"])
            else:
                print("TIME SERIES KEYS:",[
                    k for k in data.keys() if "Time Series" in k
                ])
        print("CLASSIFICATION: NOT AUTHORITY WITHOUT VALIDATED ACCESS")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def test_coinbase():
    print("\n[6] COINBASE — GBPJPY COMPATIBILITY")
    url="https://api.exchange.coinbase.com/products/GBP-JPY/candles?granularity=900"
    try:
        status,data,_=get_json(url)
        print("HTTP:",status)
        print("ROWS:",len(data) if isinstance(data,list) else 0)
        print("CLASSIFICATION: INVALID FOR GBPJPY IF PRODUCT UNAVAILABLE")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def inspect_config():
    print("\n[7] CONFIGURATION — READ ONLY")
    try:
        cfg=json.loads(Path(CONFIG).read_text(encoding="utf-8"))
        print("PAIR:",cfg.get("trading_pair"))
        print("TIMEFRAME:",cfg.get("timeframe"))
        print("ACCOUNT CURRENCY: USD")
    except Exception as e:
        print("ERROR:",type(e).__name__,str(e))

def final_gate():
    print("\n[8] AUTHORITY RESOLUTION")
    checks={
        "GBPJPY_BID_ASK":False,
        "GBPJPY_15M_OHLC":False,
        "TIMESTAMP_AND_AGE":False,
        "MARKET_STATE":False,
        "INSTRUMENT_SPECIFICATION":False,
        "PROVIDER_SYMBOL":False,
        "PROVIDER_TIMEZONE":False,
        "EXECUTABLE_QUOTE_STATUS":False,
        "GBPJPY_TO_USD_EXECUTABLE_CONVERSION":False,
    }
    for k,v in checks.items():
        print(f"{k}: {'PASS' if v else 'BLOCK'}")
    confirmed=all(checks.values())
    print("\nAUTHORITY_CONFIRMED =",confirmed)

    print("\n[9] SAFETY GATE")
    print("V4 INJECTION: BLOCKED")
    print("OMNICIPHERIST MODIFICATION: BLOCKED")
    print("ACTIVE_TRADE MODIFICATION: BLOCKED")
    print("LIVE TRADE ACTIVATION: BLOCKED")
    print("LIVE P/L: BLOCKED")
    print("SL/TP AUTO-CLOSE: BLOCKED")
    print("AUTO WIN/LOSS: BLOCKED")
    print("PRODUCTION SNAPSHOT: BLOCKED")

    return confirmed

def integrity():
    print("\n[10] PROTECTED INTEGRITY")
    ok=True
    for path,want in PROTECTED.items():
        actual=sha256(path)
        passed=actual==want and ast_ok(path)
        print(f"{path}: {'PASS' if passed else 'FAIL'}")
        print("  SHA256:",actual)
        ok &= passed
    return ok

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║ CAT STAGE A — STEP EIGHTEEN — AUTHORITY SOURCE DISCOVERY          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    scan_local()
    test_biquote()
    test_frankfurter()
    test_twelvedata()
    test_alphavantage()
    test_coinbase()
    inspect_config()
    confirmed=final_gate()
    intact=integrity()
    print("\n[11] FINAL CAT STATE")
    print("LOCAL AUTHORITY DISCOVERY: COMPLETE")
    print("EXTERNAL AUTHORITY DISCOVERY: COMPLETE")
    print("AUTHORITY_CONFIRMED:",confirmed)
    print("SOURCE_INTEGRITY:",intact)
    print("PRODUCTION MERGE:", "PERMITTED" if confirmed and intact else "BLOCKED")
    print("PRODUCTION FILES: READ ONLY")
    print("CAT STEP EIGHTEEN: COMPLETE")
    return 0 if intact else 1

if __name__=="__main__":
    raise SystemExit(main())
