#!/usr/bin/env python3
import sys,time,select,termios,tty,shutil,json,urllib.request,urllib.parse,ssl

BASE_WIDTH=112
BASE_HEIGHT=32
CHART_L,CHART_R=5,84
AXIS_L,AXIS_R=85,88

GREEN="\033[32m"
RED="\033[31m"
CYAN="\033[36m"
BLUE="\033[34m"
YELLOW="\033[33m"
WHITE="\033[37m"
DIM="\033[2m"
RESET="\033[0m"

TF={"1m":60,"5m":300,"15m":900,"1h":3600,"4h":21600,"1d":86400}
TF_ORDER=["1m","5m","15m","1h","4h","1d"]
state={"tf":"1h","zoom":1.0,"auto":True,"running":True,"menu":0,"status":"LIVE"}
WIDTH=BASE_WIDTH
HEIGHT=BASE_HEIGHT
FIRST_FRAME=True

def clamp(v,a,b):
    return max(a,min(b,v))

def fetch_candles():
    try:
        url="https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity="+str(TF[state["tf"]])
        req=urllib.request.Request(url,headers={"User-Agent":"UniversalCRT/3.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=5,context=ssl.create_default_context()) as r:
            raw=json.loads(r.read().decode())
        rows=[]
        for x in reversed(raw):
            if len(x)>=6:
                ts,lo,hi,op,cl,vol=x[:6]
                rows.append({"ts":int(ts),"o":float(op),"h":float(hi),"l":float(lo),"c":float(cl),"v":float(vol)})
        if rows:
            return rows[-300:]
    except Exception:
        pass
    return fallback_data()

def fallback_data():
    base=81000.0
    out=[]
    seed=[0.002,-0.001,0.003,0.001,-0.002,0.004,-0.003,0.002,0.001,-0.004,0.003,-0.001,0.002,-0.003,0.004,-0.002,0.001,0.003,-0.002,0.001]
    now=int(time.time()//TF[state["tf"]])*TF[state["tf"]]
    for i,p in enumerate(seed):
        o=base
        c=o*(1+p)
        h=max(o,c)*(1+abs(p)*1.8+0.001)
        l=min(o,c)*(1-abs(p)*1.8-0.001)
        out.append({"ts":now-(len(seed)-i)*TF[state["tf"]],"o":o,"h":h,"l":l,"c":c,"v":0.0})
        base=c
    return out

def visible(rows,zoom=None):
    if not rows:return []
    z=state["zoom"] if zoom is None else zoom
    n=round(60/z)
    n=clamp(n,20,min(120,len(rows)))
    return rows[-n:]

def price_range(rows,auto=None):
    if not rows:return 0.0,1.0
    lo=min(float(r["l"]) for r in rows)
    hi=max(float(r["h"]) for r in rows)
    if hi<=lo:hi=lo+1.0
    span=hi-lo
    use_auto=state["auto"] if auto is None else auto
    if use_auto:
        pad=max(span*0.08,1e-9)
        lo-=pad;hi+=pad
    return lo,hi

def py(price,lo,hi,ct,cb):
    usable=cb-ct
    if usable<=0 or hi<=lo:return ct
    return int(round(cb-(price-lo)/(hi-lo)*usable))

def money(v):
    if v>=1000000:return f"{v/1000000:.2f}M"
    if v>=1000:return f"{v/1000:.1f}k"
    return f"{v:.0f}"

def put(buf,x,y,s,color=""):
    h=len(buf)
    if h==0:return
    w=len(buf[0])
    if y<0 or y>=h:return
    if x>=w or x+len(s)<=0:return
    a=max(0,-x);s=s[a:];x=max(0,x)
    if x>=w:return
    s=s[:w-x]
    row=buf[y]
    for i,ch in enumerate(s):
        if ch!=" ":
            row[x+i]=(color+ch+RESET if color else ch)

def frame(buf,ct,cb,cl,cr):
    for x in range(cl,cr+1):
        put(buf,x,ct,"-",BLUE);put(buf,x,cb,"-",BLUE)
    for y in range(ct,cb+1):
        put(buf,cl,y,"|",BLUE);put(buf,cr,y,"|",BLUE)
    put(buf,cl,ct,"+",BLUE);put(buf,cr,ct,"+",BLUE)
    put(buf,cl,cb,"+",BLUE);put(buf,cr,cb,"+",BLUE)
    for y in range(ct+4,cb,4):
        for x in range(cl+1,cr):
            if y<len(buf) and x<len(buf[0]) and buf[y][x]==" ":
                buf[y][x]=DIM+"."+RESET
    for x in range(cl+10,cr,10):
        for y in range(ct+1,cb):
            if y<len(buf) and x<len(buf[0]) and buf[y][x]==" ":
                buf[y][x]=DIM+"."+RESET

def draw_price_axis(buf,lo,hi,ct,cb,al):
    for i in range(6):
        p=hi-(hi-lo)*i/5
        y=round(ct+(cb-ct)*i/5)
        put(buf,al,y,money(p),CYAN)

def draw_candles(buf,rows,lo,hi,ct,cb,cl,cr):
    n=len(rows)
    if n==0:return []
    left=cl+2;right=cr-2
    span=max(1,right-left)
    slot=span/(n-1 if n>1 else 1)
    body_w=max(1,min(3,int(max(1.0,slot*0.55))))
    centers=[]
    for i,r in enumerate(rows):
        x=int(round(left+i*slot));centers.append(x)
        o=float(r["o"]);c=float(r["c"])
        h=max(float(r["h"]),o,c);l=min(float(r["l"]),o,c)
        yo=clamp(py(o,lo,hi,ct,cb),ct+1,cb-1)
        yc=clamp(py(c,lo,hi,ct,cb),ct+1,cb-1)
        yh=clamp(py(h,lo,hi,ct,cb),ct+1,cb-1)
        yl=clamp(py(l,lo,hi,ct,cb),ct+1,cb-1)
        color=GREEN if c>=o else RED
        top=min(yo,yc);bot=max(yo,yc)
        if top==bot:bot=min(cb-1,top+1)
        half=max(0,(body_w-1)//2)
        x0=max(cl+1,x-half);x1=min(cr-1,x+half)
        for y in range(yh,yl+1):
            put(buf,x,y,"┃",color)
        for xx in range(x0,x1+1):
            for y in range(top,bot+1):
                put(buf,xx,y,"█",color)
        if yh<top:put(buf,x,top-1,"┬",color)
        if bot<yl:put(buf,x,bot+1,"┴",color)
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

def _ansi_at(x,y):
    return f"\033[{y+1};{x+1}H"

def _read_key(fd):
    ch=sys.stdin.read(1)
    if ch!="\033":
        return ch
    seq=""
    for _ in range(6):
        if not select.select([fd],[],[],0.02)[0]:
            break
        seq+=sys.stdin.read(1)
        if seq and (seq[-1].isalpha() or seq[-1]=="\~"):
            break
    if seq.startswith("[") and len(seq)>=2:
        code=seq[-1]
        return {"A":"UP","B":"DOWN","C":"RIGHT","D":"LEFT"}.get(code,"ESC")
    return "ESC"

MULTI_CHARTS=[]
CRYPTO_CURSOR=0
CRYPTO_PAIRS=[
    "BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","DOGE-USD","AVAX-USD","LINK-USD",
    "LTC-USD","BCH-USD","DOT-USD","ATOM-USD","UNI-USD","AAVE-USD","ETC-USD","FIL-USD",
    "NEAR-USD","ALGO-USD","XTZ-USD","MKR-USD","COMP-USD","SUSHI-USD","CRV-USD","SNX-USD",
    "EOS-USD","ZEC-USD","DASH-USD","ETP-USD"
]
MULTI_FAVORITES=[]
MULTI_MENU=0
MULTI_MENU_CHART=0
MULTI_VIEW_LIST=False
MULTI_REFRESH_SECONDS=5.0

MULTI_ITEMS=[
    ("OPEN NEW CHART","N"),
    ("CRYPTO LIST","F"),
    ("VIEW LIST","V"),
    ("TOGGLE CHART","G"),
    ("ZOOM IN","Z"),
    ("ZOOM OUT","X"),
    ("TIMEFRAME","T"),
    ("AUTO-ADJUST","A"),
    ("REFRESH ALL","R"),
    ("QUIT","Q"),
]

def _pair_normalize(pair):
    pair=pair.strip().upper().replace("/","-").replace("_","-").replace(" ","")
    if "-" not in pair and len(pair)==6:
        pair=pair[:3]+"-"+pair[3:]
    return pair

def _fetch_pair(pair,tf):
    try:
        url="https://api.exchange.coinbase.com/products/"+urllib.parse.quote(pair,safe="")+"/candles?granularity="+str(TF[tf])
        req=urllib.request.Request(url,headers={"User-Agent":"UniversalCRT/3.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=5,context=ssl.create_default_context()) as r:
            raw=json.loads(r.read().decode())
        rows=[]
        for x in reversed(raw):
            if len(x)>=6:
                ts,lo,hi,op,cl,vol=x[:6]
                rows.append({"ts":int(ts),"o":float(op),"h":float(hi),"l":float(lo),"c":float(cl),"v":float(vol)})
        return rows[-300:] if rows else []
    except Exception:
        return []

def _multi_add_chart(pair,tf=None):
    pair=_pair_normalize(pair)
    if not pair:return False
    tf=tf or state["tf"]
    rows=_fetch_pair(pair,tf)
    if not rows:rows=fallback_data()
    for c in MULTI_CHARTS:
        if c["pair"]==pair:
            c["tf"]=tf;c["data"]=rows;c["visible"]=True;c["last_refresh"]=time.time()
            if pair not in MULTI_FAVORITES:MULTI_FAVORITES.append(pair)
            return True
    MULTI_CHARTS.append({"pair":pair,"tf":tf,"data":rows,"visible":True,"last_refresh":time.time(),"zoom":1.0,"auto":True})
    if pair not in MULTI_FAVORITES:MULTI_FAVORITES.append(pair)
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
                c["data"]=rows;c["last_refresh"]=now

def _multi_input(prompt):
    fd=sys.stdin.fileno()
    old=termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write(_ansi_at(0,HEIGHT-1)+"\033[2K"+prompt)
        sys.stdout.flush()
        value=sys.stdin.readline().strip()
    finally:
        tty.setcbreak(fd)
    return value

def _multi_open_chart():
    global CRYPTO_CURSOR
    sys.stdout.write("\033[?25h");sys.stdout.flush()
    pair=_multi_input("OPEN NEW CHART | TYPE PAIR (BTC-USD) or empty=next: ")
    if not pair:
        pair=CRYPTO_PAIRS[CRYPTO_CURSOR%len(CRYPTO_PAIRS)]
        CRYPTO_CURSOR+=1
    pair=_pair_normalize(pair)
    if pair:
        sys.stdout.write(_ansi_at(0,HEIGHT-1)+"\033[2KLOADING "+pair+" ...");sys.stdout.flush()
        _multi_add_chart(pair,state["tf"])
    sys.stdout.write("\033[?25l");sys.stdout.flush()

def _crypto_toggle():
    global CRYPTO_CURSOR,MULTI_MENU_CHART
    if not CRYPTO_PAIRS:return
    pair=CRYPTO_PAIRS[CRYPTO_CURSOR%len(CRYPTO_PAIRS)]
    for i,c in enumerate(MULTI_CHARTS):
        if c["pair"]==pair:
            c["visible"]=not c["visible"]
            MULTI_MENU_CHART=i
            CRYPTO_CURSOR=(CRYPTO_CURSOR+1)%len(CRYPTO_PAIRS)
            return
    if _multi_add_chart(pair,state["tf"]):
        MULTI_MENU_CHART=len(MULTI_CHARTS)-1
        MULTI_CHARTS[-1]["visible"]=True
    CRYPTO_CURSOR=(CRYPTO_CURSOR+1)%len(CRYPTO_PAIRS)

def _multi_slots(count,term_h):
    top=3;menu_h=8;header_h=2
    usable=max(12,term_h-header_h-menu_h-1)
    count=max(1,count)
    base=usable//count;remainder=usable%count
    min_h=6
    if base<min_h:base=min_h
    slots=[];y=top
    for i in range(count):
        h=base+(1 if i<remainder else 0)
        end=min(y+h-1,term_h-menu_h-2)
        if end<=y:end=y+min_h-1
        slots.append((y,end));y=end+1
        if y>=term_h-menu_h-1:break
    return slots

def _multi_draw_chart(c,top,bottom,buf):
    ct=top;cb=max(top+4,bottom);cl=CHART_L;cr=CHART_R;al=AXIS_L
    h=len(buf)
    if ct>=h or cb>=h:return
    rows=visible(c["data"],c["zoom"])
    if not rows:
        put(buf,cl+2,ct+1,"NO DATA",YELLOW);return
    lo,hi=price_range(rows,c["auto"])
    frame(buf,ct,cb,cl,cr)
    centers=draw_candles(buf,rows,lo,hi,ct,cb,cl,cr)
    draw_trend(buf,rows,lo,hi,centers,ct,cb)
    draw_price_axis(buf,lo,hi,ct,cb,al)
    if cb-ct>=7:draw_time(buf,rows,centers,cb,cl,cr)
    put(buf,cl+2,max(0,ct-1),c["pair"]+" | "+c["tf"]+" | LIVE | "+str(len(rows))+" CANDLES",CYAN)
    last=rows[-1]
    lc=GREEN if last["c"]>=last["o"] else RED
    put(buf,cl+2,min(h-1,cb+1),"LAST "+f"{last['c']:,.2f}",lc)

def _multi_menu(buf):
    x1=1;x2=min(WIDTH-1,110);y1=HEIGHT-7;y2=HEIGHT-1
    if y1<0:y1=0
    put(buf,x1,y1,"+",BLUE);put(buf,x2,y1,"+",BLUE)
    put(buf,x1,y2,"+",BLUE);put(buf,x2,y2,"+",BLUE)
    for x in range(x1+1,x2):
        put(buf,x,y1,"-",BLUE);put(buf,x,y2,"-",BLUE)
    for y in range(y1+1,y2):
        put(buf,x1,y,"|",BLUE);put(buf,x2,y,"|",BLUE)
    put(buf,x1+2,y1,"MULTI-CHART MENU  N F V G Z X T A R Q",YELLOW)
    if CRYPTO_PAIRS:
        put(buf,x1+40,y1,"CRYPTO:"+CRYPTO_PAIRS[CRYPTO_CURSOR%len(CRYPTO_PAIRS)],CYAN)
    for i,(name,key) in enumerate(MULTI_ITEMS):
        col=i%5;row=i//5
        x=3+col*21;y=y1+1+row
        if y>=y2:continue
        selected=(i==MULTI_MENU)
        c=CYAN if selected else WHITE
        put(buf,x,y,(">" if selected else " ")+name[:14],c)
        put(buf,x+15,y,key,DIM)
    put(buf,3,y2-1,"FAVORITES",YELLOW)
    for i,c in enumerate(MULTI_CHARTS[:5]):
        x=14+i*18
        put(buf,x,y2-1,c["pair"][:10],WHITE)
        put(buf,x+11,y2-1,"ON" if c["visible"] else "OFF",GREEN if c["visible"] else DIM)

def _draw_view_list(buf):
    y=3
    put(buf,5,y,"VIEW LIST — arrows move  Enter/G toggles  V exits",YELLOW);y+=1
    put(buf,5,y,"#  PAIR          TF    ZOOM   AUTO  VIS",DIM);y+=1
    for i,c in enumerate(MULTI_CHARTS):
        if y>=HEIGHT-8:break
        sel=">" if i==MULTI_MENU_CHART else " "
        vis="ON " if c["visible"] else "OFF"
        line=f"{sel}{i:02d} {c['pair']:<12} {c['tf']:<4} {c['zoom']:.2f}  {'ON' if c['auto'] else 'OFF':3}  {vis}"
        put(buf,5,y,line,CYAN if sel==">" else WHITE);y+=1
    if not MULTI_CHARTS:
        put(buf,5,y,"(empty — press N or F to add)",DIM)

def _multi_menu_action():
    global MULTI_MENU,MULTI_VIEW_LIST,MULTI_MENU_CHART
    if MULTI_MENU==0:_multi_open_chart()
    elif MULTI_MENU==1:_crypto_toggle()
    elif MULTI_MENU==2:
        MULTI_VIEW_LIST=not MULTI_VIEW_LIST;MULTI_MENU_CHART=0
    elif MULTI_MENU==3:
        if MULTI_CHARTS:
            i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
            _multi_remove_or_toggle(i)
    elif MULTI_MENU==4:
        for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
    elif MULTI_MENU==5:
        for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
    elif MULTI_MENU==6:
        i=TF_ORDER.index(state["tf"])
        state["tf"]=TF_ORDER[(i+1)%len(TF_ORDER)]
        for c in MULTI_CHARTS:
            if c["visible"]:
                c["tf"]=state["tf"]
                rows=_fetch_pair(c["pair"],c["tf"])
                if rows:c["data"]=rows
    elif MULTI_MENU==7:
        for c in _multi_visible():c["auto"]=not c["auto"]
    elif MULTI_MENU==8:
        for c in MULTI_CHARTS:c["last_refresh"]=0
        _multi_refresh()
    elif MULTI_MENU==9:
        state["running"]=False

def _multi_key(k):
    global MULTI_MENU,MULTI_MENU_CHART,MULTI_VIEW_LIST,CRYPTO_CURSOR
    # VIEW LIST: arrows ONLY move highlight — never toggle
    if MULTI_VIEW_LIST and MULTI_CHARTS:
        if k=="UP":
            MULTI_MENU_CHART=(MULTI_MENU_CHART-1)%len(MULTI_CHARTS)
            return
        if k=="DOWN":
            MULTI_MENU_CHART=(MULTI_MENU_CHART+1)%len(MULTI_CHARTS)
            return
        if k=="\r" or k=="\n":
            _multi_remove_or_toggle(MULTI_MENU_CHART)
            return
        kl=k.lower() if isinstance(k,str) and len(k)==1 else ""
        if kl=="g":
            _multi_remove_or_toggle(MULTI_MENU_CHART)
            return
        if kl=="v":
            MULTI_VIEW_LIST=False;MULTI_MENU=2
            return
        if kl=="q":
            state["running"]=False
            return
        return
    if k=="UP":
        MULTI_MENU=(MULTI_MENU-1)%len(MULTI_ITEMS);return
    if k=="DOWN":
        MULTI_MENU=(MULTI_MENU+1)%len(MULTI_ITEMS);return
    if k=="RIGHT":
        if MULTI_MENU==4:
            for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
        elif MULTI_MENU==5:
            for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
        elif MULTI_MENU==6:
            i=(TF_ORDER.index(state["tf"])+1)%len(TF_ORDER)
            state["tf"]=TF_ORDER[i]
            for c in MULTI_CHARTS:
                if c["visible"]:
                    c["tf"]=state["tf"]
                    rows=_fetch_pair(c["pair"],c["tf"])
                    if rows:c["data"]=rows
        return
    if k=="LEFT":
        if MULTI_MENU==4:
            for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)
        elif MULTI_MENU==5:
            for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
        elif MULTI_MENU==6:
            i=(TF_ORDER.index(state["tf"])-1)%len(TF_ORDER)
            state["tf"]=TF_ORDER[i]
            for c in MULTI_CHARTS:
                if c["visible"]:
                    c["tf"]=state["tf"]
                    rows=_fetch_pair(c["pair"],c["tf"])
                    if rows:c["data"]=rows
        return
    if k=="\r" or k=="\n":
        _multi_menu_action();return
    kl=k.lower() if isinstance(k,str) and len(k)==1 else k
    if kl=="q":state["running"]=False
    elif kl=="n":_multi_open_chart()
    elif kl=="f":_crypto_toggle()
    elif kl=="v":
        MULTI_VIEW_LIST=not MULTI_VIEW_LIST;MULTI_MENU=2;MULTI_MENU_CHART=0
    elif kl=="g":
        if MULTI_CHARTS:
            i=clamp(MULTI_MENU_CHART,0,len(MULTI_CHARTS)-1)
            _multi_remove_or_toggle(i)
    elif kl=="r":
        for c in MULTI_CHARTS:c["last_refresh"]=0
        _multi_refresh()
    elif kl=="t":
        i=(TF_ORDER.index(state["tf"])+1)%len(TF_ORDER)
        state["tf"]=TF_ORDER[i]
        for c in MULTI_CHARTS:
            if c["visible"]:
                c["tf"]=state["tf"]
                rows=_fetch_pair(c["pair"],c["tf"])
                if rows:c["data"]=rows
    elif kl=="a":
        for c in _multi_visible():c["auto"]=not c["auto"]
    elif kl=="z":
        for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]+0.25,2),0.5,3.0)
    elif kl=="x":
        for c in _multi_visible():c["zoom"]=clamp(round(c["zoom"]-0.25,2),0.5,3.0)

def _multi_render():
    global FIRST_FRAME,WIDTH,HEIGHT
    term=shutil.get_terminal_size((BASE_WIDTH,BASE_HEIGHT))
    WIDTH=max(100,min(BASE_WIDTH,term.columns))
    HEIGHT=max(24,min(term.lines,80))
    rowsbuf=[[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
    put(rowsbuf,1,0,"UNIVERSAL CRT V3 | MULTI-CHART MARKET RASTER",CYAN)
    put(rowsbuf,1,1,"FIXED VIEWPORTS | OHLC MAPPING | LIVE PAIR DATA | REVEALABILITY",DIM)
    if MULTI_VIEW_LIST:
        _draw_view_list(rowsbuf)
    else:
        visible_charts=_multi_visible()
        if not visible_charts:
            put(rowsbuf,5,8,"NO CHARTS VISIBLE",YELLOW)
            put(rowsbuf,5,10,"N = OPEN NEW   F = CRYPTO LIST",WHITE)
        else:
            slots=_multi_slots(len(visible_charts),HEIGHT)
            for c,(top,bottom) in zip(visible_charts,slots):
                _multi_draw_chart(c,top,bottom,rowsbuf)
    put(rowsbuf,1,HEIGHT-9,"UP/DN SELECT  L/R ADJUST  ENTER  N F V G  Z/X ZOOM  T TF  A AUTO  R REFRESH  Q QUIT",WHITE)
    _multi_menu(rowsbuf)
    if FIRST_FRAME:
        sys.stdout.write("\033[2J\033[H");FIRST_FRAME=False
        for y in range(HEIGHT):
            sys.stdout.write(_ansi_at(0,y)+"".join(rowsbuf[y]))
        sys.stdout.flush();return
    for y in range(HEIGHT):
        sys.stdout.write(_ansi_at(0,y)+"".join(rowsbuf[y]))
    sys.stdout.flush()

def main():
    global WIDTH,HEIGHT,FIRST_FRAME,MULTI_MENU,MULTI_MENU_CHART
    term=shutil.get_terminal_size((BASE_WIDTH,BASE_HEIGHT))
    WIDTH=max(100,min(BASE_WIDTH,term.columns))
    HEIGHT=max(24,min(term.lines,80))
    rows=_fetch_pair("BTC-USD",state["tf"])
    if not rows:rows=fetch_candles()
    _multi_add_chart("BTC-USD",state["tf"])
    if rows and MULTI_CHARTS:MULTI_CHARTS[0]["data"]=rows
    MULTI_MENU=0;MULTI_MENU_CHART=0
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?25l")
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
