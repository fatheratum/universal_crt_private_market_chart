#!/usr/bin/env python3
import ast
import hashlib
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime,timezone

V4="universal_crt_v4.py"
OMNI="OMNICIPHERIST.py"
CONFIG="omnicipherist_config.json"
ACTIVE="active_trade.json"

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(65536),b""):
            h.update(block)
    return h.hexdigest()

def ast_ok(path):
    try:
        ast.parse(open(path,encoding="utf-8").read(),filename=path)
        return True,None
    except Exception as e:
        return False,str(e)

def redact(value):
    s=str(value)
    patterns=[
        r'(?i)(api[_-]?key|token|secret|password|authorization|access[_-]?token)\s*[:=]\s*[^\s,}"\'&]+',
        r'(?i)bearer\s+[A-Za-z0-9._~+/=-]+',
    ]
    for p in patterns:
        s=re.sub(p,lambda m:m.group(0).split(":")[0].split("=")[0]+"=<REDACTED>",s)
    return s

def get_json(url,timeout=8):
    req=urllib.request.Request(
        url,
        headers={"User-Agent":"CAT-Stage-A-Step-Sixteen/1.0","Accept":"application/json"}
    )
    ctx=ssl.create_default_context()
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
        raw=r.read()
        return r.status,json.loads(raw.decode("utf-8")),dict(r.headers)

def valid_number(x):
    return isinstance(x,(int,float)) and x==x

def evaluate(fields):
    checks={
        "BID_ASK_VALID":fields["bid_valid"] and fields["ask_valid"],
        "MARKET_STATE_KNOWN":fields["market_state_known"],
        "OHLC_15M_VALID":fields["ohlc_15m_valid"],
        "INSTRUMENT_SPEC_VERIFIED":fields["instrument_spec_verified"],
        "TIMESTAMP_VALID":fields["timestamp_valid"],
        "PROVIDER_IDENTITY_KNOWN":fields["provider_identity_known"],
        "ACCOUNT_CURRENCY_CONVERSION_VALID":fields["conversion_valid"],
    }
    return checks,all(checks.values())

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║ CAT STAGE A — STEP SIXTEEN — AUTHORITY DISCOVERY                  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    print("\n[1] SOURCE INTEGRITY")
    for path in (V4,OMNI):
        ok,err=ast_ok(path)
        print(f"{path}: AST={'PASS' if ok else 'FAIL'}")
        if err:
            print(redact(err))
        print(f"SHA256: {sha256(path)}")

    print("\n[2] CONFIGURATION — READ ONLY")
    try:
        cfg=json.load(open(CONFIG,encoding="utf-8"))
        print("PAIR:",cfg.get("trading_pair"))
        print("TIMEFRAME:",cfg.get("timeframe"))
        print("ACCOUNT BALANCE:",cfg.get("account_balance"))
    except Exception as e:
        print("CONFIG ERROR:",redact(e))

    fields={
        "bid_valid":False,
        "ask_valid":False,
        "market_state_known":False,
        "ohlc_15m_valid":False,
        "instrument_spec_verified":False,
        "timestamp_valid":False,
        "provider_identity_known":False,
        "conversion_valid":False,
    }

    print("\n[3] BIQUOTE — CURRENT QUOTE DISCOVERY")
    try:
        status,data,headers=get_json("https://biquote.io/api/GBPJPY")
        print("HTTP:",status)
        if isinstance(data,dict):
            bid=data.get("bid")
            ask=data.get("ask")
            stale=data.get("stale")
            market_state=data.get("marketState")
            timestamp=data.get("timestamp")
            provider=data.get("source")
            symbol=data.get("symbol")

            print("PROVIDER:",redact(provider))
            print("SYMBOL:",symbol)
            print("BID:",bid)
            print("ASK:",ask)
            print("STALE:",stale)
            print("MARKET STATE:",market_state)
            print("TIMESTAMP:",timestamp)

            fields["bid_valid"]=valid_number(bid) and bid>0
            fields["ask_valid"]=valid_number(ask) and ask>0 and ask>=bid
            fields["market_state_known"]=market_state is not None
            fields["timestamp_valid"]=timestamp is not None
            fields["provider_identity_known"]=provider is not None

            if stale is True or str(market_state).lower() not in ("open","opened","live"):
                print("QUOTE AUTHORITY: REFERENCE/STALE — NOT EXECUTABLE")
        else:
            print("INVALID JSON OBJECT")
    except Exception as e:
        print("BIQUOTE ERROR:",redact(e))

    print("\n[4] GBPJPY 15-MIN OHLC AUTHORITY")
    print("Required: authoritative provider-supplied 15-minute OHLC.")
    print("Synthetic candles: FORBIDDEN")
    print("Hard-coded candles: FORBIDDEN")
    print("BiQuote spot quote alone: INSUFFICIENT")
    print("RESULT: NOT ESTABLISHED")

    print("\n[5] INSTRUMENT SPECIFICATION")
    print("Required fields:")
    for item in (
        "pip_size","tick_size","price_precision","contract_size",
        "lot_unit","minimum_lot","maximum_lot","lot_step",
        "margin_currency","provider_symbol"
    ):
        print(f"  {item}: NOT VERIFIED")

    print("Emulator/reference specifications are explicitly excluded.")
    print("RESULT: NOT ESTABLISHED")

    print("\n[6] GBPJPY → USD CONVERSION")
    try:
        status,data,headers=get_json("https://open.er-api.com/v6/latest/JPY")
        rate=data.get("rates",{}).get("USD") if isinstance(data,dict) else None
        print("ER-API HTTP:",status)
        print("JPY→USD:",rate)
        if valid_number(rate) and rate>0:
            print("CLASSIFICATION: REFERENCE ONLY")
        else:
            print("CLASSIFICATION: INVALID")
    except Exception as e:
        print("ER-API ERROR:",redact(e))

    print("\n[7] AUTHORITY EVALUATION")
    checks,confirmed=evaluate(fields)
    for name,result in checks.items():
        print(f"{name}: {'PASS' if result else 'BLOCK'}")

    print("\nAUTHORITY_CONFIRMED =",confirmed)

    print("\n[8] SAFETY GATE")
    if not confirmed:
        print("MARKET AUTHORITY: NOT ESTABLISHED")
        print("LIVE TRADE ACTIVATION: BLOCKED")
        print("LIVE P/L: BLOCKED")
        print("SL/TP AUTO-CLOSE: BLOCKED")
        print("AUTO WIN/LOSS: BLOCKED")
        print("PRODUCTION SNAPSHOT: BLOCKED")
        print("V4 INJECTION: BLOCKED")
    else:
        print("AUTHORITY LAYER SATISFIED — NO PRODUCTION CHANGE PERMITTED BY THIS STEP")

    print("\n[9] PRODUCTION INTEGRITY")
    print(f"{V4}: READ ONLY")
    print(f"{OMNI}: READ ONLY")
    print(f"{ACTIVE}: READ ONLY")
    print("BACKUPS: READ ONLY")
    print("CAT STEP SIXTEEN: COMPLETE")

if __name__=="__main__":
    main()
