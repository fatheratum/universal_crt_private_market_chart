from pathlib import Path
import ast
import json
import re

FILES=["OMNICIPHERIST.py","universal_crt_v4.py"]

def read(path):
    return Path(path).read_text(encoding="utf-8")

def show_function(path,name):
    src=read(path)
    lines=src.splitlines()
    tree=ast.parse(src,filename=path)
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name:
            start=node.lineno
            end=getattr(node,"end_lineno",start)
            print("\n"+"="*100)
            print(f"{path} :: {name} :: L{start}-L{end}")
            print("="*100)
            for i in range(start,end+1):
                print(f"{i:4}: {lines[i-1]}")
            return
    print(f"\nNOT FOUND: {path}::{name}")

def search(path,terms):
    lines=read(path).splitlines()
    for i,line in enumerate(lines,1):
        if any(term.lower() in line.lower() for term in terms):
            print(f"{i:4}: {line}")

def calls(path,names):
    tree=ast.parse(read(path),filename=path)
    print(f"\n--- CALL SITES: {path} ---")
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            fn=ast.unparse(node.func)
            if any(name in fn for name in names):
                print(f"{node.lineno:4}: {ast.unparse(node)}")

print("CAT STAGE A — STEP SEVEN")
print("EXECUTION / TRADE-STATE LIFECYCLE AUDIT")
print("MODE: READ ONLY")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

print("\n"+"#"*100)
print("OMNICIPHERIST MENU / EXECUTION ENTRY POINT")
print("#"*100)

for name in [
    "omni_menu",
    "find_sacred_setup",
    "infinite_recursive_scan",
    "__init__",
    "handle_phaseIV_update",
]:
    show_function("OMNICIPHERIST.py",name)

print("\n"+"#"*100)
print("TRADE LIFECYCLE SYMBOL AUDIT")
print("#"*100)

TRADE_TERMS=[
    "active_trade",
    "ACTIVE_TRADE_FILE",
    "status",
    "PENDING",
    "SUCCESS",
    "FAIL",
    "WIN",
    "LOSS",
    "SL HIT",
    "TP HIT",
    "stop_loss",
    "take_profit",
    "current_price",
    "profit",
    "direction",
    "close",
    "closed",
    "trade_log",
    "snapshot",
    "jpg",
    "jpeg",
    "png",
    "screenshot",
    "savefig",
    "capture",
    "monitor",
    "while True",
    "sleep",
]

search("OMNICIPHERIST.py",TRADE_TERMS)

print("\n"+"#"*100)
print("CRT LIFECYCLE / RENDER / INPUT AUDIT")
print("#"*100)

CRT_TERMS=[
    "MULTI_CHARTS",
    "status",
    "running",
    "PENDING",
    "SUCCESS",
    "FAIL",
    "profit",
    "stop_loss",
    "take_profit",
    "current_price",
    "snapshot",
    "jpg",
    "jpeg",
    "png",
    "screenshot",
    "capture",
    "render",
    "refresh",
    "_multi_key",
    "_multi_render",
    "_multi_refresh",
]

search("universal_crt_v4.py",CRT_TERMS)

print("\n"+"#"*100)
print("OMNICIPHERIST TRADE-RELATED CALL GRAPH")
print("#"*100)

calls(
    "OMNICIPHERIST.py",
    [
        "fetch_live_price",
        "find_sacred_setup",
        "save_config",
        "load_config",
        "level200_process",
        "inevitable_50pip_meta_target",
        "matrix_disruption_ping",
    ],
)

print("\n"+"#"*100)
print("CRT TRADE-RELATED CALL GRAPH")
print("#"*100)

calls(
    "universal_crt_v4.py",
    [
        "_fetch_pair",
        "fetch_candles",
        "_multi_refresh",
        "_multi_render",
        "_multi_key",
        "_multi_menu",
        "_multi_menu_action",
    ],
)

print("\n"+"#"*100)
print("AST: FILE WRITE OPERATIONS")
print("#"*100)

for path in FILES:
    tree=ast.parse(read(path),filename=path)
    print(f"\n--- {path} ---")
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            fn=ast.unparse(node.func)
            if fn in {
                "open",
                "Path.write_text",
                "Path.write_bytes",
                "json.dump",
                "json.dump",
                "savefig",
            } or "write" in fn.lower() or "save" in fn.lower():
                print(f"{node.lineno:4}: {ast.unparse(node)}")

print("\n"+"#"*100)
print("ACTIVE TRADE JSON STRUCTURE AUDIT")
print("#"*100)

active=Path("active_trade.json")
if active.exists():
    try:
        data=json.loads(active.read_text(encoding="utf-8"))
        print("TYPE:",type(data).__name__)
        if isinstance(data,list):
            print("RECORD COUNT:",len(data))
            statuses={}
            pairs={}
            timeframes={}
            directions={}
            for r in data:
                if not isinstance(r,dict):
                    continue
                statuses[str(r.get("status"))]=statuses.get(str(r.get("status")),0)+1
                pairs[str(r.get("pair"))]=pairs.get(str(r.get("pair")),0)+1
                timeframes[str(r.get("timeframe"))]=timeframes.get(str(r.get("timeframe")),0)+1
                directions[str(r.get("direction"))]=directions.get(str(r.get("direction")),0)+1

            print("STATUSES:",json.dumps(statuses,indent=2))
            print("PAIRS:",json.dumps(pairs,indent=2))
            print("TIMEFRAMES:",json.dumps(timeframes,indent=2))
            print("DIRECTIONS:",json.dumps(directions,indent=2))

            print("\nPENDING RECORDS:")
            for r in data:
                if isinstance(r,dict) and str(r.get("status")).upper()=="PENDING":
                    print(json.dumps(r,indent=2))

            print("\nCLOSED RECORDS:")
            for r in data:
                if isinstance(r,dict) and str(r.get("status")).upper() in {"SUCCESS","FAIL","CLOSED","WIN","LOSS"}:
                    print(json.dumps(r,indent=2))
        else:
            print(json.dumps(data,indent=2))
    except Exception as e:
        print("ACTIVE TRADE JSON ERROR:",repr(e))
else:
    print("active_trade.json NOT FOUND")

print("\n"+"#"*100)
print("SNAPSHOT / IMAGE-CAPTURE AUDIT")
print("#"*100)

for path in FILES:
    print(f"\n--- {path} ---")
    search(path,[
        ".jpg",
        ".jpeg",
        ".png",
        "PIL",
        "Pillow",
        "Image",
        "ImageGrab",
        "screenshot",
        "screencap",
        "capture",
        "savefig",
        "matplotlib",
        "svg",
    ])

print("\n"+"#"*100)
print("MONITORING LOOP AUDIT")
print("#"*100)

for path in FILES:
    print(f"\n--- {path} ---")
    search(path,[
        "while True",
        "while",
        "sleep(",
        "time.sleep",
        "refresh",
        "monitor",
        "current_price",
    ])

print("\n"+"#"*100)
print("STATUS TRANSITION AUDIT")
print("#"*100)

for path in FILES:
    print(f"\n--- {path} ---")
    search(path,[
        '["status"]',
        "['status']",
        '"status":',
        "'status':",
        "PENDING",
        "SUCCESS",
        "FAIL",
        "WIN",
        "LOSS",
        "TP HIT",
        "SL HIT",
    ])

print("\n"+"#"*100)
print("STAGE A STEP SEVEN — REQUIRED LIFECYCLE QUESTIONS")
print("#"*100)

questions=[
    "1. Does OMNICIPHERIST create PENDING trades?",
    "2. Does OMNICIPHERIST continuously monitor PENDING trades?",
    "3. Does OMNICIPHERIST fetch a new market price after setup creation?",
    "4. Does OMNICIPHERIST automatically evaluate stop_loss/take_profit?",
    "5. Does OMNICIPHERIST automatically transition PENDING -> SUCCESS/FAIL?",
    "6. Does OMNICIPHERIST calculate live unrealized P/L?",
    "7. Does OMNICIPHERIST calculate drawdown?",
    "8. Does OMNICIPHERIST automatically capture JPG/JPEG snapshots?",
    "9. Does universal_crt_v4.py consume active_trade.json?",
    "10. Does universal_crt_v4.py display entry/SL/TP/P/L?",
    "11. Does universal_crt_v4.py have an existing monitoring lifecycle?",
    "12. Does either source implement a complete close-and-log lifecycle?",
]

for q in questions:
    print(q)

print("\nCAT STAGE A — STEP SEVEN READ-ONLY AUDIT COMPLETE")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")
