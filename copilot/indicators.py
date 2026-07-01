from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(length).mean()
    avg_loss = loss.rolling(length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(length).mean().fillna(tr.expanding().mean())


def vwap(df: pd.DataFrame) -> pd.Series:
    # Reset VWAP each trading day when a DatetimeIndex is available.
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
        cum_pv = (typical * df["Volume"]).groupby(dates).cumsum()
        cum_vol = df["Volume"].replace(0, np.nan).groupby(dates).cumsum()
        return (cum_pv / cum_vol).ffill()
    return ((typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()).ffill()


def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["EMA_9"] = ema(out["Close"], 9)
    out["EMA_21"] = ema(out["Close"], 21)
    out["RSI_14"] = rsi(out["Close"], 14)
    out["ATR_14"] = atr(out, 14)
    out["VWAP"] = vwap(out)
    out["AVG_VOLUME_20"] = out["Volume"].rolling(20).mean().fillna(out["Volume"].expanding().mean())
    return out
