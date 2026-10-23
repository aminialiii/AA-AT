"""Trade charts from recorded market data only; never synthesizes a price path."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .store import Warehouse, number, utc


class MarketDataUnavailable(RuntimeError):
    pass


def _market_rows(warehouse: Warehouse, symbol: str, first: str, last: str):
    bars = warehouse.db.execute(
        """SELECT timeframe,open_utc,open,high,low,close,tick_volume,spread_points,
           source_sha256 FROM market_bars WHERE symbol=? AND open_utc BETWEEN ? AND ?
           ORDER BY open_utc""", (symbol, first, last)).fetchall()
    ticks = warehouse.db.execute(
        """SELECT time_utc,bid,ask FROM market_ticks
           WHERE symbol=? AND time_utc BETWEEN ? AND ? ORDER BY time_utc""",
        (symbol, first, last)).fetchall()
    return bars, ticks


def _excursion(warehouse: Warehouse, row, bars, ticks) -> dict:
    entry = float(json.loads(row["record_json"])["entry_price"])
    stop = float(row["initial_sl"])
    distance = abs(entry - stop)
    if distance <= 0 or row["direction"] not in {"BUY", "SELL"}:
        return {"quality": "UNAVAILABLE"}
    open_time = datetime.fromisoformat(row["entry_utc"])
    close_time = datetime.fromisoformat(row["exit_utc"])
    inside_ticks = [tick for tick in ticks
                    if open_time <= datetime.fromisoformat(tick["time_utc"]) <= close_time]
    if inside_ticks:
        exit_prices = [float(tick["bid"] if row["direction"] == "BUY" else tick["ask"])
                       for tick in inside_ticks]
        moves = ([price - entry for price in exit_prices] if row["direction"] == "BUY"
                 else [entry - price for price in exit_prices])
        quality = "RECORDED_TICKS_PARTIAL"
        if (datetime.fromisoformat(inside_ticks[0]["time_utc"]) - open_time).total_seconds() <= 1 and (
                close_time - datetime.fromisoformat(inside_ticks[-1]["time_utc"])).total_seconds() <= 1:
            quality = "RECORDED_TICKS_COVERING_ENDPOINTS"
    else:
        inside_bars = [bar for bar in bars if bar["timeframe"] == "M1" and
                       datetime.fromisoformat(bar["open_utc"]) + timedelta(minutes=1) > open_time and
                       datetime.fromisoformat(bar["open_utc"]) < close_time]
        if not inside_bars:
            return {"quality": "UNAVAILABLE"}
        if row["direction"] == "BUY":
            best = max(float(bar["high"]) - entry for bar in inside_bars)
            worst = min(float(bar["low"]) - entry for bar in inside_bars)
        else:
            best = max(entry - float(bar["low"]) for bar in inside_bars)
            worst = min(entry - float(bar["high"]) for bar in inside_bars)
        moves = [best, worst]
        quality = "OHLC_APPROX_INTRABAR_AND_SPREAD_UNKNOWN"
    favorable = max(0.0, max(moves))
    adverse = max(0.0, -min(moves))
    return {"mfe_points": favorable, "mae_points": adverse,
            "mfe_r": favorable / distance, "mae_r": adverse / distance,
            "quality": quality}


def chart(warehouse: Warehouse, trade_id: str, *, pre_minutes: int = 120,
          post_minutes: int = 120) -> dict:
    if not 0 <= pre_minutes <= 10080 or not 0 <= post_minutes <= 10080:
        raise ValueError("invalid_context_window")
    row = warehouse.db.execute(
        "SELECT * FROM trades WHERE trade_id=?", (trade_id,)).fetchone()
    if row is None:
        raise KeyError("trade_not_found")
    entry = datetime.fromisoformat(row["entry_utc"])
    exit_ = datetime.fromisoformat(row["exit_utc"])
    first = (entry - timedelta(minutes=pre_minutes)).isoformat()
    last = (exit_ + timedelta(minutes=post_minutes)).isoformat()
    bars, ticks = _market_rows(warehouse, row["symbol"], first, last)
    if not bars:
        raise MarketDataUnavailable("recorded_candles_unavailable_for_trade_window")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    chart_dir = warehouse.root / "trade_charts"
    chart_dir.mkdir(exist_ok=True)
    grouped = {}
    for bar in bars:
        grouped.setdefault(bar["timeframe"], []).append(bar)
    order = [key for key in ("M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1")
             if key in grouped]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2],
                        vertical_spacing=0.03)
    for index, timeframe in enumerate(order):
        data = grouped[timeframe]
        x = [bar["open_utc"] for bar in data]
        visible = index == 0
        fig.add_trace(go.Candlestick(
            x=x, open=[bar["open"] for bar in data],
            high=[bar["high"] for bar in data], low=[bar["low"] for bar in data],
            close=[bar["close"] for bar in data], name=timeframe,
            visible=visible), row=1, col=1)
        fig.add_trace(go.Bar(
            x=x, y=[bar["tick_volume"] for bar in data], name=timeframe + " volume",
            visible=visible, marker_color="#425d7a"), row=2, col=1)
    record = json.loads(row["record_json"])
    entry_price = float(record["entry_price"])
    exit_price = float(record["exit_price"])
    fig.add_hline(y=float(row["initial_sl"]), line_color="#ef6666",
                  annotation_text="Original SL", row=1, col=1)
    fig.add_hline(y=float(row["initial_tp"]), line_color="#52c49a",
                  annotation_text="Original TP", row=1, col=1)
    fig.add_vrect(x0=row["entry_utc"], x1=row["exit_utc"],
                  fillcolor="#7195c1", opacity=0.08, line_width=0, row=1, col=1)
    fig.add_annotation(x=row["entry_utc"], y=entry_price, text="Broker entry",
                       showarrow=True, arrowcolor="#52c49a", row=1, col=1)
    fig.add_annotation(x=row["exit_utc"], y=exit_price, text="Broker exit",
                       showarrow=True, arrowcolor="#ef6666", row=1, col=1)
    buttons = []
    for index, timeframe in enumerate(order):
        visibility = [False] * (2 * len(order))
        visibility[2 * index:2 * index + 2] = [True, True]
        buttons.append({"label": timeframe, "method": "update",
                        "args": [{"visible": visibility},
                                 {"title": f"{trade_id} | {timeframe}"}]})
    fig.update_layout(
        title=f"{trade_id} | {order[0]}", template="plotly_dark",
        xaxis_rangeslider_visible=False, showlegend=False,
        updatemenus=[{"buttons": buttons, "direction": "down", "x": 1, "y": 1.15}],
        annotations=list(fig.layout.annotations) + [
            {"text": "Recorded candles only; OHLC cannot establish intrabar order.",
             "showarrow": False, "xref": "paper", "yref": "paper", "x": 0, "y": -0.15}
        ],
    )
    html = chart_dir / (trade_id + ".html")
    chart_json = chart_dir / (trade_id + ".json")
    png = chart_dir / (trade_id + ".png")
    fig.write_html(html, include_plotlyjs="directory", full_html=True)
    fig.write_json(chart_json)
    finest = grouped[order[0]]
    figure, axis = plt.subplots(figsize=(14, 6))
    axis.plot([bar["open_utc"] for bar in finest],
              [bar["close"] for bar in finest], color="#70a9e8", linewidth=1)
    axis.axhline(float(row["initial_sl"]), color="#ef6666", label="Original SL")
    axis.axhline(float(row["initial_tp"]), color="#52c49a", label="Original TP")
    axis.scatter([row["entry_utc"], row["exit_utc"]], [entry_price, exit_price],
                 c=["#52c49a", "#ef6666"], zorder=3)
    axis.set_title(f"{trade_id} | recorded {order[0]} close and broker fills")
    axis.tick_params(axis="x", rotation=40)
    axis.legend()
    figure.tight_layout()
    figure.savefig(png, dpi=120)
    plt.close(figure)
    metrics = _excursion(warehouse, row, bars, ticks)
    warehouse.db.execute(
        """INSERT INTO trade_metrics
           (trade_id,mfe_points,mae_points,mfe_r,mae_r,excursion_quality,updated_utc)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(trade_id) DO UPDATE SET
           mfe_points=excluded.mfe_points,mae_points=excluded.mae_points,
           mfe_r=excluded.mfe_r,mae_r=excluded.mae_r,
           excursion_quality=excluded.excursion_quality,updated_utc=excluded.updated_utc""",
        (trade_id, metrics.get("mfe_points"), metrics.get("mae_points"),
         metrics.get("mfe_r"), metrics.get("mae_r"), metrics["quality"], utc()))
    warehouse.db.commit()
    return {"trade_id": trade_id, "html": str(html), "json": str(chart_json), "png": str(png),
            "timeframes": order, "excursion": metrics,
            "candles": len(bars), "ticks": len(ticks)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trade_id")
    parser.add_argument("--state", type=Path,
                        default=Path(r"E:\GPT\Inves\AA-AT-research-state"))
    parser.add_argument("--pre-minutes", type=int, default=120)
    parser.add_argument("--post-minutes", type=int, default=120)
    args = parser.parse_args()
    warehouse = Warehouse(args.state)
    try:
        print(json.dumps(chart(warehouse, args.trade_id, pre_minutes=args.pre_minutes,
                               post_minutes=args.post_minutes)))
    finally:
        warehouse.close()


if __name__ == "__main__":
    main()
