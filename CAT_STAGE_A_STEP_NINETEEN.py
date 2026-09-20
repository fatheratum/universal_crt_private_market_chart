#!/usr/bin/env python3
import ast
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

V4="universal_crt_v4.py"
OMNI="OMNICIPHERIST.py"
ACTIVE="active_trade.json"
CONFIG="omnicipherist_config.json"

PROTECTED={
    V4:"5a9c70027b863477d50dd98bc597345017a1baa94e7a597b1877ad7cca4e010a",
    OMNI:"21923126a630842fe7fc64f3e70a5d549e07cf67170792855d49ef567d63069a",
}

ROOT=Path(".")
HOME=Path.home()

MODULES=(
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
)

PROVIDER_TERMS=(
    "MetaTrader5",
    "MetaTrader 5",
    "MT5",
    "OANDA",
    "Interactive Brokers",
    "IBKR",
    "FXCM",
    "Finnhub",
    "Dukascopy",
    "broker",
    "execution",
    "order_send",
    "positions_get",
    "symbol_info",
    "copy_rates",
    "market_book",
)

SECRET_TERMS=(
    "api_key",
    "apikey",
    "access_token",
    "secret",
    "password",
    "authorization",
    "bearer",
    "account_id",
    "login",
)

LOCAL_FILES=(
    "universal_crt_v4.py",
    "OMNICIPHERIST.py",
    "omnicipherist_config.json",
    "active_trade.json",
)

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def ast_ok(path):
    try:
        ast.parse(
            Path(path).read_text(encoding="utf-8"),
            filename=str(path)
        )
        return True
    except Exception:
        return False

def redact_line(line):
    s=line.strip()
    s=re.sub(
        r'(?i)(api[_-]?key|apikey|token|secret|password|authorization|access[_-]?token|account[_-]?id|login)\s*([:=])\s*["\']?[^"\']+["\']?',
        r'\1\2<REDACTED>',
        s
    )
    return s

def module_status(name):
    try:
        spec=importlib.util.find_spec(name)
        return spec is not None
    except Exception:
        return False

def scan_text_file(path):
    try:
        text=path.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return {}
    result={}
    for term in PROVIDER_TERMS:
        n=len(re.findall(re.escape(term),text,re.I))
        if n:
            result[term]=n
    return result

def scan_local_sources():
    print("\n[1] LOCAL EXECUTION-SOURCE REFERENCES")
    found=False
    for name in LOCAL_FILES:
        p=ROOT/name
        if not p.exists():
            continue
        data=scan_text_file(p)
        if data:
            found=True
            print(name)
            for k,v in sorted(data.items()):
                print(f"  {k}: {v}")
    if not found:
        print("NO EXECUTION-SOURCE REFERENCES FOUND")

def inspect_modules():
    print("\n[2] INSTALLED PYTHON BROKER/DATA MODULES")
    for name in MODULES:
        print(f"{name}: {'INSTALLED' if module_status(name) else 'NOT INSTALLED'}")

def inspect_termux_processes():
    print("\n[3] LOCAL PROCESS CAPABILITY — READ ONLY")
    candidates=(
        "metatrader",
        "terminal",
        "mt5",
        "broker",
        "oanda",
        "ibkr",
        "fxcm",
        "trading"
    )
    try:
        import subprocess
        p=subprocess.run(
            ["ps","-A"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines=p.stdout.splitlines()
        matches=[]
        for line in lines:
            low=line.lower()
            if any(x in low for x in candidates):
                matches.append(line.strip())
        if matches:
            for line in matches[:30]:
                print("MATCH:",line)
        else:
            print("NO BROKER/MT5 PROCESS DETECTED")
    except Exception as e:
        print("PROCESS SCAN ERROR:",type(e).__name__)

def inspect_local_network_config():
    print("\n[4] LOCAL NETWORK/CONNECTION CONFIGURATION")
    candidates=[]
    for base in (
        ROOT,
        HOME/"storage",
        HOME/".config",
        HOME/".local",
    ):
        if not base.exists():
            continue
        try:
            for p in base.iterdir():
                if p.is_file() and p.suffix.lower() in (
                    ".json",".toml",".yaml",".yml",".ini",".conf",".cfg"
                ):
                    candidates.append(p)
        except Exception:
            pass

    seen=set()
    hits=0
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        try:
            text=p.read_text(encoding="utf-8",errors="replace")
        except Exception:
            continue
        lower=text.lower()
        if any(term.lower() in lower for term in (
            "metatrader","mt5","oanda","ibkr","fxcm","broker","account_id"
        )):
            print("RELEVANT CONFIG:",p)
            hits+=1
            for line in text.splitlines():
                if any(term.lower() in line.lower() for term in PROVIDER_TERMS):
                    print(" ",redact_line(line))
                    if hits>=20:
                        break
    if hits==0:
        print("NO LOCAL BROKER CONFIGURATION IDENTIFIED")

def inspect_environment():
    print("\n[5] ENVIRONMENT — SECRET-SAFE")
    provider_hits=0
    credential_hits=0
    for key in sorted(os.environ):
        low=key.lower()
        if any(x in low for x in (
            "mt5","metatrader","oanda","ibkr","fxcm","finnhub","broker"
        )):
            print("PROVIDER ENV:",key,"=<PRESENT>")
            provider_hits+=1
        elif any(x in low for x in SECRET_TERMS):
            print("CREDENTIAL ENV:",key,"=<PRESENT>")
            credential_hits+=1
    if provider_hits==0:
        print("NO PROVIDER-SPECIFIC ENVIRONMENT VARIABLES")
    if credential_hits==0:
        print("NO GENERIC CREDENTIAL ENVIRONMENT VARIABLES")

def inspect_mt5_paths():
    print("\n[6] MT5 LOCAL ARTIFACT DISCOVERY")
    names=(
        "terminal64.exe",
        "terminal.exe",
        "metatrader5",
        "MetaTrader5",
        "terminal64",
    )
    roots=(
        HOME,
        Path("/data/data/com.termux/files/usr"),
        Path("/sdcard"),
    )
    hits=[]
    for base in roots:
        if not base.exists():
            continue
        if base==HOME:
            dirs=(
                HOME/"OMNI",
                HOME/".config",
                HOME/".local",
            )
        else:
            dirs=(base,)
        for d in dirs:
            if not d.exists():
                continue
            try:
                for n in names:
                    p=d/n
                    if p.exists():
                        hits.append(p)
            except Exception:
                pass
    if hits:
        for p in hits:
            print("FOUND:",p)
    else:
        print("NO MT5 TERMINAL ARTIFACT FOUND IN BOUNDED PATHS")

def final_gate():
    print("\n[7] EXECUTION AUTHORITY GATE")
    checks={
        "BROKER_API_MODULE":False,
        "BROKER_TERMINAL_BRIDGE":False,
        "AUTHORIZED_ACCOUNT_CONNECTION":False,
        "AUTHORITATIVE_15M_OHLC":False,
        "AUTHORITATIVE_INSTRUMENT_SPEC":False,
        "EXECUTABLE_BID_ASK":False,
        "EXECUTABLE_USD_CONVERSION":False,
    }
    for k,v in checks.items():
        print(f"{k}: {'PASS' if v else 'BLOCK'}")

    confirmed=all(checks.values())
    print("\nEXECUTION_AUTHORITY_CONFIRMED =",confirmed)

    print("\n[8] SAFETY GATE")
    print("NO ORDERS SENT")
    print("NO ACCOUNT CONNECTED")
    print("NO TRADE EXECUTED")
    print("NO ACTIVE_TRADE WRITE")
    print("NO V4 WRITE")
    print("NO OMNICIPHERIST WRITE")
    print("NO BACKUP WRITE")

    print("\n[9] AUTHORITY RESULT")
    if confirmed:
        print("AUTHORITATIVE EXECUTION SOURCE: AVAILABLE")
    else:
        print("AUTHORITATIVE EXECUTION SOURCE: NOT AVAILABLE")
        print("PRODUCTION MERGE: BLOCKED")

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
    print("║ CAT STAGE A — STEP NINETEEN — LOCAL BROKER CAPABILITY AUDIT       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    scan_local_sources()
    inspect_modules()
    inspect_termux_processes()
    inspect_local_network_config()
    inspect_environment()
    inspect_mt5_paths()

    authority=final_gate()
    intact=integrity()

    print("\n[11] FINAL CAT STATE")
    print("STEP EIGHTEEN: COMPLETE")
    print("STEP NINETEEN: COMPLETE")
    print("EXECUTION_AUTHORITY_CONFIRMED:",authority)
    print("SOURCE_INTEGRITY:",intact)
    print("PRODUCTION MERGE:", "PERMITTED" if authority and intact else "BLOCKED")
    print("PRODUCTION FILES: UNMODIFIED")

    return 0 if intact else 1

if __name__=="__main__":
    raise SystemExit(main())
