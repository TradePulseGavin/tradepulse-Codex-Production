import pandas as pd

from copilot.indicators import add_core_indicators


def test_add_core_indicators_columns():
    idx = pd.date_range("2026-01-01 09:30", periods=30, freq="5min")
    df = pd.DataFrame(
        {
            "Open": range(100, 130),
            "High": range(101, 131),
            "Low": range(99, 129),
            "Close": range(100, 130),
            "Volume": [1000] * 30,
        },
        index=idx,
    )
    out = add_core_indicators(df)
    for col in ["EMA_9", "EMA_21", "RSI_14", "ATR_14", "VWAP", "AVG_VOLUME_20"]:
        assert col in out.columns
    assert len(out) == len(df)
