#!/usr/bin/env python3
import ast
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT=Path.cwd()
CRT=ROOT/"universal_crt_v4.py"
OMNI=ROOT/"OMNICIPHERIST.py"
ACTIVE=ROOT/"active_trade.json"
BACKUP_DIR=ROOT/"backups"

PROTECTED=[
    CRT,
    OMNI,
    ACTIVE,
    BACKUP_DIR/"universal_crt_v4.py.BEFORE_OMNI_MERGE",
    BACKUP_DIR/"OMNICIPHERIST.py.BEFORE_OMNI_MERGE",
]

KEYWORDS=[
    "GBPJPY","GBP/JPY","GBP-JPY",
    "contract_size","contractSize","contract_units",
    "lot_size","lotSize","min_lot","minimum_lot",
    "max_lot","maximum_lot","lot_step",
    "tick_size","tickSize","digits","precision",
    "margin_currency","marginCurrency",
    "pip_size","pipSize","account_currency",
    "accountCurrency","bid","ask","ohlc","candles",
    "15m","15min","900"
]

PROVIDERS={
    "alpaca":"ALPACA",
    "oanda":"OANDA",
    "interactive brokers":"INTERACTIVE BROKERS",
    "ib_insync":"INTERACTIVE BROKERS",
    "metatrader":"METATRADER",
    "metatrader5":"METATRADER 5",
    "mt5":"METATRADER 5",
    "ctrader":"CTRADER",
    "fxcm":"FXCM",
    "dukascopy":"DUKASCOPY",
    "tradier":"TRADIER",
    "twelvedata":"TWELVE DATA",
    "alpha vantage":"ALPHA VANTAGE",
    "alphavantage":"ALPHA VANTAGE",
    "finnhub":"FINNHUB",
    "polygon":"POLYGON",
    "coinbase":"COINBASE",
    "coingecko":"COINGECKO",
    "biquote":"BIQUOTE",
    "frankfurter":"FRANKFURTER",
    "yfinance":"YAHOO FINANCE",
}

SECRET_PATTERNS=[
    r"(?i)(api[_-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9_.\-]{8,})",
    r"(?i)(secret[_-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9_.\-]{8,})",
    r"(?i)(access[_-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_.\-]{8,})",
    r"(?i)(auth[_-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_.\-]{8,})",
    r"(?i)(password)\s*[:=]\s*['\"]?([^\s'\"]{6,})",
]

def sha(path):
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ast_ok(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except Exception as e:
        print(f"AST FAILURE {path.name}: {e}")
        return False

def redact(text):
    out=text
    for pattern in SECRET_PATTERNS:
        out=re.sub(pattern,lambda m:f"{m.group(1)}=<REDACTED>",out)
    return out

def classify(text):
    low=text.lower()
    labels=[]

    providers=[]
    for needle,name in PROVIDERS.items():
        if needle in low and name not in providers:
            providers.append(name)

    if providers:
        labels.append("PROVIDER="+",".join(providers))

    if any(x in low for x in [
        "contract_size","contractsize","contract_units",
        "lot_size","lotsize","min_lot","minimum_lot",
        "max_lot","maximum_lot","lot_step"
    ]):
        labels.append("INSTRUMENT_SPEC_CANDIDATE")

    if any(x in low for x in ["bid","ask","spread","quote"]):
        labels.append("EXECUTION_QUOTE_CANDIDATE")

    if any(x in low for x in ["ohlc","candles"]):
        labels.append("OHLC_CANDIDATE")

    if "frankfurter" in low:
        labels.append("REFERENCE_RATE_CANDIDATE")

    if "pip_size" in low or "pipsize" in low:
        labels.append("PIP_SPEC_CANDIDATE")

    if "margin_currency" in low or "margincurrency" in low:
        labels.append("MARGIN_SPEC_CANDIDATE")

    return labels or ["UNCLASSIFIED"]

def scan_file(path):
    try:
        text=path.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return False

    hits=[]
    for n,line in enumerate(text.splitlines(),1):
        if any(k.lower() in line.lower() for k in KEYWORDS):
            hits.append((n,redact(line.strip())))

    if not hits:
        return False

    print(f"\nFILE: {path}")
    print("CLASSIFICATION:",", ".join(classify(text)))

    for n,line in hits[:60]:
        print(f"  L{n}: {line}")

    if len(hits)>60:
        print(f"  ... {len(hits)-60} additional matches suppressed")

    return True

def protected_integrity():
    print("\nPROTECTED FILE INTEGRITY")
    for path in PROTECTED:
        print(f"  {path}")
        print(f"    SHA256: {sha(path)}")

def source_scan():
    print("\nSOURCE AST VALIDATION")
    print(f"  universal_crt_v4.py: {ast_ok(CRT)}")
    print(f"  OMNICIPHERIST.py: {ast_ok(OMNI)}")

    print("\nUNIVERSALCRT V4 SOURCE DISCOVERY")
    scan_file(CRT)

    print("\nOMNICIPHERIST SOURCE DISCOVERY")
    scan_file(OMNI)

def json_scan():
    print("\nTARGETED JSON CONFIGURATION DISCOVERY")

    for path in [
        ROOT/"omnicipherist_config.json",
        ACTIVE,
    ]:
        if not path.exists():
            continue

        print(f"\nJSON FILE: {path}")

        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            text=json.dumps(data,indent=2)
        except Exception as e:
            print(f"  JSON INVALID: {e}")
            continue

        print("  CLASSIFICATION:",", ".join(classify(text)))

        for line in redact(text).splitlines():
            if any(k.lower() in line.lower() for k in KEYWORDS):
                print(" ",line)

def environment_scan():
    print("\nENVIRONMENT AUTHORITY DISCOVERY")

    credential_keys=[]
    provider_keys=[]
    instrument_keys=[]

    for key in os.environ:
        low=key.lower()

        if any(x in low for x in [
            "api","token","secret","credential",
            "password","key"
        ]):
            credential_keys.append(key)

        if any(x in low for x in [
            "oanda","alpaca","ibkr","interactive",
            "metatrader","mt5","ctrader","fxcm",
            "finnhub","polygon","twelve","alpha",
            "coinbase","biquote","broker","forex"
        ]):
            provider_keys.append(key)

        if any(x in low for x in [
            "gbpjpy","contract","lot","pip",
            "tick","margin","symbol"
        ]):
            instrument_keys.append(key)

    if credential_keys:
        for key in sorted(set(credential_keys)):
            print(f"  CREDENTIAL PRESENT: {key}")
            print("  SECRET VALUE: REDACTED")
    else:
        print("  NO CREDENTIAL-LIKE ENVIRONMENT VARIABLES FOUND")

    if provider_keys:
        print("\n  PROVIDER-RELATED VARIABLES:")
        for key in sorted(set(provider_keys)):
            print(f"    {key}")
    else:
        print("  NO PROVIDER-SPECIFIC ENVIRONMENT VARIABLES FOUND")

    if instrument_keys:
        print("\n  INSTRUMENT-RELATED VARIABLES:")
        for key in sorted(set(instrument_keys)):
            print(f"    {key}")
    else:
        print("  NO INSTRUMENT-SPECIFIC ENVIRONMENT VARIABLES FOUND")

def bounded_omni_scan():
    print("\nBOUNDED ~/OMNI CONFIGURATION DISCOVERY")

    allowed_extensions={
        ".py",".json",".toml",".yaml",".yml",
        ".ini",".cfg",".conf",".env",".txt",".md"
    }

    excluded={
        ".git","backups","__pycache__",
        "node_modules",".venv","venv"
    }

    candidates=[]

    try:
        entries=list(ROOT.iterdir())
    except OSError as e:
        print(f"  OMNI DIRECTORY ERROR: {e}")
        return

    for path in entries:
        if path.name in excluded:
            continue

        if path.is_file() and path.suffix.lower() in allowed_extensions:
            candidates.append(path)

        elif path.is_dir():
            try:
                for child in path.iterdir():
                    if child.name in excluded:
                        continue
                    if child.is_file() and child.suffix.lower() in allowed_extensions:
                        candidates.append(child)
            except (OSError,PermissionError):
                continue

    seen=set()

    for path in sorted(candidates):
        try:
            resolved=path.resolve()
        except OSError:
            continue

        if resolved in seen:
            continue

        seen.add(resolved)

        if resolved in {p.resolve() for p in PROTECTED if p.exists()}:
            continue

        scan_file(path)

    print(f"\n  BOUNDED FILES INSPECTED: {len(seen)}")

def termux_target_scan():
    print("\nTARGETED TERMUX CONFIGURATION DISCOVERY")

    home=Path.home()

    targets=[
        home/".config",
        home/".termux",
        home/".local",
        home/".cache",
        home/".profile",
        home/".bashrc",
        home/".zshrc",
    ]

    checked=0

    for target in targets:
        if not target.exists():
            continue

        if target.is_file():
            print(f"\nTARGET: {target}")
            scan_file(target)
            checked+=1
            continue

        try:
            children=list(target.iterdir())
        except (OSError,PermissionError):
            continue

        for child in children[:100]:
            if child.is_file():
                if child.suffix.lower() in {
                    ".json",".toml",".yaml",".yml",
                    ".ini",".cfg",".conf",".env",".txt"
                }:
                    print(f"\nTARGET: {child}")
                    scan_file(child)
                    checked+=1

    print(f"\n  TARGETED TERMUX FILES INSPECTED: {checked}")

def package_scan():
    print("\nINSTALLED PYTHON PROVIDER PACKAGE DISCOVERY")

    packages=[
        "MetaTrader5",
        "oandapyV20",
        "ib_insync",
        "alpaca",
        "finnhub",
        "yfinance",
        "fxcmpy",
        "ctrader",
        "ccxt",
        "requests",
    ]

    for package in packages:
        try:
            spec=importlib.util.find_spec(package)
        except Exception:
            spec=None

        if spec is not None:
            print(f"  PRESENT: {package}")
        else:
            print(f"  ABSENT: {package}")

def local_module_scan():
    print("\nBOUNDED LOCAL PYTHON MODULE DISCOVERY")

    found=0

    try:
        files=sorted(ROOT.glob("*.py"))
    except OSError:
        files=[]

    for path in files:
        if path.name in {
            "CAT_STAGE_A_STEP_FIFTEEN.py",
            "CAT_STAGE_A_STEP_FIFTEEN.INTERRUPTED"
        }:
            continue

        try:
            text=path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        except Exception:
            continue

        low=text.lower()

        if any(x in low for x in [
            "metatrader","mt5","oanda","alpaca",
            "ib_insync","ibkr","ctrader",
            "broker","contract_size","lot_step",
            "gbpjpy","finnhub","fxcm"
        ]):
            found+=1
            print(f"\nMODULE CANDIDATE: {path}")
            print("CLASSIFICATION:",", ".join(classify(text)))
            scan_file(path)

    print(f"\n  LOCAL MODULE CANDIDATES: {found}")

def safety():
    print("\nWRITE-SAFETY")
    print("  PRODUCTION FILE MODIFICATION: DISABLED")
    print("  ACTIVE_TRADE MODIFICATION: DISABLED")
    print("  BACKUP MODIFICATION: DISABLED")
    print("  SECRET VALUES: REDACTED")

def main():
    print("="*80)
    print("CAT STAGE A — STEP FIFTEEN")
    print("LOCAL AUTHORITY / CREDENTIAL / PROVIDER DISCOVERY")
    print("TARGET: UNIVERSALCRT V4")
    print("MODE: READ-ONLY / BOUNDED")
    print("="*80)

    protected_integrity()
    source_scan()
    json_scan()
    environment_scan()
    bounded_omni_scan()
    termux_target_scan()
    package_scan()
    local_module_scan()
    safety()

    print("\n"+"="*80)
    print("STEP FIFTEEN — BOUNDED DISCOVERY COMPLETE")
    print("="*80)
    print("  TARGET: universal_crt_v4.py")
    print("  FULL HOME RECURSION: DISABLED")
    print("  PUBLIC PROVIDER SEARCH: NOT PERFORMED")
    print("  SECRET VALUES: NEVER PRINTED")
    print("  PRODUCTION MODIFICATION: NONE")
    print("  ACTIVE_TRADE MODIFICATION: NONE")
    print("  BACKUP MODIFICATION: NONE")
    print("="*80)

if __name__=="__main__":
    main()
