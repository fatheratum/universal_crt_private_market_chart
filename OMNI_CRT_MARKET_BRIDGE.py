from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from OMNI_BROKER_ADAPTER import YahooFXProvider, Candle


@dataclass
class CRTBar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class CRTMarketBridge:
    """
    Real public FX market-data bridge.

    Source:
        Yahoo Finance GBPJPY=X

    Flow:
        Yahoo 15m OHLC
            ->
        normalized Candle
            ->
        CRTBar
            ->
        CRT consumer

    This bridge does not execute trades and does not modify
    universal_crt_v4.py or active_trade.json.
    """

    def __init__(self, symbol="GBPJPY", timeframe="15m"):
        self.symbol=symbol
        self.timeframe=timeframe
        self.provider=YahooFXProvider()

    def fetch(self, limit=100):
        result=self.provider.get_candles(
            self.symbol,
            self.timeframe,
            limit
        )

        if not result.ok:
            raise RuntimeError(
                f"Market data unavailable: {result.error}"
            )

        bars=[]

        for candle in result.data:
            bars.append(
                CRTBar(
                    timestamp=int(candle.timestamp),
                    open=float(candle.open),
                    high=float(candle.high),
                    low=float(candle.low),
                    close=float(candle.close),
                    volume=float(
                        candle.volume
                        if candle.volume is not None
                        else 0.0
                    )
                )
            )

        if not bars:
            raise RuntimeError(
                "Yahoo returned zero usable CRT bars"
            )

        return bars

    def latest(self):
        bars=self.fetch(1)
        return bars[-1]

    def state(self, limit=100):
        bars=self.fetch(limit)
        latest=bars[-1]

        return {
            "symbol":self.symbol,
            "timeframe":self.timeframe,
            "source":"YAHOO_FINANCE",
            "classification":"PUBLIC_MARKET_REFERENCE",
            "authoritative":False,
            "executable":False,
            "count":len(bars),
            "latest":latest,
        }


def main():
    bridge=CRTMarketBridge(
        symbol="GBPJPY",
        timeframe="15m"
    )

    bars=bridge.fetch(100)
    latest=bars[-1]

    print("╔════════════════════════════════════════════════════════════╗")
    print("║ OMNI → CRT MARKET BRIDGE                                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("SYMBOL       :",bridge.symbol)
    print("TIMEFRAME    :",bridge.timeframe)
    print("SOURCE       : YAHOO_FINANCE")
    print("BARS         :",len(bars))
    print("CLASS        : PUBLIC_MARKET_REFERENCE")
    print("AUTHORITATIVE: FALSE")
    print("EXECUTABLE   : FALSE")
    print()
    print("LATEST CRT BAR")
    print("TIMESTAMP    :",latest.timestamp)
    print("OPEN         :",latest.open)
    print("HIGH         :",latest.high)
    print("LOW          :",latest.low)
    print("CLOSE        :",latest.close)
    print("VOLUME       :",latest.volume)
    print()
    print("CRT MARKET BRIDGE: PASS")


if __name__=="__main__":
    main()
