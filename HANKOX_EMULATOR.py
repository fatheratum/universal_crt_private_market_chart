#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime,timezone

APP_NAME="HankoX Emulator"
VERSION="1.0"
MODE="EMULATOR_ONLY"
AUTHORITY="EMULATED"
STATE_FILE="hankox_emulator_state.json"

state={
    "account":{
        "currency":"USD",
        "balance":20.00,
        "equity":20.00,
        "margin":0.00,
        "free_margin":20.00
    },
    "instrument":{
        "symbol":"GBPJPY",
        "base_currency":"GBP",
        "quote_currency":"JPY",
        "pip_size":0.01,
        "tick_size":0.001,
        "price_precision":3,
        "contract_size":100000,
        "lot_unit":"lot",
        "minimum_lot":0.01,
        "maximum_lot":100.0,
        "lot_step":0.01,
        "margin_currency":"GBP"
    },
    "market":{
        "symbol":"GBPJPY",
        "timeframe":"15m",
        "bid":210.082,
        "ask":210.128,
        "mid":210.105,
        "spread":0.046,
        "timestamp":None,
        "fresh":False,
        "market_state":"EMULATED"
    },
    "trade":{
        "status":"NO_TRADE",
        "direction":None,
        "entry":None,
        "stop_loss":None,
        "take_profit":None,
        "lots":0.0,
        "current_price":None,
        "unrealized_pnl":0.0,
        "drawdown":0.0
    },
    "ohlc":{
        "provider":"HankoX Emulator",
        "authority":"EMULATED",
        "symbol":"GBPJPY",
        "timeframe":"15m",
        "candles":[]
    }
}

def save():
    with open(STATE_FILE,"w",encoding="utf-8") as f:
        json.dump(state,f,indent=2)

def load():
    global state
    if not os.path.exists(STATE_FILE):
        save()
        return
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f:
            loaded=json.load(f)
        if isinstance(loaded,dict):
            state=loaded
    except Exception:
        pass

def clear():
    os.system("clear")

def line():
    print("+"+"-"*78+"+")

def header(title):
    clear()
    line()
    print("|"+" HANKOX EMULATOR".center(78)+"|")
    print("|"+title.center(78)+"|")
    line()

def field(label,value,width=30):
    print(f"| {label:<28}: {str(value):<{width}}|")

def account_screen():
    header("ACCOUNT")
    field("MODE",MODE)
    field("AUTHORITY",AUTHORITY)
    field("CURRENCY",state["account"]["currency"])
    field("BALANCE",f'{state["account"]["balance"]:.2f}')
    field("EQUITY",f'{state["account"]["equity"]:.2f}')
    field("MARGIN",f'{state["account"]["margin"]:.2f}')
    field("FREE MARGIN",f'{state["account"]["free_margin"]:.2f}')
    line()
    print("| EMULATOR DATA IS NOT BROKER DATA.                                       |")
    line()
    input("Press ENTER...")

def instrument_screen():
    header("GBPJPY INSTRUMENT SPECIFICATION")
    i=state["instrument"]
    for k in [
        "symbol","base_currency","quote_currency",
        "pip_size","tick_size","price_precision",
        "contract_size","lot_unit","minimum_lot",
        "maximum_lot","lot_step","margin_currency"
    ]:
        field(k.upper(),i[k])
    line()
    print("| AUTHORITY: EMULATED                                                   |")
    print("| These values exist only to exercise the bridge architecture.          |")
    line()
    input("Press ENTER...")

def market_screen():
    header("MARKET DATA")
    m=state["market"]
    field("SYMBOL",m["symbol"])
    field("TIMEFRAME",m["timeframe"])
    field("BID",m["bid"])
    field("ASK",m["ask"])
    field("MID",m["mid"])
    field("SPREAD",m["spread"])
    field("TIMESTAMP",m["timestamp"])
    field("FRESH",m["fresh"])
    field("MARKET STATE",m["market_state"])
    field("AUTHORITY",AUTHORITY)
    line()
    print("| EMULATED QUOTE — NEVER TREATED AS EXECUTABLE AUTHORITY             |")
    line()
    input("Press ENTER...")

def candle_screen():
    header("15m OHLC")
    o=state["ohlc"]
    field("PROVIDER",o["provider"])
    field("AUTHORITY",o["authority"])
    field("SYMBOL",o["symbol"])
    field("TIMEFRAME",o["timeframe"])
    line()
    if not o["candles"]:
        print("| NO EMULATED CANDLES LOADED                                            |")
    else:
        for c in o["candles"][-10:]:
            print(
                f'| {c["timestamp"]} '
                f'O={c["open"]} H={c["high"]} '
                f'L={c["low"]} C={c["close"]}'
            )
    line()
    print("| EMULATED OHLC — NEVER TREATED AS REAL MARKET DATA                   |")
    line()
    input("Press ENTER...")

def trade_screen():
    header("ACTIVE TRADE")
    t=state["trade"]
    field("STATUS",t["status"])
    field("DIRECTION",t["direction"])
    field("ENTRY",t["entry"])
    field("STOP LOSS",t["stop_loss"])
    field("TAKE PROFIT",t["take_profit"])
    field("LOTS",t["lots"])
    field("CURRENT PRICE",t["current_price"])
    field("UNREALIZED P/L",t["unrealized_pnl"])
    field("DRAWDOWN",t["drawdown"])
    line()
    print("| TRADE EXECUTION: DISABLED                                             |")
    print("| AUTO-CLOSE: DISABLED                                                  |")
    line()
    input("Press ENTER...")

def setup_trade():
    header("EMULATED TRADE SETUP")
    direction=input("Direction [BUY/SELL]: ").strip().upper()
    if direction not in ("BUY","SELL"):
        return

    try:
        entry=float(input("Entry: "))
        sl=float(input("Stop Loss: "))
        tp=float(input("Take Profit: "))
        lots=float(input("Lots: "))
    except ValueError:
        input("Invalid numeric value. Press ENTER...")
        return

    if direction=="BUY":
        valid=sl<entry<tp
    else:
        valid=tp<entry<sl

    if not valid:
        input("Invalid directional SL/TP topology. Press ENTER...")
        return

    state["trade"]={
        "status":"EMULATED_PENDING",
        "direction":direction,
        "entry":entry,
        "stop_loss":sl,
        "take_profit":tp,
        "lots":lots,
        "current_price":entry,
        "unrealized_pnl":0.0,
        "drawdown":0.0
    }
    save()
    input("EMULATED setup saved. Press ENTER...")

def authority_screen():
    header("AUTHORITY STATUS")
    rows=[
        ("EXECUTION QUOTE","EMULATED / NOT REAL"),
        ("15m OHLC","EMULATED / NOT REAL"),
        ("CONTRACT SPEC","EMULATED / NOT REAL"),
        ("LOT SPEC","EMULATED / NOT REAL"),
        ("P/L AUTHORITY","DISABLED"),
        ("SL/TP AUTHORITY","DISABLED"),
        ("AUTO-CLOSE","DISABLED"),
        ("TRADE EXECUTION","DISABLED"),
        ("BROKER CONNECTION","NONE"),
        ("REAL ACCOUNT ACCESS","NONE")
    ]
    for k,v in rows:
        field(k,v)
    line()
    input("Press ENTER...")

def menu():
    while True:
        header("MAIN MENU")
        print("| 1  ACCOUNT                                                               |")
        print("| 2  GBPJPY INSTRUMENT                                                     |")
        print("| 3  MARKET DATA                                                           |")
        print("| 4  15m OHLC                                                              |")
        print("| 5  ACTIVE TRADE                                                          |")
        print("| 6  CREATE EMULATED SETUP                                                 |")
        print("| 7  AUTHORITY STATUS                                                       |")
        print("| 8  EXIT                                                                  |")
        line()
        choice=input("HankoX> ").strip()

        if choice=="1":
            account_screen()
        elif choice=="2":
            instrument_screen()
        elif choice=="3":
            market_screen()
        elif choice=="4":
            candle_screen()
        elif choice=="5":
            trade_screen()
        elif choice=="6":
            setup_trade()
        elif choice=="7":
            authority_screen()
        elif choice=="8":
            break

def main():
    load()
    state["market"]["timestamp"]=datetime.now(timezone.utc).isoformat()
    menu()

if __name__=="__main__":
    main()
