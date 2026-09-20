from pathlib import Path
import json
import math
from collections import Counter

ACTIVE=Path("active_trade.json")

TF_MAP={
    "1MIN":"1m","1M":"1m","1MINUTE":"1m",
    "5MIN":"5m","5M":"5m","5MINUTE":"5m",
    "15MIN":"15m","15M":"15m","15MINUTE":"15m",
    "30MIN":"30m","30M":"30m",
    "1H":"1h","1HR":"1h","1HOUR":"1h",
    "4H":"4h","4HR":"4h","4HOUR":"4h",
    "1D":"1d","1DAY":"1d",
}

REQUIRED_CORE=["id","pair","entry","take_profit","stop_loss","lot_size","timeframe","status"]

def norm_pair(value):
    if not isinstance(value,str):
        return None
    s=value.strip().upper().replace("/","").replace("-","").replace("_","").replace(" ","")
    if len(s)==6 and s.isalpha():
        return s
    return None

def norm_tf(value):
    if not isinstance(value,str):
        return None
    return TF_MAP.get(value.strip().upper())

def finite_number(value):
    try:
        x=float(value)
        return math.isfinite(x)
    except Exception:
        return False

def direction_topology(record):
    d=str(record.get("direction","")).strip().upper()
    try:
        e=float(record["entry"])
        sl=float(record["stop_loss"])
        tp=float(record["take_profit"])
    except Exception:
        return "INVALID_NUMERIC"

    if d=="BUY":
        return "VALID" if sl<e<tp else "INVALID_BUY_TOPOLOGY"
    if d=="SELL":
        return "VALID" if tp<e<sl else "INVALID_SELL_TOPOLOGY"

    return "MISSING_DIRECTION"

def price_geometry(record):
    try:
        e=float(record["entry"])
        sl=float(record["stop_loss"])
        tp=float(record["take_profit"])
        return {
            "sl_distance":abs(e-sl),
            "tp_distance":abs(tp-e),
            "balanced":math.isclose(abs(e-sl),abs(tp-e),rel_tol=1e-9,abs_tol=1e-9)
        }
    except Exception:
        return {
            "sl_distance":None,
            "tp_distance":None,
            "balanced":False
        }

def price_scale_flags(record):
    pair=norm_pair(record.get("pair"))
    try:
        e=float(record["entry"])
        sl=float(record["stop_loss"])
        tp=float(record["take_profit"])
    except Exception:
        return ["NON_NUMERIC_PRICE"]

    flags=[]

    if e<=0 or sl<=0 or tp<=0:
        flags.append("NON_POSITIVE_PRICE")

    if pair and pair.endswith("JPY"):
        if e<20 or e>300:
            flags.append("JPY_PRICE_SCALE_SUSPICIOUS")
    elif pair:
        if e>20:
            flags.append("NON_JPY_PRICE_SCALE_SUSPICIOUS")

    return flags

def age_key(record):
    try:
        return int(str(record.get("id")))
    except Exception:
        return -1

print("CAT STAGE A — STEP EIGHT")
print("STATE / SCHEMA + SELECTION INTEGRITY AUDIT")
print("MODE: READ ONLY")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")

if not ACTIVE.exists():
    print("\nERROR: active_trade.json NOT FOUND")
    raise SystemExit(1)

try:
    data=json.loads(ACTIVE.read_text(encoding="utf-8"))
except Exception as e:
    print("\nERROR: active_trade.json INVALID JSON")
    print(repr(e))
    raise SystemExit(1)

if not isinstance(data,list):
    print("\nERROR: active_trade.json root is not a list")
    print("TYPE:",type(data).__name__)
    raise SystemExit(1)

print("\n"+"="*110)
print("FILE")
print("="*110)
print("PATH:",ACTIVE)
print("RECORD COUNT:",len(data))

print("\n"+"="*110)
print("FIELD PRESENCE")
print("="*110)

all_fields=Counter()
field_missing=Counter()

for r in data:
    if not isinstance(r,dict):
        continue
    all_fields.update(r.keys())
    for field in REQUIRED_CORE:
        if field not in r:
            field_missing[field]+=1

print("FIELDS:")
for field,count in all_fields.most_common():
    print(f"{field:20} {count}/{len(data)}")

print("\nREQUIRED FIELD MISSING COUNTS:")
for field in REQUIRED_CORE:
    print(f"{field:20} {field_missing[field]}")

print("\n"+"="*110)
print("NORMALIZATION INVENTORY")
print("="*110)

pairs=Counter()
timeframes=Counter()
directions=Counter()
statuses=Counter()

for r in data:
    if not isinstance(r,dict):
        continue
    pairs[str(r.get("pair"))]+=1
    timeframes[str(r.get("timeframe"))]+=1
    directions[str(r.get("direction"))]+=1
    statuses[str(r.get("status"))]+=1

print("RAW PAIRS:")
for k,v in pairs.items():
    print(f"  {k}: {v}")

print("\nNORMALIZED PAIRS:")
for k,v in pairs.items():
    print(f"  {k} -> {norm_pair(k)}: {v}")

print("\nRAW TIMEFRAMES:")
for k,v in timeframes.items():
    print(f"  {k}: {v}")

print("\nNORMALIZED TIMEFRAMES:")
for k,v in timeframes.items():
    print(f"  {k} -> {norm_tf(k)}: {v}")

print("\nDIRECTIONS:")
for k,v in directions.items():
    print(f"  {k}: {v}")

print("\nSTATUSES:")
for k,v in statuses.items():
    print(f"  {k}: {v}")

print("\n"+"="*110)
print("RECORD-BY-RECORD ELIGIBILITY MATRIX")
print("="*110)

eligible=[]
ineligible=[]
pending=[]

for index,r in enumerate(data):
    if not isinstance(r,dict):
        result={
            "index":index,
            "classification":"INVALID_RECORD",
            "reasons":["RECORD_NOT_OBJECT"]
        }
        print(json.dumps(result,indent=2))
        ineligible.append(result)
        continue

    status=str(r.get("status","")).strip().upper()
    pair=norm_pair(r.get("pair"))
    tf=norm_tf(r.get("timeframe"))
    direction=str(r.get("direction","")).strip().upper()

    reasons=[]
    warnings=[]

    for field in REQUIRED_CORE:
        if field not in r:
            reasons.append("MISSING_"+field.upper())

    if pair is None:
        reasons.append("INVALID_PAIR")

    if tf is None:
        reasons.append("INVALID_TIMEFRAME")

    for field in ["entry","take_profit","stop_loss","lot_size"]:
        if field in r and not finite_number(r[field]):
            reasons.append("INVALID_"+field.upper())

    topology=direction_topology(r)

    if topology.startswith("INVALID"):
        reasons.append(topology)
    elif topology=="MISSING_DIRECTION":
        reasons.append("MISSING_DIRECTION")

    geometry=price_geometry(r)

    for flag in price_scale_flags(r):
        warnings.append(flag)

    if not geometry["balanced"]:
        warnings.append("ASYMMETRIC_SL_TP_DISTANCE")

    if status=="PENDING":
        pending.append(index)
        if not reasons:
            eligible.append(index)
            classification="PENDING_STRUCTURALLY_ELIGIBLE"
        else:
            ineligible.append(index)
            classification="PENDING_STRUCTURALLY_INVALID"
    elif status in {"SUCCESS","FAIL","WIN","LOSS","CLOSED"}:
        classification="HISTORICAL_CLOSED"
    else:
        classification="NONSTANDARD_STATUS"

    print(
        f"[{index:02d}] "
        f"id={r.get('id')} "
        f"pair={r.get('pair')}->{pair} "
        f"tf={r.get('timeframe')}->{tf} "
        f"direction={direction or 'NONE'} "
        f"status={status or 'NONE'} "
        f"class={classification}"
    )

    if reasons:
        print("     REASONS:",", ".join(reasons))
    if warnings:
        print("     WARNINGS:",", ".join(warnings))

print("\n"+"="*110)
print("PENDING RECORD DETERMINISM")
print("="*110)

pending_records=[
    (i,r) for i,r in enumerate(data)
    if isinstance(r,dict) and str(r.get("status","")).strip().upper()=="PENDING"
]

print("PENDING COUNT:",len(pending_records))
print("STRUCTURALLY ELIGIBLE COUNT:",len(eligible))
print("STRUCTURALLY INVALID COUNT:",len(ineligible))

print("\nPENDING ORDER BY RECORD ID:")
for i,r in sorted(pending_records,key=lambda x:age_key(x[1])):
    print(
        f"index={i:02d} "
        f"id={r.get('id')} "
        f"pair={r.get('pair')} "
        f"tf={r.get('timeframe')} "
        f"direction={r.get('direction','NONE')}"
    )

print("\nLATEST PENDING RECORD:")
if pending_records:
    i,r=max(pending_records,key=lambda x:age_key(x[1]))
    print("INDEX:",i)
    print(json.dumps(r,indent=2))
else:
    print("NONE")

print("\n"+"="*110)
print("GBPJPY / 15m SELECTION TEST")
print("="*110)

matches=[]

for i,r in enumerate(data):
    if not isinstance(r,dict):
        continue
    if (
        norm_pair(r.get("pair"))=="GBPJPY"
        and norm_tf(r.get("timeframe"))=="15m"
    ):
        matches.append((i,r))

print("TOTAL GBPJPY/15m RECORDS:",len(matches))

for i,r in matches:
    print(
        f"index={i:02d} "
        f"id={r.get('id')} "
        f"status={r.get('status')} "
        f"direction={r.get('direction','NONE')} "
        f"entry={r.get('entry')} "
        f"SL={r.get('stop_loss')} "
        f"TP={r.get('take_profit')}"
    )

print("\nPENDING GBPJPY/15m:")
pending_matches=[
    (i,r) for i,r in matches
    if str(r.get("status","")).strip().upper()=="PENDING"
]

for i,r in pending_matches:
    print(
        f"index={i:02d} "
        f"id={r.get('id')} "
        f"direction={r.get('direction','NONE')} "
        f"entry={r.get('entry')} "
        f"SL={r.get('stop_loss')} "
        f"TP={r.get('take_profit')}"
    )

print("\n"+"="*110)
print("SELECTION RULE ANALYSIS")
print("="*110)

print("Candidate rule A: latest PENDING record")
print("Candidate rule B: latest structurally valid PENDING record")
print("Candidate rule C: latest valid PENDING matching CRT pair/timeframe")
print("Candidate rule D: explicit active-trade identifier")
print()
print("CAT WILL NOT SELECT OR ACTIVATE A TRADE.")
print("This stage only determines whether the existing file provides enough")
print("information for deterministic selection.")

duplicate_keys=Counter()

for i,r in pending_records:
    key=(
        norm_pair(r.get("pair")),
        norm_tf(r.get("timeframe")),
        str(r.get("direction","")).strip().upper()
    )
    duplicate_keys[key]+=1

print("\nPENDING NORMALIZED PAIR/TF/DIRECTION DUPLICATES:")
for key,count in duplicate_keys.items():
    if count>1:
        print(f"  {key}: {count}")

print("\n"+"="*110)
print("HISTORICAL SAFETY")
print("="*110)

closed_count=0
closed_with_current_price=0

for r in data:
    if not isinstance(r,dict):
        continue
    if str(r.get("status","")).strip().upper() in {"SUCCESS","FAIL","WIN","LOSS","CLOSED"}:
        closed_count+=1
        if "current_price" in r:
            closed_with_current_price+=1

print("CLOSED/HISTORICAL RECORDS:",closed_count)
print("CLOSED RECORDS WITH current_price:",closed_with_current_price)
print("HISTORICAL RECORDS WILL NOT BE REWRITTEN BY THIS AUDIT.")

print("\n"+"="*110)
print("FINAL CAT GATE")
print("="*110)

if len(pending_records)==0:
    print("ACTIVE TRADE SELECTION: NO PENDING RECORD EXISTS")
elif len(pending_records)==1:
    print("ACTIVE TRADE SELECTION: UNIQUE PENDING RECORD EXISTS")
else:
    print("ACTIVE TRADE SELECTION: AMBIGUOUS")
    print("REASON: MULTIPLE PENDING RECORDS EXIST")

if len(eligible)==0:
    print("STRUCTURAL ELIGIBILITY: NO PENDING RECORD PASSES ALL CORE CHECKS")
elif len(eligible)==1:
    print("STRUCTURAL ELIGIBILITY: ONE PENDING RECORD PASSES CORE CHECKS")
else:
    print("STRUCTURAL ELIGIBILITY: MULTIPLE PENDING RECORDS PASS CORE CHECKS")

print("\nCAT STAGE A — STEP EIGHT READ-ONLY AUDIT COMPLETE")
print("SOURCE FILES MODIFIED: NO")
print("BACKUPS MODIFIED: NO")
