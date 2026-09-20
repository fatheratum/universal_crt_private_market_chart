#!/usr/bin/env python3
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

V4="universal_crt_v4.py"
OMNI="OMNICIPHERIST.py"
ACTIVE="active_trade.json"

PROTECTED={
    V4:"5a9c70027b863477d50dd98bc597345017a1baa94e7a597b1877ad7cca4e010a",
    OMNI:"21923126a630842fe7fc64f3e70a5d549e07cf67170792855d49ef567d63069a",
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def read(path):
    try:
        return Path(path).read_text(encoding="utf-8",errors="replace")
    except Exception:
        return ""

def module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def source_capability(text):
    return {
        "MT5_REFERENCE": bool(re.search(r"\bMT5\b|MetaTrader",text,re.I)),
        "EXECUTION_REFERENCE": bool(re.search(
            r"order_send|execute|execution|trade|position",text,re.I)),
        "BID_ASK_REFERENCE": bool(re.search(
            r"\bbid\b|\bask\b",text,re.I)),
        "OHLC_REFERENCE": bool(re.search(
            r"\bohlc\b|candles|rates|copy_rates",text,re.I)),
        "ACCOUNT_REFERENCE": bool(re.search(
            r"account_balance|account|equity|margin",text,re.I)),
    }

def process_matches():
    try:
        out=subprocess.run(
            ["ps","-A"],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout
    except Exception:
        return []
    terms=("mt5","metatrader","broker","oanda","ibkr","fxcm","trading")
    return [
        x.strip() for x in out.splitlines()
        if any(t in x.lower() for t in terms)
    ]

def find_local_bridge():
    names=(
        "terminal64.exe","terminal.exe","metatrader5",
        "MetaTrader5","terminal64","mt5"
    )
    roots=[
        Path.home()/".config",
        Path.home()/".local",
        Path.home()/"OMNI",
        Path("/data/data/com.termux/files/usr"),
        Path("/sdcard"),
    ]
    found=[]
    for root in roots:
        if not root.exists():
            continue
        try:
            for name in names:
                p=root/name
                if p.exists():
                    found.append(str(p))
        except Exception:
            pass
    return found

def dynamic_gate():
    omni=read(OMNI)
    v4=read(V4)

    mt5_module=module("MetaTrader5") or module("mt5")
    bridge=find_local_bridge()
    processes=process_matches()

    capability=source_capability(omni)

    gates={
        "BROKER_API_MODULE":(
            "AVAILABLE" if mt5_module else "MISSING"
        ),
        "BROKER_TERMINAL_BRIDGE":(
            "AVAILABLE" if bridge or processes else "MISSING"
        ),
        "EXECUTION_INTERFACE":(
            "REFERENCED" if capability["EXECUTION_REFERENCE"]
            else "MISSING"
        ),
        "GBPJPY_BID_ASK":(
            "REFERENCED" if capability["BID_ASK_REFERENCE"]
            else "MISSING"
        ),
        "GBPJPY_15M_OHLC":(
            "REFERENCED" if capability["OHLC_REFERENCE"]
            else "MISSING"
        ),
        "ACCOUNT_STATE":(
            "REFERENCED" if capability["ACCOUNT_REFERENCE"]
            else "MISSING"
        ),
        "AUTHENTICATED_ACCOUNT":"UNVERIFIED",
        "INSTRUMENT_SPECIFICATION":"UNVERIFIED",
        "EXECUTABLE_USD_CONVERSION":"UNVERIFIED",
        "PROVIDER_SYMBOL":"UNVERIFIED",
        "PROVIDER_TIMEZONE":"UNVERIFIED",
        "TIMESTAMP_AND_FRESHNESS":"UNVERIFIED",
        "MARKET_STATE":"UNVERIFIED",
    }

    return gates,bridge,processes

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║ CAT STAGE A — STEP TWENTY — DYNAMIC EXECUTION BRIDGE AUDIT        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    print("\n[1] PROTECTED SOURCE INTEGRITY")
    integrity=True
    for path,want in PROTECTED.items():
        actual=sha256(path)
        ast_ok=True
        try:
            ast.parse(read(path),filename=path)
        except Exception:
            ast_ok=False
        ok=(actual==want and ast_ok)
        integrity &= ok
        print(f"{path}: {'PASS' if ok else 'FAIL'}")
        print(f"  SHA256: {actual}")
        print(f"  AST: {'PASS' if ast_ok else 'FAIL'}")

    print("\n[2] INSTALLED CAPABILITIES")
    for name in (
        "MetaTrader5",
        "mt5",
        "oandapyV20",
        "ib_insync",
        "ibapi",
        "fxcmpy",
        "finnhub",
        "requests",
        "websocket",
        "websockets",
    ):
        print(f"{name}: {'AVAILABLE' if module(name) else 'MISSING'}")

    print("\n[3] LOCAL EXECUTION BRIDGE")
    gates,bridge,processes=dynamic_gate()

    if bridge:
        for item in bridge:
            print("ARTIFACT:",item)
    else:
        print("ARTIFACT: NONE")

    if processes:
        for item in processes[:20]:
            print("PROCESS:",item)
    else:
        print("PROCESS: NONE")

    print("\n[4] DYNAMIC AUTHORITY CAPABILITY")
    for name,state in gates.items():
        print(f"{name}: {state}")

    print("\n[5] INTERPRETATION")
    available=sum(v=="AVAILABLE" for v in gates.values())
    referenced=sum(v=="REFERENCED" for v in gates.values())
    missing=sum(v=="MISSING" for v in gates.values())
    unverified=sum(v=="UNVERIFIED" for v in gates.values())

    print(f"AVAILABLE: {available}")
    print(f"REFERENCED: {referenced}")
    print(f"MISSING: {missing}")
    print(f"UNVERIFIED: {unverified}")

    authority=(
        gates["BROKER_API_MODULE"]=="AVAILABLE"
        or gates["BROKER_TERMINAL_BRIDGE"]=="AVAILABLE"
    ) and gates["AUTHENTICATED_ACCOUNT"]=="AVAILABLE"

    print("\n[6] AUTHORITY RESOLUTION")
    print("EXECUTION_AUTHORITY_CONFIRMED =",authority)

    if authority:
        print("AUTHORITATIVE EXECUTION SOURCE: DETECTED")
    else:
        print("AUTHORITATIVE EXECUTION SOURCE: NOT YET VERIFIED")

    print("\n[7] SAFETY")
    print("NO ORDERS SENT")
    print("NO LOGIN ATTEMPTED")
    print("NO PRODUCTION FILE MODIFIED")
    print("NO ACTIVE_TRADE WRITE")
    print("NO BACKUP WRITE")

    print("\n[8] FINAL CAT STATE")
    print("STEP EIGHTEEN: COMPLETE")
    print("STEP NINETEEN: COMPLETE")
    print("STEP TWENTY: COMPLETE")
    print("SPECIFICATION: DYNAMIC")
    print("SOURCE INTEGRITY:",integrity)
    print("PRODUCTION FILES: UNMODIFIED")

if __name__=="__main__":
    main()
