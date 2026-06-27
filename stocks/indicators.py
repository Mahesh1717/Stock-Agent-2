from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Sequence

import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator


@dataclass(frozen=True)
class IndicatorResult:
    rsi: float
    macd: float
    macd_signal: float
    macd_bullish: bool
    sma20: float
    sma50: float
    close: float
    price_above_sma20: bool
    volume_ratio: float


class TechnicalAnalyzer:
    def analyze(self, yahoo_symbols: str | Sequence[str]) -> IndicatorResult:
        symbols = [yahoo_symbols] if isinstance(yahoo_symbols, str) else list(yahoo_symbols)
        data = pd.DataFrame()
        used_symbol = ""

        yfinance_logger = logging.getLogger("yfinance")
        previous_level = yfinance_logger.level
        yfinance_logger.setLevel(logging.CRITICAL)
        try:
            for symbol in symbols:
                used_symbol = symbol
                data = yf.download(
                    symbol,
                    period="6mo",
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if not data.empty:
                    break
        finally:
            yfinance_logger.setLevel(previous_level)

        if data.empty:
            tried = ", ".join(symbols)
            raise ValueError(f"No market data found for any Yahoo symbol: {tried}")

        frame = self._normalize_columns(data)
        if len(frame) < 50:
            raise ValueError(
                f"Not enough market history for {used_symbol}: "
                f"{len(frame)} rows found, 50 rows needed"
            )

        close = frame["Close"]
        volume = frame["Volume"]

        frame["RSI"] = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close)
        frame["MACD"] = macd.macd()
        frame["MACD_SIGNAL"] = macd.macd_signal()
        frame["SMA20"] = SMAIndicator(close=close, window=20).sma_indicator()
        frame["SMA50"] = SMAIndicator(close=close, window=50).sma_indicator()
        frame["VOLUME_AVG20"] = volume.rolling(20).mean()

        calculated = frame.dropna()
        if calculated.empty:
            raise ValueError(f"Unable to calculate indicators for {used_symbol}")

        latest = calculated.iloc[-1]
        volume_ratio = latest["Volume"] / latest["VOLUME_AVG20"] if latest["VOLUME_AVG20"] else 0.0

        return IndicatorResult(
            rsi=float(latest["RSI"]),
            macd=float(latest["MACD"]),
            macd_signal=float(latest["MACD_SIGNAL"]),
            macd_bullish=bool(latest["MACD"] > latest["MACD_SIGNAL"]),
            sma20=float(latest["SMA20"]),
            sma50=float(latest["SMA50"]),
            close=float(latest["Close"]),
            price_above_sma20=bool(latest["Close"] > latest["SMA20"]),
            volume_ratio=float(volume_ratio),
        )

    @staticmethod
    def _normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = data.columns.get_level_values(0)
        return data
