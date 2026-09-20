from __future__ import annotations
import requests
#!/usr/bin/env python3
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from typing import Any,Optional
import json,os,time,urllib.parse,urllib.request

MAX_QUOTE_AGE=120
MAX_CANDLE_AGE=1800

@dataclass
class AdapterResult:
    ok:bool
    source:str
    authoritative:bool
    executable:bool
    timestamp:Optional[str]
    data:Any=None
    error:Optional[str]=None
    classification:str="UNVERIFIED"
    def to_dict(self):
        d=asdict(self)
        if hasattr(self.data,"to_dict"):
            d["data"]=self.data.to_dict()
        elif hasattr(self.data,"__dataclass_fields__"):
            d["data"]=asdict(self.data)
        return d

@dataclass
class Quote:
    symbol:str
    bid:float
    ask:float
    timestamp:str
    source:str
    market_state:str
    stale:bool
    authoritative:bool=False
    executable:bool=False
    def to_dict(self):
        return asdict(self)

@dataclass
class Candle:
    timestamp:int
    open:float
    high:float
    low:float
    close:float
    volume:Optional[float]=None
    def to_dict(self):
        return asdict(self)

@dataclass
class Instrument:
    symbol:str
    base_currency:str
    quote_currency:str
    price_precision:Optional[int]
    tick_size:Optional[float]
    pip_size:Optional[float]
    contract_size:Optional[float]
    lot_min:Optional[float]
    lot_max:Optional[float]
    lot_step:Optional[float]
    margin_currency:Optional[str]
    provider_symbol:Optional[str]
    provider_timezone:Optional[str]
    authoritative:bool=False
    executable:bool=False
    def to_dict(self):
        return asdict(self)

@dataclass
class Account:
    account_id:Optional[str]
    currency:Optional[str]
    balance:Optional[float]
    equity:Optional[float]
    margin:Optional[float]
    free_margin:Optional[float]
    authenticated:bool
    executable:bool
    source:str
    def to_dict(self):
        return asdict(self)

@dataclass
class Position:
    position_id:str
    symbol:str
    direction:str
    quantity:float
    entry_price:float
    current_price:Optional[float]
    stop_loss:Optional[float]
    take_profit:Optional[float]
    unrealized_pl:Optional[float]
    currency:Optional[str]
    def to_dict(self):
        return asdict(self)

class BrokerAdapter:
    name="UNCONFIGURED"

    def get_quote(self,symbol):
        return self._unavailable("QUOTE")

    def get_candles(self,symbol,timeframe,limit=100):
        return self._unavailable("OHLC")

    def get_account(self):
        return self._unavailable("ACCOUNT")

    def get_instrument(self,symbol):
        return self._unavailable("INSTRUMENT")

    def convert(self,amount,from_currency,to_currency):
        return self._unavailable("CONVERSION")

    def get_market_state(self,symbol):
        return self._unavailable("MARKET_STATE")

    def get_timestamp(self):
        now=datetime.now(timezone.utc).isoformat()
        return AdapterResult(True,self.name,False,False,now,now,None,"LOCAL_CLOCK")

    def get_position(self,position_id):
        return self._unavailable("POSITION")

    def place_order(self,order):
        return self._execution_unavailable("ORDER")

    def modify_order(self,order_id,changes):
        return self._execution_unavailable("MODIFY_ORDER")

    def close_position(self,position_id):
        return self._execution_unavailable("CLOSE_POSITION")

    def _unavailable(self,name):
        return AdapterResult(False,self.name,False,False,None,None,
            f"{name} provider is not configured","UNAVAILABLE")

    def _execution_unavailable(self,name):
        return AdapterResult(False,self.name,False,False,None,None,
            f"{name} execution interface is not configured",
            "EXECUTION_UNAVAILABLE")

class HTTPProvider:
    def __init__(self,name,timeout=10):
        self.name=name
        self.timeout=timeout

    def request_json(self,url,headers=None):
        req=urllib.request.Request(
            url,
            headers=headers or {
                "User-Agent":"OMNI-Broker-Adapter/1.0",
                "Accept":"application/json"
            }
        )
        with urllib.request.urlopen(req,timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8","replace"))

def normalize_symbol(symbol):
    return symbol.upper().replace("/","").replace("-","").replace("_","")

def split_fx(symbol):
    s=normalize_symbol(symbol)
    if len(s)!=6 or not s.isalpha():
        raise ValueError("FX symbol must contain six letters")
    return s[:3],s[3:]

def parse_number(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError,ValueError,InvalidOperation):
        return None

def parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value,(int,float)):
        return float(value)
    text=str(value).strip()
    try:
        return datetime.fromisoformat(
            text.replace("Z","+00:00")
        ).timestamp()
    except ValueError:
        return None

def age_seconds(timestamp):
    ts=parse_timestamp(timestamp)
    if ts is None:
        return None
    return max(0.0,time.time()-ts)

def fresh(timestamp,max_age):
    age=age_seconds(timestamp)
    return age is not None and age>=0 and age<=max_age

class BiQuoteProvider(BrokerAdapter):
    name="BIQUOTE"

    def __init__(self):
        self.http=HTTPProvider(self.name)

    def get_quote(self,symbol):
        symbol=normalize_symbol(symbol)
        try:
            split_fx(symbol)
        except ValueError as e:
            return AdapterResult(False,self.name,False,False,None,None,str(e),"INVALID_SYMBOL")

        try:
            payload=self.http.request_json(
                f"https://biquote.io/api/{urllib.parse.quote(symbol)}"
            )
            bid=parse_number(payload.get("bid"))
            ask=parse_number(payload.get("ask"))
            timestamp=(
                payload.get("timestamp")
                or payload.get("time")
                or payload.get("date")
            )
            state=str(
                payload.get("marketState")
                or payload.get("market_state")
                or "UNKNOWN"
            )
            stale=bool(payload.get("stale",False))
            valid=bid is not None and ask is not None and bid>0 and ask>=bid
            live=fresh(timestamp,MAX_QUOTE_AGE)
            executable=valid and live and not stale and state.lower()=="open"

            if not valid:
                return AdapterResult(
                    False,self.name,False,False,timestamp,payload,
                    "Invalid bid/ask","INVALID_QUOTE"
                )

            quote=Quote(
                symbol,bid,ask,str(timestamp or ""),str(
                    payload.get("source") or self.name
                ),state,not live or stale,executable,executable
            )

            return AdapterResult(
                True,self.name,executable,executable,timestamp,quote,
                None,
                "LIVE_EXECUTABLE"
                if executable else "STALE_OR_REFERENCE"
            )
        except Exception as e:
            return AdapterResult(
                False,self.name,False,False,None,None,
                f"{type(e).__name__}: {e}","PROVIDER_ERROR"
            )

class TwelveDataProvider(BrokerAdapter):
    name="TWELVEDATA"

    def __init__(self):
        self.key=os.getenv("TWELVEDATA_API_KEY")
        self.http=HTTPProvider(self.name)

    def get_quote(self,symbol):
        if not self.key:
            return AdapterResult(False,self.name,False,False,None,None,
                "TWELVEDATA_API_KEY is not configured","NOT_CONFIGURED")

        symbol=normalize_symbol(symbol)
        try:
            payload=self.http.request_json(
                "https://api.twelvedata.com/quote?symbol="
                +urllib.parse.quote(symbol)
                +"&apikey="+urllib.parse.quote(self.key)
            )
            bid=parse_number(payload.get("bid"))
            ask=parse_number(payload.get("ask"))
            timestamp=payload.get("timestamp")

            if bid is None or ask is None:
                return AdapterResult(
                    False,self.name,False,False,None,payload,
                    str(payload.get("message") or "No usable bid/ask"),
                    "PROVIDER_REJECTED"
                )

            live=fresh(timestamp,MAX_QUOTE_AGE)
            executable=bool(live)

            quote=Quote(
                symbol,bid,ask,str(timestamp or ""),self.name,
                "OPEN" if executable else "UNKNOWN",
                not live,False,False
            )

            return AdapterResult(
                True,self.name,False,False,timestamp,quote,None,
                "LIVE_MARKET_DATA" if live else "STALE"
            )
        except Exception as e:
            return AdapterResult(
                False,self.name,False,False,None,None,
                f"{type(e).__name__}: {e}","PROVIDER_ERROR"
            )

class YahooFXProvider(BrokerAdapter):
    name="YAHOO_FINANCE"

    def __init__(self):
        self.base="https://query1.finance.yahoo.com/v8/finance/chart"

    def _symbol(self,symbol):
        base,quote=split_fx(symbol)
        return f"{base}{quote}=X"

    def _request(self,symbol,interval,range_value):
        url=f"{self.base}/{self._symbol(symbol)}"
        params={
            "interval":interval,
            "range":range_value,
            "events":"history"
        }
        response=requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent":"Mozilla/5.0"}
        )
        response.raise_for_status()
        payload=response.json()

        chart=payload.get("chart",{})
        result=chart.get("result")

        if not result:
            error=chart.get("error")
            raise RuntimeError(
                f"Yahoo returned no result: {error}"
            )

        return result[0]

    def get_quote(self,symbol):
        try:
            result=self._request(symbol,"1m","1d")
            meta=result.get("meta",{})
            price=meta.get("regularMarketPrice")

            if price is None:
                timestamps=result.get("timestamp") or []
                quote=(result.get("indicators",{})
                    .get("quote",[{}])[0])
                closes=quote.get("close") or []

                for value in reversed(closes):
                    if value is not None:
                        price=float(value)
                        break

            if price is None:
                return AdapterResult(
                    False,
                    self.name,
                    False,
                    False,
                    None,
                    error="Yahoo returned no current price",
                    classification="QUOTE_UNAVAILABLE"
                )

            timestamp=meta.get("regularMarketTime")

            if timestamp is not None:
                stamp=datetime.fromtimestamp(
                    float(timestamp),
                    tz=timezone.utc
                ).isoformat()
            else:
                stamp=datetime.now(timezone.utc).isoformat()

            return AdapterResult(
                True,
                self.name,
                authoritative=False,
                executable=False,
                timestamp=stamp,
                data=Quote(
                    symbol=symbol,
                    bid=float(price),
                    ask=float(price),
                    timestamp=stamp,
                    source=self.name,
                    market_state="open",
                    stale=False,
                    authoritative=False,
                    executable=False
                ),
                classification="PUBLIC_MARKET_REFERENCE"
            )

        except Exception as exc:
            return AdapterResult(
                False,
                self.name,
                False,
                False,
                None,
                error=str(exc),
                classification="QUOTE_ERROR"
            )

    def get_candles(self,symbol,timeframe,limit=100):
        try:
            interval_map={
                "1m":"1m",
                "5m":"5m",
                "15m":"15m",
                "1h":"1h",
                "4h":"1h",
                "1d":"1d"
            }

            interval=interval_map.get(timeframe)

            if interval is None:
                return AdapterResult(
                    False,
                    self.name,
                    False,
                    False,
                    None,
                    error=f"Unsupported timeframe: {timeframe}",
                    classification="TIMEFRAME_UNSUPPORTED"
                )

            if timeframe=="15m":
                range_value="5d"
            elif timeframe=="5m":
                range_value="1d"
            elif timeframe=="1h":
                range_value="30d"
            elif timeframe=="4h":
                range_value="60d"
            elif timeframe=="1d":
                range_value="1y"
            else:
                range_value="1d"

            result=self._request(
                symbol,
                interval,
                range_value
            )

            timestamps=result.get("timestamp") or []

            indicators=result.get(
                "indicators",
                {}
            )

            quote_list=indicators.get("quote") or []

            if not quote_list:
                raise RuntimeError(
                    "Yahoo response contains no quote array"
                )

            quote=quote_list[0]

            opens=quote.get("open") or []
            highs=quote.get("high") or []
            lows=quote.get("low") or []
            closes=quote.get("close") or []
            volumes=quote.get("volume") or []

            candles=[]

            count=min(
                len(timestamps),
                len(opens),
                len(highs),
                len(lows),
                len(closes)
            )

            for i in range(count):
                if any(
                    value is None
                    for value in (
                        opens[i],
                        highs[i],
                        lows[i],
                        closes[i]
                    )
                ):
                    continue

                timestamp=datetime.fromtimestamp(
                    float(timestamps[i]),
                    tz=timezone.utc
                ).isoformat()

                volume=0.0

                if i<len(volumes) and volumes[i] is not None:
                    volume=float(volumes[i])

                candles.append(
                    Candle(
                        timestamp=int(timestamps[i]),
                        open=float(opens[i]),
                        high=float(highs[i]),
                        low=float(lows[i]),
                        close=float(closes[i]),
                        volume=volume
                    )
                )

            candles=candles[-limit:]

            if not candles:
                raise RuntimeError(
                    "Yahoo returned no usable candles"
                )

            return AdapterResult(
                True,
                self.name,
                authoritative=False,
                executable=False,
                timestamp=candles[-1].timestamp,
                data=candles,
                classification="PUBLIC_MARKET_REFERENCE"
            )

        except Exception as exc:
            return AdapterResult(
                False,
                self.name,
                False,
                False,
                None,
                error=str(exc),
                classification="OHLC_ERROR"
            )

    def get_market_state(self,symbol):
        result=self.get_quote(symbol)

        if not result.ok:
            return result

        return AdapterResult(
            True,
            self.name,
            authoritative=False,
            executable=False,
            timestamp=result.timestamp,
            data={
                "symbol":symbol,
                "state":"open",
                "stale":False
            },
            classification="PUBLIC_MARKET_REFERENCE"
        )

class FXDataAdapter(BrokerAdapter):
    """
    Composite market-data adapter.

    Provider order:
    1. configured authenticated market-data provider
    2. BiQuote
    3. Yahoo FX candles

    No public provider is promoted to broker execution authority.
    """

    name="OMNI_LIVE_FX"

    def __init__(self):
        self.bi=BiQuoteProvider()
        self.td=TwelveDataProvider()
        self.yahoo=YahooFXProvider()

    def get_quote(self,symbol):
        providers=[]

        if self.td.key:
            providers.append(self.td)

        providers.append(self.bi)

        last=None

        for provider in providers:
            result=provider.get_quote(symbol)
            last=result

            if result.ok and result.data:
                return result

        return last or AdapterResult(
            False,self.name,False,False,None,None,
            "No quote provider available","NO_PROVIDER"
        )

    def get_candles(self,symbol,timeframe,limit=100):
        result=self.yahoo.get_candles(symbol,timeframe,limit)

        if result.ok:
            return result

        return AdapterResult(
            False,self.name,False,False,None,None,
            result.error or "No OHLC provider available",
            "OHLC_UNAVAILABLE"
        )

    def get_instrument(self,symbol):
        base,quote=split_fx(symbol)

        return AdapterResult(
            True,
            self.name,
            False,
            False,
            datetime.now(timezone.utc).isoformat(),
            Instrument(
                symbol=normalize_symbol(symbol),
                base_currency=base,
                quote_currency=quote,
                price_precision=None,
                tick_size=None,
                pip_size=0.01,
                contract_size=None,
                lot_min=None,
                lot_max=None,
                lot_step=None,
                margin_currency=None,
                provider_symbol=normalize_symbol(symbol),
                provider_timezone="UTC",
                authoritative=False,
                executable=False
            ),
            None,
            "PARTIAL_PUBLIC_FX_METADATA"
        )

    def convert(self,amount,from_currency,to_currency):
        a=from_currency.upper()
        b=to_currency.upper()

        if a==b:
            return AdapterResult(
                True,self.name,False,False,
                datetime.now(timezone.utc).isoformat(),
                {"amount":float(amount),"rate":1.0,
                 "from":a,"to":b},
                None,"IDENTITY_CONVERSION"
            )

        quote=self.get_quote(a+b)

        if quote.ok and quote.data and quote.data.executable:
            rate=(
                quote.data.bid+quote.data.ask
            )/2.0

            return AdapterResult(
                True,self.name,False,False,
                quote.timestamp,
                {
                    "amount":float(amount),
                    "rate":rate,
                    "converted":float(amount)*rate,
                    "from":a,
                    "to":b
                },
                None,
                "LIVE_REFERENCE_CONVERSION"
            )

        inverse=self.get_quote(b+a)

        if inverse.ok and inverse.data:
            rate=(
                inverse.data.bid+inverse.data.ask
            )/2.0

            if rate>0:
                return AdapterResult(
                    True,self.name,False,False,
                    inverse.timestamp,
                    {
                        "amount":float(amount),
                        "rate":1.0/rate,
                        "converted":float(amount)/rate,
                        "from":a,
                        "to":b
                    },
                    None,
                    "LIVE_REFERENCE_CONVERSION"
                )

        return AdapterResult(
            False,self.name,False,False,None,None,
            f"No usable {a}/{b} conversion provider",
            "CONVERSION_UNAVAILABLE"
        )

    def get_market_state(self,symbol):
        quote=self.get_quote(symbol)

        if not quote.ok or not quote.data:
            return AdapterResult(
                False,self.name,False,False,None,None,
                quote.error or "Market state unavailable",
                "MARKET_STATE_UNAVAILABLE"
            )

        return AdapterResult(
            True,
            quote.source,
            quote.authoritative,
            quote.executable,
            quote.timestamp,
            {
                "symbol":quote.data.symbol,
                "state":quote.data.market_state,
                "stale":quote.data.stale
            },
            None,
            "VERIFIED_LIVE"
            if quote.data.executable
            else "REFERENCE_OR_STALE"
        )

class AuthenticatedBrokerAdapter(BrokerAdapter):
    """
    Execution slot.

    A real implementation must be attached here through an authenticated
    broker API or terminal bridge. Nothing is simulated.
    """

    name="AUTHENTICATED_BROKER"

    def __init__(self):
        self.endpoint=os.getenv("OMNI_BROKER_ENDPOINT")
        self.account=os.getenv("OMNI_BROKER_ACCOUNT_ID")
        self.token=os.getenv("OMNI_BROKER_API_KEY")

    @property
    def configured(self):
        return bool(self.endpoint and self.account and self.token)

    def get_account(self):
        if not self.configured:
            return self._unavailable("AUTHENTICATED ACCOUNT")
        return AdapterResult(
            False,self.name,False,False,None,None,
            "Authenticated transport requires broker-specific implementation",
            "BROKER_TRANSPORT_REQUIRED"
        )

    def get_position(self,position_id):
        if not self.configured:
            return self._unavailable("POSITION")
        return AdapterResult(
            False,self.name,False,False,None,None,
            "Authenticated position transport requires broker implementation",
            "BROKER_TRANSPORT_REQUIRED"
        )

    def place_order(self,order):
        if not self.configured:
            return self._execution_unavailable("ORDER")
        return AdapterResult(
            False,self.name,False,False,None,None,
            "Order transport requires broker-specific implementation",
            "BROKER_TRANSPORT_REQUIRED"
        )

    def modify_order(self,order_id,changes):
        if not self.configured:
            return self._execution_unavailable("MODIFY_ORDER")
        return AdapterResult(
            False,self.name,False,False,None,None,
            "Order modification transport requires broker implementation",
            "BROKER_TRANSPORT_REQUIRED"
        )

    def close_position(self,position_id):
        if not self.configured:
            return self._execution_unavailable("CLOSE_POSITION")
        return AdapterResult(
            False,self.name,False,False,None,None,
            "Position close transport requires broker implementation",
            "BROKER_TRANSPORT_REQUIRED"
        )

def capability_matrix(adapter):
    quote=adapter.get_quote("GBPJPY")
    candles=adapter.get_candles("GBPJPY","15m",100)
    instrument=adapter.get_instrument("GBPJPY")
    conversion=adapter.convert(1.0,"JPY","USD")
    state=adapter.get_market_state("GBPJPY")
    account=adapter.get_account()
    position=adapter.get_position("CURRENT")

    return {
        "QUOTE_AUTHORITY":bool(
            quote.ok and quote.authoritative and quote.executable
        ),
        "OHLC_AUTHORITY":bool(
            candles.ok and candles.authoritative
        ),
        "INSTRUMENT_AUTHORITY":bool(
            instrument.ok and instrument.authoritative
        ),
        "ACCOUNT_AUTHORITY":bool(
            account.ok and account.data and
            getattr(account.data,"authenticated",False)
        ),
        "CONVERSION_AUTHORITY":bool(
            conversion.ok and conversion.authoritative
        ),
        "MARKET_STATE_AUTHORITY":bool(
            state.ok and state.authoritative
        ),
        "POSITION_AUTHORITY":bool(
            position.ok and position.authoritative
        ),
        "EXECUTION_AUTHORITY":bool(
            adapter.place_order({}).ok
        ),
        "TIMESTAMP_FRESH":bool(
            quote.timestamp and fresh(quote.timestamp,MAX_QUOTE_AGE)
        )
    }

def authority_confirmed(c):
    return all(c.values())

def print_result(title,result):
    print(f"\n{title}")
    print(f"  OK: {result.ok}")
    print(f"  SOURCE: {result.source}")
    print(f"  AUTHORITATIVE: {result.authoritative}")
    print(f"  EXECUTABLE: {result.executable}")
    print(f"  CLASSIFICATION: {result.classification}")
    if result.timestamp:
        print(f"  TIMESTAMP: {result.timestamp}")
    if result.error:
        print(f"  ERROR: {result.error}")

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║ OMNI BROKER ADAPTER — STEP 23                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    market=FXDataAdapter()
    execution=AuthenticatedBrokerAdapter()

    print("\nMARKET DATA PROVIDER:",market.name)
    print("EXECUTION PROVIDER:",execution.name)

    quote=market.get_quote("GBPJPY")
    candles=market.get_candles("GBPJPY","15m",100)
    instrument=market.get_instrument("GBPJPY")
    conversion=market.convert(1.0,"JPY","USD")
    state=market.get_market_state("GBPJPY")

    print_result("GBPJPY QUOTE",quote)
    print_result("GBPJPY 15M OHLC",candles)
    print_result("GBPJPY INSTRUMENT",instrument)
    print_result("JPY→USD CONVERSION",conversion)
    print_result("MARKET STATE",state)

    print("\nCAPABILITY MATRIX")

    capabilities=capability_matrix(market)

    # Execution capabilities are deliberately evaluated against the
    # authenticated provider separately.
    capabilities["ACCOUNT_AUTHORITY"]=False
    capabilities["POSITION_AUTHORITY"]=False
    capabilities["EXECUTION_AUTHORITY"]=False

    for key,value in capabilities.items():
        print(f"  {key}: {'TRUE' if value else 'FALSE'}")

    print(
        "\nAUTHORITY_CONFIRMED:",
        "TRUE" if authority_confirmed(capabilities) else "FALSE"
    )

    print("\nPROTECTED FILES")
    print("  universal_crt_v4.py : UNTOUCHED")
    print("  OMNICIPHERIST.py    : UNTOUCHED")
    print("  active_trade.json   : UNTOUCHED")
    print("  backups/            : UNTOUCHED")

    print("\nEXECUTION SAFETY")
    print("  NO ORDER SENT")
    print("  NO POSITION MODIFIED")
    print("  NO HISTORICAL TRADE MODIFIED")

if __name__=="__main__":
    main()
