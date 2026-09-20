#!/usr/bin/env python3
import hashlib
import json
import os
import sys
from pathlib import Path

SOURCE=Path("universal_crt_v4.py")
LOCKDIR=Path(".crt_lock")
LINES=LOCKDIR/"line_hashes.json"
UNLOCKED=LOCKDIR/"unlocked.json"
MANIFEST=LOCKDIR/"manifest.sha256"

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def read_source():
    return SOURCE.read_text(encoding="utf-8",newline="")

def load_lines():
    return read_source().splitlines(keepends=True)

def save_json(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def lock_all():
    LOCKDIR.mkdir(exist_ok=True)
    lines=load_lines()
    records={
        str(i+1):{
            "sha256":digest(line),
            "locked":True
        }
        for i,line in enumerate(lines)
    }
    save_json(LINES,records)
    save_json(UNLOCKED,[])
    MANIFEST.write_text(
        digest(json.dumps(records,sort_keys=True,separators=(",",":"))),
        encoding="utf-8"
    )
    print(f"LOCKED: {SOURCE}")
    print(f"LINES: {len(lines)}")
    print("EVERY LINE: LOCKED")
    print(f"MANIFEST: {MANIFEST}")

def verify():
    if not LINES.exists() or not MANIFEST.exists():
        print("LOCK SYSTEM NOT INITIALIZED")
        return 2

    records=json.loads(LINES.read_text(encoding="utf-8"))
    expected=MANIFEST.read_text(encoding="utf-8").strip()
    actual=digest(json.dumps(records,sort_keys=True,separators=(",",":")))

    if actual!=expected:
        print("FAIL: LOCK MANIFEST TAMPERED")
        return 3

    lines=load_lines()
    failures=[]

    if len(lines)!=len(records):
        failures.append(
            f"LINE COUNT CHANGED: locked={len(records)} current={len(lines)}"
        )

    for number,record in records.items():
        n=int(number)
        if n>len(lines):
            failures.append(f"LINE {n}: DELETED")
            continue
        current=digest(lines[n-1])
        if current!=record["sha256"] and record["locked"]:
            failures.append(f"LINE {n}: CHANGED WHILE LOCKED")

    if failures:
        print("LOCK VERIFICATION FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 4

    print("LOCK VERIFICATION PASSED")
    print(f"LINES VERIFIED: {len(lines)}")
    print("EVERY LOCKED LINE: INTEGRITY OK")
    return 0

def unlock(number):
    records=json.loads(LINES.read_text(encoding="utf-8"))
    key=str(number)

    if key not in records:
        print(f"INVALID LINE: {number}")
        return 2

    unlocked=json.loads(UNLOCKED.read_text(encoding="utf-8"))
    if number not in unlocked:
        unlocked.append(number)
    save_json(UNLOCKED,sorted(set(unlocked)))

    records[key]["locked"]=False
    save_json(LINES,records)
    MANIFEST.write_text(
        digest(json.dumps(records,sort_keys=True,separators=(",",":"))),
        encoding="utf-8"
    )
    print(f"UNLOCKED LINE: {number}")
    print("LINE MAY NOW BE EDITED")

def relock(number):
    lines=load_lines()
    records=json.loads(LINES.read_text(encoding="utf-8"))
    key=str(number)

    if key not in records:
        print(f"INVALID LINE: {number}")
        return 2

    n=int(number)
    if n<1 or n>len(lines):
        print(f"LINE DOES NOT EXIST: {number}")
        return 2

    records[key]={
        "sha256":digest(lines[n-1]),
        "locked":True
    }

    unlocked=json.loads(UNLOCKED.read_text(encoding="utf-8"))
    unlocked=[x for x in unlocked if x!=number]
    save_json(UNLOCKED,sorted(set(unlocked)))
    save_json(LINES,records)

    MANIFEST.write_text(
        digest(json.dumps(records,sort_keys=True,separators=(",",":"))),
        encoding="utf-8"
    )

    print(f"RELOCKED LINE: {number}")
    print("LINE IS NOW LOCKED")

def status():
    records=json.loads(LINES.read_text(encoding="utf-8"))
    unlocked=json.loads(UNLOCKED.read_text(encoding="utf-8"))
    locked=sum(1 for r in records.values() if r["locked"])
    print(f"SOURCE: {SOURCE}")
    print(f"TOTAL LINES: {len(records)}")
    print(f"LOCKED: {locked}")
    print(f"UNLOCKED: {len(unlocked)}")
    if unlocked:
        print("UNLOCKED LINES:",",".join(map(str,sorted(unlocked))))

def main():
    if len(sys.argv)==1:
        lock_all()
        return

    command=sys.argv[1].lower()

    if command=="lock":
        if len(sys.argv)==2:
            lock_all()
        else:
            relock(int(sys.argv[2]))
    elif command=="unlock" and len(sys.argv)==3:
        unlock(int(sys.argv[2]))
    elif command=="verify":
        raise SystemExit(verify())
    elif command=="status":
        status()
    else:
        print("USAGE:")
        print("  python3 crt_lock.py")
        print("  python3 crt_lock.py lock")
        print("  python3 crt_lock.py unlock LINE")
        print("  python3 crt_lock.py lock LINE")
        print("  python3 crt_lock.py verify")
        print("  python3 crt_lock.py status")
        raise SystemExit(2)

if __name__=="__main__":
    main()
