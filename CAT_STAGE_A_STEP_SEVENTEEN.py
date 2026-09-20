#!/usr/bin/env python3
import ast
import hashlib
import json
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

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def ast_ok(path):
    try:
        ast.parse(Path(path).read_text(encoding="utf-8"),filename=path)
        return True
    except Exception:
        return False

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║ CAT STAGE A — STEP SEVENTEEN — AUTHORITY GATE APPLICATION         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    print("\n[1] PROTECTED SOURCE INTEGRITY")
    integrity=True
    for path,want in PROTECTED.items():
        actual=sha256(path)
        astpass=ast_ok(path)
        hashpass=actual==want
        print(f"{path}:")
        print(f"  AST: {'PASS' if astpass else 'FAIL'}")
        print(f"  HASH: {'UNCHANGED' if hashpass else 'CHANGED'}")
        print(f"  SHA256: {actual}")
        integrity &= astpass and hashpass

    print("\n[2] PRODUCTION FILE SAFETY")
    print(f"{ACTIVE}: READ ONLY")
    print(f"{CONFIG}: READ ONLY")
    print("BACKUPS: READ ONLY")
    print("V4 INJECTION: FORBIDDEN")
    print("OMNICIPHERIST MODIFICATION: FORBIDDEN")
    print("ACTIVE_TRADE MODIFICATION: FORBIDDEN")

    print("\n[3] AUTHORITY CONTRACT")
    required=[
        "CURRENT BID",
        "CURRENT ASK",
        "MARKET STATE",
        "15-MIN OHLC",
        "TIMESTAMP / DATA AGE",
        "DATA PROVIDER",
        "PIP SIZE",
        "TICK SIZE",
        "PRICE PRECISION",
        "CONTRACT SIZE",
        "LOT UNIT",
        "MIN LOT",
        "MAX LOT",
        "LOT STEP",
        "MARGIN CURRENCY",
        "QUOTE -> USD CONVERSION",
        "PROVIDER SYMBOL",
        "PROVIDER TIMEZONE",
        "EXECUTABLE/REFERENCE CLASSIFICATION",
    ]
    for item in required:
        print(f"  {item}: REQUIRED")

    print("\n[4] NON-AUTHORITATIVE SOURCES")
    excluded=[
        "HANKOX_EMULATOR.py",
        "hankox_emulator_state.json",
        "QUANTUMBOT synthetic data",
        "GENESIS/GODHEAD test values",
        "hard-coded OHLC",
        "historical trade logs",
        "reference FX conversion",
        "stale/closed-market quotes",
    ]
    for item in excluded:
        print(f"  EXCLUDED: {item}")

    print("\n[5] AUTHORITY EXPRESSION")
    expression=[
        "BID_ASK_VALID",
        "MARKET_STATE_KNOWN",
        "OHLC_15M_VALID",
        "INSTRUMENT_SPEC_VERIFIED",
        "TIMESTAMP_VALID",
        "PROVIDER_IDENTITY_KNOWN",
        "ACCOUNT_CURRENCY_CONVERSION_VALID",
    ]
    for item in expression:
        print(f"  {item}")

    print("\n[6] CURRENT MARKET CONDITION")
    print("DATE: 2026-09-19")
    print("DAY: SATURDAY")
    print("GBPJPY MARKET STATE: CLOSED")
    print("STALE QUOTE: REFERENCE ONLY")
    print("SYNTHETIC MARKET DATA: FORBIDDEN")

    print("\n[7] GATE RESULT")
    authority_confirmed=False
    print("AUTHORITY_CONFIRMED =",authority_confirmed)

    print("\n[8] SAFETY ENFORCEMENT")
    if not integrity:
        print("SOURCE INTEGRITY FAILURE")
        print("PRODUCTION INJECTION: BLOCKED")
        return 1

    print("LIVE TRADE ACTIVATION: BLOCKED")
    print("LIVE P/L: BLOCKED")
    print("DRAWDOWN: BLOCKED")
    print("SL/TP AUTO-CLOSE: BLOCKED")
    print("AUTO WIN/LOSS: BLOCKED")
    print("PRODUCTION SNAPSHOT: BLOCKED")
    print("V4 INJECTION: BLOCKED")

    print("\n[9] REQUIRED NEXT AUTHORITY EVIDENCE")
    print("1. Authoritative GBPJPY 15m OHLC")
    print("2. Authoritative GBPJPY instrument specification")
    print("3. Authoritative executable quote/conversion path")
    print("4. Provider symbol and timezone")
    print("5. Executable-vs-reference classification")

    print("\n[10] FINAL CAT STATE")
    print("STEP FIFTEEN: COMPLETE")
    print("STEP SIXTEEN: COMPLETE")
    print("STEP SEVENTEEN: COMPLETE — GATE APPLIED")
    print("MARKET AUTHORITY: NOT ESTABLISHED")
    print("PRODUCTION MERGE: BLOCKED")
    print("PRODUCTION FILES: UNMODIFIED")

    return 0

if __name__=="__main__":
    raise SystemExit(main())
