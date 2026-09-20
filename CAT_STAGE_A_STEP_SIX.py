from pathlib import Path
import ast
import re

FILES=["OMNICIPHERIST.py","universal_crt_v4.py"]

def source(path):
    return Path(path).read_text(encoding="utf-8")

def lines(path):
    return source(path).splitlines()

def function_body(path,name):
    tree=ast.parse(source(path),filename=path)
    src=lines(path)
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name:
            start=node.lineno
            end=getattr(node,"end_lineno",start)
            return "\n".join(f"{i:4}: {src[i-1]}" for i in range(start,end+1))
    return None

def find_terms(path,terms):
    src=source(path).splitlines()
    hits=[]
    for i,line in enumerate(src,1):
        if any(term in line for term in terms):
            hits.append(f"{i:4}: {line}")
    return hits

def show(path,name):
    print("\n"+"="*100)
    print(f"{path} :: {name}")
    print("="*100)
    body=function_body(path,name)
    print(body if body else "NOT FOUND")

print("CAT STAGE A — STEP SIX")
print("MARKET-DATA AUTHORITY + PRICE/PIP MATHEMATICS")
print("MODE: READ ONLY")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

for path in FILES:
    print("\n"+"#"*100)
    print(f"SOURCE: {path}")
    print("#"*100)
    print(f"LINES: {len(lines(path))}")

print("\n\n[1] OMNICIPHERIST MARKET-DATA PATH")
for name in ["fetch_live_price","load_config","save_config","find_sacred_setup"]:
    show("OMNICIPHERIST.py",name)

print("\n\n[2] UNIVERSAL CRT MARKET-DATA PATH")
for name in ["api_url","fetch_candles","_pair_normalize","_pair_url","_fetch_pair","_multi_refresh"]:
    show("universal_crt_v4.py",name)

terms=[
    "PIP_TO_PRICE_RATIO",
    "PIP_DISTANCE",
    "TARGET_GROWTH",
    "PIP_VALUE",
    "FOREX_API_URL",
    "FOREX_API_KEY",
    "COINGECKO_API_URL",
    "biquote.io",
    "CoinGecko",
    "requests.get",
    "urlopen",
    "urllib",
    "symbol",
    "mid",
    "bid",
    "ask",
    "price",
    "entry",
    "stop_loss",
    "take_profit",
    "lot_size",
    "profit",
    "direction",
]

print("\n\n[3] OMNICIPHERIST PRICE/MATH SYMBOL AUDIT")
for hit in find_terms("OMNICIPHERIST.py",terms):
    print(hit)

print("\n\n[4] UNIVERSAL CRT PRICE/MATH SYMBOL AUDIT")
for hit in find_terms("universal_crt_v4.py",terms):
    print(hit)

print("\n\n[5] OMNICIPHERIST IMPORTS")
tree=ast.parse(source("OMNICIPHERIST.py"),filename="OMNICIPHERIST.py")
for node in tree.body:
    if isinstance(node,ast.Import):
        print(f"{node.lineno:4}: {ast.unparse(node)}")
    elif isinstance(node,ast.ImportFrom):
        print(f"{node.lineno:4}: {ast.unparse(node)}")

print("\n\n[6] UNIVERSAL CRT IMPORTS")
tree=ast.parse(source("universal_crt_v4.py"),filename="universal_crt_v4.py")
for node in tree.body:
    if isinstance(node,ast.Import):
        print(f"{node.lineno:4}: {ast.unparse(node)}")
    elif isinstance(node,ast.ImportFrom):
        print(f"{node.lineno:4}: {ast.unparse(node)}")

print("\n\n[7] GLOBAL CONSTANTS / CONFIGURATION REFERENCES")
for path in FILES:
    print("\n---",path,"---")
    src=source(path)
    for pattern in [
        r"^[A-Z][A-Z0-9_]+\s*=.*$",
        r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*.*PIP.*$",
        r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*.*FOREX.*$",
        r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*.*TIME.*$",
    ]:
        for match in re.finditer(pattern,src,re.MULTILINE):
            print(match.group(0))

print("\n\n[8] AST CALL-SITE AUDIT")
for path in FILES:
    tree=ast.parse(source(path),filename=path)
    print("\n---",path,"---")
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            fn=ast.unparse(node.func)
            if any(x in fn for x in [
                "fetch_live_price",
                "_fetch_pair",
                "fetch_candles",
                "api_url",
                "find_sacred_setup",
                "inevitable_50pip_meta_target",
            ]):
                print(f"{node.lineno:4}: {ast.unparse(node)}")

print("\n\n[9] CURRENT CONFIGURATION FILE")
config=Path("omnicipherist_config.json")
if config.exists():
    print(config.read_text(encoding="utf-8"))
else:
    print("omnicipherist_config.json NOT FOUND")

print("\n\n[10] CURRENT ACTIVE TRADE RECORD SAMPLE")
active=Path("active_trade.json")
if active.exists():
    text=active.read_text(encoding="utf-8")
    print(text[:12000])
    if len(text)>12000:
        print("\n...OUTPUT TRUNCATED AFTER 12000 CHARACTERS...")
else:
    print("active_trade.json NOT FOUND")

print("\n\nCAT STAGE A — STEP SIX READ-ONLY AUDIT COMPLETE")
print("NO SOURCE FILES MODIFIED")
print("NO BACKUPS MODIFIED")
