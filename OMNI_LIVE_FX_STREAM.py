#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime,timezone
from collections import deque
from typing import Optional


SYMBOL=os.getenv("OMNI_FX_SYMBOL","GBPJPY")
TIMEFRAME_SECONDS=900
MAX_TICKS=int(os.getenv("OMNI_MAX_TICKS","10000"))
MAX_TICK_AGE=float(os.getenv("OMNI_MAX_TICK_AGE","15"))


@dataclass
class FXTick:
    symbol:str
    timestamp:float
    bid:float
    ask:float

    @property
    def mid(self):
        return (self.bid+self.ask)/2.0


@dataclass
class Candle15M:
    symbol:str
    bucket_start:int
    open:float
    high:float
    low:float
    close:float
    tick_count:int
    first_timestamp:float
    last_timestamp:float

    def to_dict(self):
        return {
            "symbol":self.symbol,
            "timeframe":"15m",
            "bucket_start":self.bucket_start,
            "bucket_iso":datetime.fromtimestamp(
                self.bucket_start,
                timezone.utc
            ).isoformat(),
            "open":self.open,
            "high":self.high,
            "low":self.low,
            "close":self.close,
            "tick_count":self.tick_count,
            "first_timestamp":self.first_timestamp,
            "last_timestamp":self.last_timestamp
        }


class LiveCandleAggregator:
    def __init__(self):
        self.current:Optional[Candle15M]=None
        self.completed=deque(maxlen=500)

    def update(self,tick:FXTick):
        bucket=int(tick.timestamp)//TIMEFRAME_SECONDS
        bucket*=TIMEFRAME_SECONDS
        price=tick.mid

        if self.current is None:
            self.current=Candle15M(
                tick.symbol,
                bucket,
                price,
                price,
                price,
                price,
                1,
                tick.timestamp,
                tick.timestamp
            )
            return self.current

        if bucket<self.current.bucket_start:
            return self.current

        if bucket>self.current.bucket_start:
            self.completed.append(self.current)

            self.current=Candle15M(
                tick.symbol,
                bucket,
                price,
                price,
                price,
                price,
                1,
                tick.timestamp,
                tick.timestamp
            )
            return self.current

        self.current.high=max(self.current.high,price)
        self.current.low=min(self.current.low,price)
        self.current.close=price
        self.current.tick_count+=1
        self.current.last_timestamp=tick.timestamp

        return self.current

    def latest(self):
        return self.current

    def history(self):
        return list(self.completed)


class LiveFXStream:
    """
    Provider-neutral WebSocket transport.

    The provider endpoint and authentication format must be supplied
    explicitly through environment variables.

    No synthetic ticks are generated.
    """

    def __init__(self):
        self.url=os.getenv("OMNI_FX_WS_URL")
        self.api_key=os.getenv("OMNI_FX_WS_API_KEY")
        self.symbol=SYMBOL.upper()
        self.running=False
        self.ticks=deque(maxlen=MAX_TICKS)
        self.aggregator=LiveCandleAggregator()
        self.last_tick:Optional[FXTick]=None

    def configured(self):
        return bool(self.url)

    def parse_tick(self,message):
        """
        Accepts normalized provider messages.

        Supported forms:

        {
          "symbol":"GBPJPY",
          "bid":210.10,
          "ask":210.12,
          "timestamp":...
        }

        or nested:

        {
          "data":{
             "symbol":"GBPJPY",
             "bid":...,
             "ask":...,
             "timestamp":...
          }
        }
        """

        if isinstance(message,str):
            message=json.loads(message)

        if not isinstance(message,dict):
            return None

        if isinstance(message.get("data"),dict):
            message=message["data"]

        symbol=str(
            message.get("symbol")
            or message.get("pair")
            or message.get("instrument")
            or ""
        ).upper().replace("/","").replace("-","")

        bid=message.get("bid")
        ask=message.get("ask")
        timestamp=message.get("timestamp") or message.get("time")

        try:
            bid=float(bid)
            ask=float(ask)
        except (TypeError,ValueError):
            return None

        if not symbol:
            symbol=self.symbol

        if symbol!=self.symbol:
            return None

        try:
            timestamp=float(timestamp)
        except (TypeError,ValueError):
            timestamp=time.time()

        if timestamp>100000000000:
            timestamp/=1000.0

        if bid<=0 or ask<=0 or ask<bid:
            return None

        return FXTick(
            symbol,
            timestamp,
            bid,
            ask
        )

    async def handle_message(self,message):
        tick=self.parse_tick(message)

        if tick is None:
            return None

        self.last_tick=tick
        self.ticks.append(tick)

        candle=self.aggregator.update(tick)

        return candle

    async def run(self):
        if not self.configured():
            raise RuntimeError(
                "OMNI_FX_WS_URL is not configured. "
                "No live stream will be simulated."
            )

        try:
            import websockets
        except ImportError:
            raise RuntimeError(
                "Python package 'websockets' is required"
            )

        headers={}

        if self.api_key:
            headers["Authorization"]="Bearer "+self.api_key

        self.running=True

        while self.running:
            try:
                async with websockets.connect(
                    self.url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=4*1024*1024
                ) as socket:

                    await self.subscribe(socket)

                    async for raw in socket:
                        candle=await self.handle_message(raw)

                        if candle:
                            self.print_state()

            except asyncio.CancelledError:
                self.running=False
                raise

            except Exception as exc:
                print(
                    f"[STREAM ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

                if self.running:
                    print("[STREAM] reconnecting in 3 seconds")
                    await asyncio.sleep(3)

    async def subscribe(self,socket):
        """
        Provider-specific subscription payload.

        Override through OMNI_FX_WS_SUBSCRIBE when the selected provider
        specifies its own JSON subscription contract.
        """

        raw=os.getenv("OMNI_FX_WS_SUBSCRIBE")

        if raw:
            payload=json.loads(raw)

            if isinstance(payload,dict):
                if "symbol" not in payload:
                    payload["symbol"]=self.symbol

                await socket.send(json.dumps(payload))
                return

        print(
            "[STREAM] Connected. "
            "No generic subscription sent."
        )
        print(
            "[STREAM] Configure OMNI_FX_WS_SUBSCRIBE "
            "for the selected provider."
        )

    def freshness(self):
        if self.last_tick is None:
            return False

        return (
            time.time()-self.last_tick.timestamp
        )<=MAX_TICK_AGE

    def print_state(self):
        tick=self.last_tick
        candle=self.aggregator.latest()

        if tick is None or candle is None:
            return

        age=time.time()-tick.timestamp

        print(
            "\n"
            "╔════════════════════════════════════════════════════════════╗\n"
            "║ LIVE FX STREAM                                             ║\n"
            "╚════════════════════════════════════════════════════════════╝"
        )

        print(f"SYMBOL       : {tick.symbol}")
        print(f"BID          : {tick.bid}")
        print(f"ASK          : {tick.ask}")
        print(f"MID          : {tick.mid}")
        print(f"TICK AGE     : {age:.3f}s")
        print(
            "LIVE         :",
            "TRUE" if self.freshness() else "FALSE"
        )

        print("\nCURRENT 15M CANDLE")
        print(f"OPEN         : {candle.open}")
        print(f"HIGH         : {candle.high}")
        print(f"LOW          : {candle.low}")
        print(f"CLOSE        : {candle.close}")
        print(f"TICKS        : {candle.tick_count}")

        bucket_iso=datetime.fromtimestamp(
            candle.bucket_start,
            tz=timezone.utc
        ).isoformat()

        print(f"BUCKET       : {bucket_iso}")


async def main():
    stream=LiveFXStream()

    print("╔════════════════════════════════════════════════════════════╗")
    print("║ OMNI LIVE FX STREAM — STEP 24                             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"SYMBOL       : {stream.symbol}")
    print(f"TIMEFRAME    : 15m")
    print(f"BUCKET       : {TIMEFRAME_SECONDS}s")
    print(f"WS CONFIGURED: {stream.configured()}")
    print("SYNTHETIC    : FALSE")
    print("MOCK DATA    : FALSE")

    if not stream.configured():
        print("\nLIVE STREAM: NOT CONFIGURED")
        print(
            "Set OMNI_FX_WS_URL to the actual WebSocket "
            "endpoint supplied by the selected FX provider."
        )
        return

    await stream.run()


if __name__=="__main__":
    asyncio.run(main())
