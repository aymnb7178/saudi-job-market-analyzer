"""Matplotlib (Agg) charts. Labels are canonical English names so no Arabic font is needed."""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from saudi_jobs import analytics as an  # noqa: E402
from saudi_jobs.normalize import ROLES  # noqa: E402
from saudi_jobs.skills import Taxonomy  # noqa: E402

BLUE, GREY = "#2a6f97", "#9aa5b1"
NOTE = "Synthetic demo data - not real market statistics"


def _finish(fig, note: str | None):
    if note:
        fig.text(0.99, 0.01, note, ha="right", va="bottom", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig


def fig_top_skills(df: pd.DataFrame, tax: Taxonomy, n: int = 15, note: str | None = None):
    t = an.top_skills(df, tax, n=n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(t["skill"], t["share_pct"], color=BLUE)
    for y, v in enumerate(t["share_pct"]):
        ax.text(v + 0.5, y, f"{v:.0f}%", va="center", fontsize=8)
    ax.set_xlabel("% of postings mentioning the skill")
    ax.set_title(f"Top {n} skills across all postings (n={len(df):,})")
    ax.spines[["top", "right"]].set_visible(False)
    return _finish(fig, note)


def fig_role_heatmap(df: pd.DataFrame, tax: Taxonomy, n: int = 6, note: str | None = None):
    per = an.skills_by_role(df, tax, n=n)
    skills = list(dict.fromkeys(s for t in per.values() for s in t["skill"]))
    roles = list(per)
    mat = np.array([[ (df[df["role"] == r]["skills"].map(lambda sk, s=s: s in sk).mean() * 100) for s in skills]
                    for r in roles])
    fig, ax = plt.subplots(figsize=(10, 3.6))
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(skills)), skills, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(roles)), roles, fontsize=9)
    for i in range(len(roles)):
        for j in range(len(skills)):
            ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if mat[i, j] > 55 else "black")
    fig.colorbar(im, ax=ax, label="% of role's postings")
    ax.set_title("Skill demand by role (top skills per role)")
    return _finish(fig, note)


def fig_cooccurrence(df: pd.DataFrame, tax: Taxonomy, n: int = 12, note: str | None = None):
    skills = list(an.top_skills(df, tax, n=n, include_soft=False)["skill"])
    c = an.cooccurrence(df, skills)
    diag = np.diag(c.values).astype(float)
    jac = c.values / (diag[:, None] + diag[None, :] - c.values)  # Jaccard similarity
    np.fill_diagonal(jac, np.nan)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(jac, cmap="Blues")
    ax.set_xticks(range(len(skills)), skills, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(skills)), skills, fontsize=8)
    fig.colorbar(im, ax=ax, label="Jaccard overlap of postings")
    ax.set_title("Skill co-occurrence (top technical skills)")
    return _finish(fig, note)


def fig_trend(df: pd.DataFrame, tax: Taxonomy, n: int = 5, note: str | None = None):
    movers = an.trend_movers(df, n=n)
    skills = list(movers.head(n)["skill"])
    t = an.monthly_trend(df, skills)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for s in skills:
        ax.plot(t.index, t[s], marker="o", ms=3, label=s)
    ax.set_xticks(range(0, len(t), 2), t.index[::2], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("% of that month's postings")
    ax.set_title("Fastest-rising skills by monthly share")
    ax.legend(fontsize=8, ncol=2, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return _finish(fig, note)


def fig_city_sector(df: pd.DataFrame, note: str | None = None):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, col, title in ((axes[0], "city_norm", "Postings by city"), (axes[1], "sector_norm", "Postings by sector")):
        b = an.breakdown(df, col).head(10).iloc[::-1]
        ax.barh(b[col], b["postings"], color=BLUE)
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
    return _finish(fig, note)


def all_figures(df: pd.DataFrame, tax: Taxonomy) -> dict[str, "matplotlib.figure.Figure"]:
    note = NOTE if an.is_synthetic(df) else None
    return {
        "top_skills": fig_top_skills(df, tax, note=note),
        "role_heatmap": fig_role_heatmap(df, tax, note=note),
        "cooccurrence": fig_cooccurrence(df, tax, note=note),
        "trend": fig_trend(df, tax, note=note),
        "city_sector": fig_city_sector(df, note=note),
    }


def to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    return buf.getvalue()


def save_all(df: pd.DataFrame, tax: Taxonomy, out_dir: str | Path) -> dict[str, bytes]:
    """Write one PNG per chart into ``out_dir``; return the PNG bytes by name."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pngs = {}
    for name, fig in all_figures(df, tax).items():
        pngs[name] = to_png_bytes(fig)
        (out / f"{name}.png").write_bytes(pngs[name])
        plt.close(fig)
    return pngs
