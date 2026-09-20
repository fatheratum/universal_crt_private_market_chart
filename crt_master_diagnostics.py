#!/usr/bin/env python3
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path.cwd()
CRT=ROOT/"universal_crt_v4.py"
ANDROID_CRT=ROOT/"app/src/main/assets/universal_crt_v4.py"
LOCKDIR=ROOT/".crt_lock"
LOCKS=LOCKDIR/"line_hashes.json"
MANIFEST=LOCKDIR/"manifest.sha256"

W=112
H=32

RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
BLUE="\033[34m"
WHITE="\033[37m"
DIM="\033[2m"

ERRORS=[]
WARNINGS=[]
PASSES=[]
DETAILS=[]

def record_pass(name,msg):
    PASSES.append((name,msg))

def record_warn(name,msg):
    WARNINGS.append((name,msg))

def record_error(name,msg):
    ERRORS.append((name,msg))

def reset_results():
    ERRORS.clear()
    WARNINGS.clear()
    PASSES.clear()
    DETAILS.clear()

def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return ""

def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()

def digest_text(text):
    return digest_bytes(text.encode("utf-8"))

def run(cmd,timeout=30):
    try:
        p=subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )
        return p.returncode,p.stdout
    except Exception as e:
        return 999,str(e)

def terminal_size():
    s=shutil.get_terminal_size((W,H))
    return max(60,s.columns),max(20,s.lines)

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def pause():
    input("\nPRESS ENTER TO CONTINUE...")

def header(title):
    clear()
    print(CYAN+BOLD+"╔"+"═"*110+"╗"+RESET)
    print(CYAN+BOLD+"║"+" UNIVERSAL CRT | MASTER DIAGNOSTICS CONSOLE".ljust(110)+"║"+RESET)
    print(CYAN+BOLD+"╠"+"═"*110+"╣"+RESET)
    print(CYAN+"║ "+WHITE+title.ljust(108)+CYAN+"║"+RESET)
    print(CYAN+BOLD+"╚"+"═"*110+"╝"+RESET)
    print()

def line():
    print(DIM+"─"*112+RESET)

def status(ok):
    return GREEN+"PASS"+RESET if ok else RED+"FAIL"+RESET

def scan_required():
    header("SYSTEM FILE INVENTORY")

    required=[
        "universal_crt_v4.py",
        "crt_lock.py",
        "crt_master_diagnostics.py",
        "settings.gradle",
        "build.gradle",
        "app/build.gradle",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/java/com/fatheratum/omniterminal/MainActivity.kt",
        "app/src/main/java/com/fatheratum/omniterminal/PtyProcess.kt",
        "app/src/main/java/com/fatheratum/omniterminal/TerminalView.kt",
        "app/src/main/python/omni_runner.py",
        "app/src/main/assets/universal_crt_v4.py",
        ".github/workflows/android.yml",
    ]

    for item in required:
        exists=(ROOT/item).is_file()
        print(f"{status(exists)}  {item}")
        if exists:
            record_pass("FILE",item)
        else:
            record_error("FILE",f"MISSING: {item}")

def scan_lock():
    header("LINE-BY-LINE SOURCE LOCK")

    if not CRT.is_file():
        record_error("LOCK","universal_crt_v4.py missing")
        print(RED+"FAIL: CRT SOURCE MISSING"+RESET)
        return

    if not LOCKS.is_file():
        record_error("LOCK","line_hashes.json missing")
        print(RED+"FAIL: LOCK DATABASE MISSING"+RESET)
        return

    if not MANIFEST.is_file():
        record_error("LOCK","manifest.sha256 missing")
        print(RED+"FAIL: LOCK MANIFEST MISSING"+RESET)
        return

    try:
        records=json.loads(LOCKS.read_text(encoding="utf-8"))
    except Exception as e:
        record_error("LOCK",f"Invalid lock database: {e}")
        return

    expected=MANIFEST.read_text(encoding="utf-8").strip()
    actual=digest_text(
        json.dumps(records,sort_keys=True,separators=(",",":"))
    )

    if expected!=actual:
        record_error("LOCK","LOCK MANIFEST HASH MISMATCH")
        print(RED+"FAIL: MANIFEST TAMPERED OR DRIFTED"+RESET)
        return

    lines=CRT.read_text(encoding="utf-8").splitlines(keepends=True)

    print(f"SOURCE LINES : {len(lines)}")
    print(f"LOCK RECORDS : {len(records)}")
    line()

    if len(lines)!=len(records):
        record_error(
            "LOCK",
            f"LINE COUNT MISMATCH source={len(lines)} locked={len(records)}"
        )

    changed=0
    unlocked=0

    for number,record in records.items():
        n=int(number)

        if not record.get("locked",False):
            unlocked+=1
            continue

        if n>len(lines):
            changed+=1
            record_error("LOCK",f"LOCKED LINE {n} WAS DELETED")
            continue

        current=digest_text(lines[n-1])

        if current!=record.get("sha256"):
            changed+=1
            record_error("LOCK",f"LOCK VIOLATION AT LINE {n}")

    print(f"LOCKED       : {len(records)-unlocked}")
    print(f"UNLOCKED     : {unlocked}")
    print(f"CHANGED      : {changed}")

    if changed==0 and len(lines)==len(records):
        record_pass("LOCK","ALL LOCKED LINES VERIFIED")
        print(GREEN+"LOCK INTEGRITY: PASS"+RESET)
    else:
        print(RED+"LOCK INTEGRITY: FAIL"+RESET)

def scan_python():
    header("PYTHON COMPILER / AST DIAGNOSTICS")

    targets=[
        CRT,
        ROOT/"crt_lock.py",
        ROOT/"crt_master_diagnostics.py",
        ROOT/"app/src/main/python/omni_runner.py",
    ]

    for path in targets:
        if not path.is_file():
            continue

        rc,out=run([sys.executable,"-m","py_compile",str(path)])

        if rc==0:
            print(GREEN+"PASS"+RESET,f"{path}")
            record_pass("PYTHON",f"Syntax valid: {path}")
        else:
            print(RED+"FAIL"+RESET,f"{path}")
            print(out)
            record_error("PYTHON",f"Syntax failure: {path}")

    if CRT.is_file():
        source=read(CRT)

        try:
            tree=ast.parse(source,filename=str(CRT))
            functions=[
                n for n in ast.walk(tree)
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
            ]

            classes=[
                n for n in ast.walk(tree)
                if isinstance(n,ast.ClassDef)
            ]

            print()
            print(f"CRT FUNCTIONS : {len(functions)}")
            print(f"CRT CLASSES   : {len(classes)}")
            print(f"AST PARSE     : {GREEN}PASS{RESET}")
            record_pass("AST","CRT AST parsed successfully")

            seen={}

            for fn in functions:
                seen.setdefault(fn.name,[]).append(fn.lineno)

            for name,locations in sorted(seen.items()):
                if len(locations)>1:
                    record_warn(
                        "AST",
                        f"Duplicate function {name}: {locations}"
                    )

        except SyntaxError as e:
            record_error(
                "AST",
                f"Parse failure line {e.lineno}: {e.msg}"
            )

def scan_crt_structure():
    header("CRT STRUCTURE / FUNCTION MATRIX")

    source=read(CRT)

    required=[
        "clamp",
        "fetch_candles",
        "fallback_data",
        "aggregate",
        "visible",
        "price_range",
        "py",
        "money",
        "put",
        "frame",
        "draw_price_axis",
        "draw_candles",
        "draw_trend",
        "draw_time",
        "_fetch_pair",
        "_multi_add_chart",
        "_multi_remove_or_toggle",
        "_multi_visible",
        "_multi_refresh",
        "_multi_slots",
        "_multi_draw_chart",
        "_multi_menu",
        "_draw_view_list",
        "_multi_menu_action",
        "_multi_key",
        "_multi_render",
        "main",
    ]

    for name in required:
        found=re.search(
            rf"^\s*def\s+{re.escape(name)}\s*\(",
            source,
            re.MULTILINE
        )

        if found:
            print(GREEN+"PRESENT"+RESET,f"{name}()")
            record_pass("FUNCTION",name)
        else:
            print(RED+"MISSING"+RESET,f"{name}()")
            record_error("FUNCTION",f"Missing CRT function: {name}")

def scan_crt_dependencies():
    header("CRT RUNTIME DEPENDENCY MATRIX")

    source=read(CRT)

    dependencies=[
        ("sys.stdin","terminal input"),
        ("sys.stdout","terminal output"),
        ("termios","Unix terminal control"),
        ("tty","terminal cbreak mode"),
        ("select","terminal input polling"),
        ("shutil.get_terminal_size","terminal geometry"),
        ("urllib.request","market HTTP"),
        ("ssl","TLS"),
        ("json","market data decoding"),
        ("time","timestamps"),
    ]

    for token,description in dependencies:
        found=token in source
        print(
            GREEN+"FOUND"+RESET if found else YELLOW+"ABSENT"+RESET,
            f"{token:<32} {description}"
        )

        if found:
            record_pass("DEPENDENCY",token)

    if "termios" in source and "android_main" not in source:
        record_warn(
            "ANDROID",
            "CRT currently contains terminal-only execution dependencies "
            "without android_main()"
        )

def scan_android():
    header("ANDROID RUNTIME DIAGNOSTICS")

    manifest=read(ROOT/"app/src/main/AndroidManifest.xml")
    main=read(ROOT/"app/src/main/java/com/fatheratum/omniterminal/MainActivity.kt")
    pty=read(ROOT/"app/src/main/java/com/fatheratum/omniterminal/PtyProcess.kt")
    view=read(ROOT/"app/src/main/java/com/fatheratum/omniterminal/TerminalView.kt")
    runner=read(ROOT/"app/src/main/python/omni_runner.py")

    tests=[
        (
            "Manifest landscape",
            'android:screenOrientation="landscape"' in manifest
        ),
        (
            "Manifest exported launcher",
            'android:exported="true"' in manifest
        ),
        (
            "Activity landscape request",
            "SCREEN_ORIENTATION_LANDSCAPE" in main
        ),
        (
            "Chaquopy initialization",
            "Python.start" in pty
        ),
        (
            "Chaquopy Python instance",
            "Python.getInstance" in pty
        ),
        (
            "omni_runner bridge",
            "omni_runner" in pty
        ),
        (
            "CRT asset copied",
            ANDROID_CRT.is_file()
        ),
        (
            "Runner start function",
            "def start(" in runner
        ),
        (
            "Runner input function",
            "def send_key(" in runner
        ),
        (
            "Runner output function",
            "def read_output(" in runner
        ),
        (
            "Runner stop function",
            "def stop(" in runner
        ),
    ]

    for name,ok in tests:
        print(status(ok),name)
        if ok:
            record_pass("ANDROID",name)
        else:
            record_error("ANDROID",name)

    if 'android:screenOrientation="landscape"' in manifest:
        count=manifest.count('android:screenOrientation="landscape"')
        if count>1:
            record_error(
                "ANDROID",
                f"Duplicate manifest screenOrientation attributes: {count}"
            )

def scan_android_drift():
    header("ROOT CRT ↔ ANDROID ASSET DRIFT")

    if not CRT.is_file() or not ANDROID_CRT.is_file():
        record_error("DRIFT","One or both CRT files are missing")
        return

    root=CRT.read_bytes()
    asset=ANDROID_CRT.read_bytes()

    h1=digest_bytes(root)
    h2=digest_bytes(asset)

    print("ROOT CRT SHA256   :",h1)
    print("ANDROID SHA256   :",h2)
    print()

    if root==asset:
        print(GREEN+"BYTE-IDENTICAL: PASS"+RESET)
        record_pass("DRIFT","Android CRT asset identical to root CRT")
    else:
        print(RED+"DRIFT DETECTED: FAIL"+RESET)
        record_error(
            "DRIFT",
            "app/src/main/assets/universal_crt_v4.py differs from root CRT"
        )

def scan_gradle():
    header("GRADLE / CHAQUOPY BUILD DIAGNOSTICS")

    root=read(ROOT/"build.gradle")
    app=read(ROOT/"app/build.gradle")
    workflow=read(ROOT/".github/workflows/android.yml")

    tests=[
        ("Android plugin","com.android.application" in root),
        ("Kotlin plugin","org.jetbrains.kotlin.android" in root),
        ("Chaquopy plugin","com.chaquo.python" in root),
        ("Chaquopy block","chaquopy" in app),
        ("ABI filters","abiFilters" in app),
        ("ARM64 ABI","arm64-v8a" in app),
        ("Java 17 source","sourceCompatibility JavaVersion.VERSION_17" in app),
        ("Java 17 target","targetCompatibility JavaVersion.VERSION_17" in app),
        ("Kotlin JVM 17","jvmTarget = '17'" in app or 'jvmTarget = "17"' in app),
        ("assembleDebug","assembleDebug" in workflow),
        ("APK artifact upload","actions/upload-artifact@v4" in workflow),
    ]

    for name,ok in tests:
        print(status(ok),name)
        if ok:
            record_pass("GRADLE",name)
        else:
            record_error("GRADLE",name)

def scan_workflow():
    header("GITHUB ACTIONS WORKFLOW")

    path=ROOT/".github/workflows/android.yml"
    source=read(path)

    tests=[
        "actions/checkout@v4",
        "actions/setup-java@v5",
        "gradle/actions/setup-gradle@v4",
        "sdkmanager",
        "platforms;android-35",
        "build-tools;35.0.0",
        "gradle assembleDebug",
        "app/build/outputs/apk/debug/app-debug.apk",
        "actions/upload-artifact@v4",
    ]

    for token in tests:
        ok=token in source
        print(status(ok),token)
        if ok:
            record_pass("WORKFLOW",token)
        else:
            record_error("WORKFLOW",f"Missing workflow component: {token}")

def scan_targeted_bugs():
    header("CRT TARGETED BUG HUNT")

    source=read(CRT)

    tests=[
        (
            "ANSI full clear",
            "\033[2J" in source,
            "Full-screen ANSI clear exists"
        ),
        (
            "ANSI cursor addressing",
            "_ansi_at(" in source,
            "Absolute cursor addressing exists"
        ),
        (
            "Terminal stdin",
            "sys.stdin" in source,
            "CRT depends on terminal stdin"
        ),
        (
            "Terminal stdout",
            "sys.stdout" in source,
            "CRT emits terminal output"
        ),
        (
            "Broad swallowed exception",
            bool(re.search(r"except\s+Exception\s*:\s*pass",source)),
            "Exception may be hidden"
        ),
        (
            "Synthetic fallback",
            "fallback_data" in source,
            "Fallback market data path exists"
        ),
        (
            "Android entry point",
            "def android_main(" in source,
            "Android-native CRT renderer exists"
        ),
        (
            "Network timeout",
            "timeout=" in source,
            "HTTP calls have explicit timeout"
        ),
    ]

    for name,found,description in tests:
        if found:
            print(GREEN+"DETECTED"+RESET,name)
            if "swallowed" in name.lower():
                record_warn("BUG",description)
            elif "Synthetic" in name:
                record_warn("DATA",description)
            elif name=="Android entry point":
                record_pass("ANDROID",description)
            else:
                record_pass("CRT",description)
        else:
            print(YELLOW+"NOT DETECTED"+RESET,name)
            if name=="Android entry point":
                record_warn("ANDROID",description)
            elif name=="Network timeout":
                record_warn("NETWORK",description)

def scan_geometry():
    header("CRT GEOMETRY / VIEWPORT VALIDATION")

    source=read(CRT)

    expected={
        "BASE_WIDTH":112,
        "BASE_HEIGHT":32,
        "CHART_L":5,
        "CHART_R":84,
        "AXIS_L":85,
        "AXIS_R":88,
        "MENU_L":90,
        "MENU_R":110,
    }

    for name,value in expected.items():
        match=re.search(
            rf"^\s*{name}\s*=\s*{value}\s*$",
            source,
            re.MULTILINE
        )

        print(status(bool(match)),f"{name} = {value}")

        if match:
            record_pass("GEOMETRY",f"{name}={value}")
        else:
            record_error(
                "GEOMETRY",
                f"{name} expected {value} not found"
            )

def scan_line_integrity():
    header("SOURCE BYTE INTEGRITY")

    if not CRT.is_file():
        record_error("BYTES","CRT missing")
        return

    data=CRT.read_bytes()

    print("BYTE COUNT :",len(data))
    print("LF COUNT   :",data.count(b"\n"))
    print("CRLF COUNT :",data.count(b"\r\n"))
    print("CR COUNT   :",data.count(b"\r"))
    print("SHA256     :",digest_bytes(data))

    if b"\r\n" in data and data.count(b"\r\n")==data.count(b"\n"):
        record_pass("BYTES","CRLF line endings consistent")
    elif b"\r\n" not in data:
        record_pass("BYTES","LF line endings consistent")
    else:
        record_warn("BYTES","Mixed line endings detected")

def show_results():
    header("DIAGNOSTIC RESULTS")

    print(GREEN+BOLD+f"PASS   : {len(PASSES)}"+RESET)
    print(YELLOW+BOLD+f"WARNING: {len(WARNINGS)}"+RESET)
    print(RED+BOLD+f"ERROR  : {len(ERRORS)}"+RESET)

    line()

    if ERRORS:
        print(RED+BOLD+"ERRORS"+RESET)
        for i,(name,msg) in enumerate(ERRORS,1):
            print(f"{RED}[E{i:03d}]{RESET} {name}: {msg}")
        print()

    if WARNINGS:
        print(YELLOW+BOLD+"WARNINGS"+RESET)
        for i,(name,msg) in enumerate(WARNINGS,1):
            print(f"{YELLOW}[W{i:03d}]{RESET} {name}: {msg}")
        print()

    if not ERRORS:
        print(GREEN+BOLD+"MASTER RESULT: PASS"+RESET)
    else:
        print(RED+BOLD+"MASTER RESULT: FAIL"+RESET)

def full_scan():
    reset_results()

    scan_required()
    scan_lock()
    scan_python()
    scan_crt_structure()
    scan_crt_dependencies()
    scan_android()
    scan_android_drift()
    scan_gradle()
    scan_workflow()
    scan_targeted_bugs()
    scan_geometry()
    scan_line_integrity()

    show_results()
    pause()

def source_browser():
    header("CRT SOURCE LINE INSPECTOR")

    if not CRT.is_file():
        print(RED+"CRT SOURCE MISSING"+RESET)
        pause()
        return

    lines=CRT.read_text(encoding="utf-8").splitlines()

    while True:
        clear()
        print(CYAN+BOLD+"UNIVERSAL CRT SOURCE INSPECTOR"+RESET)
        print(DIM+"Enter a line number, range (100-120), or Q."+RESET)
        print()

        value=input("LINE/RANGE > ").strip()

        if value.lower()=="q":
            return

        try:
            if "-" in value:
                a,b=value.split("-",1)
                start=max(1,int(a))
                end=min(len(lines),int(b))
            else:
                start=max(1,int(value))
                end=min(len(lines),start+20)

            print()

            for n in range(start,end+1):
                print(f"{n:04d} | {lines[n-1]}")

            print()
            input("ENTER TO CONTINUE...")
        except Exception:
            print("INVALID RANGE")
            time.sleep(1)

def function_browser():
    header("CRT FUNCTION MAP")

    source=read(CRT)

    try:
        tree=ast.parse(source)
    except SyntaxError as e:
        print(RED+f"AST ERROR: {e}"+RESET)
        pause()
        return

    functions=[
        n for n in ast.walk(tree)
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
    ]

    functions.sort(key=lambda n:n.lineno)

    for n in functions:
        print(f"{n.lineno:04d}  {n.name}()")

    print()
    print(f"TOTAL FUNCTIONS: {len(functions)}")
    pause()

def menu():
    while True:
        header("REAL CRT DIAGNOSTICS CONTROL CENTER")

        print(CYAN+"[1] "+WHITE+"FULL SYSTEM DIAGNOSTIC SCAN")
        print(CYAN+"[2] "+WHITE+"LINE-LOCK INTEGRITY SCAN")
        print(CYAN+"[3] "+WHITE+"PYTHON / AST DIAGNOSTICS")
        print(CYAN+"[4] "+WHITE+"CRT FUNCTION / STRUCTURE SCAN")
        print(CYAN+"[5] "+WHITE+"CRT RUNTIME DEPENDENCY SCAN")
        print(CYAN+"[6] "+WHITE+"ANDROID RUNTIME SCAN")
        print(CYAN+"[7] "+WHITE+"ROOT ↔ ANDROID CRT DRIFT SCAN")
        print(CYAN+"[8] "+WHITE+"GRADLE / CHAQUOPY BUILD SCAN")
        print(CYAN+"[9] "+WHITE+"GITHUB ACTIONS WORKFLOW SCAN")
        print(CYAN+"[10] "+WHITE+"TARGETED CRT BUG HUNT")
        print(CYAN+"[11] "+WHITE+"GEOMETRY / VIEWPORT VALIDATION")
        print(CYAN+"[12] "+WHITE+"SOURCE BYTE INTEGRITY")
        print(CYAN+"[13] "+WHITE+"CRT SOURCE LINE INSPECTOR")
        print(CYAN+"[14] "+WHITE+"CRT FUNCTION MAP")
        print(CYAN+"[15] "+WHITE+"SHOW LAST RESULTS")
        print(CYAN+"[Q] "+WHITE+"QUIT")
        print()

        choice=input("CRT DIAGNOSTICS > ").strip().lower()

        if choice=="1":
            full_scan()
        elif choice=="2":
            reset_results()
            scan_lock()
            show_results()
            pause()
        elif choice=="3":
            reset_results()
            scan_python()
            show_results()
            pause()
        elif choice=="4":
            reset_results()
            scan_crt_structure()
            show_results()
            pause()
        elif choice=="5":
            reset_results()
            scan_crt_dependencies()
            show_results()
            pause()
        elif choice=="6":
            reset_results()
            scan_android()
            show_results()
            pause()
        elif choice=="7":
            reset_results()
            scan_android_drift()
            show_results()
            pause()
        elif choice=="8":
            reset_results()
            scan_gradle()
            show_results()
            pause()
        elif choice=="9":
            reset_results()
            scan_workflow()
            show_results()
            pause()
        elif choice=="10":
            reset_results()
            scan_targeted_bugs()
            show_results()
            pause()
        elif choice=="11":
            reset_results()
            scan_geometry()
            show_results()
            pause()
        elif choice=="12":
            reset_results()
            scan_line_integrity()
            show_results()
            pause()
        elif choice=="13":
            source_browser()
        elif choice=="14":
            function_browser()
        elif choice=="15":
            show_results()
            pause()
        elif choice=="q":
            clear()
            print("UNIVERSAL CRT MASTER DIAGNOSTICS CLOSED")
            break

if __name__=="__main__":
    menu()
