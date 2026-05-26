from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path("/Users/keith/Desktop/LifeTrack")
OUT = ROOT / "final_project_proposal"
FIG = OUT / "figures"
SAMPLE = OUT / "data" / "acceleration_every500.csv"
REFERENCE = ROOT / "LifeTrack White Stork SW Germany_2013-2019-reference-data.csv"

FIG.mkdir(parents=True, exist_ok=True)


BG = "#090b10"
PANEL = "#10151f"
GRID = "#263142"
TEXT = "#f3f6ff"
MUTED = "#a6adbb"
CYAN = "#56d6ff"
GOLD = "#ffcb57"
CORAL = "#ff6b5f"
GREEN = "#84f2b6"
PURPLE = "#ba8cff"


def set_style():
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
            "axes.titlesize": 16,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "grid.color": GRID,
            "grid.alpha": 0.55,
        }
    )


def save(fig, name):
    fig.savefig(FIG / name, dpi=220, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def short_name(value):
    name = str(value).split("/")[0].replace("+", "").strip()
    return name[:18]


def season(month):
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Fall"


def activity_index(raw):
    values = np.fromstring(str(raw), sep=" ", dtype=np.float32)
    if len(values) < 6:
        return np.nan
    values = values[: len(values) - (len(values) % 3)]
    arr = values.reshape(-1, 3)
    centered = arr - arr.mean(axis=0)
    return float(np.sqrt((centered * centered).sum(axis=1)).mean())


def load_data():
    df = pd.read_csv(SAMPLE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["month_name"] = df["timestamp"].dt.strftime("%b")
    df["period"] = df["timestamp"].dt.to_period("M").astype(str)
    df["hour"] = df["timestamp"].dt.hour
    df["hour_float"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
    df["season"] = df["month"].map(season)
    df["bird"] = df["individual-local-identifier"].map(short_name)
    df["activity"] = df["eobs:accelerations-raw"].map(activity_index)
    df = df.dropna(subset=["activity"])
    df["log_activity"] = np.log10(df["activity"] + 1)
    return df


def load_reference(sample):
    ref = pd.read_csv(REFERENCE)
    ref["deploy-on-date"] = pd.to_datetime(ref["deploy-on-date"], errors="coerce")
    ref["deploy-off-date"] = pd.to_datetime(ref["deploy-off-date"], errors="coerce")
    ref["tag-id"] = ref["tag-id"].astype(str)
    sample_last = sample.groupby("tag-local-identifier")["timestamp"].max()
    ref["last-sampled"] = ref["tag-id"].map(sample_last)
    ref["visual-end-date"] = ref["deploy-off-date"].fillna(ref["last-sampled"]).fillna(sample["timestamp"].max())
    ref["duration_days"] = (ref["visual-end-date"] - ref["deploy-on-date"]).dt.days
    ref["status"] = np.where(ref["deployment-end-type"].eq("dead"), "recorded dead", "no recorded death")
    ref["bird"] = ref["animal-id"].map(short_name)
    return ref.dropna(subset=["deploy-on-date", "visual-end-date", "duration_days"])


def fig_month_heatmap(df):
    counts = df.groupby(["year", "month"]).size().unstack(fill_value=0)
    counts = counts.reindex(index=range(int(df.year.min()), int(df.year.max()) + 1), columns=range(1, 13), fill_value=0)

    cmap = LinearSegmentedColormap.from_list("stork_heat", [PANEL, "#24324e", CYAN, GOLD])
    fig, ax = plt.subplots(figsize=(10, 4.8))
    im = ax.imshow(counts.values, aspect="auto", cmap=cmap)
    ax.set_title("When the tags spoke: acceleration records by month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(len(counts.index)), counts.index)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("sampled acceleration events")
    cbar.ax.yaxis.set_tick_params(color=MUTED)
    ax.text(0, -1.15, "A final interactive version will let readers scrub this calendar and jump to individual birds.",
            color=MUTED, fontsize=9, transform=ax.transData)
    save(fig, "01_monthly_signal_heatmap.png")


def fig_sensor_sky(df):
    plot_df = df.sort_values("timestamp")
    fig, ax = plt.subplots(figsize=(12, 5))
    sc = ax.scatter(
        plot_df["timestamp"],
        plot_df["hour_float"],
        c=plot_df["log_activity"],
        s=8,
        cmap=LinearSegmentedColormap.from_list("pulse", [CYAN, GOLD, CORAL]),
        alpha=0.72,
        linewidths=0,
    )
    ax.set_title("A sky of sensor pulses: time of day across the whole study")
    ax.set_ylabel("Hour of day")
    ax.set_xlabel("Observation date")
    ax.set_ylim(0, 24)
    ax.set_yticks([0, 6, 12, 18, 24], ["midnight", "6 AM", "noon", "6 PM", "midnight"])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="y")
    cbar = fig.colorbar(sc, ax=ax, fraction=0.025, pad=0.015)
    cbar.set_label("log activity")
    ax.text(0.01, 0.04, "Each dot is a sampled acceleration burst; bright points are high-motion moments.",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "02_sensor_sky_timeline.png")


def fig_activity_clock(df):
    by_hour = df.groupby("hour")["activity"].mean().reindex(range(24))
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    width = 2 * np.pi / 24 * 0.88

    colors = []
    for h in range(24):
        if 6 <= h < 18:
            colors.append(GOLD)
        elif 18 <= h < 21 or 4 <= h < 6:
            colors.append(CORAL)
        else:
            colors.append(CYAN)

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="polar", facecolor=PANEL)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    vals = by_hour.fillna(0).values
    vals = vals / vals.max()
    ax.bar(theta, vals, width=width, bottom=0.08, color=colors, alpha=0.85, edgecolor=BG, linewidth=0.8)
    ax.set_title("The daily pulse of a stork tag", pad=22)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False), ["0", "3", "6", "9", "12", "15", "18", "21"])
    ax.set_yticklabels([])
    ax.grid(color=GRID, alpha=0.45)
    ax.text(0.5, 0.49, "mean\nactivity", transform=ax.transAxes, ha="center", va="center", fontsize=13, color=TEXT)
    ax.text(0.5, 0.07, "hour of day", transform=ax.transAxes, ha="center", color=MUTED, fontsize=9)
    save(fig, "03_activity_clock.png")


def fig_season_distribution(df):
    order = ["Spring", "Summer", "Fall", "Winter"]
    data = [df.loc[df["season"].eq(s), "log_activity"].values for s in order]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    parts = ax.violinplot(data, positions=np.arange(len(order)), showmeans=False, showmedians=True, widths=0.78)
    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor([GREEN, GOLD, CORAL, CYAN][i])
        body.set_edgecolor("none")
        body.set_alpha(0.62)
    for key in ("cmedians", "cbars", "cmins", "cmaxes"):
        parts[key].set_color(TEXT)
        parts[key].set_linewidth(1.1)
    rng = np.random.default_rng(7)
    for i, values in enumerate(data):
        values = values[~np.isnan(values)]
        if len(values) > 600:
            values = rng.choice(values, 600, replace=False)
        ax.scatter(rng.normal(i, 0.055, len(values)), values, s=5, alpha=0.22, color=TEXT, linewidths=0)
    ax.set_title("Season changes the shape of motion")
    ax.set_ylabel("log10(activity index + 1)")
    ax.set_xticks(np.arange(len(order)), order)
    ax.grid(True, axis="y")
    ax.text(0.02, 0.93, "Violin width shows how often each activity level occurs.", transform=ax.transAxes, color=MUTED, fontsize=9)
    save(fig, "04_season_activity_distribution.png")


def fig_individual_heatmap(df):
    top = df["bird"].value_counts().head(14).index
    sub = df[df["bird"].isin(top)].copy()
    month_order = sorted(sub["period"].unique())
    pivot = sub.pivot_table(index="bird", columns="period", values="log_activity", aggfunc="median")
    pivot = pivot.loc[top, month_order]

    cmap = LinearSegmentedColormap.from_list("fingerprint", ["#171c27", CYAN, GOLD, CORAL])
    fig, ax = plt.subplots(figsize=(13, 5.8))
    masked = np.ma.masked_invalid(pivot.values)
    im = ax.imshow(masked, aspect="auto", cmap=cmap)
    ax.set_title("Individual birds have different motion fingerprints")
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    tick_positions = [i for i, p in enumerate(month_order) if p.endswith("-01")]
    ax.set_xticks(tick_positions, [month_order[i][:4] for i in tick_positions], rotation=0)
    ax.set_xlabel("Year")
    ax.set_ylabel("Bird")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cbar.set_label("median log activity")
    ax.text(0, -1.1, "Missing tiles are periods without sampled acceleration records for that bird.",
            color=MUTED, fontsize=9, transform=ax.transData)
    save(fig, "05_individual_motion_fingerprints.png")


def fig_deployment_lifelines(ref):
    sub = ref.sort_values("deploy-on-date").copy()
    sub = sub.tail(70)
    y = np.arange(len(sub))
    colors = np.where(sub["status"].eq("recorded dead"), CORAL, CYAN)

    fig, ax = plt.subplots(figsize=(11, 9))
    for yi, (_, row) in zip(y, sub.iterrows()):
        ax.plot([row["deploy-on-date"], row["visual-end-date"]], [yi, yi], color=colors[yi], lw=1.8, alpha=0.9)
        ax.scatter(row["visual-end-date"], yi, s=18, color=colors[yi], edgecolor=BG, linewidth=0.5)
    ax.set_title("Life after tagging: deployment lifelines in the reference table")
    ax.set_xlabel("Date")
    ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="x")
    ax.text(0.01, 0.96, "coral = deployment ended with recorded death; cyan = no recorded death in metadata",
            transform=ax.transAxes, color=MUTED, fontsize=9)
    ax.text(0.01, 0.90, f"{(ref['status'].eq('recorded dead')).sum()} of {len(ref)} reference deployments are marked dead.",
            transform=ax.transAxes, color=TEXT, fontsize=12, weight="bold")
    save(fig, "06_deployment_lifelines.png")


def main():
    set_style()
    df = load_data()
    ref = load_reference(df)
    fig_month_heatmap(df)
    fig_sensor_sky(df)
    fig_activity_clock(df)
    fig_season_distribution(df)
    fig_individual_heatmap(df)
    fig_deployment_lifelines(ref)

    summary = {
        "sample_rows": len(df),
        "sample_birds": int(df["bird"].nunique()),
        "sample_start": str(df["timestamp"].min()),
        "sample_end": str(df["timestamp"].max()),
        "reference_rows": len(pd.read_csv(REFERENCE)),
        "reference_deaths": int(ref["status"].eq("recorded dead").sum()),
    }
    pd.Series(summary).to_csv(OUT / "proposal_stats.csv", header=False)
    print(summary)
    print(f"Saved figures to {FIG}")


if __name__ == "__main__":
    main()
