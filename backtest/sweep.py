#!/usr/bin/env python3
"""
Parameter sweep for the short-only ORB + VWAP + trailing-stop strategy, run
against the Parquet day-cache produced by build_cache.py (tick price + running
in-session VWAP, 09:30-16:00 ET, front-month NQ already resolved).

Because everything reads from the cache (no DBN decompression, no front-month
selection), each parameter combination costs milliseconds per day instead of
seconds, so a search over hundreds of combinations finishes in well under a
minute.

Parameters explored, beyond the original spec:
  - orb_minutes        : opening-range length
  - buffer_pts          : trailing distance above VWAP
  - freeze_minutes      : NEW — how long after entry the stop stays frozen at
                           the initial ORB high before it starts trailing VWAP.
                           Added because the original 65-trade baseline showed
                           many trades getting stopped within minutes of entry,
                           when VWAP is still noisy (built on very few ticks).
  - entry_window_end    : how late the resting sell-limit stays live
  - min_orb_range_pts   : NEW — skip signal days where the ORB candle's range
                           is too small (low-conviction / chop filter)
  - day_filter          : which weekdays are eligible

Methodology: a greedy, one-dimension-at-a-time search (same style as the
buffer sweep already used to arrive at the original 10pt figure), run on an
in-sample slice of the data (first ~75% of trading days chronologically) and
then re-checked on the untouched out-of-sample tail (last ~25%), because nine
free parameters swept independently on one year of data will find *something*
that looks good in-sample by chance alone — the out-of-sample check is what
tells us whether that's signal or noise.

Usage:
    python backtest/sweep.py --cache-dir backtest/cache --output backtest/sweep_results.csv
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from datetime import date as ddate

import numpy as np
import pandas as pd

MULTIPLIER = 20.0

DAY_FILTERS = {
    "all": {0, 1, 2, 3, 4},
    "mon_tue_thu": {0, 1, 3},
    "mon_wed_fri": {0, 2, 4},
    "tue_wed_thu": {1, 2, 3},
    "mon": {0}, "tue": {1}, "wed": {2}, "thu": {3}, "fri": {4},
}


# ---------------------------------------------------------------------------
# Cache loading
# ---------------------------------------------------------------------------

def load_cache(cache_dir: str) -> dict[ddate, dict[str, np.ndarray]]:
    files = sorted(glob.glob(os.path.join(cache_dir, "*.parquet")))
    if not files:
        raise FileNotFoundError(f"No cached day files under {cache_dir!r} — run build_cache.py first.")
    days = {}
    for f in files:
        date = ddate.fromisoformat(os.path.basename(f).removesuffix(".parquet"))
        df = pd.read_parquet(f)
        days[date] = {
            "sec": df["sec"].to_numpy(),
            "price": df["price"].to_numpy(dtype="float64"),
            "vwap": df["vwap"].to_numpy(dtype="float64"),
            "weekday": date.weekday(),
        }
    return days


# ---------------------------------------------------------------------------
# Core per-day simulation (pure numpy, no pandas — this is the hot path)
# ---------------------------------------------------------------------------

def simulate_day(sec: np.ndarray, price: np.ndarray, vwap: np.ndarray,
                  orb_minutes: int, buffer_pts: float, freeze_minutes: float,
                  entry_end_min: float, min_orb_range_pts: float,
                  entry_style: str = "limit_retest"):
    """entry_style:
      - "limit_retest": original spec — resting sell LIMIT at the ORB low, fills
        when price rises back UP to that level (a bounce/retest short).
      - "breakout": sell when price BREAKS BELOW the ORB low (momentum
        continuation short) — fills on the first print at or under the low.
    """
    orb_end_sec = orb_minutes * 60
    orb_mask = sec < orb_end_sec
    if not orb_mask.any():
        return None
    orb_price = price[orb_mask]
    o, h, l, c = orb_price[0], orb_price.max(), orb_price.min(), orb_price[-1]
    vwap_at_close = vwap[orb_mask][-1]

    if not (c < o and c < vwap_at_close):
        return None
    if (h - l) < min_orb_range_pts:
        return None

    trigger_price = l
    initial_stop = h

    entry_end_sec = entry_end_min * 60
    window_mask = (sec >= orb_end_sec) & (sec <= entry_end_sec)
    if not window_mask.any():
        return None
    win_sec = sec[window_mask]
    win_price = price[window_mask]
    fillable = win_price >= trigger_price if entry_style == "limit_retest" else win_price <= trigger_price
    if not fillable.any():
        return None
    entry_i = np.argmax(fillable)
    entry_sec = win_sec[entry_i]
    entry_price = trigger_price

    after_mask = sec >= entry_sec
    sub_sec = sec[after_mask]
    sub_price = price[after_mask]
    sub_vwap = vwap[after_mask]

    freeze_until_sec = entry_sec + freeze_minutes * 60
    stop_candidate = np.where(sub_sec < freeze_until_sec, initial_stop, sub_vwap + buffer_pts)
    running_stop = np.minimum.accumulate(np.minimum(initial_stop, stop_candidate))

    hit = sub_price >= running_stop
    if hit.any():
        exit_i = np.argmax(hit)
        exit_price = running_stop[exit_i]
        exit_reason = "trail_stop"
    else:
        exit_price = sub_price[-1]
        exit_reason = "session_close"

    pnl_dollars = (entry_price - exit_price) * MULTIPLIER
    return pnl_dollars, exit_reason


def run_backtest(days: dict, orb_minutes: int, buffer_pts: float, freeze_minutes: float,
                  entry_end_min: float, min_orb_range_pts: float, day_filter: str,
                  entry_style: str = "limit_retest", date_subset: set | None = None) -> dict:
    allowed_weekdays = DAY_FILTERS[day_filter]
    pnls = []
    for date, d in days.items():
        if date_subset is not None and date not in date_subset:
            continue
        if d["weekday"] not in allowed_weekdays:
            continue
        res = simulate_day(d["sec"], d["price"], d["vwap"], orb_minutes, buffer_pts,
                            freeze_minutes, entry_end_min, min_orb_range_pts, entry_style)
        if res is not None:
            pnls.append(res[0])

    if not pnls:
        return {"trades": 0, "net_pnl": 0.0, "win_rate": None, "avg_win": None, "avg_loss": None,
                "expectancy": 0.0}
    pnls_arr = np.array(pnls)
    wins = pnls_arr[pnls_arr > 0]
    losses = pnls_arr[pnls_arr <= 0]
    return {
        "trades": len(pnls_arr),
        "net_pnl": round(float(pnls_arr.sum()), 2),
        "win_rate": round(100.0 * len(wins) / len(pnls_arr), 2),
        "avg_win": round(float(wins.mean()), 2) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else None,
        "expectancy": round(float(pnls_arr.mean()), 2),
    }


# ---------------------------------------------------------------------------
# Greedy one-dimension-at-a-time search
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="backtest/cache")
    ap.add_argument("--output", default="backtest/sweep_results.csv")
    ap.add_argument("--train-frac", type=float, default=0.75,
                     help="Fraction of chronologically-earliest days used for in-sample search")
    args = ap.parse_args()

    days = load_cache(args.cache_dir)
    all_dates = sorted(days.keys())
    split_i = int(len(all_dates) * args.train_frac)
    train_dates = set(all_dates[:split_i])
    test_dates = set(all_dates[split_i:])
    print(f"{len(all_dates)} cached trading days: {len(train_dates)} in-sample "
          f"({all_dates[0]}..{all_dates[split_i-1]}), {len(test_dates)} out-of-sample "
          f"({all_dates[split_i]}..{all_dates[-1]})", file=sys.stderr)

    # starting point = the originally specified strategy
    params = {"orb_minutes": 5, "buffer_pts": 10.0, "freeze_minutes": 0.0,
              "entry_end_min": 150.0, "min_orb_range_pts": 0.0, "day_filter": "mon_tue_thu"}

    search_space = [
        ("orb_minutes", [5, 10, 15, 20, 30, 45, 60]),
        ("buffer_pts", [5, 10, 15, 20, 30, 40, 50, 75, 100, 150]),
        ("freeze_minutes", [0, 2, 5, 10, 15, 20, 30, 45]),
        ("entry_end_min", [60, 90, 120, 150, 180, 210, 270, 390]),  # 390 = 16:00, i.e. all session
        ("min_orb_range_pts", [0, 5, 10, 15, 20, 30, 50]),
        ("day_filter", ["all", "mon_tue_thu", "mon_wed_fri", "tue_wed_thu", "mon", "tue", "wed", "thu", "fri"]),
    ]

    all_rows = []

    def score(res):
        # Rank by net P&L in-sample; require a minimum sample size so a 2-trade
        # lucky streak can't look better than a well-sampled strategy.
        if res["trades"] < 15:
            return -1e18
        return res["net_pnl"]

    # baseline
    base_res = run_backtest(days, date_subset=train_dates, **params)
    print(f"Baseline (in-sample): {params} -> {base_res}", file=sys.stderr)
    all_rows.append({"step": "baseline", **params, **base_res})

    for dim, values in search_space:
        best_val = params[dim]
        best_res = run_backtest(days, date_subset=train_dates, **params)
        best_score = score(best_res)
        for v in values:
            trial = dict(params)
            trial[dim] = v
            res = run_backtest(days, date_subset=train_dates, **trial)
            all_rows.append({"step": dim, **trial, **res})
            s = score(res)
            if s > best_score:
                best_score = s
                best_val = v
                best_res = res
        params[dim] = best_val
        print(f"After optimizing {dim}: {dim}={best_val} -> in-sample {best_res}", file=sys.stderr)

    print(f"\nFinal params after greedy search: {params}", file=sys.stderr)
    final_in = run_backtest(days, date_subset=train_dates, **params)
    final_out = run_backtest(days, date_subset=test_dates, **params)
    final_all = run_backtest(days, date_subset=None, **params)
    print(f"Final IN-SAMPLE   : {final_in}", file=sys.stderr)
    print(f"Final OUT-OF-SAMPLE: {final_out}", file=sys.stderr)
    print(f"Final FULL PERIOD  : {final_all}", file=sys.stderr)

    pd.DataFrame(all_rows).to_csv(args.output, index=False)
    print(f"\nWrote {len(all_rows)} tried combinations -> {args.output}")


if __name__ == "__main__":
    main()
