#!/usr/bin/env python3
"""
One-time pass over the downloaded Databento DBN files: selects the front-month
NQ contract per day, restricts to the 09:30-16:00 ET session, computes the
cumulative in-session VWAP tick-by-tick, and writes one compact Parquet file
per trading day (columns: sec [seconds since 09:30], price, vwap).

This lets sweep.py try hundreds of ORB/buffer/entry-window/day-filter
combinations in seconds instead of re-reading and re-decompressing gigabytes
of raw tick data on every run.

Usage:
    python backtest/build_cache.py --data-dir /path/to/GLBX-... --cache-dir backtest/cache
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
SESSION_OPEN_H, SESSION_OPEN_M = 9, 30
SESSION_CLOSE_H, SESSION_CLOSE_M = 16, 0


def find_data_files(data_dir: str) -> list[str]:
    files = sorted(glob.glob(os.path.join(data_dir, "**", "*.dbn.zst"), recursive=True))
    files += sorted(glob.glob(os.path.join(data_dir, "**", "*.dbn"), recursive=True))
    if not files:
        raise FileNotFoundError(f"No .dbn/.dbn.zst files found under {data_dir!r}")
    return files


def load_file_df(path: str, warned: set) -> pd.DataFrame:
    import databento as db

    store = db.DBNStore.from_file(path)
    df = store.to_df(map_symbols=True)
    df = df.reset_index()
    ts_col = "ts_event" if "ts_event" in df.columns else df.columns[0]

    if "symbol" not in df.columns:
        if "no_symbol" not in warned:
            print("WARNING: no symbol column from Databento symbology; falling back to raw "
                  "instrument_id.", file=sys.stderr)
            warned.add("no_symbol")
        df["symbol"] = df["instrument_id"].astype(str)

    if "action" in df.columns:
        df = df[df["action"] == "T"]

    df[ts_col] = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(ET)
    df = df.rename(columns={ts_col: "ts_event"})
    df["date"] = df["ts_event"].dt.date
    df["price"] = df["price"].astype(float)
    df["size"] = df["size"].astype(float)
    return df[["ts_event", "date", "symbol", "price", "size"]]


def pick_front_month(df: pd.DataFrame) -> pd.DataFrame:
    symbols = df["symbol"].unique()
    if len(symbols) <= 1:
        return df
    looks_continuous = all("." in s for s in symbols) and len(symbols) <= 3
    if looks_continuous:
        return df
    is_outright = df["symbol"].str.match(r"^NQ[A-Z]\d$", na=False)
    candidates = df[is_outright] if is_outright.any() else df
    vol = candidates.groupby(["date", "symbol"])["size"].sum()
    front = vol.groupby(level=0).idxmax().apply(lambda t: t[1])
    df = df.merge(front.rename("front_symbol"), left_on="date", right_index=True)
    return df[df["symbol"] == df["front_symbol"]].drop(columns=["front_symbol"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--cache-dir", default="backtest/cache")
    ap.add_argument("--progress-every", type=int, default=20)
    args = ap.parse_args()

    os.makedirs(args.cache_dir, exist_ok=True)
    files = find_data_files(args.data_dir)
    print(f"{len(files)} files under {args.data_dir}", file=sys.stderr)

    warned: set = set()
    written = 0
    for i, path in enumerate(files, start=1):
        df = load_file_df(path, warned)
        if df.empty:
            continue
        df = pick_front_month(df)
        for date, day in df.groupby("date"):
            base = pd.Timestamp(date).tz_localize(ET)
            open_dt = base + pd.Timedelta(hours=SESSION_OPEN_H, minutes=SESSION_OPEN_M)
            close_dt = base + pd.Timedelta(hours=SESSION_CLOSE_H, minutes=SESSION_CLOSE_M)
            day = day[(day["ts_event"] >= open_dt) & (day["ts_event"] <= close_dt)]
            if day.empty:
                continue
            day = day.sort_values("ts_event")
            cum_pv = (day["price"] * day["size"]).cumsum()
            cum_vol = day["size"].cumsum()
            vwap = cum_pv / cum_vol
            sec = (day["ts_event"] - open_dt).dt.total_seconds()
            out = pd.DataFrame({
                "sec": sec.to_numpy().astype("int32"),
                "price": day["price"].to_numpy().astype("float32"),
                "vwap": vwap.to_numpy().astype("float32"),
            })
            out.to_parquet(os.path.join(args.cache_dir, f"{date}.parquet"), index=False)
            written += 1
        if i % args.progress_every == 0 or i == len(files):
            print(f"  {i}/{len(files)} files -> {written} day-caches written", file=sys.stderr)

    print(f"Done. {written} day files in {args.cache_dir}")


if __name__ == "__main__":
    main()
