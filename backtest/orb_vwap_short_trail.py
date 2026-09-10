#!/usr/bin/env python3
"""
Short-only ORB + VWAP + trailing-stop backtest for NQ (Databento GLBX.MDP3 tick data).

Strategy (see backtest/README notes at the bottom of this file for the full rule text):
  - Instrument: NQ, front-month dominant contract per day, $20/point multiplier.
  - VWAP computed in-session from 09:30 ET, cumulative tick-by-tick, reset every day.
  - ORB candle = first N minutes of the session (N = 5 / 15 / 30, configurable).
  - Signal: ORB candle must close bearish (close < open) AND close below the VWAP
    value at the end of the ORB candle. Otherwise no trade that day.
  - Entry: resting sell LIMIT at the ORB candle's low, live from the end of the ORB
    candle until 11:00 ET. If never touched, the order is cancelled (no trade).
  - Initial stop: the ORB candle's high.
  - From the moment of entry, the stop trails VWAP + buffer (buffer = 10 points,
    already optimized via a 5/10/20/30/40/50 sweep upstream). The stop only ever
    ratchets tighter (down) — it never loosens even if VWAP moves back up.
  - Exit: trailing stop touched, or forced flat at 16:00 ET at the last traded price.
    No take-profit.
  - Day filter and ORB length are both configurable per scenario (see SCENARIOS below):
      * baseline   : 5-minute ORB,  Mon/Tue/Thu only  (original spec)
      * every_15m  : 15-minute ORB, every weekday     (requested change)
      * every_30m  : 30-minute ORB, every weekday     (requested change)
    Each day only ever produces at most one signal/trade, so "one trade per day" is
    already the natural behavior of this engine — no separate flag needed for that.

Usage:
    pip install -r backtest/requirements.txt
    python backtest/orb_vwap_short_trail.py --data-dir "/path/to/GLBX-20260811-G3H4AEKRCH" \
        --output backtest/results.json --trades-csv backtest/trades.csv

The script prints a summary table to stdout and writes:
  - results.json  -> one entry per scenario, shaped to drop straight into the
                      `strategies` Postgres table used by this repo's Strategy Desk app
                      (see backtest/seed_strategies.js).
  - trades.csv     -> every individual simulated trade, for manual verification.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import time as dtime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
MULTIPLIER = 20.0  # $ per point, NQ

SESSION_OPEN = dtime(9, 30)
SESSION_CLOSE = dtime(16, 0)
ENTRY_WINDOW_END = dtime(11, 0)
TRAIL_BUFFER_PTS = 10.0

# Python weekday(): Mon=0 ... Sun=6
DAY_FILTERS = {
    "all": {0, 1, 2, 3, 4},
    "mon_tue_thu": {0, 1, 3},
}

SCENARIOS = [
    {"key": "baseline_5m_mtt", "orb_minutes": 5, "day_filter": "mon_tue_thu",
     "label": "Short ORB 5min + VWAP + Trail 10pts (Lun/Mar/Jeu)"},
    {"key": "every_15m_all_days", "orb_minutes": 15, "day_filter": "all",
     "label": "Short ORB 15min + VWAP + Trail 10pts (tous les jours)"},
    {"key": "every_30m_all_days", "orb_minutes": 30, "day_filter": "all",
     "label": "Short ORB 30min + VWAP + Trail 10pts (tous les jours)"},
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trades(data_dir: str) -> pd.DataFrame:
    import databento as db

    files = sorted(glob.glob(os.path.join(data_dir, "**", "*.dbn.zst"), recursive=True))
    files += sorted(glob.glob(os.path.join(data_dir, "**", "*.dbn"), recursive=True))
    if not files:
        raise FileNotFoundError(f"No .dbn/.dbn.zst files found under {data_dir!r}")

    print(f"Loading {len(files)} DBN file(s) from {data_dir} ...", file=sys.stderr)

    frames = []
    for f in files:
        store = db.DBNStore.from_file(f)
        df = store.to_df(map_symbols=True)
        frames.append(df)
    raw = pd.concat(frames)
    raw = raw.sort_index()
    raw = raw.reset_index()

    ts_col = "ts_event" if "ts_event" in raw.columns else raw.columns[0]

    if "symbol" not in raw.columns:
        raw["symbol"] = raw["instrument_id"].astype(str)
        print("WARNING: no 'symbol' column from Databento symbology — falling back to raw "
              "instrument_id. Front-month selection may be unreliable; re-download using "
              "parent/continuous symbology (e.g. stype_in='parent', symbols=['NQ.FUT']) if this "
              "looks wrong.", file=sys.stderr)

    # Keep only actual trade prints if the schema carries an `action` column
    # (mbp-1 / tbbo / mbo all do; a pure `trades` schema does not).
    if "action" in raw.columns:
        raw = raw[raw["action"] == "T"]

    missing = {"price", "size"} - set(raw.columns)
    if missing:
        raise ValueError(f"Expected 'price'/'size' columns in trade data, missing {missing}. "
                          f"Got columns: {raw.columns.tolist()}")

    raw[ts_col] = pd.to_datetime(raw[ts_col], utc=True).dt.tz_convert(ET)
    raw = raw.rename(columns={ts_col: "ts_event"})
    raw["date"] = raw["ts_event"].dt.date
    raw["price"] = raw["price"].astype(float)
    raw["size"] = raw["size"].astype(float)

    return raw[["ts_event", "date", "symbol", "price", "size"]]


def pick_front_month(df: pd.DataFrame) -> pd.DataFrame:
    """Keep, for each trading day, only the NQ contract with the highest traded volume.

    Skipped automatically if the data already looks like a single continuous
    series (Databento continuous symbols like 'NQ.v.0' / 'NQ.c.0').
    """
    symbols = df["symbol"].unique()
    if len(symbols) <= 1:
        return df
    looks_continuous = all("." in s for s in symbols) and len(symbols) <= 3
    if looks_continuous:
        return df

    is_outright = df["symbol"].str.match(r"^NQ[A-Z]\d$", na=False)
    candidates = df[is_outright] if is_outright.any() else df

    vol_by_day_symbol = candidates.groupby(["date", "symbol"])["size"].sum()
    front = vol_by_day_symbol.groupby(level=0).idxmax().apply(lambda t: t[1])
    df = df.merge(front.rename("front_symbol"), left_on="date", right_index=True)
    return df[df["symbol"] == df["front_symbol"]].drop(columns=["front_symbol"])


# ---------------------------------------------------------------------------
# Per-day simulation
# ---------------------------------------------------------------------------

def session_bounds(date) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    base = pd.Timestamp(date).tz_localize(ET)
    open_dt = base + pd.Timedelta(hours=SESSION_OPEN.hour, minutes=SESSION_OPEN.minute)
    close_dt = base + pd.Timedelta(hours=SESSION_CLOSE.hour, minutes=SESSION_CLOSE.minute)
    entry_end_dt = base + pd.Timedelta(hours=ENTRY_WINDOW_END.hour, minutes=ENTRY_WINDOW_END.minute)
    return open_dt, close_dt, entry_end_dt


def build_orb(day: pd.DataFrame, open_dt: pd.Timestamp, orb_minutes: int):
    orb_end_dt = open_dt + pd.Timedelta(minutes=orb_minutes)
    orb_slice = day[(day["ts_event"] >= open_dt) & (day["ts_event"] < orb_end_dt)]
    if orb_slice.empty:
        return None
    return {
        "open": orb_slice["price"].iloc[0],
        "high": orb_slice["price"].max(),
        "low": orb_slice["price"].min(),
        "close": orb_slice["price"].iloc[-1],
        "vwap_at_close": orb_slice["vwap"].iloc[-1],
        "end_time": orb_end_dt,
    }


def simulate_day(day: pd.DataFrame, orb: dict, entry_end_dt: pd.Timestamp,
                  buffer_pts: float = TRAIL_BUFFER_PTS):
    if not (orb["close"] < orb["open"] and orb["close"] < orb["vwap_at_close"]):
        return None  # not bearish-and-below-VWAP -> no signal

    limit_price = orb["low"]
    initial_stop = orb["high"]

    window = day[(day["ts_event"] >= orb["end_time"]) & (day["ts_event"] <= entry_end_dt)]
    fillable = window[window["price"] >= limit_price]
    if fillable.empty:
        return None  # resting sell limit never touched -> cancelled

    entry_row = fillable.iloc[0]
    entry_time = entry_row["ts_event"]
    entry_price = limit_price

    sub = day[day["ts_event"] >= entry_time].copy()
    sub["stop_candidate"] = sub["vwap"] + buffer_pts
    # Ratchet: stop only ever tightens. Equivalent to a running min against the
    # initial stop and the cumulative-min of (vwap + buffer) since entry.
    sub["running_stop"] = np.minimum(initial_stop, sub["stop_candidate"].cummin())

    hit = sub[sub["price"] >= sub["running_stop"]]
    if not hit.empty:
        exit_row = hit.iloc[0]
        exit_time = exit_row["ts_event"]
        exit_price = float(exit_row["running_stop"])
        exit_reason = "trail_stop"
    else:
        exit_row = sub.iloc[-1]
        exit_time = exit_row["ts_event"]
        exit_price = float(exit_row["price"])
        exit_reason = "session_close"

    mfe_price = sub[sub["ts_event"] <= exit_time]["price"].min()
    pnl_points = entry_price - exit_price
    pnl_dollars = pnl_points * MULTIPLIER

    return {
        "date": str(day["date"].iloc[0]),
        "entry_time": entry_time.isoformat(),
        "entry_price": float(entry_price),
        "exit_time": exit_time.isoformat(),
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "initial_stop": float(initial_stop),
        "pnl_points": float(pnl_points),
        "pnl_dollars": float(pnl_dollars),
        "reached_breakeven": bool(mfe_price < entry_price),
    }


def run_scenario(df_front: pd.DataFrame, orb_minutes: int, day_filter: str,
                  buffer_pts: float = TRAIL_BUFFER_PTS) -> list[dict]:
    allowed_weekdays = DAY_FILTERS[day_filter]
    trades = []
    for date, day in df_front.groupby("date"):
        if pd.Timestamp(date).weekday() not in allowed_weekdays:
            continue
        open_dt, close_dt, entry_end_dt = session_bounds(date)
        day = day[(day["ts_event"] >= open_dt) & (day["ts_event"] <= close_dt)]
        if day.empty:
            continue
        day = day.sort_values("ts_event")
        day["cum_pv"] = (day["price"] * day["size"]).cumsum()
        day["cum_vol"] = day["size"].cumsum()
        day["vwap"] = day["cum_pv"] / day["cum_vol"]

        orb = build_orb(day, open_dt, orb_minutes)
        if orb is None:
            continue
        trade = simulate_day(day, orb, entry_end_dt, buffer_pts)
        if trade:
            trades.append(trade)
    return trades


# ---------------------------------------------------------------------------
# Summary / output shaping
# ---------------------------------------------------------------------------

def summarize(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0, "net_pnl": 0.0, "win_rate": None, "avg_win": None,
                "avg_loss": None, "trades_reaching_breakeven": 0}
    pnls = [t["pnl_dollars"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    return {
        "trades": len(trades),
        "net_pnl": round(sum(pnls), 2),
        "win_rate": round(100.0 * len(wins) / len(trades), 2),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else None,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else None,
        "trades_reaching_breakeven": sum(1 for t in trades if t["reached_breakeven"]),
    }


def build_rules(orb_minutes: int, day_filter: str) -> dict:
    days_txt = {"mon_tue_thu": "lundi, mardi, jeudi uniquement",
                "all": "tous les jours de semaine (lundi a vendredi), un trade par jour"}[day_filter]
    return {
        "vwap": {
            "definition": (
                f"VWAP calcule en session, demarre a {SESSION_OPEN.strftime('%Hh%M')}, reset chaque "
                "jour, cumule tick par tick : VWAP = somme(prix x volume) / somme(volume) depuis "
                "l'ouverture."
            )
        },
        "entry": {
            "note": (
                f"Jours tradés : {days_txt}. Short uniquement (longs exclus). On attend la cloture "
                f"de la premiere bougie de {orb_minutes} minutes."
            ),
            "short": (
                f"Bougie {orb_minutes}min baissiere (close < open) ET close < VWAP a la cloture de la "
                "bougie -> ordre limite de vente au plus bas (low) de la bougie, actif de la fin de "
                f"la bougie jusqu'a {ENTRY_WINDOW_END.strftime('%Hh%M')}."
            ),
            "no_trade": (
                f"Si l'ordre limite n'est jamais touche avant {ENTRY_WINDOW_END.strftime('%Hh%M')}, "
                "il est annule -> pas de trade ce jour-la."
            ),
            "entry_price": "Low de la bougie d'ouverture (fill limite, sans slippage modelise)",
        },
        "initial_stop": {
            "method": "Stop initial = high de la bougie d'ouverture.",
            "short": f"High de la bougie {orb_minutes}min d'ouverture.",
        },
        "position_sizing": {
            "risk_dist": "1 contrat NQ, multiplicateur $20/point.",
        },
        "stop_management": {
            "on_trigger": (
                f"Des l'entree, le stop suit le VWAP + {TRAIL_BUFFER_PTS:.0f} points (buffer fixe, "
                "trouve optimal par sweep 5/10/20/30/40/50)."
            ),
            "after_trigger": "Le stop ne se resserre que dans le sens favorable (ratchet), jamais l'inverse.",
            "if_never_stopped": (
                f"Sortie forcee a {SESSION_CLOSE.strftime('%Hh%M')} (cloture de session), au dernier "
                "prix trade."
            ),
        },
        "notes": (
            f"Variante: ORB {orb_minutes} minutes, {days_txt}. Pas de take-profit; sortie uniquement "
            "sur trailing stop ou cloture de session."
        ),
    }


def scenario_to_strategy_row(scn: dict, trades: list[dict]) -> dict:
    summary = summarize(trades)
    return {
        "slug": scn["key"].replace("_", "-"),
        "name": scn["label"],
        "category": "ORB + VWAP",
        "description": (
            f"Short-only opening-range breakout ({scn['orb_minutes']}min) filtre par VWAP, stop "
            f"initial au high de l'ORB puis trailing VWAP+{TRAIL_BUFFER_PTS:.0f}pts (ratchet). "
            f"Jours: {'Lun/Mar/Jeu' if scn['day_filter'] == 'mon_tue_thu' else 'tous les jours'}."
        ),
        **summary,
        "rules": build_rules(scn["orb_minutes"], scn["day_filter"]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True, help="Folder containing the Databento .dbn/.dbn.zst files")
    ap.add_argument("--output", default="backtest/results.json", help="Where to write the per-scenario JSON summary")
    ap.add_argument("--trades-csv", default="backtest/trades.csv", help="Where to write the full trade log (all scenarios)")
    ap.add_argument("--buffer", type=float, default=TRAIL_BUFFER_PTS, help="Trailing buffer above VWAP, in points")
    args = ap.parse_args()

    raw = load_trades(args.data_dir)
    front = pick_front_month(raw)
    front = front.reset_index(drop=True)

    print(f"{len(front):,} trade ticks across {front['date'].nunique()} trading days after front-month filter.",
          file=sys.stderr)

    results = []
    all_trades_rows = []
    for scn in SCENARIOS:
        trades = run_scenario(front, scn["orb_minutes"], scn["day_filter"], args.buffer)
        for t in trades:
            all_trades_rows.append({"scenario": scn["key"], **t})
        row = scenario_to_strategy_row(scn, trades)
        results.append(row)

        s = row
        print(f"\n=== {scn['label']} ===")
        print(f"  trades: {s['trades']}  net_pnl: ${s['net_pnl']:,}  win_rate: {s['win_rate']}%  "
              f"avg_win: {s['avg_win']}  avg_loss: {s['avg_loss']}  "
              f"reached_breakeven: {s['trades_reaching_breakeven']}/{s['trades']}")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote scenario summary -> {args.output}")

    if all_trades_rows:
        pd.DataFrame(all_trades_rows).to_csv(args.trades_csv, index=False)
        print(f"Wrote full trade log -> {args.trades_csv}")


if __name__ == "__main__":
    main()
