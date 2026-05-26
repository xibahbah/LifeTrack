from __future__ import annotations

import json
import math
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP = ROOT / "raw" / "lifetrack_gps_2016_2023.csv.zip"
OUT_JSON = ROOT / "data" / "stork_migration_map.json"
OUT_STATS = ROOT / "data" / "stork_migration_stats.csv"

USECOLS = [
    "timestamp",
    "location-long",
    "location-lat",
    "ground-speed",
    "individual-local-identifier",
    "visible",
    "algorithm-marked-outlier",
    "import-marked-outlier",
    "manually-marked-outlier",
]


def truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "t", "yes"])


def season_day(ts: pd.Series) -> pd.Series:
    season_start_year = ts.dt.year.where(ts.dt.month >= 7, ts.dt.year - 1)
    start = pd.to_datetime(season_start_year.astype(str) + "-07-01")
    return (ts.dt.floor("D") - start).dt.days


def clean_id(label: str) -> str:
    label = str(label)
    if "/" in label:
        label = label.split("/", 1)[0].strip()
    return label.replace("+", "").strip() or "unnamed stork"


@dataclass
class RouteSummary:
    route_id: str
    bird_id: str
    display_name: str
    season: int
    destination: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    n_days: int
    first_date: str
    last_date: str
    mean_speed: float
    route_score: float


def load_daily_points() -> pd.DataFrame:
    chunks: list[pd.DataFrame] = []
    with zipfile.ZipFile(RAW_ZIP) as zf:
        csv_name = [
            name
            for name in zf.namelist()
            if name.endswith(".csv") and not name.startswith("__MACOSX")
        ][0]
        with zf.open(csv_name) as raw:
            reader = pd.read_csv(
                raw,
                usecols=USECOLS,
                chunksize=500_000,
                low_memory=False,
            )
            for i, chunk in enumerate(reader, start=1):
                ts = pd.to_datetime(chunk["timestamp"], errors="coerce")
                lon = pd.to_numeric(chunk["location-long"], errors="coerce")
                lat = pd.to_numeric(chunk["location-lat"], errors="coerce")
                speed = pd.to_numeric(chunk["ground-speed"], errors="coerce")

                mask = ts.notna() & lon.notna() & lat.notna()
                mask &= ts.dt.year.between(2013, 2019)
                mask &= ts.dt.month.isin([7, 8, 9, 10, 11, 12, 1, 2, 3])
                mask &= lon.between(-20, 45) & lat.between(-35, 60)
                mask &= chunk["visible"].astype(str).str.lower().isin(["true", "1"])
                for col in [
                    "algorithm-marked-outlier",
                    "import-marked-outlier",
                    "manually-marked-outlier",
                ]:
                    mask &= ~truthy(chunk[col].fillna(False))

                if not mask.any():
                    continue

                kept = pd.DataFrame(
                    {
                        "bird_id": chunk.loc[mask, "individual-local-identifier"].astype(str),
                        "date": ts.loc[mask].dt.floor("D"),
                        "timestamp": ts.loc[mask],
                        "lon": lon.loc[mask],
                        "lat": lat.loc[mask],
                        "speed": speed.loc[mask],
                    }
                )
                kept["season"] = kept["timestamp"].dt.year.where(
                    kept["timestamp"].dt.month >= 7,
                    kept["timestamp"].dt.year - 1,
                )
                kept["season_day"] = season_day(kept["timestamp"])
                kept = kept[kept["season_day"].between(0, 273)]

                daily = (
                    kept.sort_values("timestamp")
                    .groupby(["bird_id", "season", "date", "season_day"], as_index=False)
                    .agg(
                        lon=("lon", "median"),
                        lat=("lat", "median"),
                        speed=("speed", "median"),
                        timestamp=("timestamp", "first"),
                    )
                )
                chunks.append(daily)
                if i % 20 == 0:
                    print(f"processed chunk {i}, daily pieces {len(chunks)}")

    if not chunks:
        raise RuntimeError("No usable GPS points were found.")

    daily = pd.concat(chunks, ignore_index=True)
    daily = (
        daily.sort_values("timestamp")
        .groupby(["bird_id", "season", "date", "season_day"], as_index=False)
        .agg(
            lon=("lon", "median"),
            lat=("lat", "median"),
            speed=("speed", "median"),
            timestamp=("timestamp", "first"),
        )
        .sort_values(["bird_id", "season", "season_day"])
    )
    return daily


def classify_route(group: pd.DataFrame) -> str:
    crosses_africa = ((group["lat"] < 35.0) & group["lon"].between(-20, 45)).any()
    if crosses_africa:
        return "Africa crossing"
    return "Spain / short-stopper"


def choose_routes(daily: pd.DataFrame) -> tuple[list[RouteSummary], pd.DataFrame]:
    summaries: list[RouteSummary] = []
    for (bird_id, season), group in daily.groupby(["bird_id", "season"], sort=False):
        group = group.sort_values("season_day")
        n_days = group["date"].nunique()
        if n_days < 28:
            continue
        lat_span = group["lat"].max() - group["lat"].min()
        starts_near_germany = (
            group["lat"].between(45, 55) & group["lon"].between(4, 16)
        ).any()
        moves_south = group["lat"].min() < 46
        if not (starts_near_germany and moves_south and lat_span > 5):
            continue

        destination = classify_route(group)
        africa_bonus = 8 if destination == "Africa crossing" else 0
        score = float(lat_span * 8 + n_days * 0.18 + africa_bonus)
        summaries.append(
            RouteSummary(
                route_id=f"{clean_id(bird_id)} · {season}",
                bird_id=str(bird_id),
                display_name=clean_id(bird_id),
                season=int(season),
                destination=destination,
                min_lat=float(group["lat"].min()),
                max_lat=float(group["lat"].max()),
                min_lon=float(group["lon"].min()),
                max_lon=float(group["lon"].max()),
                n_days=int(n_days),
                first_date=group["date"].min().strftime("%Y-%m-%d"),
                last_date=group["date"].max().strftime("%Y-%m-%d"),
                mean_speed=float(group["speed"].mean(skipna=True)),
                route_score=score,
            )
        )

    summary_df = pd.DataFrame([s.__dict__ for s in summaries])
    if summary_df.empty:
        raise RuntimeError("No complete migration routes survived filtering.")

    # Keep one representative seasonal track per bird, choosing the longest/southernmost
    # migration so the map reads as birds rather than repeated-year duplicates.
    selected = (
        summary_df.sort_values(["bird_id", "route_score"], ascending=[True, False])
        .groupby("bird_id", as_index=False)
        .head(1)
        .sort_values(["destination", "season", "display_name"])
    )

    # Browser readability: keep the map dense enough to show paths, but not so dense
    # that 169 birds become an opaque knot. If more than 169 representative birds are
    # available, use the strongest 169 to mirror the original study size.
    if len(selected) > 169:
        selected = selected.sort_values("route_score", ascending=False).head(169)
    return [RouteSummary(**row) for row in selected.to_dict("records")], selected


def build_json(daily: pd.DataFrame, selected: pd.DataFrame) -> dict:
    selected_keys = set(zip(selected["bird_id"], selected["season"]))
    working = daily[
        daily.apply(lambda row: (row["bird_id"], row["season"]) in selected_keys, axis=1)
    ].copy()
    working["destination"] = working.merge(
        selected[["bird_id", "season", "destination"]],
        on=["bird_id", "season"],
        how="left",
    )["destination"].values

    routes = []
    for _, info in selected.sort_values(["destination", "season", "display_name"]).iterrows():
        group = working[
            (working["bird_id"] == info["bird_id"])
            & (working["season"] == info["season"])
        ].sort_values("season_day")
        points = []
        for row in group.itertuples(index=False):
            speed = None
            if row.speed == row.speed and not math.isinf(row.speed):
                speed = round(float(row.speed), 2)
            points.append(
                {
                    "lon": round(float(row.lon), 5),
                    "lat": round(float(row.lat), 5),
                    "day": int(row.season_day),
                    "date": row.date.strftime("%Y-%m-%d"),
                    "speed": speed,
                }
            )
        if len(points) < 2:
            continue
        routes.append(
            {
                "routeId": info["route_id"],
                "birdId": info["bird_id"],
                "name": info["display_name"],
                "season": int(info["season"]),
                "destination": info["destination"],
                "nDays": int(info["n_days"]),
                "minLat": round(float(info["min_lat"]), 3),
                "meanSpeed": round(float(info["mean_speed"]), 2)
                if info["mean_speed"] == info["mean_speed"]
                else None,
                "firstDate": info["first_date"],
                "lastDate": info["last_date"],
                "points": points,
            }
        )

    africa = sum(1 for r in routes if r["destination"] == "Africa crossing")
    spain = sum(1 for r in routes if r["destination"] == "Spain / short-stopper")
    departures = (
        working.groupby("season_day")
        .agg(n=("bird_id", "nunique"))
        .reset_index()
        .to_dict("records")
    )
    return {
        "source": {
            "title": "LifeTrack White Stork SW Germany GPS tracking data",
            "doi": "10.5441/001/1.ck04mn78",
            "repository": "Movebank Data Repository",
            "yearsUsed": "2013-2019",
            "note": "Daily seasonal samples from real GPS fixes; position always encodes latitude/longitude.",
        },
        "domain": {
            "startDay": 0,
            "endDay": 273,
            "monthTicks": [
                {"day": 0, "label": "Jul"},
                {"day": 31, "label": "Aug"},
                {"day": 62, "label": "Sep"},
                {"day": 92, "label": "Oct"},
                {"day": 123, "label": "Nov"},
                {"day": 153, "label": "Dec"},
                {"day": 184, "label": "Jan"},
                {"day": 215, "label": "Feb"},
                {"day": 243, "label": "Mar"},
            ],
        },
        "summary": {
            "birds": len(routes),
            "africaCrossing": africa,
            "spainShortStopper": spain,
            "spainShare": round(spain / len(routes), 3) if routes else 0,
        },
        "routes": routes,
        "seasonalCounts": departures,
    }


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    daily = load_daily_points()
    summaries, selected = choose_routes(daily)
    data = build_json(daily, selected)
    with OUT_JSON.open("w") as f:
        json.dump(data, f, separators=(",", ":"))
    selected.to_csv(OUT_STATS, index=False)
    print(json.dumps(data["summary"], indent=2))
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_STATS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
