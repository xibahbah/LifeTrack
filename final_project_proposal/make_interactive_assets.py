from pathlib import Path
import json

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path("/Users/keith/Desktop/LifeTrack")
OUT = ROOT / "final_project_proposal"
FIG = OUT / "figures_interactive"
DATA = OUT / "data"
SAMPLE = DATA / "acceleration_every500.csv"
REFERENCE = ROOT / "LifeTrack White Stork SW Germany_2013-2019-reference-data.csv"
JSON_OUT = DATA / "stork_pulse_interactive.json"

FIG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

BG = "#05070c"
PANEL = "#0b1020"
PANEL2 = "#111827"
GRID = "#243044"
TEXT = "#f8fbff"
MUTED = "#9aa6b8"
CYAN = "#47d7ff"
GOLD = "#ffd166"
CORAL = "#ff5c6c"
GREEN = "#7cf6bf"
PURPLE = "#b88cff"

CMAP = LinearSegmentedColormap.from_list("pulse", ["#0b1020", "#18405c", CYAN, GOLD, CORAL])


def activity_index(raw):
    values = np.fromstring(str(raw), sep=" ", dtype=np.float32)
    values = values[: len(values) - (len(values) % 3)]
    if len(values) < 6:
        return np.nan
    arr = values.reshape(-1, 3)
    centered = arr - arr.mean(axis=0)
    return float(np.sqrt((centered * centered).sum(axis=1)).mean())


def short_name(value):
    return str(value).split("/")[0].replace("+", "").strip()


def season(month):
    return ["Winter", "Spring", "Summer", "Fall"][(month % 12) // 3]


def setup():
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": PANEL,
            "savefig.facecolor": BG,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": TEXT,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 18,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "grid.color": GRID,
            "grid.alpha": 0.45,
        }
    )


def save(fig, name):
    fig.savefig(FIG / name, dpi=230, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def load():
    df = pd.read_csv(SAMPLE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["activity"] = df["eobs:accelerations-raw"].map(activity_index)
    df = df.dropna(subset=["activity"])
    df["log_activity"] = np.log10(df["activity"] + 1)
    df["bird"] = df["individual-local-identifier"].map(short_name)
    df["period"] = df["timestamp"].dt.to_period("M").astype(str)
    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.month
    df["season"] = df["month"].map(season)

    ref = pd.read_csv(REFERENCE)
    ref["tag-id"] = ref["tag-id"].astype(str)
    ref["bird"] = ref["animal-id"].map(short_name)
    ref["status"] = np.where(ref["deployment-end-type"].eq("dead"), "recorded dead", "no recorded death")
    ref["deploy-on-date"] = pd.to_datetime(ref["deploy-on-date"], errors="coerce")
    ref["deploy-off-date"] = pd.to_datetime(ref["deploy-off-date"], errors="coerce")
    ref = ref.drop_duplicates("bird")
    meta = ref.set_index("bird")
    df["status"] = df["bird"].map(meta["status"]).fillna("unknown")
    df["sex"] = df["bird"].map(meta["animal-sex"]).fillna("")
    return df, ref


def write_json(df):
    top = df["bird"].value_counts().head(20).index.tolist()
    months = sorted(df["period"].unique())
    birds = []
    for bird in top:
        sub = df[df["bird"].eq(bird)]
        monthly = sub.groupby("period")["log_activity"].median()
        counts = sub.groupby("period").size()
        hourly = sub.groupby("hour")["log_activity"].mean().reindex(range(24)).fillna(0)
        seasons = sub.groupby("season")["log_activity"].median()
        birds.append(
            {
                "name": bird,
                "records": int(len(sub)),
                "first": str(sub["timestamp"].min().date()),
                "last": str(sub["timestamp"].max().date()),
                "status": str(sub["status"].mode().iloc[0]) if len(sub) else "",
                "sex": str(sub["sex"].mode().iloc[0]) if len(sub) else "",
                "monthly": [None if pd.isna(monthly.get(m, np.nan)) else round(float(monthly.get(m)), 3) for m in months],
                "counts": [int(counts.get(m, 0)) for m in months],
                "hourly": [round(float(v), 3) for v in hourly.values],
                "season": {s: round(float(seasons.get(s)), 3) for s in seasons.index},
            }
        )
    payload = {
        "months": months,
        "birds": birds,
        "maxLogActivity": round(float(df["log_activity"].quantile(0.98)), 3),
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2))
    return payload


def draw_ui_chrome(ax, title, subtitle):
    ax.set_facecolor(BG)
    ax.text(0.015, 0.965, title, transform=ax.transAxes, fontsize=25, weight="bold", color=TEXT, va="top")
    ax.text(0.017, 0.91, subtitle, transform=ax.transAxes, fontsize=10.5, color=MUTED, va="top")
    chips = ["All birds", "Season", "Outcome", "Play pulse"]
    x = 0.72
    for chip in chips:
        ax.text(
            x,
            0.955,
            chip,
            transform=ax.transAxes,
            fontsize=8.5,
            color=TEXT,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.8", fc=PANEL2, ec=GRID, lw=0.8),
        )
        x += 0.075


def fig_pulse_wall(df):
    top = df["bird"].value_counts().head(18).index
    months = sorted(df["period"].unique())
    pivot = df[df["bird"].isin(top)].pivot_table(index="bird", columns="period", values="log_activity", aggfunc="median")
    pivot = pivot.loc[top, months]

    fig, ax = plt.subplots(figsize=(15, 8))
    draw_ui_chrome(ax, "STORK PULSE", "A proposed D3 interaction: click a bird row, scrub months, and watch its motion profile recompose.")
    heat_ax = fig.add_axes([0.08, 0.13, 0.84, 0.66], facecolor=PANEL)
    im = heat_ax.imshow(np.ma.masked_invalid(pivot.values), aspect="auto", cmap=CMAP, vmin=0.8, vmax=df["log_activity"].quantile(0.98))
    heat_ax.set_yticks(range(len(pivot.index)), pivot.index)
    ticks = [i for i, m in enumerate(months) if m.endswith("-01")]
    heat_ax.set_xticks(ticks, [months[i][:4] for i in ticks])
    heat_ax.tick_params(length=0)
    for spine in heat_ax.spines.values():
        spine.set_visible(False)
    # Highlight a selected month column like an interactive scrubber.
    h = months.index("2014-08") if "2014-08" in months else len(months) // 4
    heat_ax.axvline(h, color=TEXT, lw=1.2, alpha=0.9)
    heat_ax.text(h + 0.6, -1.2, "scrubbed month", color=TEXT, fontsize=9)
    cbar = fig.colorbar(im, ax=heat_ax, fraction=0.018, pad=0.012)
    cbar.set_label("median motion pulse")
    save(fig, "01_interactive_pulse_wall.png")


def fig_selected_bird(df):
    bird = df["bird"].value_counts().index[0]
    sub = df[df["bird"].eq(bird)].sort_values("timestamp")
    monthly = sub.groupby("period")["log_activity"].median()
    months = sorted(df["period"].unique())
    values = np.array([monthly.get(m, np.nan) for m in months], dtype=float)
    hourly = sub.groupby("hour")["log_activity"].mean().reindex(range(24)).fillna(0)

    fig = plt.figure(figsize=(14, 8), facecolor=BG)
    title_ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    title_ax.set_axis_off()
    draw_ui_chrome(title_ax, f"SELECTED BIRD: {bird.upper()}", "The final page will make every stork feel inspectable, not anonymous.")

    ax1 = fig.add_axes([0.07, 0.16, 0.58, 0.55], facecolor=PANEL)
    x = np.arange(len(months))
    ax1.bar(x, np.nan_to_num(values, nan=0), color=[CYAN if not np.isnan(v) else "#182033" for v in values], width=0.8)
    ax1.plot(x, pd.Series(values).interpolate(limit_direction="both"), color=GOLD, lw=2.2)
    ax1.set_title("Monthly pulse timeline", loc="left")
    ax1.set_xticks([i for i, m in enumerate(months) if m.endswith("-01")], [m[:4] for m in months if m.endswith("-01")])
    ax1.set_ylabel("median log activity")
    ax1.grid(True, axis="y")
    ax1.text(0.02, 0.9, f"{len(sub):,} sampled bursts\\n{sub.timestamp.min().date()} to {sub.timestamp.max().date()}",
             transform=ax1.transAxes, fontsize=12, color=TEXT, bbox=dict(fc="#111827cc", ec=GRID, pad=7))

    ax2 = fig.add_axes([0.72, 0.16, 0.22, 0.55], polar=True, facecolor=PANEL)
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    vals = hourly.values
    vals = vals / max(vals.max(), 0.01)
    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.bar(theta, vals, width=2 * np.pi / 24 * 0.82, color=CORAL, alpha=0.82)
    ax2.set_title("24-hour rhythm", pad=18)
    ax2.set_yticklabels([])
    ax2.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False), ["0", "3", "6", "9", "12", "15", "18", "21"])
    ax2.grid(color=GRID, alpha=0.45)
    save(fig, "02_selected_bird_dashboard.png")


def fig_comparison_mode(df):
    birds = df["bird"].value_counts().head(6).index
    months = sorted(df["period"].unique())
    fig, axes = plt.subplots(3, 2, figsize=(13, 9), sharex=True, facecolor=BG)
    fig.suptitle("Comparison mode: six birds, six different rhythms", fontsize=23, weight="bold", y=0.98)
    for ax, bird in zip(axes.flat, birds):
        sub = df[df["bird"].eq(bird)]
        s = sub.groupby("period")["log_activity"].median().reindex(months)
        x = np.arange(len(months))
        ax.fill_between(x, 0, s.interpolate(limit_direction="both"), color=CYAN, alpha=0.2)
        ax.plot(x, s.interpolate(limit_direction="both"), color=GOLD, lw=2)
        ax.scatter(x, s, s=10, color=CORAL, alpha=0.9)
        ax.set_title(bird, loc="left", fontsize=12)
        ax.set_ylim(0.7, max(2.5, df["log_activity"].quantile(0.98)))
        ax.grid(True, axis="y")
        ticks = [i for i, m in enumerate(months) if m.endswith("-01")]
        ax.set_xticks(ticks, [months[i][:4] for i in ticks])
    save(fig, "03_comparison_mode.png")


def fig_behavior_constellation(df):
    birds = []
    for bird, sub in df.groupby("bird"):
        if len(sub) < 40:
            continue
        day = sub[sub["hour"].between(7, 18)]["log_activity"].median()
        night = sub[~sub["hour"].between(7, 18)]["log_activity"].median()
        summer = sub[sub["season"].eq("Summer")]["log_activity"].median()
        winter = sub[sub["season"].eq("Winter")]["log_activity"].median()
        birds.append(
            {
                "bird": bird,
                "day_night_gap": day - night,
                "season_gap": summer - winter,
                "records": len(sub),
                "status": sub["status"].mode().iloc[0],
            }
        )
    pts = pd.DataFrame(birds).dropna()
    fig, ax = plt.subplots(figsize=(10, 7), facecolor=BG)
    colors = np.where(pts["status"].eq("recorded dead"), CORAL, CYAN)
    sizes = np.clip(pts["records"] / 2.2, 25, 600)
    ax.scatter(pts["day_night_gap"], pts["season_gap"], s=sizes, c=colors, alpha=0.75, edgecolor=TEXT, linewidth=0.4)
    for _, row in pts.nlargest(7, "records").iterrows():
        ax.text(row["day_night_gap"] + 0.01, row["season_gap"] + 0.01, row["bird"], fontsize=8, color=TEXT)
    ax.axhline(0, color=GRID, lw=1)
    ax.axvline(0, color=GRID, lw=1)
    ax.set_title("Behavior constellation")
    ax.set_xlabel("day activity minus night activity")
    ax.set_ylabel("summer activity minus winter activity")
    ax.text(0.02, 0.94, "Each circle is a bird; size = sampled records; coral = recorded dead.", transform=ax.transAxes, color=MUTED, fontsize=9)
    ax.grid(True)
    save(fig, "04_behavior_constellation.png")


def fig_story_scrubber(df):
    months = ["2014-08", "2015-01", "2018-07"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.5), facecolor=BG)
    fig.suptitle("Story scrubber: the same birds under different months", fontsize=22, weight="bold", y=1.02)
    for ax, month in zip(axes, months):
        sub = df[df["period"].eq(month)]
        ranks = sub.groupby("bird")["log_activity"].median().sort_values(ascending=False).head(12).sort_values()
        ax.barh(ranks.index, ranks.values, color=CMAP((ranks.values - df["log_activity"].min()) / (df["log_activity"].quantile(0.98) - df["log_activity"].min())))
        ax.set_title(month)
        ax.set_xlabel("median pulse")
        ax.grid(True, axis="x")
    save(fig, "05_story_scrubber_frames.png")


def fig_lifeline_map(ref, df):
    ref = ref.copy()
    last_sample = df.groupby("bird")["timestamp"].max()
    ref["visual_end"] = ref["deploy-off-date"].fillna(ref["bird"].map(last_sample)).fillna(df["timestamp"].max())
    ref["duration"] = (ref["visual_end"] - ref["deploy-on-date"]).dt.days
    ref = ref.dropna(subset=["deploy-on-date", "duration"]).sort_values("duration").tail(45)
    y = np.arange(len(ref))
    fig, ax = plt.subplots(figsize=(12, 8), facecolor=BG)
    for yi, (_, r) in enumerate(ref.iterrows()):
        color = CORAL if r["status"] == "recorded dead" else CYAN
        ax.plot([r["deploy-on-date"], r["visual_end"]], [yi, yi], color=color, lw=2.2, alpha=0.92)
        ax.scatter(r["visual_end"], yi, s=35, color=color, edgecolor=BG, linewidth=0.8)
    ax.set_title("Deployment lifelines: the human stakes behind the pulses")
    ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="x")
    ax.text(0.02, 0.94, "The final interaction will let readers click a lifeline and jump to that bird's pulse record.",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "06_outcome_lifelines.png")


def main():
    setup()
    df, ref = load()
    write_json(df)
    fig_pulse_wall(df)
    fig_selected_bird(df)
    fig_comparison_mode(df)
    fig_behavior_constellation(df)
    fig_story_scrubber(df)
    fig_lifeline_map(ref, df)
    print(f"wrote {JSON_OUT}")
    print(f"wrote figures to {FIG}")


if __name__ == "__main__":
    main()
