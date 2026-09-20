#!/usr/bin/env python3
import ast
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CRT=Path("universal_crt_v4.py")
LOCKDIR=Path(".crt_lock")
LOCKFILE=LOCKDIR/"line_hashes.json"
STATE=LOCKDIR/"architecture_baseline.json"
BACKUPS=LOCKDIR/"cat_backups"
CANDIDATE=Path(".crt_lock/cat_candidate.py")

REQUIRED_FUNCTIONS=[
    "main",
    "_multi_render",
    "_multi_key",
    "fetch_candles",
    "_fetch_pair",
]

GEOMETRY={
    "BASE_WIDTH":112,
    "BASE_HEIGHT":32,
    "CHART_L":5,
    "CHART_R":84,
    "AXIS_L":85,
    "AXIS_R":88,
    "MENU_L":90,
    "MENU_R":110,
}

ANDROID_NAMES=[
    "android_main",
    "send_key",
    "read_output",
    "running",
    "prepare",
    "start",
    "stop",
]

FORBIDDEN_SILENT_PATTERNS=[
    "except Exception:",
    "except BaseException:",
]

NETWORK_MARKERS=[
    "urllib.request",
    "urlopen",
    "requests.",
    "http://",
    "https://",
]

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha256_file(path):
    return sha256_bytes(path.read_bytes())

def load_source(path):
    return path.read_text(encoding="utf-8")

def parse_source(path):
    return ast.parse(load_source(path),filename=str(path))

def names_from_ast(tree):
    defined=set()
    called=set()
    imported=set()

    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node,ast.Name):
            if isinstance(node.ctx,ast.Load):
                called.add(node.id)
            elif isinstance(node.ctx,(ast.Store,ast.Del)):
                defined.add(node.id)
        elif isinstance(node,ast.Import):
            for item in node.names:
                imported.add(item.asname or item.name.split(".")[0])
        elif isinstance(node,ast.ImportFrom):
            for item in node.names:
                if item.name!="*":
                    imported.add(item.asname or item.name)

    builtin_names=set(dir(__builtins__))
    undefined=sorted(
        x for x in called
        if x not in defined
        and x not in imported
        and x not in builtin_names
    )
    return defined,called,imported,undefined

def function_map(tree):
    result={}

    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            calls=[]
            for child in ast.walk(node):
                if isinstance(child,ast.Call):
                    if isinstance(child.func,ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func,ast.Attribute):
                        calls.append(child.func.attr)

            result[node.name]={
                "line":node.lineno,
                "end_line":getattr(node,"end_lineno",node.lineno),
                "args":[a.arg for a in node.args.args],
                "calls":sorted(set(calls)),
            }

    return result

def class_map(tree):
    result={}

    for node in ast.walk(tree):
        if isinstance(node,ast.ClassDef):
            methods=[
                x.name for x in node.body
                if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))
            ]
            result[node.name]={
                "line":node.lineno,
                "end_line":getattr(node,"end_lineno",node.lineno),
                "methods":methods,
            }

    return result

def constants_from_source(text):
    found={}
    tree=ast.parse(text)

    for node in ast.walk(tree):
        if not isinstance(node,ast.Assign):
            continue

        if len(node.targets)!=1:
            continue

        target=node.targets[0]
        value=node.value

        if isinstance(target,ast.Name):
            if target.id in GEOMETRY and isinstance(value,ast.Constant):
                if isinstance(value.value,int):
                    found[target.id]=value.value

        elif isinstance(target,ast.Tuple) and isinstance(value,ast.Tuple):
            if len(target.elts)!=len(value.elts):
                continue

            for target_item,value_item in zip(target.elts,value.elts):
                if (
                    isinstance(target_item,ast.Name)
                    and target_item.id in GEOMETRY
                    and isinstance(value_item,ast.Constant)
                    and isinstance(value_item.value,int)
                ):
                    found[target_item.id]=value_item.value

    return found

def architecture(path):
    text=load_source(path)
    tree=parse_source(path)
    defined,called,imported,undefined=names_from_ast(tree)

    return {
        "sha256":sha256_file(path),
        "lines":len(text.splitlines(keepends=True)),
        "functions":function_map(tree),
        "classes":class_map(tree),
        "defined":sorted(defined),
        "called":sorted(called),
        "imports":sorted(imported),
        "undefined":undefined,
        "geometry":constants_from_source(text),
        "has_main":"main" in defined,
        "has_android_main":"android_main" in defined,
        "has_multirender":"_multi_render" in defined,
        "has_multikey":"_multi_key" in defined,
        "has_fetch":"fetch_candles" in defined,
        "has_pair_fetch":"_fetch_pair" in defined,
        "has_terminal_imports":any(
            x in imported for x in ["termios","tty","select"]
        ),
        "network_markers":[
            x for x in NETWORK_MARKERS if x in text
        ],
        "silent_exception_count":sum(
            text.count(x) for x in FORBIDDEN_SILENT_PATTERNS
        ),
        "fallback_data":"fallback_data" in text,
        "tf_order":"TF_ORDER" in text,
        "state":"state" in text,
    }

def print_header(title):
    print()
    print("="*78)
    print("CAT INJECTION MODULE :: "+title)
    print("="*78)

def save_baseline():
    print_header("ARCHITECTURE BASELINE")

    if not CRT.exists():
        print("[FAIL] universal_crt_v4.py not found")
        return 1

    try:
        data=architecture(CRT)
    except Exception as exc:
        print("[FAIL] Cannot parse CRT")
        print(f"       {type(exc).__name__}: {exc}")
        return 1

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(
        json.dumps(data,indent=2,ensure_ascii=False)+"\n",
        encoding="utf-8"
    )

    print(f"[BASELINE] {CRT}")
    print(f"[SHA256]   {data['sha256']}")
    print(f"[LINES]    {data['lines']}")
    print(f"[FUNCS]    {len(data['functions'])}")
    print(f"[CLASSES]  {len(data['classes'])}")
    print(f"[IMPORTS]  {len(data['imports'])}")
    print(f"[GEOMETRY] {data['geometry']}")
    print(f"[ANDROID]  {'YES' if data['has_android_main'] else 'NO'}")
    print(f"[FALLBACK] {'YES' if data['fallback_data'] else 'NO'}")
    print(f"[STATE]    {'YES' if data['state'] else 'NO'}")
    print(f"[SAVED]    {STATE}")

    return 0

def load_baseline():
    if not STATE.exists():
        print("[INFO] No architecture baseline exists.")
        print("[INFO] Create it with option B or:")
        print("       python3 crt_cat_injection.py baseline")
        return None

    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAIL] Architecture baseline unreadable: {exc}")
        return None

def locked_lines():
    if not LOCKFILE.exists():
        return None

    try:
        records=json.loads(
            LOCKFILE.read_text(encoding="utf-8")
        )
        return records
    except Exception:
        return None

def changed_lines(old,new):
    old_lines=old.splitlines(keepends=True)
    new_lines=new.splitlines(keepends=True)

    matcher=difflib.SequenceMatcher(
        None,
        old_lines,
        new_lines,
        autojunk=False
    )

    changes=[]

    for tag,i1,i2,j1,j2 in matcher.get_opcodes():
        if tag=="equal":
            continue

        old_numbers=list(range(i1+1,i2+1))
        new_numbers=list(range(j1+1,j2+1))

        changes.append({
            "type":tag,
            "old_start":i1+1,
            "old_end":i2,
            "new_start":j1+1,
            "new_end":j2,
            "old_lines":old_numbers,
            "new_lines":new_numbers,
        })

    return changes

def lock_conflicts(changes,records):
    if records is None:
        return [],["LINE-LOCK MANIFEST NOT AVAILABLE"]

    conflicts=[]
    unlocked=[]

    for change in changes:
        for n in change["old_lines"]:
            record=records.get(str(n))

            if record is None:
                continue

            if record.get("locked",True):
                conflicts.append(n)
            else:
                unlocked.append(n)

    return sorted(set(conflicts)),sorted(set(unlocked))

def compare_architecture(base,candidate):
    issues=[]
    warnings=[]
    passes=[]

    for required in REQUIRED_FUNCTIONS:
        if required not in candidate["functions"]:
            issues.append(
                f"REQUIRED FUNCTION REMOVED: {required}"
            )
        elif required in base.get("functions",{}):
            passes.append(f"FUNCTION PRESERVED: {required}")

    for name in base.get("functions",{}):
        if name not in candidate["functions"]:
            issues.append(
                f"BASELINE FUNCTION DISAPPEARED: {name}"
            )

    for name in base.get("classes",{}):
        if name not in candidate["classes"]:
            issues.append(
                f"BASELINE CLASS DISAPPEARED: {name}"
            )

    for key,expected in base.get("geometry",{}).items():
        actual=candidate.get("geometry",{}).get(key)

        if actual is None:
            warnings.append(
                f"GEOMETRY CONSTANT NOT DETECTED: {key}"
            )
        elif actual!=expected:
            issues.append(
                f"GEOMETRY INVARIANT CHANGED: {key} "
                f"{expected} -> {actual}"
            )
        else:
            passes.append(f"GEOMETRY PRESERVED: {key}={expected}")

    if base.get("has_main") and not candidate["has_main"]:
        issues.append("EXECUTION ENTRY POINT main() REMOVED")

    if base.get("has_multirender") and not candidate["has_multirender"]:
        issues.append("_multi_render() REMOVED")

    if base.get("has_multikey") and not candidate["has_multikey"]:
        issues.append("_multi_key() REMOVED")

    if base.get("has_fetch") and not candidate["has_fetch"]:
        issues.append("fetch_candles() REMOVED")

    if base.get("has_pair_fetch") and not candidate["has_pair_fetch"]:
        issues.append("_fetch_pair() REMOVED")

    if base.get("tf_order") and not candidate["tf_order"]:
        issues.append("TF_ORDER ARCHITECTURE REMOVED")

    if base.get("state") and not candidate["state"]:
        issues.append("GLOBAL STATE ARCHITECTURE REMOVED")

    if base.get("fallback_data") and not candidate["fallback_data"]:
        warnings.append(
            "fallback_data() removed; network-failure behavior changed"
        )

    if candidate["silent_exception_count"] > base.get(
        "silent_exception_count",0
    ):
        warnings.append(
            "NEW BROAD/SILENT EXCEPTION HANDLING DETECTED"
        )

    for marker in base.get("network_markers",[]):
        if marker not in candidate["network_markers"]:
            warnings.append(
                f"NETWORK ARCHITECTURE MARKER REMOVED: {marker}"
            )

    base_android=base.get("has_android_main",False)
    cand_android=candidate.get("has_android_main",False)

    if base_android and not cand_android:
        issues.append(
            "ANDROID EXECUTION ENTRY POINT android_main() REMOVED"
        )

    if cand_android and not base_android:
        warnings.append(
            "ANDROID ENTRY POINT ADDED; desktop architecture remains separate"
        )

    if candidate["undefined"]:
        warnings.append(
            "POTENTIAL UNRESOLVED SYMBOLS: "+
            ",".join(candidate["undefined"][:20])
        )

    if len(candidate["lines"]) if False else False:
        pass

    return issues,warnings,passes

def python_compile(path):
    result=subprocess.run(
        [sys.executable,"-m","py_compile",str(path)],
        capture_output=True,
        text=True
    )

    if result.returncode==0:
        return True,"PYTHON COMPILE PASSED"

    message=(result.stderr or result.stdout).strip()
    return False,message

def candidate_report(candidate_path):
    print_header("PROPOSED UPGRADE ANALYSIS")

    if not CRT.exists():
        print("[FAIL] CRT does not exist")
        return 1

    if not candidate_path.exists():
        print(f"[FAIL] Candidate does not exist: {candidate_path}")
        return 1

    base=load_baseline()

    if base is None:
        print("[FAIL] Architecture baseline required before injection")
        return 1

    try:
        old=load_source(CRT)
        new=load_source(candidate_path)
        cand=architecture(candidate_path)
    except SyntaxError as exc:
        print("[REJECT]")
        print(f"[SYNTAX ERROR] line {exc.lineno}: {exc.msg}")
        return 2
    except Exception as exc:
        print("[REJECT]")
        print(f"[LOAD ERROR] {type(exc).__name__}: {exc}")
        return 2

    ok,message=python_compile(candidate_path)

    if not ok:
        print("[REJECT] PYTHON SYNTAX FAILURE")
        print(message)
        return 2

    print("[PASS] Candidate compiles")

    changes=changed_lines(old,new)

    print(f"[DIFF] Changed regions: {len(changes)}")

    records=locked_lines()
    conflicts,unlocked=lock_conflicts(changes,records)

    if conflicts:
        print()
        print("[REJECT] LOCKED-LINE CONFLICT")
        print(
            "The proposed upgrade attempts to modify locked CRT lines:"
        )
        print(" ".join(map(str,conflicts[:100])))
        print()
        print("Required action:")
        print("  Explicitly unlock the exact intended lines first.")
        return 3

    if unlocked:
        print(
            "[INFO] Changed lines already explicitly unlocked: "+
            ",".join(map(str,unlocked[:100]))
        )

    issues,warnings,passes=compare_architecture(base,cand)

    print()
    print("[ARCHITECTURE PASSES]")
    for item in passes:
        print("  + "+item)

    print()
    print("[ARCHITECTURE WARNINGS]")
    for item in warnings:
        print("  ! "+item)

    print()
    print("[ARCHITECTURE ERRORS]")
    for item in issues:
        print("  X "+item)

    print()
    print("[CANDIDATE]")
    print(f"  SHA256 : {cand['sha256']}")
    print(f"  LINES  : {cand['lines']}")
    print(f"  FUNCS  : {len(cand['functions'])}")
    print(f"  CLASSES: {len(cand['classes'])}")

    if issues:
        print()
        print("RESULT: REJECTED")
        print("REASON: ARCHITECTURE INCOMPATIBILITY")
        print("FIX CATEGORY:")
        for item in issues:
            print("  -> "+classify_issue(item))
        return 4

    print()
    print("RESULT: PRE-INJECTION COMPATIBLE")
    print("STATUS: READY FOR EXPLICIT APPLY")
    return 0

def classify_issue(issue):
    text=issue.upper()

    if "FUNCTION" in text or "ENTRY POINT" in text:
        return "STRUCTURAL / EXECUTION PATH FIX"
    if "GEOMETRY" in text:
        return "RENDERER / VIEWPORT INVARIANT FIX"
    if "CLASS" in text:
        return "OBJECT MODEL / STRUCTURE FIX"
    if "STATE" in text:
        return "GLOBAL STATE / DATA FLOW FIX"
    if "ANDROID" in text:
        return "ANDROID / CHAQUOPY BRIDGE FIX"
    if "TF_ORDER" in text:
        return "TIMEFRAME MODEL FIX"
    if "SYNTAX" in text:
        return "PYTHON SYNTAX FIX"

    return "ARCHITECTURE COMPATIBILITY FIX"

def make_backup():
    BACKUPS.mkdir(parents=True,exist_ok=True)

    stamp=time.strftime("%Y%m%d_%H%M%S")
    backup=BACKUPS/f"universal_crt_v4.py.{stamp}.bak"

    shutil.copy2(CRT,backup)

    metadata={
        "source":str(CRT),
        "backup":str(backup),
        "sha256":sha256_file(CRT),
        "created":time.time(),
    }

    (backup.with_suffix(".json")).write_text(
        json.dumps(metadata,indent=2)+"\n",
        encoding="utf-8"
    )

    return backup

def post_verify(expected_baseline):
    print_header("POST-INJECTION STRUCTURAL VERIFICATION")

    try:
        current=architecture(CRT)
    except SyntaxError as exc:
        print("[FAIL] Syntax error after injection")
        print(f"       line {exc.lineno}: {exc.msg}")
        return False

    ok,message=python_compile(CRT)

    if not ok:
        print("[FAIL] Post-injection compile failed")
        print(message)
        return False

    print("[PASS] Python compilation")

    issues,warnings,passes=compare_architecture(
        expected_baseline,
        current
    )

    for item in passes:
        print("[PASS] "+item)

    for item in warnings:
        print("[WARN] "+item)

    for item in issues:
        print("[FAIL] "+item)

    if issues:
        return False

    print("[PASS] Architecture invariants preserved")
    return True

def apply_candidate(candidate_path):
    print_header("CAT EXPLICIT INJECTION")

    if not CRT.exists():
        print("[FAIL] CRT not found")
        return 1

    if not candidate_path.exists():
        print(f"[FAIL] Candidate not found: {candidate_path}")
        return 1

    base=load_baseline()

    if base is None:
        print("[FAIL] Establish architecture baseline first")
        return 1

    result=candidate_report(candidate_path)

    if result!=0:
        print()
        print("[CAT] INJECTION BLOCKED")
        print("[CAT] Candidate did not pass pre-injection validation")
        return result

    print()
    print("PRE-INJECTION VALIDATION PASSED.")
    print("This operation will replace the CRT with the candidate.")
    print("A rollback snapshot will be created first.")
    print()

    answer=input("TYPE APPLY TO CONTINUE: ").strip()

    if answer!="APPLY":
        print("[CAT] Injection cancelled.")
        return 0

    backup=make_backup()

    try:
        shutil.copy2(candidate_path,CRT)
    except Exception as exc:
        print("[FAIL] Injection write failed")
        print(f"       {type(exc).__name__}: {exc}")
        return 5

    print(f"[BACKUP] {backup}")
    print("[WRITE] Candidate installed")

    if post_verify(base):
        print()
        print("[SUCCESS] CAT INJECTION VERIFIED")
        print("[SUCCESS] Upgrade preserved baseline architecture")
        return 0

    print()
    print("[FAIL] POST-INJECTION VERIFICATION FAILED")
    print("[CAT] AUTOMATIC ROLLBACK STARTING")

    try:
        shutil.copy2(backup,CRT)
        print("[ROLLBACK] CRT restored")
    except Exception as exc:
        print("[CRITICAL] ROLLBACK FAILED")
        print(f"           {type(exc).__name__}: {exc}")
        return 6

    if sha256_file(CRT)==base["sha256"]:
        print("[ROLLBACK] BASELINE SHA256 RESTORED")
    else:
        print("[CRITICAL] BASELINE HASH NOT RESTORED")
        return 7

    print("[RESULT] INJECTION REJECTED")
    return 8

def diff_view(candidate_path):
    print_header("CAT ARCHITECTURE DIFF")

    if not CRT.exists() or not candidate_path.exists():
        print("[FAIL] CRT or candidate missing")
        return 1

    old=load_source(CRT).splitlines()
    new=load_source(candidate_path).splitlines()

    diff=difflib.unified_diff(
        old,
        new,
        fromfile=str(CRT),
        tofile=str(candidate_path),
        lineterm=""
    )

    found=False

    for line in diff:
        print(line)
        found=True

    if not found:
        print("[PASS] Candidate is byte-content identical")

    return 0

def line_analysis(candidate_path):
    print_header("CAT LOCK / LINE ANALYSIS")

    if not CRT.exists() or not candidate_path.exists():
        print("[FAIL] CRT or candidate missing")
        return 1

    records=locked_lines()

    if records is None:
        print("[FAIL] Lock manifest unavailable")
        return 1

    old=load_source(CRT)
    new=load_source(candidate_path)

    changes=changed_lines(old,new)

    if not changes:
        print("[PASS] No changed lines")
        return 0

    for change in changes:
        print()
        print(
            f"{change['type'].upper()} "
            f"OLD {change['old_start']}-{change['old_end']} "
            f"NEW {change['new_start']}-{change['new_end']}"
        )

        locked=[]
        unlocked=[]

        for number in change["old_lines"]:
            record=records.get(str(number))
            if not record:
                continue

            if record.get("locked",True):
                locked.append(number)
            else:
                unlocked.append(number)

        if locked:
            print(
                "[BLOCKED LOCKED LINES]: "+
                ",".join(map(str,locked))
            )

        if unlocked:
            print(
                "[AUTHORIZED UNLOCKED LINES]: "+
                ",".join(map(str,unlocked))
            )

    return 0

def rollback_latest():
    print_header("CAT ROLLBACK")

    if not BACKUPS.exists():
        print("[FAIL] No CAT backups")
        return 1

    backups=sorted(
        BACKUPS.glob("universal_crt_v4.py.*.bak"),
        key=lambda p:p.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("[FAIL] No CAT backup available")
        return 1

    backup=backups[0]

    print(f"[LATEST] {backup}")
    print(f"[SHA256] {sha256_file(backup)}")

    answer=input("TYPE ROLLBACK TO RESTORE: ").strip()

    if answer!="ROLLBACK":
        print("[CAT] Rollback cancelled.")
        return 0

    shutil.copy2(backup,CRT)

    print("[PASS] CRT restored")
    print(f"[SHA256] {sha256_file(CRT)}")

    return 0

def function_map_view():
    print_header("CRT ARCHITECTURE MAP")

    try:
        tree=parse_source(CRT)
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        return 1

    functions=function_map(tree)

    for name,data in functions.items():
        calls=", ".join(data["calls"]) or "none"
        print(
            f"{name} "
            f"[L{data['line']}-{data['end_line']}] "
            f"-> {calls}"
        )

    return 0

def status():
    print_header("CAT STATUS")

    print(f"CRT: {CRT}")
    print(f"EXISTS: {CRT.exists()}")

    if CRT.exists():
        print(f"SHA256: {sha256_file(CRT)}")
        print(f"LINES: {len(load_source(CRT).splitlines(keepends=True))}")

    print(f"BASELINE: {STATE.exists()}")
    print(f"LOCKFILE: {LOCKFILE.exists()}")
    print(f"BACKUP DIRECTORY: {BACKUPS}")

    records=locked_lines()

    if records:
        locked=sum(
            1 for record in records.values()
            if record.get("locked",True)
        )
        unlocked=len(records)-locked
        print(f"LOCKED LINES: {locked}")
        print(f"UNLOCKED LINES: {unlocked}")

    base=load_baseline()

    if base:
        print(f"BASELINE SHA256: {base.get('sha256')}")
        print(f"BASELINE LINES: {base.get('lines')}")
        print(
            "BASELINE ARCHITECTURE: "
            f"{len(base.get('functions',{}))} functions / "
            f"{len(base.get('classes',{}))} classes"
        )

def create_candidate():
    print_header("CAT CANDIDATE CREATOR")

    CANDIDATE.parent.mkdir(parents=True,exist_ok=True)

    if CANDIDATE.exists():
        print(f"[EXISTS] {CANDIDATE}")
        answer=input("TYPE OVERWRITE TO REPLACE IT: ").strip()
        if answer!="OVERWRITE":
            print("[CANCELLED]")
            return 0

    shutil.copy2(CRT,CANDIDATE)

    print(f"[CREATED] {CANDIDATE}")
    print()
    print("Edit ONLY the candidate:")
    print(f"  {CANDIDATE}")
    print()
    print("Then run:")
    print(f"  python3 crt_cat_injection.py inspect {CANDIDATE}")
    print(f"  python3 crt_cat_injection.py diff {CANDIDATE}")
    print(f"  python3 crt_cat_injection.py apply {CANDIDATE}")

    return 0

def menu():
    while True:
        print_header("CONTROL CENTER")

        print("[1] BUILD / REFRESH ARCHITECTURE BASELINE")
        print("[2] INSPECT CANDIDATE")
        print("[3] LOCK-LINE ANALYSIS")
        print("[4] ARCHITECTURE DIFF")
        print("[5] CRT FUNCTION / CALL MAP")
        print("[6] APPLY VERIFIED CANDIDATE")
        print("[7] ROLLBACK LATEST CAT INJECTION")
        print("[8] CREATE CANDIDATE FROM CURRENT CRT")
        print("[9] CAT STATUS")
        print("[Q] QUIT")

        choice=input("\nCAT> ").strip().lower()

        if choice=="1":
            save_baseline()

        elif choice=="2":
            path=input(
                "Candidate path [.crt_lock/cat_candidate.py]: "
            ).strip() or str(CANDIDATE)
            candidate_report(Path(path))

        elif choice=="3":
            path=input(
                "Candidate path [.crt_lock/cat_candidate.py]: "
            ).strip() or str(CANDIDATE)
            line_analysis(Path(path))

        elif choice=="4":
            path=input(
                "Candidate path [.crt_lock/cat_candidate.py]: "
            ).strip() or str(CANDIDATE)
            diff_view(Path(path))

        elif choice=="5":
            function_map_view()

        elif choice=="6":
            path=input(
                "Candidate path [.crt_lock/cat_candidate.py]: "
            ).strip() or str(CANDIDATE)
            apply_candidate(Path(path))

        elif choice=="7":
            rollback_latest()

        elif choice=="8":
            create_candidate()

        elif choice=="9":
            status()

        elif choice=="q":
            print("CAT INJECTION MODULE OFFLINE")
            break

        else:
            print("[INVALID] Select 1-9 or Q.")

def usage():
    print(
        """
CAT INJECTION MODULE

Commands:

  baseline
      Build architecture baseline from universal_crt_v4.py

  inspect CANDIDATE
      Pre-injection architecture validation

  diff CANDIDATE
      Show exact source differences

  lines CANDIDATE
      Check changed lines against CRT lock

  apply CANDIDATE
      Validate, request explicit APPLY, inject, verify, rollback on failure

  rollback
      Restore latest CAT backup

  map
      Show CRT function/call architecture

  status
      Show CAT/CRT/lock state

  create
      Create a candidate copy of the current CRT

  menu
      Open CAT Injection Control Center
"""
    )

def main():
    if len(sys.argv)==1:
        menu()
        return 0

    command=sys.argv[1].lower()

    if command=="baseline":
        return save_baseline()

    if command=="inspect" and len(sys.argv)>=3:
        return candidate_report(Path(sys.argv[2]))

    if command=="diff" and len(sys.argv)>=3:
        return diff_view(Path(sys.argv[2]))

    if command=="lines" and len(sys.argv)>=3:
        return line_analysis(Path(sys.argv[2]))

    if command=="apply" and len(sys.argv)>=3:
        return apply_candidate(Path(sys.argv[2]))

    if command=="rollback":
        return rollback_latest()

    if command=="map":
        return function_map_view()

    if command=="status":
        status()
        return 0

    if command=="create":
        return create_candidate()

    if command=="menu":
        menu()
        return 0

    usage()
    return 2

if __name__=="__main__":
    raise SystemExit(main())
