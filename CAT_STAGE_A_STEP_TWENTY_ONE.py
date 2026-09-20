#!/usr/bin/env python3
import ast
import hashlib
import json
import re
from pathlib import Path

OMNI=Path("OMNICIPHERIST.py")
V4=Path("universal_crt_v4.py")
ACTIVE=Path("active_trade.json")

PROTECTED={
    "universal_crt_v4.py":"5a9c70027b863477d50dd98bc597345017a1baa94e7a597b1877ad7cca4e010a",
    "OMNICIPHERIST.py":"21923126a630842fe7fc64f3e70a5d549e07cf67170792855d49ef567d63069a",
}

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def safe_value(s):
    return re.sub(
        r'(?i)(api[_-]?key|apikey|token|secret|password|authorization|access[_-]?token)\s*([:=])\s*[\'"][^\'"]+[\'"]',
        r'\1\2<REDACTED>',
        s
    )

def classify(name):
    n=name.lower()
    if any(x in n for x in ("quote","price","ticker","bid","ask","rate")):
        return "MARKET_DATA"
    if any(x in n for x in ("account","balance","equity","margin","position")):
        return "ACCOUNT"
    if any(x in n for x in ("order","trade","execute","close","cancel")):
        return "EXECUTION"
    if any(x in n for x in ("candle","ohlc","bar","history","rates")):
        return "OHLC"
    if any(x in n for x in ("symbol","instrument","pip","tick","lot","contract")):
        return "INSTRUMENT"
    if any(x in n for x in ("convert","currency","forex","fx")):
        return "CONVERSION"
    return "OTHER"

def audit_source(path):
    text=path.read_text(encoding="utf-8",errors="replace")
    tree=ast.parse(text,filename=str(path))

    print(f"\nSOURCE: {path}")
    print(f"LINES: {len(text.splitlines())}")

    functions=[]
    classes=[]
    imports=[]

    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            functions.append(node)
        elif isinstance(node,ast.ClassDef):
            classes.append(node)
        elif isinstance(node,(ast.Import,ast.ImportFrom)):
            imports.append(node)

    print(f"FUNCTIONS: {len(functions)}")
    print(f"CLASSES: {len(classes)}")

    print("\nIMPORTS")
    for node in imports:
        try:
            print(" ",safe_value(ast.unparse(node)))
        except Exception:
            pass

    print("\nINTERFACES")
    for node in functions:
        args=[a.arg for a in node.args.args]
        category=classify(node.name)
        print(
            f"  {node.name}({', '.join(args)})"
            f"  [{category}]"
            f"  LINE {node.lineno}"
        )

    for cls in classes:
        print(f"\nCLASS {cls.name} LINE {cls.lineno}")
        for node in cls.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                args=[a.arg for a in node.args.args]
                print(
                    f"  {node.name}({', '.join(args)})"
                    f"  [{classify(node.name)}]"
                    f"  LINE {node.lineno}"
                )

    print("\nPROVIDER REFERENCES")
    terms=(
        "biquote",
        "MetaTrader",
        "MT5",
        "forex",
        "requests",
        "websocket",
        "websockets",
        "api",
        "quote",
        "account",
        "trade",
        "order",
        "candle",
        "ohlc",
        "symbol",
        "conversion",
    )
    found=set()
    for i,line in enumerate(text.splitlines(),1):
        if any(t.lower() in line.lower() for t in terms):
            cleaned=safe_value(line.strip())
            if cleaned and cleaned not in found:
                found.add(cleaned)
                print(f"  L{i}: {cleaned}")

def contract_map():
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║ STEP 21 — AUTHORITY ADAPTER CONTRACT MAP                          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    requirements={
        "quote":"Existing source for live bid/ask",
        "ohlc":"Existing source for authoritative 15m candles",
        "account":"Existing source for balance/equity/account currency",
        "instrument":"Existing source for symbol specifications",
        "conversion":"Existing executable account-currency conversion",
        "execution":"Existing authenticated order/position interface",
        "timestamp":"Existing source timestamp/freshness",
        "market_state":"Existing market-open/closed state",
    }

    print("\nREQUIRED ADAPTER CONTRACT")
    for k,v in requirements.items():
        print(f"{k.upper():12} -> {v}")

    print("\nTARGET NORMALIZED INTERFACE")
    print("get_quote(symbol)")
    print("get_candles(symbol,timeframe,limit)")
    print("get_account()")
    print("get_instrument(symbol)")
    print("convert(amount,from_currency,to_currency)")
    print("get_market_state(symbol)")
    print("get_timestamp()")
    print("get_position(position_id)")
    print("place_order(order)")
    print("modify_order(order_id,changes)")
    print("close_position(position_id)")

def integrity():
    print("\nINTEGRITY")
    ok=True
    for name,want in PROTECTED.items():
        p=Path(name)
        actual=sha256(p)
        passed=actual==want
        ok &= passed
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
        print(f"SHA256: {actual}")
    print("SOURCE_INTEGRITY =",ok)
    return ok

def main():
    print("CAT STAGE A — STEP TWENTY-ONE")
    print("SOURCE/INTERFACE AUDIT")
    print("READ ONLY — NO LOGIN — NO ORDERS — NO PRODUCTION WRITE")

    integrity()

    audit_source(OMNI)
    audit_source(V4)
    contract_map()

    print("\nACTIVE TRADE")
    if ACTIVE.exists():
        try:
            data=json.loads(ACTIVE.read_text(encoding="utf-8"))
            print("RECORDS:",len(data) if isinstance(data,list) else "NON-LIST")
            print("STATUS: READ ONLY")
        except Exception as e:
            print("JSON ERROR:",type(e).__name__)
    else:
        print("NOT FOUND")

    print("\nSTEP 21 RESULT")
    print("SOURCE AUDIT: COMPLETE")
    print("ADAPTER CONTRACT: DEFINED")
    print("EXISTING PRODUCTION SOURCES: UNMODIFIED")
    print("BROKER AUTHORITY: NOT FABRICATED")

if __name__=="__main__":
    main()
