#!/usr/bin/env python3
import sys,time,select,termios,tty,shutil,json,urllib.request,urllib.parse,ssl
from OMNI_CRT_MARKET_BRIDGE import CRTMarketBridge
from pathlib import Path

# ---- fixed base geometry (physical chart width never changes) ----
BASE_WIDTH=112
BASE_HEIGHT=32
CHART_L,CHART_R=5,84
AXIS_L,AXIS_R=85,88
MENU_L,MENU_R=90,110

GREEN="\033[32m"
RED="\033[31m"
CYAN="\033[36m"
BLUE="\033[34m"
YELLOW="\033[33m"
WHITE="\033[37m"
DIM="\033[2m"
RESET="\033[0m"
BOLD="\033[1m"

TF={"1m":60,"5m":300,"15m":900,"1h":3600,"4h":21600,"1d":86400}
TF_ORDER=["1m","5m","15m","1h","4h","1d"]

state={"tf":"1h","zoom":1.0,"auto":True,"running":True,"menu":0,"status":"LIVE"}
DATA=[]

WIDTH=BASE_WIDTH
HEIGHT=BASE_HEIGHT
FIRST_FRAME=True

def clamp(v,a,b):
    return max(a,min(b,v))

def api_url(tf):
    return "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity="+str(TF[tf])

def fetch_candles():
    try:
        req=urllib.request.Request(api_url(state["tf"]),headers={"User-Agent":"UniversalCRT/3.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=5,context=ssl.create_default_context()) as r:
            raw=json.loads(r.read().decode())
        rows=[]
        for x in reversed(raw):
            if len(x)>=6:
                ts,lo,hi,op,cl,vol=x[:6]
                rows.append({"ts":int(ts),"o":float(op),"h":float(hi),"l":float(lo),"c":float(cl),"v":float(vol)})
        if rows:
            return rows[-120:]
    except Exception:
        pass
    return fallback_data()

def fallback_data():
    base=81000.0
    out=[]
    seed=[0.002,-0.001,0.003,0.001,-0.002,0.004,-0.003,0.002,0.001,-0.004,0.003,-0.001,0.002,-0.003,0.004,-0.002,0.001,0.003,-0.002,0.001,-0.001,0.003,-0.002,0.002]
    now=int(time.time()//TF[state["tf"]])*TF[state["tf"]]
    for i,p in enumerate(seed):
        o=base
        c=o*(1+p)
        h=max(o,c)*(1+abs(p)*1.8+0.001)
        l=min(o,c)*(1-abs(p)*1.8-0.001)
        out.append({"ts":now-(len(seed)-i)*TF[state["tf"]],"o":o,"h":h,"l":l,"c":c,"v":0.0})
        base=c
    return out

def aggregate(rows,target):
    if not rows:return []
    if target=="1m":return rows
    sec=TF[target]
    groups={}
    for r in rows:
        k=(r["ts"]//sec)*sec
        groups.setdefault(k,[]).append(r)
    out=[]
    for k,g in sorted(groups.items()):
        out.append({"ts":k,"o":g[0]["o"],"h":max(x["h"] for x in g),"l":min(x["l"] for x in g),"c":g[-1]["c"],"v":sum(x["v"] for x in g)})
    return out

def visible(rows,zoom=None):
    if not rows:return []
    z=state["zoom"] if zoom is None else zoom
    n=round(24/z)
    n=clamp(n,10,min(60,len(rows)))
    return rows[-n:]

def price_range(rows,auto=None):
    if not rows:
        return 0.0,1.0
    lo=min(float(r["l"]) for r in rows)
    hi=max(float(r["h"]) for r in rows)
    if hi<=lo:
        hi=lo+1.0
    span=hi-lo
    use_auto=state["auto"] if auto is None else auto
    if use_auto:
        pad=max(span*0.08,1e-9)
        lo-=pad
        hi+=pad
    return lo,hi


def price_range_padded(rows,auto,pair=""):
    lo,hi=price_range(rows,auto)
    p=str(pair or "").upper()
    if "JPY" in p:
        pad=2.0
    else:
        pad=(hi-lo)*0.12 if hi>lo else 1
    return lo-pad,hi+pad

def py(price,lo,hi,ct,cb):
    usable=cb-ct
    if usable<=0 or hi<=lo:
        return ct
    return int(round(cb-(price-lo)/(hi-lo)*usable))

def money(v):
    if v>=1000000:return f"{v/1000000:.2f}M"
    if v>=1000:return f"{v/1000:.1f}k"
    return f"{v:.0f}"

def put(buf,x,y,s,color=""):
    h=len(buf)
    if h==0:return
    w=len(buf[0]) if buf else 0
    if y<0 or y>=h:return
    if x>=w or x+len(s)<=0:return
    a=max(0,-x)
    s=s[a:]
    x=max(0,x)
    if x>=w:return
    s=s[:w-x]
    row=buf[y]
    for i,ch in enumerate(s):
        if ch!=" ":
            row[x+i]=(color+ch+RESET if color else ch)

def frame(buf,ct,cb,cl,cr):
    for x in range(cl,cr+1):
        put(buf,x,ct,"-",BLUE)
        put(buf,x,cb,"-",BLUE)
    for y in range(ct,cb+1):
        put(buf,cl,y,"|",BLUE)
        put(buf,cr,y,"|",BLUE)
    put(buf,cl,ct,"+",BLUE)
    put(buf,cr,ct,"+",BLUE)
    put(buf,cl,cb,"+",BLUE)
    put(buf,cr,cb,"+",BLUE)

def draw_price_axis(buf,lo,hi,ct,cb,al):
    fmt=_pxfmt(lo,hi,locals().get("pair","") if "pair" in dir() else "")
    for i in range(6):
        p=hi-(hi-lo)*i/5
        y=round(ct+(cb-ct)*i/5)
        put(buf,al,y,_pxfmt(lo,hi).format(p),CYAN)

def draw_candles(buf,rows,lo,hi,ct,cb,cl,cr):
    n=len(rows)
    if n==0:return []
    left=cl+2
    right=cr-2
    span=max(1,right-left)
    # candle slots from fixed chart width — never half the viewport
    slot=span/(n-1 if n>1 else 1)
    body_w=max(1,min(3,int(max(1.0,slot*0.55))))
    centers=[]
    for i,r in enumerate(rows):
        x=int(round(left+i*slot))
        centers.append(x)
        o=float(r["o"])
        c=float(r["c"])
        h=max(float(r["h"]),o,c)
        l=min(float(r["l"]),o,c)
        yo=clamp(py(o,lo,hi,ct,cb),ct+1,cb-1)
        yc=clamp(py(c,lo,hi,ct,cb),ct+1,cb-1)
        yh=clamp(py(h,lo,hi,ct,cb),ct+1,cb-1)
        yl=clamp(py(l,lo,hi,ct,cb),ct+1,cb-1)
        color=GREEN if c>=o else RED
        top=min(yo,yc)
        bot=max(yo,yc)
        if top==bot:
            bot=min(cb-1,top+1)
        half=max(0,(body_w-1)//2)
        x0=max(cl+1,x-half)
        x1=min(cr-1,x+half)
        # wick
        for y in range(yh,yl+1):
            put(buf,x,y,"┃",color)
        # solid body
        for xx in range(x0,x1+1):
            for y in range(top,bot+1):
                put(buf,xx,y,"█",color)
        if yh<top:
            put(buf,x,top-1,"┬",color)
        if bot<yl:
            put(buf,x,bot+1,"┴",color)
    return centers

def draw_trend(buf,rows,lo,hi,centers,ct,cb):
    if len(rows)<2:return
    for i in range(len(rows)-1):
        x1,x2=centers[i],centers[i+1]
        y1=clamp(py(rows[i]["c"],lo,hi,ct,cb),ct+1,cb-1)
        y2=clamp(py(rows[i+1]["c"],lo,hi,ct,cb),ct+1,cb-1)
        dx=x2-x1
        if dx<=0:continue
        for x in range(x1+1,x2):
            t=(x-x1)/dx
            y=round(y1+(y2-y1)*t)
            if ct<y<cb and y<len(buf) and x<len(buf[0]) and buf[y][x]==" ":
                buf[y][x]=DIM+"."+RESET

def draw_time(buf,rows,centers,cb,cl,cr):
    if not rows:return
    for i in range(0,len(rows),max(1,len(rows)//6)):
        x=centers[i]
        label=time.strftime("%H:%M",time.localtime(rows[i]["ts"]))
        if x-2>=cl and x+3<=cr:
            put(buf,x-2,cb+1,label,DIM)

# ===== LOCKED TERMINAL COMPOSITOR helpers =====
def _ansi_at(x,y):
    return f"\033[{y+1};{x+1}H"

def _write_region(buf,x1,x2,y1,y2):
    out=[]
    h=len(buf)
    w=len(buf[0]) if h else 0
    x1=max(0,x1);x2=min(w-1,x2)
    y1=max(0,y1);y2=min(h-1,y2)
    for y in range(y1,y2+1):
        out.append(_ansi_at(x1,y))
        out.append("".join(buf[y][x1:x2+1]))
    sys.stdout.write("".join(out))

def _read_key(fd):
    ch=sys.stdin.read(1)
    if ch!="\033":return ch
    if not select.select([fd],[],[],0.05)[0]:return ch
    seq=sys.stdin.read(1)
    if seq=="[" and select.select([fd],[],[],0.05)[0]:
        code=sys.stdin.read(1)
        return {"A":"UP","B":"DOWN","C":"RIGHT","D":"LEFT"}.get(code,"ESC")
    return "ESC"

# ===== MULTICHART / FAVORITES / REVEALABILITY =====
MULTI_CHARTS=[]
CRYPTO_CURSOR=0
CRYPTO_PAIRS=[
    "BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD","AVAX-USD","LINK-USD",
    "LTC-USD","BCH-USD","DOT-USD","ATOM-USD","UNI-USD","AAVE-USD","ETC-USD","FIL-USD",
    "NEAR-USD","ALGO-USD","XTZ-USD","MKR-USD","COMP-USD","SUSHI-USD","CRV-USD","SNX-USD",
    "EOS-USD","ZEC-USD","DASH-USD"
]
MULTI_FAVORITES=[]
MULTI_MENU=0
MULTI_MENU_CHART=0
MULTI_VIEW_LIST=False
MULTI_REFRESH_SECONDS=5.0
MULTI_LAST_REFRESH=0.0

# menu items
# C=CRT MARKET, B=ACCOUNT (omni_menu), N=OPEN NEW, F=CRYPTO LIST, V=VIEW LIST, G=TOGGLE,
# Z/X=zoom, T=timeframe, A=auto, R=refresh, Q=quit
MULTI_ITEMS=[
    ("CRT MARKET","C"),
    ("ACCOUNT","B"),
    ("OPEN NEW CHART","N"),
    ("CRYPTO LIST","F"),
    ("VIEW LIST","V"),
    ("TOGGLE CHART","G"),
    ("ZOOM IN","Z"),
    ("ZOOM OUT","X"),
    ("TIMEFRAME","T"),
    ("AUTO-ADJUST","A"),
    ("REFRESH ALL","R"),
    ("TRACKER","K"),
    ("QUIT","Q"),
]

def _pair_normalize(pair):
    pair=pair.strip().upper().replace("/","-").replace("_","-").replace(" ","")
    if "-" not in pair and len(pair)==6:
        pair=pair[:3]+"-"+pair[3:]
    return pair

def _pair_url(pair,tf):
    return "https://api.exchange.coinbase.com/products/"+urllib.parse.quote(pair,safe="")+"/candles?granularity="+str(TF[tf])

def _fetch_pair(pair,tf):
    try:
        normalized=_pair_normalize(pair)
        fx_pairs={"GBP-JPY","EUR-JPY","USD-JPY","AUD-JPY","NZD-JPY","CAD-JPY","CHF-JPY","EUR-GBP","GBP-USD","EUR-USD","AUD-USD","NZD-USD","USD-CAD","USD-CHF"}
        if normalized in fx_pairs:
            symbol=normalized.replace("-","")
            bridge_tf=tf
            bridge=CRTMarketBridge(symbol=symbol,timeframe=bridge_tf)
            bars=bridge.fetch(120)
            return [
                {
                    "ts":int(bar.timestamp),
                    "o":float(bar.open),
                    "h":float(bar.high),
                    "l":float(bar.low),
                    "c":float(bar.close),
                    "v":float(bar.volume)
                }
                for bar in bars
            ][-120:]

        req=urllib.request.Request(
            _pair_url(pair,tf),
            headers={"User-Agent":"UniversalCRT/3.0","Accept":"application/json"}
        )
        with urllib.request.urlopen(
            req,
            timeout=5,
            context=ssl.create_default_context()
        ) as r:
            raw=json.loads(r.read().decode())

        rows=[]
        for x in reversed(raw):
            if len(x)>=6:
                ts,lo,hi,op,cl,vol=x[:6]
                rows.append({
                    "ts":int(ts),
                    "o":float(op),
                    "h":float(hi),
                    "l":float(lo),
                    "c":float(cl),
                    "v":float(vol)
                })
        return rows[-120:] if rows else []
    except Exception:
        return []

def _multi_add_chart(pair,tf=None):
    """Assign pair to next chart slot (or update existing). Hardcoded list cycle supported via CRYPTO_CURSOR."""
    pair=_pair_normalize(pair)
    if not pair:return False
    tf=tf or state["tf"]
    rows=_fetch_pair(pair,tf)
    if not rows:
        # still add with empty data so user can toggle; fallback later
        rows=fallback_data()
    for c in MULTI_CHARTS:
        if c["pair"]==pair:
            c["tf"]=tf
            c["data"]=rows
            c["visible"]=True
            c["last_refresh"]=time.time()
            if pair not in MULTI_FAVORITES:
                MULTI_FAVORITES.append(pair)
            return True
    MULTI_CHARTS.append({
        "pair":pair,"tf":tf,"data":rows,"visible":True,
        "last_refresh":time.time(),"zoom":1.0,"auto":True
    })
    if pair not in MULTI_FAVORITES:
        MULTI_FAVORITES.append(pair)
    return True

def _multi_remove_or_toggle(index):
    if 0<=index<len(MULTI_CHARTS):
        MULTI_CHARTS[index]["visible"]=not MULTI_CHARTS[index]["visible"]

def _multi_visible():
    return [c for c in MULTI_CHARTS if c["visible"]]

def _multi_refresh():
    now=time.time()
    for c in MULTI_CHARTS:
        if now-c["last_refresh"]>=MULTI_REFRESH_SECONDS:
            rows=_fetch_pair(c["pair"],c["tf"])
            if rows:
                c["data"]=rows
                c["last_refresh"]=now

def _multi_input(prompt):
    fd=sys.stdin.fileno()
    old=termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        # write prompt at bottom without full clear
        sys.stdout.write(_ansi_at(0,HEIGHT-1)+"\033[2K"+prompt)
        sys.stdout.flush()
        value=sys.stdin.readline().strip()
    finally:
        tty.setcbreak(fd)
    return value

def _multi_open_chart():
    """N = OPEN NEW CHART — next free chart gets the pair."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()
    pair=_multi_input("OPEN NEW CHART | TYPE PAIR (BTC-USD) or empty=next from list: ")
    if not pair:
        global CRYPTO_CURSOR
        pair=CRYPTO_PAIRS[CRYPTO_CURSOR%len(CRYPTO_PAIRS)]
        CRYPTO_CURSOR+=1
    pair=_pair_normalize(pair)
    if pair:
        tf=state["tf"]
        sys.stdout.write(_ansi_at(0,HEIGHT-1)+"\033[2KLOADING "+pair+" "+tf+" ...")
        sys.stdout.flush()
        _multi_add_chart(pair,tf)
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def _multi_cycle_crypto_list():
    """F = CRYPTO LIST — cycle hardcoded list and assign next pair to next chart."""
    global CRYPTO_CURSOR
    pair=CRYPTO_PAIRS[CRYPTO_CURSOR%len(CRYPTO_PAIRS)]
    CRYPTO_CURSOR+=1
    _multi_add_chart(pair,state["tf"])

def _multi_slots(count,term_h):
    """
    Compute fixed vertical slots that fit inside terminal height.
    Chart physical width (CHART_L..CHART_R) is never changed.
    Only interior height per chart shrinks when many charts are visible.
    """
    top=3
    menu_h=8          # reserved for bottom menu
    header_h=2
    usable=max(12,term_h-header_h-menu_h-1)
    count=max(1,count)
    base=usable//count
    remainder=usable%count
    # minimum chart interior height so candles still render
    min_h=6
    if base<min_h:
        # cannot fit all; still allocate but clamp later
        base=min_h
    slots=[]
    y=top
    for i in range(count):
        h=base+(1 if i<remainder else 0)
        end=min(y+h-1,term_h-max(menu_h,11)-2)
        if end<=y:
            end=y+min_h-1
        slots.append((y,end))
        y=end+1
        if y>=term_h-max(menu_h,11)-1:
            break
    return slots


def _clear_pane(buf,ct,cb,cl,cr):
    for y in range(ct+1,cb):
        for x in range(cl+1,cr):
            put(buf,x,y," ",DIM)
    _draw_wallpaper(buf,ct,cb,cl,cr)

def _draw_wallpaper(buf,ct,cb,cl,cr):
    lines=[
        "ALGEBRA SUPER TRADING SYSTEM",
        "DESIGNED BY ATUM",
        "OWNED BY: PARTICLELC",
        "LICENSED: PARTICLELC",
    ]
    mid_x=(cl+cr)//2
    mid_y=(ct+cb)//2
    top=max(ct+1,mid_y-2)
    for n,txt in enumerate(lines):
        x=max(cl+1,mid_x-len(txt)//2)
        y=top+n
        if y>=cb: break
        put(buf,x,y,txt[:max(0,cr-x-1)],DIM)

def _multi_draw_chart(c,top,bottom,buf):
    """Draw one chart into fixed region [top..bottom]. Only interior cells change on refresh."""
    ct=top
    cb=max(top+4,bottom)
    cl=CHART_L
    cr=CHART_R
    al=AXIS_L
    # clamp to buffer
    h=len(buf)
    if ct>=h or cb>=h:
        return
    rows=visible(c["data"],c["zoom"])
    if not rows:
        put(buf,cl+2,ct+1,"NO DATA",YELLOW)
        return
    lo,hi=price_range(rows,c["auto"])
    frame(buf,ct,cb,cl,cr)
    _clear_pane(buf,ct,cb,cl,cr)
    centers=draw_candles(buf,rows,lo,hi,ct,cb,cl,cr)
    draw_trend(buf,rows,lo,hi,centers,ct,cb)
    draw_price_axis(buf,lo,hi,ct,cb,al)
    if cb-ct>=5:
        draw_time(buf,rows,centers,cb,cl,cr)
    put(buf,cl+2,max(0,ct-1),c["pair"]+" | "+c["tf"]+" | LIVE | "+str(len(rows))+" CANDLES",CYAN)
    last=rows[-1]
    lc=GREEN if last["c"]>=last["o"] else RED

    ov=_overlay_for_chart(c)
    if ov:
        ey=_y_from_price(ov.get("entry"),lo,hi,ct,cb)
        sy=_y_from_price(ov.get("sl"),lo,hi,ct,cb)
        ty=_y_from_price(ov.get("tp"),lo,hi,ct,cb)
        _draw_price_line(buf,ey,cl,cr,"-",YELLOW)
        _draw_price_line(buf,sy,cl,cr,"-",RED)
        _draw_price_line(buf,ty,cl,cr,"-",GREEN)
        if ey is not None:
            put(buf,cl+2,ey,"ENTRY "+("{:.3f}".format(float(ov.get("entry")))),YELLOW)
        if sy is not None:
            put(buf,cl+2,min(h-1,sy),"SL "+("{:.3f}".format(float(ov.get("sl")))),RED)
        if ty is not None:
            put(buf,cl+2,max(0,ty),"TP "+("{:.3f}".format(float(ov.get("tp")))),GREEN)
        lastp=last["c"]
        try:
            entry=float(ov.get("entry"))
            bal=float(ov.get("balance") or 0)
            direction=str(ov.get("direction") or "").upper()
            chg=(entry-float(lastp)) if direction=="SELL" else (float(lastp)-entry)
            put(buf,cl+2,min(h-1,cb+1),"LAST "+f"{lastp:,.2f}"+" BAL "+f"{bal:.2f}"+" dP "+f"{chg:+.3f}",lc)
        except Exception:
            put(buf,cl+2,min(h-1,cb+1),"LAST "+f"{last['c']:,.2f}",lc)
    else:
        put(buf,cl+2,min(h-1,cb+1),"LAST "+f"{last['c']:,.2f}",lc)



TRACKER_FILE=Path("trade_tracker.json")
SESSION_FILE=Path("crt_session.json")

def _crt_tracker_default():
    return {"open":[], "closed":[]}

def _crt_load_tracker():
    try:
        import json
        if TRACKER_FILE.exists():
            data=json.loads(TRACKER_FILE.read_text(encoding="utf-8",errors="replace"))
            if isinstance(data,dict):
                data.setdefault("open",[])
                data.setdefault("closed",[])
                return data
    except Exception:
        pass
    return _crt_tracker_default()

def _crt_save_tracker(tr):
    try:
        import json
        TRACKER_FILE.write_text(json.dumps(tr,indent=2),encoding="utf-8")
    except Exception as e:
        print("tracker save failed",e)

def _crt_trade_id(rec):
    return "|".join([
        str(rec.get("pair","")),
        str(rec.get("entry","")),
        str(rec.get("sl","")),
        str(rec.get("tp","")),
        str(rec.get("lots","")),
    ])

def _crt_upsert_open_trade(overlay):
    if not overlay or overlay.get("entry") in (None,"--"):
        return
    tr=_crt_load_tracker()
    rec={
        "status":"OPEN",
        "pair":overlay.get("pair"),
        "tf":overlay.get("tf"),
        "direction":overlay.get("direction"),
        "entry":overlay.get("entry"),
        "sl":overlay.get("sl"),
        "tp":overlay.get("tp"),
        "lots":overlay.get("lots"),
        "balance":overlay.get("balance"),
        "opened_at":overlay.get("opened_at"),
    }
    tid=_crt_trade_id(rec)
    exists=False
    for i,o in enumerate(tr["open"]):
        if _crt_trade_id(o)==tid:
            tr["open"][i].update(rec)
            exists=True
            break
    if not exists:
        import time as _t
        rec["opened_at"]=rec.get("opened_at") or _t.strftime("%Y-%m-%dT%H:%M:%SZ",_t.gmtime())
        tr["open"].append(rec)
    _crt_save_tracker(tr)

def _crt_classify_result(rec,lastp):
    try:
        entry=float(rec.get("entry")); sl=float(rec.get("sl")); tp=float(rec.get("tp")); lastp=float(lastp)
    except Exception:
        return None
    side=str(rec.get("direction") or "").upper()
    if side not in ("BUY","SELL"):
        side="BUY" if sl<entry<tp else "SELL" if tp<entry<sl else ""
    if side=="BUY":
        if lastp>=tp: return "WIN"
        if lastp<=sl: return "LOSS"
    elif side=="SELL":
        if lastp<=tp: return "WIN"
        if lastp>=sl: return "LOSS"
    return None

def _crt_eval_open_trades(lastp):
    if lastp is None:
        return
    tr=_crt_load_tracker()
    still=[]
    changed=False
    import time as _t
    for rec in tr.get("open",[]):
        result=_crt_classify_result(rec,lastp)
        if result:
            rec["status"]="CLOSED"
            rec["result"]=result
            rec["closed_at"]=_t.strftime("%Y-%m-%dT%H:%M:%SZ",_t.gmtime())
            rec["close_price"]=lastp
            try:
                entry=float(rec.get("entry")); lots=float(rec.get("lots") or 0); bal=float(rec.get("balance") or 0)
                side=str(rec.get("direction") or "").upper()
                if side not in ("BUY","SELL"):
                    sl=float(rec.get("sl")); tp=float(rec.get("tp"))
                    side="BUY" if sl<entry<tp else "SELL"
                chg=(entry-float(lastp)) if side=="SELL" else (float(lastp)-entry)
                rec["profit"]=round((chg/0.01)*10.0*lots,2)
                rec["equity"]=round(bal+rec["profit"],2)
            except Exception:
                rec["profit"]=None
            tr["closed"].append(rec)
            changed=True
        else:
            still.append(rec)
    if changed:
        tr["open"]=still
        _crt_save_tracker(tr)

def _crt_save_state():
    try:
        import json,time
        cfg={}
        try:
            from OMNICIPHERIST import load_config
            cfg=load_config()
        except Exception:
            pass
        charts=[]
        for c in MULTI_CHARTS:
            charts.append({
                "pair":c.get("pair"),
                "tf":c.get("tf"),
                "zoom":c.get("zoom"),
                "auto":c.get("auto"),
                "visible":c.get("visible"),
            })
        payload={
            "saved_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "tf":state.get("tf"),
            "overlay":state.get("trade_overlay"),
            "tracker_view":state.get("tracker_view",False),
            "config":{
                "account_balance":cfg.get("account_balance"),
                "trading_pair":cfg.get("trading_pair"),
                "timeframe":cfg.get("timeframe"),
                "last_entry":cfg.get("last_entry"),
            },
            "charts":charts,
        }
        SESSION_FILE.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    except Exception:
        pass

def _crt_restore_state():
    try:
        import json
        if not SESSION_FILE.exists():
            _crt_load_trade_overlay()
            if state.get("trade_overlay"):
                _crt_upsert_open_trade(state.get("trade_overlay"))
            return
        data=json.loads(SESSION_FILE.read_text(encoding="utf-8",errors="replace"))
        if not isinstance(data,dict):
            return
        if data.get("tf"):
            state["tf"]=data["tf"]
        state["tracker_view"]=bool(data.get("tracker_view",False))
        ov=data.get("overlay")
        if ov:
            state["trade_overlay"]=ov
        charts=data.get("charts") or []
        if charts and not MULTI_CHARTS:
            for ch in charts:
                pair=ch.get("pair") or "GBP-JPY"
                tf=ch.get("tf") or state.get("tf","15m")
                try:
                    _multi_add_chart(pair,tf)
                except Exception:
                    pass
                if MULTI_CHARTS:
                    MULTI_CHARTS[-1]["visible"]=bool(ch.get("visible",True))
                    if ch.get("zoom") is not None:
                        MULTI_CHARTS[-1]["zoom"]=ch["zoom"]
                    if ch.get("auto") is not None:
                        MULTI_CHARTS[-1]["auto"]=ch["auto"]
                    if ov and _same_pair(MULTI_CHARTS[-1].get("pair"), ov.get("pair")):
                        MULTI_CHARTS[-1]["overlay"]=ov
        elif MULTI_CHARTS and ov:
            for _c in MULTI_CHARTS:
                if _same_pair(_c.get("pair"), ov.get("pair")):
                    _c["overlay"]=ov
        if not ov:
            _crt_load_trade_overlay()
            ov=state.get("trade_overlay")
        if ov:
            _crt_upsert_open_trade(ov)
    except Exception:
        pass

def _draw_tracker_list(buf):
    tr=_crt_load_tracker()
    y=3
    put(buf,5,y,"TRACKER LIST — OPEN SETUPS / COMPLETED WIN-LOSS",YELLOW)
    y+=1
    put(buf,5,y,"OPEN",CYAN)
    y+=1
    if not tr.get("open"):
        put(buf,5,y,"(no open trades)",DIM); y+=1
    else:
        for rec in tr["open"][-8:]:
            line=f"OPEN {rec.get('pair')} {rec.get('tf')} E={rec.get('entry')} SL={rec.get('sl')} TP={rec.get('tp')} L={rec.get('lots')}"
            put(buf,5,y,line[:108],WHITE); y+=1
            if y>=HEIGHT-14: break
    y+=1
    put(buf,5,y,"COMPLETED",CYAN); y+=1
    if not tr.get("closed"):
        put(buf,5,y,"(no completed trades)",DIM); y+=1
    else:
        for rec in tr["closed"][-10:]:
            res=str(rec.get("result","?"))
            col=GREEN if res=="WIN" else RED
            line=f"{res} {rec.get('pair')} E={rec.get('entry')} CLOSE={rec.get('close_price')} P/L={rec.get('profit')} {rec.get('closed_at')}"
            put(buf,5,y,line[:108],col); y+=1
            if y>=HEIGHT-8: break
    put(buf,5,min(HEIGHT-8,y+1),"K closes tracker   B account/setup   R refresh",DIM)


def _draw_portfolio_box(buf):
    x1=1
    x2=min(WIDTH-1,110)
    y1=HEIGHT-5
    y2=HEIGHT-1
    if y1<0:y1=0
    put(buf,x1,y1,"+",BLUE)
    put(buf,x2,y1,"+",BLUE)
    put(buf,x1,y2,"+",BLUE)
    put(buf,x2,y2,"+",BLUE)
    for x in range(x1+1,x2):
        put(buf,x,y1,"-",BLUE)
        put(buf,x,y2,"-",BLUE)
    for y in range(y1+1,y2):
        put(buf,x1,y,"|",BLUE)
        put(buf,x2,y,"|",BLUE)
    put(buf,x1+2,y1,"PORTFOLIO",YELLOW)
    ov=None
    if MULTI_CHARTS:
        i=clamp(MULTI_MENU_CHART,0,max(0,len(MULTI_CHARTS)-1)) if MULTI_CHARTS else 0
        if MULTI_CHARTS:
            ov=MULTI_CHARTS[i].get("overlay")
    ov=ov or state.get("trade_overlay")
    bal="--"
    pair="--"
    tf="--"
    entry="--"
    sl="--"
    tp="--"
    lots="--"
    side="--"
    last="--"
    dp="--"
    dd="--"
    growth="--"
    try:
        from OMNICIPHERIST import load_config
        cfg=load_config()
        bal=cfg.get("account_balance",bal)
    except Exception:
        pass
    if ov:
        pair=_omni_pair_to_crt(ov.get("pair") or pair)
        tf=_omni_tf_to_crt(ov.get("tf") or ov.get("timeframe") or tf)
        tf=ov.get("tf") or tf
        entry=ov.get("entry") if ov.get("entry") is not None else entry
        sl=ov.get("sl") if ov.get("sl") is not None else sl
        tp=ov.get("tp") if ov.get("tp") is not None else tp
        lots=ov.get("lots") if ov.get("lots") is not None else lots
        side=_side_from_levels(ov.get("entry"),ov.get("sl"),ov.get("tp"),ov.get("direction"))
        if ov.get("balance") is not None:
            bal=ov.get("balance")
        try:
            src=None
            for _c in MULTI_CHARTS:
                if ov and _same_pair(_c.get("pair"), ov.get("pair")) and _c.get("data"):
                    src=_c; break
            lastp=None
            if src and src.get("data"):
                lastp=float(src["data"][-1]["c"])
            elif ov.get("entry") is not None:
                lastp=float(ov.get("entry"))
                last=f"{lastp:.3f}"
                if ov.get("entry") is not None:
                    e=float(ov.get("entry"))
                    chg=(e-lastp) if str(side).upper()=="SELL" else (lastp-e)
                    dp=f"{chg:+.3f}"
                    if str(side).upper()=="SELL":
                        dd=f"{min(0.0,chg):.3f}"
                        growth=f"{max(0.0,chg):.3f}"
                    else:
                        dd=f"{min(0.0,chg):.3f}"
                        growth=f"{max(0.0,chg):.3f}"
        except Exception:
            pass
    profit="--"
    equity="--"
    try:
        b=float(bal)
        e=float(entry)
        lastp=float(last)
        lts=float(lots)
        chg=(e-lastp) if str(side).upper()=="SELL" else (lastp-e)
        pips=chg/0.01
        # display-only from existing OMNI lot + pip convention; not broker P/L
        pr=pips*10.0*lts
        profit=f"{pr:+.2f}"
        equity=f"{b+pr:.2f}"
    except Exception:
        try:
            b=float(bal)
            equity=f"{b:.2f}"
            profit="+0.00"
        except Exception:
            pass
    put(buf,x1+2,y1+1,f"BAL {bal}  PAIR {pair}  TF {tf}  SIDE {side}",CYAN)
    put(buf,x1+2,y1+2,f"ENTRY {entry}  SL {sl}  TP {tp}  LOTS {lots}",WHITE)
    profit="--"
    equity="--"
    try:
        b=float(bal); e=float(entry); lastp=float(last); lts=float(lots)
        chg=(e-lastp) if str(side).upper()=="SELL" else (lastp-e)
        pr=(chg/0.01)*10.0*lts
        profit=f"{pr:+.2f}"
        equity=f"{b+pr:.2f}"
    except Exception:
        try:
            b=float(bal); equity=f"{b:.2f}"; profit="+0.00"
        except Exception:
            pass
    put(buf,x1+2,y1+3,f"LAST {last}  GROWTH {growth}  DRAWDOWN {dd}  dP {dp}  PROFIT {profit}  EQUITY {equity}",GREEN)

def _multi_menu(buf):
    x1=1
    x2=min(WIDTH-1,110)
    y1=HEIGHT-12
    y2=HEIGHT-6
    if y1<0:y1=0
    put(buf,x1,y1,"+",BLUE)
    put(buf,x2,y1,"+",BLUE)
    put(buf,x1,y2,"+",BLUE)
    put(buf,x2,y2,"+",BLUE)
    for x in range(x1+1,x2):
        put(buf,x,y1,"-",BLUE)
        put(buf,x,y2,"-",BLUE)
    for y in range(y1+1,y2):
        put(buf,x1,y,"|",BLUE)
        put(buf,x2,y,"|",BLUE)
    put(buf,x1+2,y1,"MULTI-CHART MENU  C B N F V G Z X T A R K Q",YELLOW)
    # two rows of items
    for i,(name,key) in enumerate(MULTI_ITEMS):
        col=i%5
        row=i//5
        x=3+col*21
        y=y1+1+row
        if y>=y2:continue
        selected=(i==MULTI_MENU)
        c=CYAN if selected else WHITE
        put(buf,x,y,(">" if selected else " ")+name[:14],c)
        put(buf,x+15,y,key,DIM)
    # favorites strip
    put(buf,3,y2-1,"FAVORITES",YELLOW)
    show=MULTI_CHARTS[:5]
    for i,c in enumerate(show):
        x=14+i*18
        put(buf,x,y2-1,c["pair"][:10],WHITE)
        put(buf,x+11,y2-1,"ON" if c["visible"] else "OFF",GREEN if c["visible"] else DIM)

def _draw_view_list(buf):
    """V = VIEW LIST — show all added charts with ON/OFF."""
    y=3
    put(buf,5,y,"VIEW LIST — all charts (G toggles)",YELLOW)
    y+=1
    put(buf,5,y,"#  PAIR          TF    ZOOM   AUTO  VIS",DIM)
    y+=1
    for i,c in enumerate(MULTI_CHARTS):
        if y>=HEIGHT-8:break
        sel=">" if (MULTI_VIEW_LIST and i==MULTI_MENU_CHART) else " "
        vis="ON " if c["visible"] else "OFF"
        line=f"{sel}{i:02d} {c['pair']:<12} {c['tf']:<4} {c['zoom']:.2f}  {'ON' if c['auto'] else 'OFF':3}  {vis}"
        put(buf,5,y,line,CYAN if sel==">" else WHITE)
        y+=1
    if not MULTI_CHARTS:
        put(buf,5,y,"(empty — press N or F to add)",DIM)



def _norm_sym(p):
    return str(p or "").upper().replace("/","").replace("-","").replace("_","").replace(" ","")



def _side_from_levels(entry,sl,tp,side=None):
    raw=str(side or "").upper()
    if raw in ("BUY","SELL"):
        return raw
    try:
        e=float(entry); sl=float(sl); tp=float(tp)
        if sl<e<tp: return "BUY"
        if tp<e<sl: return "SELL"
    except Exception:
        pass
    return "--"

def _overlay_for_chart(c):
    ov=c.get("overlay") if isinstance(c,dict) else None
    if ov and _same_pair(c.get("pair"), ov.get("pair")):
        return ov
    st=state.get("trade_overlay")
    if st and _same_pair(c.get("pair"), st.get("pair")):
        return st
    try:
        tr=_crt_load_tracker()
        for rec in tr.get("open",[]):
            if _same_pair(c.get("pair"), rec.get("pair")):
                return rec
    except Exception:
        pass
    return None

def _same_pair(a,b):
    return _norm_sym(a)==_norm_sym(b) and _norm_sym(a)!=""

def _omni_pair_to_crt(pair):
    raw=str(pair or "").strip().upper().replace("/","").replace("_","").replace("-","").replace(" ","")
    if len(raw)==6 and raw.isalpha():
        return raw[:3]+"-"+raw[3:]
    return str(pair or "GBP-JPY").strip().upper().replace("/","-")

def _omni_tf_to_crt(tf):
    raw=str(tf or "").strip().lower().replace(" ","")
    aliases={"1min":"1m","1m":"1m","5min":"5m","5m":"5m","15min":"15m","15m":"15m","30min":"30m","30m":"30m","1h":"1h","1hr":"1h","60min":"1h","60m":"1h","4h":"4h","1d":"1d","1day":"1d","daily":"1d"}
    mapped=aliases.get(raw,raw)
    try:
        if mapped in TF_ORDER:
            return mapped
    except Exception:
        pass
    return state.get("tf","15m")

def _crt_apply_omni_config(config):
    if not isinstance(config,dict):
        return
    pair=_omni_pair_to_crt(config.get("trading_pair","GBPJPY"))
    tf=_omni_tf_to_crt(config.get("timeframe",state.get("tf","15m")))
    state["tf"]=tf
    rows=None
    try:
        rows=_fetch_pair(pair,tf)
    except Exception:
        rows=None
    if MULTI_CHARTS:
        i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
        c=MULTI_CHARTS[i]
        c["pair"]=pair
        c["tf"]=tf
        if rows:
            c["data"]=rows
            c["last_refresh"]=time.time()
        c["visible"]=True
    else:
        _multi_add_chart(pair,tf)


def _crt_load_trade_overlay():
    """Read existing OMNI active_trade.json only. Do not write it."""
    overlay=None
    try:
        import json
        raw=Path("active_trade.json").read_text(encoding="utf-8",errors="replace")
        data=json.loads(raw)
        rec=data
        if isinstance(data,list) and data:
            rec=data[-1]
        if isinstance(rec,dict):
            overlay={
                "pair":str(rec.get("pair") or rec.get("trading_pair") or "GBPJPY"),
                "tf":str(rec.get("timeframe") or rec.get("tf") or state.get("tf","15m")),
                "entry":rec.get("entry") or rec.get("sacred_entry") or rec.get("last_entry"),
                "sl":rec.get("stop_loss") or rec.get("sl") or rec.get("stoploss"),
                "tp":rec.get("take_profit") or rec.get("tp") or rec.get("target") or rec.get("takeprofit"),
                "lots":rec.get("lots") or rec.get("lot_size") or rec.get("lot"),
                "direction":rec.get("direction") or rec.get("side"),
                "balance":None,
            }
            try:
                from OMNICIPHERIST import load_config
                overlay["balance"]=load_config().get("account_balance")
            except Exception:
                pass
    except Exception:
        overlay=None
    state["trade_overlay"]=overlay
    if overlay:
        _crt_upsert_open_trade(overlay)
    _crt_save_state()
    if MULTI_CHARTS and overlay:
        i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
        MULTI_CHARTS[i]["overlay"]=overlay


def _pxfmt(lo,hi,pair=""):
    span=abs(float(hi)-float(lo)) if hi!=lo else 1
    p=str(pair or "").upper()
    if "JPY" in p or span<2:
        return "{:.3f}"
    if span<20:
        return "{:.2f}"
    if span<200:
        return "{:.1f}"
    return "{:.0f}"

def _y_from_price(price,lo,hi,ct,cb):
    try:
        price=float(price); lo=float(lo); hi=float(hi)
    except Exception:
        return None
    if hi<=lo:
        return None
    if price<lo or price>hi:
        return None
    y=int(round(cb-(price-lo)/(hi-lo)*(cb-ct)))
    if y<ct or y>cb:
        return None
    return y

def _draw_price_line(buf,y,cl,cr,ch,color):
    if y is None:
        return
    for x in range(cl+1,cr):
        put(buf,x,y,ch,color)

def _crt_account_menu():
    import sys,termios,tty
    fd=None
    old=None
    try:
        fd=sys.stdin.fileno()
        old=termios.tcgetattr(fd)
        termios.tcsetattr(fd,termios.TCSADRAIN,termios.tcgetattr(fd))
        # force cooked + echo so omni_menu() input() works
        import termios as _t
        attr=_t.tcgetattr(fd)
        attr[3]=attr[3]|_t.ECHO|_t.ICANON
        _t.tcsetattr(fd,_t.TCSADRAIN,attr)
    except Exception:
        old=None
    try:
        sys.stdout.write("\n\033[2J\033[H")
        sys.stdout.flush()
    except Exception:
        pass
    try:
        import OMNICIPHERIST as _omni
        load_config=_omni.load_config
        save_config=_omni.save_config
        omni_menu=_omni.omni_menu
    except Exception as e:
        print("ACCOUNT: cannot import omni_menu():",e)
        try: input("Press ENTER to return to CRT...")
        except Exception: pass
        if fd is not None and old is not None:
            try: termios.tcsetattr(fd,termios.TCSADRAIN,old)
            except Exception: pass
        return
    config=load_config()
    _omni.config=config
    print("")
    print("CRT ACCOUNT")
    print("ACCOUNT BALANCE :",config.get("account_balance"))
    print("TRADING PAIR    :",config.get("trading_pair"))
    print("TIMEFRAME       :",config.get("timeframe"))
    print("LAST ENTRY      :",config.get("last_entry"))
    print("4 Find Sacred Setup starts the existing OMNI trade/account process.")
    print("5 Exit returns to CRT.")
    print("Opening existing OMNICIPHERIST omni_menu()...")
    try:
        _omni.config=load_config()
        omni_menu()
    except Exception as e:
        print("omni_menu() error:",e)
        try: input("Press ENTER to return to CRT...")
        except Exception: pass
    config=load_config()
    _omni.config=config
    try:
        save_config(config)
    except Exception:
        pass
    _crt_apply_omni_config(config)
    _crt_load_trade_overlay()
    _crt_save_state()
    if fd is not None and old is not None:
        try: termios.tcsetattr(fd,termios.TCSADRAIN,old)
        except Exception: pass

def _multi_menu_action():
    global MULTI_MENU,MULTI_VIEW_LIST,MULTI_MENU_CHART
    if not MULTI_ITEMS:
        return
    key=MULTI_ITEMS[MULTI_MENU][1] if 0<=MULTI_MENU<len(MULTI_ITEMS) else ""
    if key=="C":
        if MULTI_CHARTS:
            i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
            c=MULTI_CHARTS[i]
            c["pair"]="GBP-JPY"
            c["tf"]=state["tf"]
            rows=_fetch_pair("GBP-JPY",state["tf"])
            if rows:
                c["data"]=rows
                c["last_refresh"]=time.time()
                c["visible"]=True
        else:
            _multi_add_chart("GBP-JPY",state["tf"])
    elif key=="B":
        _crt_account_menu()
    elif key=="N":
        _multi_open_chart()
    elif key=="F":
        _multi_cycle_crypto_list()
    elif key=="V":
        MULTI_VIEW_LIST=not MULTI_VIEW_LIST
        MULTI_MENU_CHART=0
    elif key=="G":
        if MULTI_CHARTS:
            i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
            _multi_remove_or_toggle(i)
    elif key=="Z":
        for c in _multi_visible():
            c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
    elif key=="X":
        for c in _multi_visible():
            c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
    elif key=="T":
        i=TF_ORDER.index(state["tf"])
        state["tf"]=TF_ORDER[(i+1)%len(TF_ORDER)]
        for c in MULTI_CHARTS:
            if c["visible"]:
                c["tf"]=state["tf"]
                rows=_fetch_pair(c["pair"],c["tf"])
                if rows:c["data"]=rows
    elif key=="A":
        for c in _multi_visible():
            c["auto"]=not c["auto"]
    elif key=="R":
        for c in MULTI_CHARTS:
            c["last_refresh"]=0
        _multi_refresh()
    elif key=="K":
        state["tracker_view"]=not state.get("tracker_view",False)
        _crt_save_state()
    elif key=="Q":
        _crt_save_state()
        state["running"]=False


def _multi_key(k):
    global MULTI_MENU,MULTI_MENU_CHART,MULTI_VIEW_LIST,CRYPTO_CURSOR
    if k=="UP":
        if MULTI_VIEW_LIST and MULTI_CHARTS:
            MULTI_MENU_CHART=(MULTI_MENU_CHART-1)%len(MULTI_CHARTS)
        else:
            MULTI_MENU=(MULTI_MENU-1)%len(MULTI_ITEMS)
        return
    if k=="DOWN":
        if MULTI_VIEW_LIST and MULTI_CHARTS:
            MULTI_MENU_CHART=(MULTI_MENU_CHART+1)%len(MULTI_CHARTS)
        else:
            MULTI_MENU=(MULTI_MENU+1)%len(MULTI_ITEMS)
        return
    if k=="RIGHT":
        if MULTI_MENU==5:
            for c in _multi_visible():
                c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
        elif MULTI_MENU==6:
            for c in _multi_visible():
                c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
        elif MULTI_MENU==7:
            i=(TF_ORDER.index(state["tf"])+1)%len(TF_ORDER)
            state["tf"]=TF_ORDER[i]
            for c in MULTI_CHARTS:
                if c["visible"]:
                    c["tf"]=state["tf"]
                    rows=_fetch_pair(c["pair"],c["tf"])
                    if rows:
                        c["data"]=rows
        return
    if k=="LEFT":
        if MULTI_MENU==5:
            for c in _multi_visible():
                c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
        elif MULTI_MENU==6:
            for c in _multi_visible():
                c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
        elif MULTI_MENU==7:
            i=(TF_ORDER.index(state["tf"])-1)%len(TF_ORDER)
            state["tf"]=TF_ORDER[i]
            for c in MULTI_CHARTS:
                if c["visible"]:
                    c["tf"]=state["tf"]
                    rows=_fetch_pair(c["pair"],c["tf"])
                    if rows:
                        c["data"]=rows
        return
    if k in ("\r","\n"):
        if MULTI_VIEW_LIST and MULTI_CHARTS:
            _multi_remove_or_toggle(MULTI_MENU_CHART)
        else:
            _multi_menu_action()
        return
    if isinstance(k,str) and (k.startswith("\x1b") or k in ("UP","DOWN","LEFT","RIGHT","")):
        return
    kl=k.lower() if isinstance(k,str) and len(k)==1 and k.isalpha() else k
    keymap={item[1].lower():idx for idx,item in enumerate(MULTI_ITEMS)}
    if kl=="b":
        MULTI_MENU=keymap.get("b",1)
        _crt_account_menu()
        return
    if kl=="q":
        MULTI_MENU=keymap.get("q",len(MULTI_ITEMS)-1)
        state["running"]=False
        return
    if isinstance(kl,str) and kl in keymap:
        MULTI_MENU=keymap[kl]
        _multi_menu_action()
        return

def _multi_render():
    global FIRST_FRAME,WIDTH,HEIGHT
    term=shutil.get_terminal_size((BASE_WIDTH,BASE_HEIGHT))
    ts=(term.columns,term.lines)
    if state.get("_term_size")!=ts:
        state["_term_size"]=ts
        FIRST_FRAME=True
        try:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
        except Exception:
            pass

    state.setdefault("tracker_view",False)
    if not state.get("_session_restored"):
        _crt_restore_state()
        state["_session_restored"]=True
    # lock geometry to current terminal — never grow past it (prevents IndexError + viewport jump)
    term=shutil.get_terminal_size((BASE_WIDTH,BASE_HEIGHT))
    WIDTH=max(100,min(BASE_WIDTH,term.columns))
    HEIGHT=max(24,min(term.lines,80))

    rowsbuf=[[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
    put(rowsbuf,1,0,"UNIVERSAL CRT V3 | MULTI-CHART MARKET RASTER",CYAN)
    put(rowsbuf,1,1,"FIXED VIEWPORTS | OHLC MAPPING | LIVE PAIR DATA | REVEALABILITY",DIM)

    if state.get("tracker_view"):
        _draw_tracker_list(rowsbuf)
    elif MULTI_VIEW_LIST:
        _draw_view_list(rowsbuf)
    else:
        visible_charts=_multi_visible()
        if not visible_charts:
            put(rowsbuf,5,8,"NO CHARTS VISIBLE",YELLOW)
            put(rowsbuf,5,10,"N = OPEN NEW   F = NEXT FROM CRYPTO LIST",WHITE)
        else:
            slots=_multi_slots(len(visible_charts),HEIGHT)
            for c,(top,bottom) in zip(visible_charts,slots):
                _multi_draw_chart(c,top,bottom,rowsbuf)

        _multi_menu(rowsbuf)
    _draw_portfolio_box(rowsbuf)

    # compositor: first frame full paint; later frames rewrite only interior regions
    # no \033[2J / no \033[H on refresh — cursor addressed per cell
    if FIRST_FRAME:
        sys.stdout.write("\033[2J\033[H")
        FIRST_FRAME=False
        for y in range(HEIGHT):
            sys.stdout.write(_ansi_at(0,y)+"".join(rowsbuf[y]))
        sys.stdout.flush()
        return

    # rewrite entire logical buffer with absolute positioning (no clear, no home)
    # chart boundaries stay fixed; only content cells change
    for y in range(HEIGHT):
        sys.stdout.write(_ansi_at(0,y)+"".join(rowsbuf[y]))
    sys.stdout.flush()

def main():
    global WIDTH,HEIGHT,FIRST_FRAME,MULTI_MENU,MULTI_MENU_CHART
    term=shutil.get_terminal_size((BASE_WIDTH,BASE_HEIGHT))
    WIDTH=max(100,min(BASE_WIDTH,term.columns))
    HEIGHT=max(24,min(term.lines,80))

    # seed with BTC
    rows=_fetch_pair("BTC-USD",state["tf"])
    if not rows:
        rows=fetch_candles()
    _multi_add_chart("BTC-USD",state["tf"])
    if rows and MULTI_CHARTS:
        MULTI_CHARTS[0]["data"]=rows

    MULTI_MENU=0
    MULTI_MENU_CHART=0
    fd=sys.stdin.fileno()
    old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?25l")  # hide cursor
        FIRST_FRAME=True
        while state["running"]:
            _multi_refresh()
            _multi_render()
            if select.select([fd],[],[],0.35)[0]:
                _multi_key(_read_key(fd))
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write("\033[0m\033[?25h\033[H")
        sys.stdout.flush()

if __name__=="__main__":
    main()
