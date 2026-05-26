from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch


ROOT = Path("/Users/keith/Desktop/LifeTrack")
OUT = ROOT / "final_project_proposal"
DATA = OUT / "data"
FIG = OUT / "figures_ecosystem"
SAMPLE = DATA / "acceleration_every500.csv"
REFERENCE = ROOT / "LifeTrack White Stork SW Germany_2013-2019-reference-data.csv"
INTERACTIVE_JSON = DATA / "sky_pulse_ecosystem.json"

FIG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

BG = "#03060a"
INK = "#f7fbff"
MUTED = "#9aa8b7"
DEEP = "#07111d"
FOG = "#1b2a36"
CYAN = "#55e6ff"
GOLD = "#ffd166"
CORAL = "#ff4f64"
GREEN = "#7cf6bf"
MOSS = "#536f5b"
SAND = "#d7c6a3"
PURPLE = "#bca0ff"

PULSE = LinearSegmentedColormap.from_list("pulse", [DEEP, "#12324b", CYAN, GOLD, CORAL])


def setup():
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "font.family": "DejaVu Sans",
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
        }
    )


def save(fig, name):
    fig.savefig(FIG / name, dpi=240, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


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
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def load():
    df = pd.read_csv(SAMPLE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["activity"] = df["eobs:accelerations-raw"].map(activity_index)
    df = df.dropna(subset=["activity"])
    df["log_activity"] = np.log10(df["activity"] + 1)
    df["bird"] = df["individual-local-identifier"].map(short_name)
    df["month"] = df["timestamp"].dt.month
    df["year"] = df["timestamp"].dt.year
    df["period"] = df["timestamp"].dt.to_period("M").astype(str)
    df["hour"] = df["timestamp"].dt.hour
    df["season"] = df["month"].map(season)

    ref = pd.read_csv(REFERENCE)
    ref["tag-id"] = ref["tag-id"].astype(str)
    ref["bird"] = ref["animal-id"].map(short_name)
    ref["deploy-on-date"] = pd.to_datetime(ref["deploy-on-date"], errors="coerce")
    ref["deploy-off-date"] = pd.to_datetime(ref["deploy-off-date"], errors="coerce")
    ref["status"] = np.where(ref["deployment-end-type"].eq("dead"), "recorded dead", "open record")
    meta = ref.drop_duplicates("bird").set_index("bird")
    df["status"] = df["bird"].map(meta["status"]).fillna("unknown")
    df["sex"] = df["bird"].map(meta["animal-sex"]).fillna("")
    return df, ref


def write_interactive_json(df, ref):
    top = df["bird"].value_counts().head(32).index.tolist()
    months = sorted(df["period"].unique())
    max_pulse = float(df["log_activity"].quantile(0.985))
    birds = []
    for i, bird in enumerate(top):
        sub = df[df["bird"].eq(bird)].copy()
        monthly = sub.groupby("period")["log_activity"].median()
        hourly = sub.groupby("hour")["log_activity"].mean().reindex(range(24)).fillna(0)
        phase = (i / max(1, len(top))) * np.pi * 2
        radius = 0.18 + 0.72 * (i / max(1, len(top) - 1))
        birds.append(
            {
                "name": bird,
                "records": int(len(sub)),
                "first": str(sub["timestamp"].min().date()),
                "last": str(sub["timestamp"].max().date()),
                "status": str(sub["status"].mode().iloc[0]) if len(sub) else "unknown",
                "sex": str(sub["sex"].mode().iloc[0]) if len(sub) else "",
                "phase": round(float(phase), 4),
                "radius": round(float(radius), 4),
                "monthly": [None if pd.isna(monthly.get(m, np.nan)) else round(float(monthly.get(m)), 3) for m in months],
                "hourly": [round(float(v), 3) for v in hourly.values],
            }
        )
    payload = {
        "months": months,
        "maxPulse": round(max_pulse, 3),
        "sampleRows": int(len(df)),
        "referenceRows": int(len(ref)),
        "birds": birds,
    }
    INTERACTIVE_JSON.write_text(json.dumps(payload, indent=2))
    return payload


def glow_scatter(ax, x, y, s, c, alpha=0.9, cmap=PULSE, vmin=None, vmax=None):
    ax.scatter(x, y, s=np.asarray(s) * 9, c=c, alpha=0.06, cmap=cmap, vmin=vmin, vmax=vmax, linewidths=0)
    ax.scatter(x, y, s=np.asarray(s) * 3.5, c=c, alpha=0.16, cmap=cmap, vmin=vmin, vmax=vmax, linewidths=0)
    ax.scatter(x, y, s=s, c=c, alpha=alpha, cmap=cmap, vmin=vmin, vmax=vmax, linewidths=0)


def title(ax, main, sub):
    ax.text(0.02, 0.96, main, transform=ax.transAxes, ha="left", va="top", fontsize=26, weight="bold")
    ax.text(0.02, 0.90, sub, transform=ax.transAxes, ha="left", va="top", fontsize=10.5, color=MUTED, linespacing=1.4)


def fig_01_sky(df):
    rng = np.random.default_rng(18)
    bird_stats = (
        df.groupby("bird")
        .agg(records=("bird", "size"), pulse=("log_activity", "median"), status=("status", lambda s: s.mode().iloc[0]))
        .sort_values("records", ascending=False)
        .head(44)
    )
    n = len(bird_stats)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    theta += rng.normal(0, 0.08, n)
    radius = np.sqrt(np.linspace(0.08, 1, n))
    x = radius * np.cos(theta) + rng.normal(0, 0.05, n)
    y = radius * np.sin(theta) + rng.normal(0, 0.05, n)
    pulse = bird_stats["pulse"].to_numpy()
    size = 50 + 520 * (bird_stats["records"].to_numpy() / bird_stats["records"].max()) ** 0.7

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.0, 1.0)
    ax.axis("off")
    # atmospheric fog
    for r, a in [(1.1, 0.08), (0.8, 0.08), (0.48, 0.1)]:
        t = np.linspace(0, 2 * np.pi, 300)
        ax.plot(r * np.cos(t), 0.72 * r * np.sin(t), color=CYAN, alpha=a, lw=1)
    glow_scatter(ax, x, y, size, pulse, vmax=df["log_activity"].quantile(0.985))
    dead = bird_stats["status"].eq("recorded dead").to_numpy()
    ax.scatter(x[dead], y[dead], s=size[dead] * 0.28, facecolors="none", edgecolors=CORAL, linewidths=1.3, alpha=0.9)
    for idx in np.argsort(size)[-7:]:
        ax.text(x[idx] + 0.025, y[idx] + 0.02, bird_stats.index[idx], fontsize=8.5, color=INK, alpha=0.9)
    title(
        ax,
        "The Sky Has a Pulse",
        "Opening frame: each glowing organism is one tagged white stork. Size encodes sensor presence; color encodes median motion.",
    )
    ax.text(0.02, 0.08, "Interaction: hover a pulse to hear/see its rhythm; click to enter that bird's story.", transform=ax.transAxes, color=MUTED, fontsize=10)
    save(fig, "01_living_sky.png")


def fig_02_currents(df):
    top = df["bird"].value_counts().head(18).index
    months = sorted(df["period"].unique())
    month_x = {m: i for i, m in enumerate(months)}
    fig, ax = plt.subplots(figsize=(14, 7.4))
    ax.axis("off")
    ax.set_xlim(-2, len(months) + 1)
    ax.set_ylim(-2, len(top) + 2)
    title(ax, "Migration Currents", "Bird histories are drawn as drifting ribbons; brighter knots are months with stronger body motion.")
    season_color = {"winter": CYAN, "spring": GREEN, "summer": GOLD, "fall": CORAL}
    for j, bird in enumerate(top[::-1]):
        sub = df[df["bird"].eq(bird)]
        med = sub.groupby("period")["log_activity"].median()
        available = med.dropna()
        if len(available) < 3:
            continue
        xs = np.array([month_x[m] for m in available.index])
        ys = np.full_like(xs, j, dtype=float) + 0.42 * np.sin(xs * 0.38 + j)
        verts = [(xs[0], ys[0])]
        codes = [MplPath.MOVETO]
        for k in range(1, len(xs)):
            cx = (xs[k - 1] + xs[k]) / 2
            verts += [(cx, ys[k - 1]), (cx, ys[k]), (xs[k], ys[k])]
            codes += [MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
        patch = PathPatch(MplPath(verts, codes), facecolor="none", edgecolor=CYAN, lw=1.2, alpha=0.28)
        ax.add_patch(patch)
        colors = [season_color[season(pd.Period(m).month)] for m in available.index]
        sizes = 22 + 85 * (available.values / df["log_activity"].quantile(0.985))
        ax.scatter(xs, ys, s=sizes, color=colors, alpha=0.8, linewidths=0)
        ax.text(-1.35, j, bird, fontsize=7.8, color=MUTED, va="center")
    for year in sorted(df["year"].unique()):
        x = month_x.get(f"{year}-01")
        if x is not None:
            ax.text(x, -1.25, str(year), fontsize=9, color=MUTED)
    save(fig, "02_migration_currents.png")


def fig_03_orbit(df):
    bird = df["bird"].value_counts().index[0]
    sub = df[df["bird"].eq(bird)]
    monthly = sub.groupby("period")["log_activity"].median()
    months = sorted(df["period"].unique())
    vals = np.array([monthly.get(m, np.nan) for m in months])
    maxv = np.nanquantile(df["log_activity"], 0.985)
    theta = np.linspace(0, 2 * np.pi, len(months), endpoint=False)
    r = 0.35 + 0.55 * np.nan_to_num(vals / maxv, nan=0)

    fig, ax = plt.subplots(figsize=(8.4, 8.4), subplot_kw={"projection": "polar"})
    ax.set_facecolor(BG)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.grid(color="#26344a", alpha=0.35)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    for i in range(len(months)):
        color = PULSE(0 if np.isnan(vals[i]) else min(vals[i] / maxv, 1))
        ax.plot([theta[i], theta[i]], [0.27, r[i]], color=color, lw=2.4, alpha=0.86)
        ax.scatter([theta[i]], [r[i]], s=38 if not np.isnan(vals[i]) else 8, color=color, alpha=0.9)
    ax.text(0.5, 0.51, bird, transform=ax.transAxes, ha="center", va="center", fontsize=24, weight="bold")
    ax.text(0.5, 0.45, f"{len(sub):,} sampled bursts\\n{str(sub.timestamp.min().date())} → {str(sub.timestamp.max().date())}", transform=ax.transAxes, ha="center", va="center", fontsize=10, color=MUTED)
    ax.set_title("Individual Pulse Orbit", pad=24, fontsize=24, weight="bold")
    save(fig, "03_individual_pulse_orbit.png")


def fig_04_constellation(df):
    rows = []
    for bird, sub in df.groupby("bird"):
        if len(sub) < 35:
            continue
        day = sub[sub["hour"].between(7, 18)]["log_activity"].median()
        night = sub[~sub["hour"].between(7, 18)]["log_activity"].median()
        summer = sub[sub["season"].eq("summer")]["log_activity"].median()
        winter = sub[sub["season"].eq("winter")]["log_activity"].median()
        rows.append(
            {
                "bird": bird,
                "day_night": day - night,
                "summer_winter": summer - winter,
                "records": len(sub),
                "pulse": sub["log_activity"].median(),
                "status": sub["status"].mode().iloc[0],
            }
        )
    pts = pd.DataFrame(rows).dropna()
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(pts["day_night"].min() - 0.25, pts["day_night"].max() + 0.25)
    ax.set_ylim(pts["summer_winter"].min() - 0.25, pts["summer_winter"].max() + 0.25)
    title(ax, "Behavior Constellation", "Birds drift into clusters based on daily rhythm and seasonal rhythm, rather than being sorted into a table.")
    ax.axhline(0, color=FOG, lw=1, alpha=0.6)
    ax.axvline(0, color=FOG, lw=1, alpha=0.6)
    sizes = 40 + 480 * (pts["records"] / pts["records"].max()) ** 0.7
    colors = np.where(pts["status"].eq("recorded dead"), CORAL, CYAN)
    ax.scatter(pts["day_night"], pts["summer_winter"], s=sizes * 4, color=colors, alpha=0.06, linewidths=0)
    ax.scatter(pts["day_night"], pts["summer_winter"], s=sizes, color=colors, alpha=0.75, edgecolors=INK, linewidths=0.4)
    for _, row in pts.nlargest(9, "records").iterrows():
        ax.text(row["day_night"] + 0.015, row["summer_winter"] + 0.015, row["bird"], fontsize=8.5, color=INK)
    ax.text(0.06, 0.08, "left/right = night-to-day shift    up/down = winter-to-summer shift", transform=ax.transAxes, color=MUTED, fontsize=10)
    save(fig, "04_behavior_constellation.png")


def fig_05_vanishing(ref, df):
    ref = ref.copy()
    last_sample = df.groupby("bird")["timestamp"].max()
    ref["end"] = ref["deploy-off-date"].fillna(ref["bird"].map(last_sample)).fillna(df["timestamp"].max())
    ref["duration"] = (ref["end"] - ref["deploy-on-date"]).dt.days
    ref = ref.dropna(subset=["deploy-on-date", "duration"]).sort_values("duration").tail(58)
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.axis("off")
    title(ax, "Vanishing Trails", "Reference metadata becomes memory threads: cyan trails remain open; red endpoints mark recorded deaths.")
    start = ref["deploy-on-date"].min()
    end = ref["end"].max()
    total = (end - start).days
    rng = np.random.default_rng(44)
    for i, (_, r) in enumerate(ref.iterrows()):
        x0 = (r["deploy-on-date"] - start).days / total
        x1 = (r["end"] - start).days / total
        y = 0.12 + 0.75 * i / max(1, len(ref) - 1)
        wiggle = 0.012 * np.sin(np.linspace(0, np.pi * 2, 90) * rng.uniform(0.7, 1.5) + rng.uniform(0, 5))
        xs = np.linspace(x0, x1, 90)
        ys = y + wiggle
        color = CORAL if r["status"] == "recorded dead" else CYAN
        ax.plot(xs, ys, color=color, alpha=0.42, lw=1.8)
        ax.scatter([x1], [ys[-1]], s=42, color=color, alpha=0.85, linewidths=0)
    for yr in range(start.year, end.year + 1):
        x = (pd.Timestamp(f"{yr}-01-01") - start).days / total
        ax.text(x, 0.04, str(yr), color=MUTED, fontsize=9, ha="center")
    ax.text(0.03, 0.91, f"{(ref.status.eq('recorded dead')).sum()} recorded deaths in the reference table", transform=ax.transAxes, color=CORAL, fontsize=13, weight="bold")
    save(fig, "05_vanishing_trails.png")


def fig_06_storyboard(df):
    fig, ax = plt.subplots(figsize=(13, 7.2))
    ax.axis("off")
    title(ax, "Interaction Storyboard", "The final page is an explorable article: scroll to reveal scale, hover to reveal identity, click to enter a life.")
    scenes = [
        ("1", "Wake the sky", "Pulses emerge from darkness as the dataset loads."),
        ("2", "Scrub seasons", "A vertical time beam moves through years of sensor memory."),
        ("3", "Touch a pulse", "Hover pulls hidden trails toward the cursor."),
        ("4", "Enter one bird", "The ecosystem folds into an individual pulse orbit."),
        ("5", "Feel disappearance", "Recorded deaths become red fractures in the rhythm."),
        ("6", "Return to flock", "The ending reconnects individuals into one fragile archive."),
    ]
    xs = np.linspace(0.11, 0.89, 3)
    ys = [0.61, 0.27]
    for idx, (num, head, body) in enumerate(scenes):
        x = xs[idx % 3]
        y = ys[idx // 3]
        ax.scatter([x], [y], s=1800, color=[CYAN, GOLD, GREEN, PURPLE, CORAL, SAND][idx], alpha=0.12, linewidths=0)
        ax.scatter([x], [y], s=260, color=[CYAN, GOLD, GREEN, PURPLE, CORAL, SAND][idx], alpha=0.75, linewidths=0)
        ax.text(x, y + 0.015, num, ha="center", va="center", fontsize=18, weight="bold")
        ax.text(x, y - 0.13, head, ha="center", va="center", fontsize=13, weight="bold")
        ax.text(x, y - 0.205, body, ha="center", va="center", fontsize=9, color=MUTED, wrap=True)
        if idx % 3 != 2:
            ax.plot([x + 0.08, xs[idx % 3 + 1] - 0.08], [y, y], color=FOG, lw=1.2, alpha=0.8)
    save(fig, "06_storyboard.png")


def main():
    setup()
    df, ref = load()
    payload = write_interactive_json(df, ref)
    fig_01_sky(df)
    fig_02_currents(df)
    fig_03_orbit(df)
    fig_04_constellation(df)
    fig_05_vanishing(ref, df)
    fig_06_storyboard(df)
    print(f"Wrote {INTERACTIVE_JSON}")
    print(f"Wrote {len(list(FIG.glob('*.png')))} ecosystem figures to {FIG}")
    print(json.dumps({"birds": len(payload["birds"]), "months": len(payload["months"]), "sampleRows": payload["sampleRows"]}, indent=2))


if __name__ == "__main__":
    main()
