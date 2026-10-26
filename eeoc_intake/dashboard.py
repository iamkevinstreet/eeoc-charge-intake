"""Evaluation dashboard (Plotly Dash): compare runs, see which fields fail on which documents.

    python -m eeoc_intake.dashboard            # http://127.0.0.1:8050

Reads every results file under eeoc_intake/evals/results/{live,smoke}/. The same tidy frames feed the CSV
export for Tableau (`python -m eeoc_intake.evals.export`), so the three views agree with each other.

The look follows the design system of kevindstreet.com (Geist, a near-black or paper ground, one yellow
highlight, green for right), in light and dark, so the app and the case study read as one product.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from eeoc_intake.evals.stats import clear_change, fixed, pct_label
from eeoc_intake.fake import SCORED_FIELDS

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(os.environ.get("EEOC_RESULTS_DIR", REPO_ROOT / "eeoc_intake" / "evals" / "results"))

FIELD_LABELS = {
    "charge_number": "Charge number",
    "charging_party": "Charging party",
    "respondent": "Respondent",
    "eeoc_office": "EEOC office",
    "bases": "Bases",
    "issues": "Issues",
    "earliest_date": "Earliest date",
    "latest_date": "Latest date",
    "continuing_action": "Continuing action",
    "notice_date": "Notice date",
}
KIND_LABELS = {
    "clean": "Clean",
    "missing_number": "Missing charge number",
    "rotated": "Rotated page",
    "long": "Long particulars",
    "two_respondents": "Two respondents",
}
# Column heads for the heatmap: short lines, so each fits under its cell even when the panels are narrow.
KIND_TICKS = {
    "Clean": "Standard",
    "Missing charge number": "No charge<br>number",
    "Rotated page": "Rotated<br>page",
    "Long particulars": "Long<br>particulars",
    "Two respondents": "Two<br>respondents",
}

# ---------- design tokens ----------
# The values of kevindstreet.com. Runs are an ordered ramp: the run you are looking at in full ink, earlier runs
# in lighter steps of the same gray (validated: monotone, visible steps, the light end clears the surface).
# Accuracy is one sequential hue, from the surface to the green the site uses for "right".
THEMES: dict[str, dict] = {
    "light": {
        "ground": "#f5f5f2",
        "surface": "#ffffff",
        "surface2": "#ecece8",
        "ink": "#111214",
        "ink2": "#585d66",
        "ink3": "#868c96",
        "grid": "rgba(17,18,20,0.08)",
        "rule": "rgba(17,18,20,0.20)",
        "mark": "#ffe45c",
        "mark_wash": "rgba(255,228,92,0.42)",
        "pass": "#13794a",
        "miss": "#b5641a",
        "runs": ["#111214", "#80868f", "#a7acb4"],
    },
    "dark": {
        "ground": "#0a0b0e",
        "surface": "#121419",
        "surface2": "#1a1d24",
        "ink": "#f2f3f5",
        "ink2": "#9aa1ac",
        "ink3": "#6e7581",
        "grid": "rgba(255,255,255,0.07)",
        "rule": "rgba(255,255,255,0.22)",
        "mark": "#f3cf4a",
        "mark_wash": "rgba(243,207,74,0.14)",
        "pass": "#5dd39e",
        "miss": "#f0b14c",
        "runs": ["#f2f3f5", "#7d8490", "#4a505b"],
    },
}
FONT = "Geist, 'Geist Variable', ui-sans-serif, system-ui, 'Helvetica Neue', Arial, sans-serif"


# ---------- data ----------
def load_runs(results_dir: Path = RESULTS_DIR) -> list[dict]:
    runs = []
    for folder in ("live", "smoke"):
        for path in sorted((results_dir / folder).glob("*.json")):
            run = json.loads(path.read_text(encoding="utf-8"))
            if "results" not in run:  # index.json, figures.json and anything else that is not a run
                continue
            run["run_id"] = path.stem
            run["kind"] = folder
            runs.append(run)
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    return runs


def frames(runs: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Three tidy tables: one row per run, per case, and per (case, field)."""
    run_rows, case_rows, field_rows = [], [], []
    for r in runs:
        stamp = r["started_at"][:16].replace("T", " ")
        label = f"{r['model']} {stamp}" + (" smoke" if r["kind"] == "smoke" else "")
        s = r["summary"]
        run_rows.append(
            {
                "run_id": r["run_id"],
                "run": label,
                "model": r["model"],
                "provider": r["provider"],
                "started_at": r["started_at"],
                "kind": r["kind"],
                "cases": r["cases"],
                "failures": r["failures"],
                "field_accuracy": s.get("field_accuracy"),
                "unsupported_rate": s.get("unsupported_rate"),
                "false_abstentions": s.get("false_abstentions"),
                "guesses": s.get("guesses"),
                "latency_p50_ms": s.get("latency_p50_ms"),
                "latency_p95_ms": s.get("latency_p95_ms"),
                "cost_per_case_usd": s.get("cost_per_case_usd"),
                "cost_total_usd": s.get("cost_total_usd"),
            }
        )
        for c in r["results"]:
            sc = c["scores"]
            kind = c["tags"][0] if c["tags"] else "clean"
            case_rows.append(
                {
                    "run_id": r["run_id"],
                    "run": label,
                    "model": r["model"],
                    "case_id": c["case_id"],
                    "case_kind": KIND_LABELS.get(kind, kind),
                    "ok": c["ok"],
                    "latency_ms": c["latency_ms"],
                    "cost_usd": c["cost_usd"],
                    "field_accuracy": sc.get("field_accuracy"),
                    "unsupported_removed": sc.get("unsupported_removed"),
                    "false_abstentions": sc.get("false_abstentions"),
                    "guesses": sc.get("guesses"),
                    "error": c.get("error"),
                }
            )
            for f in SCORED_FIELDS:
                if f"f_{f}" in sc:
                    field_rows.append(
                        {
                            "run_id": r["run_id"],
                            "run": label,
                            "model": r["model"],
                            "case_id": c["case_id"],
                            "case_kind": KIND_LABELS.get(kind, kind),
                            "field": FIELD_LABELS.get(f, f),
                            "correct": int(sc[f"f_{f}"]),
                            "value": json.dumps((sc.get("values") or {}).get(f)),
                            "expected": json.dumps((sc.get("gold") or {}).get(f)),
                            "removed_by_verification": f in (sc.get("removed") or []),
                        }
                    )
    return pd.DataFrame(run_rows), pd.DataFrame(case_rows), pd.DataFrame(field_rows)


def run_labels(runs_df: pd.DataFrame, run_ids: list[str]) -> dict[str, str]:
    """Short names for the selected runs: the start time, plus the model when the selection mixes models."""
    sub = runs_df.set_index("run_id").loc[[r for r in run_ids if r in set(runs_df.run_id)]]
    mixed = sub.model.nunique() > 1
    out = {}
    for rid, row in sub.iterrows():
        when = datetime.fromisoformat(str(row.started_at).replace("Z", "+00:00"))
        label = f"{when.strftime('%b')} {when.day}, {when.strftime('%H:%M')} UTC"
        if mixed:
            label = f"{row.model}, {label}"
        if row.kind == "smoke":
            label += " (smoke)"
        out[rid] = label
    return out


def _ids(run_ids: str | list[str]) -> list[str]:
    return [run_ids] if isinstance(run_ids, str) else list(run_ids)


def _readable(raw: str | None) -> str:
    """A value from the results file as a person would write it: lists joined, nothing shown as empty."""
    v = json.loads(raw) if raw else None
    if v is None or v == []:
        return "empty"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def _pct(v: float) -> str:
    return pct_label(v)


# ---------- figures ----------
def _base(fig, height: int, theme: str, legend: bool = False):
    t = THEMES[theme]
    fig.update_layout(
        template="none",
        height=height,
        margin={"l": 8, "r": 12, "t": 34 if legend else 8, "b": 8},
        font={"family": FONT, "size": 12, "color": t["ink2"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": 1.0,
            "yanchor": "bottom",
            "font": {"color": t["ink2"], "size": 12},
            "bgcolor": "rgba(0,0,0,0)",
            "itemclick": "toggleothers",
        },
        hoverlabel={
            "bgcolor": t["surface2"],
            "bordercolor": t["rule"],
            "font": {"family": FONT, "color": t["ink"], "size": 12},
        },
        hovermode="closest",
    )
    fig.update_xaxes(
        automargin=True,
        showgrid=True,
        gridcolor=t["grid"],
        gridwidth=1,
        zeroline=False,
        showline=False,
        ticks="",
        tickfont={"color": t["ink3"], "size": 11},
    )
    fig.update_yaxes(
        automargin=True,
        showgrid=False,
        zeroline=False,
        showline=False,
        ticks="",
        ticklabelstandoff=10,
        tickfont={"color": t["ink2"], "size": 12},
    )
    return fig


def fig_accuracy_by_field(fields: pd.DataFrame, run_ids: list[str], theme: str = "light", labels=None):
    """A dot per run on each field, joined where the runs disagree; rows that changed get the highlight."""
    import plotly.graph_objects as go

    t = THEMES[theme]
    run_ids = [r for r in _ids(run_ids) if r in set(fields.run_id)][:3]
    labels = labels or {r: fields[fields.run_id == r].run.iloc[0] for r in run_ids}
    acc = fields[fields.run_id.isin(run_ids)].groupby(["run_id", "field"])["correct"].mean()
    order = [FIELD_LABELS[f] for f in SCORED_FIELDS if (FIELD_LABELS[f] in set(fields.field))]
    fig = go.Figure()

    changed = []
    for i, f in enumerate(order):
        vals = [acc[(r, f)] for r in run_ids if (r, f) in acc]
        if len(vals) > 1 and max(vals) - min(vals) > 0.001:
            changed.append(f)
            fig.add_shape(
                type="rect",
                xref="paper",
                x0=0,
                x1=1,
                yref="y",
                y0=i - 0.42,
                y1=i + 0.42,
                fillcolor=t["mark_wash"],
                line={"width": 0},
                layer="below",
                name="highlight",
            )
            fig.add_scatter(
                x=[min(vals), max(vals)],
                y=[f, f],
                mode="lines",
                line={"color": t["rule"], "width": 2},
                hoverinfo="skip",
                showlegend=False,
                meta={"role": "connector"},
            )

    # Earlier runs first, so the run in focus is drawn on top.
    for i in reversed(range(len(run_ids))):
        rid = run_ids[i]
        xs = [acc.get((rid, f)) for f in order]
        fig.add_scatter(
            x=xs,
            y=order,
            mode="markers+text",
            name=labels[rid],
            marker={"size": 12, "color": t["runs"][i], "line": {"color": t["surface"], "width": 2}},
            text=[
                _pct(v) if (f in changed and v is not None) else "" for v, f in zip(xs, order, strict=True)
            ],
            textposition="middle right" if i == 0 else "middle left",
            textfont={"color": t["ink2"], "size": 12},
            cliponaxis=False,
            # The share is written out here, so the hover never rounds a value just under 100% up to it.
            customdata=[_pct(v) if v is not None else "" for v in xs],
            hovertemplate="<b>%{customdata}</b>  %{y}<extra>" + labels[rid] + "</extra>",
            meta={"role": f"run-{i}"},
        )
    # The category order is set here, not left to the order traces happen to name the fields.
    fig.update_layout(
        xaxis={"range": [-0.02, 1.13], "tickvals": [0, 0.25, 0.5, 0.75, 1], "tickformat": ".0%"},
        yaxis={
            "categoryorder": "array",
            "categoryarray": order,
            "autorange": "reversed",
            "showgrid": True,
            "gridcolor": t["grid"],
        },
    )
    # The runs' key sits above all the charts, so the chart carries none of its own.
    return _base(fig, 48 + 30 * len(order), theme)


def fig_heatmap(fields: pd.DataFrame, run_ids: str | list[str], theme: str = "light", labels=None):
    """Fields right for each field and kind of document, one panel per run on the same scale."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    t = THEMES[theme]
    run_ids = [r for r in _ids(run_ids) if r in set(fields.run_id)][:3]
    if not run_ids:
        return _base(go.Figure(), 300, theme)
    labels = labels or {r: fields[fields.run_id == r].run.iloc[0] for r in run_ids}
    order = [FIELD_LABELS[f] for f in SCORED_FIELDS if (FIELD_LABELS[f] in set(fields.field))]
    fig = make_subplots(
        rows=1,
        cols=len(run_ids),
        shared_yaxes=True,
        horizontal_spacing=0.035,
        subplot_titles=[labels[r] for r in run_ids] if len(run_ids) > 1 else None,
    )
    for i, rid in enumerate(run_ids, start=1):
        sub = fields[fields.run_id == rid]
        pivot = sub.pivot_table(index="field", columns="case_kind", values="correct", aggfunc="mean")
        counts = sub.groupby("case_kind")["case_id"].nunique()
        pivot = pivot.reindex(order)
        cols = [c for c in KIND_LABELS.values() if c in pivot.columns]
        pivot = pivot[cols]
        fig.add_trace(
            go.Heatmap(
                z=pivot.values,
                x=[f"{KIND_TICKS.get(c, c)}<br>({counts[c]})" for c in cols],
                y=list(pivot.index),
                zmin=0,
                zmax=1,
                colorscale=[[0, t["surface2"]], [1, t["pass"]]],
                xgap=3,
                ygap=3,
                # Only the cells that are not all right carry a number; the colour says the rest.
                text=[["" if pd.isna(v) or v >= 1 else _pct(v) for v in row] for row in pivot.values],
                texttemplate="%{text}",
                textfont={"size": 12},
                showscale=i == len(run_ids),
                colorbar={
                    "tickformat": ".0%",
                    "tickvals": [0, 0.5, 1],
                    "thickness": 8,
                    "len": 0.9,
                    "outlinewidth": 0,
                    "tickfont": {"color": t["ink3"], "size": 11},
                },
                customdata=[
                    [
                        "no documents"
                        if pd.isna(v)
                        else f"<b>{_pct(v)}</b>  {f}, {KIND_TICKS.get(c, c).replace('<br>', ' ')} ({counts[c]} documents)"
                        for v, c in zip(row, cols, strict=True)
                    ]
                    for f, row in zip(pivot.index, pivot.values, strict=True)
                ],
                hovertemplate="%{customdata}<extra>" + labels[rid] + "</extra>",
                meta={"role": "accuracy"},
            ),
            row=1,
            col=i,
        )
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=order)
    fig.update_xaxes(showgrid=False, tickangle=0, tickfont={"size": 11})
    for i, a in enumerate(fig.layout.annotations, start=1):  # the panel titles, over each panel's left edge
        domain = fig.layout[f"xaxis{'' if i == 1 else i}"].domain
        a.update(font={"color": t["ink2"], "size": 12}, xanchor="left", x=domain[0])
    fig = _base(fig, 96 + 32 * len(order) + (24 if len(run_ids) > 1 else 0), theme)
    fig.update_layout(margin={"t": 30 if len(run_ids) > 1 else 8, "b": 40})
    fig.update_xaxes(showgrid=False)
    return fig


def fig_latency(cases: pd.DataFrame, run_ids: list[str], theme: str = "light", labels=None):
    """Every document's time as a dot, with the box of the middle half; each row names its typical time."""
    import plotly.graph_objects as go

    t = THEMES[theme]
    run_ids = [r for r in _ids(run_ids) if r in set(cases.run_id)][:3]
    labels = labels or {r: cases[cases.run_id == r].run.iloc[0] for r in run_ids}
    fig = go.Figure()
    rows = []
    # The axis fits where documents fall. Times have a long right tail, so it stops at the far-out fence
    # (upper quartile plus three times the spread of the middle half) of the most spread-out run; documents
    # past it are counted at the right edge with the slowest time, not stretched across the chart.
    secs_by_run = {rid: cases[cases.run_id == rid]["latency_ms"] / 1000 for rid in run_ids}
    shown = [s for s in secs_by_run.values() if len(s)]
    fastest = min(float(s.min()) for s in shown) if shown else 0.0
    slowest = max(float(s.max()) for s in shown) if shown else 1.0
    fence = (
        max(float(s.quantile(0.75) + 3 * (s.quantile(0.75) - s.quantile(0.25))) for s in shown)
        if shown
        else 1.0
    )
    top = min(slowest, fence)
    pad = max(0.15, (top - fastest) * 0.06)
    x_range = [max(0.0, fastest - pad), top + pad if slowest <= fence else fence]
    for i, rid in enumerate(run_ids):
        c = cases[cases.run_id == rid]
        secs = secs_by_run[rid]
        row = f"{labels[rid]}<br><b>{fixed(secs.median(), 1)} s</b> typical"
        rows.append(row)
        past = secs[secs > x_range[1]]
        if len(past):
            # In the margin beside the row, so the count never sits on the dots or on the axis labels.
            fig.add_annotation(
                x=1,
                xref="paper",
                xanchor="left",
                xshift=10,
                y=row,
                yref="y",
                showarrow=False,
                align="left",
                text=f"{len(past)} slower,<br>up to {fixed(past.max(), 1)} s",
                font={"color": t["ink2"], "size": 11},
                name="beyond",
            )
        # The box and its quartiles come from every document; dots past the axis are drawn clear rather than
        # cut in half at its edge, since the note beside the row counts them.
        inside = [i for i, v in enumerate(secs) if v <= x_range[1]]
        fig.add_box(
            x=secs,
            y=[row] * len(c),
            name=labels[rid],
            orientation="h",
            selectedpoints=inside if len(past) else None,
            unselected={"marker": {"opacity": 0}},
            boxpoints="all",
            jitter=0.6,
            pointpos=0,
            width=0.36,
            whiskerwidth=0.6,
            marker={
                "color": t["runs"][i],
                "size": 7,
                "opacity": 0.8,
                "line": {"color": t["surface"], "width": 1},
            },
            line={"color": t["runs"][i], "width": 1.5},
            fillcolor="rgba(0,0,0,0)",
            hovertemplate="<b>%{x:.1f} s</b>  %{text}<extra>" + labels[rid] + "</extra>",
            text=c["case_id"],
            meta={"role": f"run-{i}"},
        )
    fig.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": rows, "autorange": "reversed"},
        xaxis={"range": x_range, "ticksuffix": " s"},
    )
    fig = _base(fig, 64 + 62 * max(1, len(run_ids)), theme)
    if fig.layout.annotations:
        fig.update_layout(margin={"r": 88})
    return fig


def fig_cost(runs_df: pd.DataFrame, run_ids: list[str], theme: str = "light", labels=None):
    """Cost per document at list prices, one bar per run with its value at the end."""
    import plotly.graph_objects as go

    t = THEMES[theme]
    run_ids = [r for r in _ids(run_ids) if r in set(runs_df.run_id)][:3]
    labels = labels or {r: runs_df[runs_df.run_id == r].run.iloc[0] for r in run_ids}
    fig = go.Figure()
    top = 0.0
    for i, rid in enumerate(run_ids):
        v = float(runs_df.loc[runs_df.run_id == rid, "cost_per_case_usd"].fillna(0).iloc[0])
        top = max(top, v)
        fig.add_bar(
            x=[v],
            y=[labels[rid]],
            name=labels[rid],
            orientation="h",
            width=0.34,
            marker={"color": t["runs"][i], "line": {"width": 0}, "cornerradius": 4},
            text=[f"${fixed(v, 4)}"],
            textposition="outside",
            textfont={"color": t["ink2"], "size": 12},
            cliponaxis=False,
            hovertemplate="<b>$%{x:.4f}</b> per document<extra>" + labels[rid] + "</extra>",
            meta={"role": f"run-{i}"},
        )
    fig.update_layout(
        barmode="overlay",
        yaxis={
            "categoryorder": "array",
            "categoryarray": [labels[r] for r in run_ids],
            "autorange": "reversed",
        },
        xaxis={"tickprefix": "$", "tickformat": ".3f", "range": [0, max(0.01, top * 1.32)]},
    )
    return _base(fig, 64 + 52 * max(1, len(run_ids)), theme)


# ---------- tiles ----------
# Plain-language measures, in the words the case study uses: the column, its label, how to write the value,
# how to write a change, and which way is better.
TILES = [
    (
        "field_accuracy",
        "Fields right",
        lambda v: "100%" if v >= 1 else pct_label(v, 1),
        lambda d: f"{fixed(abs(d) * 100, 1)} pts",
        "up",
    ),
    (
        "unsupported_rate",
        "Quotes that did not match the page",
        pct_label,
        lambda d: f"{fixed(abs(d) * 100, 1)} pts",
        "down",
    ),
    ("guesses", "Made-up values per document", lambda v: fixed(v, 2), lambda d: fixed(abs(d), 2), "down"),
    (
        "false_abstentions",
        "Fields wrongly left blank, per document",
        lambda v: fixed(v, 2),
        lambda d: fixed(abs(d), 2),
        "down",
    ),
    (
        "latency_p50_ms",
        "Seconds per document, typical",
        lambda v: f"{fixed(v / 1000, 1)} s",
        lambda d: f"{fixed(abs(d) / 1000, 1)} s",
        "down",
    ),
    (
        "cost_per_case_usd",
        "Cost per document",
        lambda v: f"${fixed(v, 4)}",
        lambda d: f"${fixed(abs(d), 4)}",
        "down",
    ),
]


# Each tile's per-document values, and the test that says whether two runs really differ (see evals/stats.py).
TILE_TESTS = {
    "field_accuracy": ("field_accuracy", "welch"),
    "unsupported_rate": ("unsupported_removed", "welch"),
    "guesses": ("guesses", "welch"),
    "false_abstentions": ("false_abstentions", "welch"),
    "latency_p50_ms": ("latency_ms", "rank"),
    "cost_per_case_usd": ("cost_usd", "welch"),
}


def tile_rows(runs_df: pd.DataFrame, run_ids: list[str], cases_df: pd.DataFrame | None = None) -> list[dict]:
    """Each measure for the run in focus, and how it moved against the next selected run.

    A change that rounds to nothing at the precision shown is no change. With the per-document rows, a change
    gets a direction and a colour only when it is bigger than run-to-run noise at 95% confidence; a smaller one
    is no clear change.
    """
    if not run_ids:
        return []
    by_id = runs_df.set_index("run_id")
    now = by_id.loc[run_ids[0]]
    then = by_id.loc[run_ids[1]] if len(run_ids) > 1 else None
    rows = []
    for column, label, fmt, change, better in TILES:
        v = float(now[column] or 0)
        row = {"measure": column, "label": label, "value": fmt(v), "delta": None, "good": None}
        if then is not None:
            d = v - float(then[column] or 0)
            shown = change(d)
            if abs(d) < 1e-12 or not any(ch in "123456789" for ch in shown):
                row["delta"] = "no change"
            elif cases_df is not None and column in TILE_TESTS:
                per_doc, test = TILE_TESTS[column]
                a = cases_df.loc[cases_df.run_id == run_ids[1], per_doc].dropna().astype(float).tolist()
                b = cases_df.loc[cases_df.run_id == run_ids[0], per_doc].dropna().astype(float).tolist()
                if clear_change(a, b, test):
                    row["delta"] = ("up " if d > 0 else "down ") + shown
                    row["good"] = (d > 0) == (better == "up")
                else:
                    row["delta"] = "no clear change"
            else:
                row["delta"] = ("up " if d > 0 else "down ") + shown
                row["good"] = (d > 0) == (better == "up")
        rows.append(row)
    return rows


# ---------- app ----------
def build_app(results_dir: Path = RESULTS_DIR):
    from dash import Dash, Input, Output, dash_table, dcc, html
    from dash.dash_table.Format import Format, Scheme, Symbol

    runs = load_runs(results_dir)
    runs_df, cases_df, fields_df = frames(runs)
    names = run_labels(runs_df, list(runs_df.run_id))
    options = [{"label": names[r], "value": r} for r in runs_df.run_id]
    default = [options[0]["value"]] if options else []

    def card(title: str, graph_id: str, wide: bool = False):
        return html.Section(
            className="card wide" if wide else "card",
            children=[html.H3(title), dcc.Graph(id=graph_id, config={"displayModeBar": False})],
        )

    two = Format(precision=2, scheme=Scheme.fixed)
    whole = Format(precision=0, scheme=Scheme.fixed, group=True)
    money = Format(precision=4, scheme=Scheme.fixed, symbol=Symbol.yes, symbol_prefix="$")

    table_cell = {
        "fontFamily": "var(--font)",
        "fontSize": 13,
        "padding": "10px 12px",
        "textAlign": "left",
        "whiteSpace": "normal",
        "height": "auto",
        "backgroundColor": "var(--surface)",
        "color": "var(--ink)",
        "border": "none",
        "borderBottom": "1px solid var(--line)",
    }
    table_header = {
        "fontWeight": 500,
        "color": "var(--ink-2)",
        "backgroundColor": "var(--surface)",
        "borderBottom": "1px solid var(--line-strong)",
    }

    app = Dash(__name__, title="EEOC charge intake: evaluation")
    app.layout = html.Div(
        className="wrap",
        children=[
            dcc.Location(id="url"),
            dcc.Store(id="scheme"),
            html.Header(
                className="head",
                children=[
                    html.P("EEOC charge intake", className="eyebrow"),
                    html.H1("Evaluation runs"),
                    html.P(
                        "Every run extracts the same generated documents and scores each field against the known "
                        "answer. Pick up to three runs to compare; the first one you pick is the one in focus. "
                        "Smoke runs answer from the known answers and only check the pipeline.",
                        className="lede",
                    ),
                ],
            ),
            html.Div(
                className="controls",
                children=[
                    html.Label("Runs", htmlFor="runs"),
                    dcc.Dropdown(id="runs", options=options, value=default, multi=True, clearable=False),
                ],
            ),
            html.Div(id="legend", className="legend"),
            html.Div(id="tiles", className="tiles"),
            html.Div(
                className="grid",
                children=[
                    card("Fields right, by field", "by-field", wide=True),
                    card("Fields right, by field and kind of document", "heatmap", wide=True),
                    card("Seconds per document", "latency"),
                    card("Cost per document, at list prices", "cost"),
                ],
            ),
            html.H2("Runs"),
            dash_table.DataTable(
                id="runs-table",
                columns=[
                    {"name": n, "id": i, **({"type": "numeric", "format": f} if f else {})}
                    for i, n, f in [
                        ("run", "Run", None),
                        ("cases", "Documents", whole),
                        ("failures", "Failures", whole),
                        ("field_accuracy", "Fields right", None),
                        ("unsupported_rate", "Unmatched quotes", None),
                        ("false_abstentions", "Wrongly blank", two),
                        ("guesses", "Made-up values", two),
                        ("latency_p50_ms", "Typical ms", whole),
                        ("latency_p95_ms", "Slow-end ms", whole),
                        ("cost_per_case_usd", "Cost per document", money),
                    ]
                ],
                # Shares as text, so a value just under 100% is never shown as 100.0%.
                data=runs_df.assign(
                    field_accuracy=runs_df.field_accuracy.map(lambda v: pct_label(v, 1)),
                    unsupported_rate=runs_df.unsupported_rate.map(lambda v: pct_label(v, 1)),
                ).to_dict("records"),
                style_as_list_view=True,
                cell_selectable=False,
                style_cell=table_cell,
                style_header=table_header,
            ),
            html.H2("Fields that went wrong"),
            html.P(
                "Every field the selected runs got wrong, with what the model returned and what the document said.",
                className="lede",
            ),
            dash_table.DataTable(
                id="wrong-table",
                columns=[
                    {"name": n, "id": i}
                    for i, n in [
                        ("run", "Run"),
                        ("case_id", "Document"),
                        ("case_kind", "Kind of document"),
                        ("field", "Field"),
                        ("value", "Returned"),
                        ("expected", "Expected"),
                        ("removed_by_verification", "Removed by verification"),
                    ]
                ],
                page_size=15,
                style_as_list_view=True,
                cell_selectable=False,
                style_cell=table_cell,
                style_header=table_header,
            ),
        ],
    )

    # The figures need real colours, so the browser tells the server which scheme it is in.
    app.clientside_callback(
        "function(_) { return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches"
        " ? 'dark' : 'light'; }",
        Output("scheme", "data"),
        Input("url", "pathname"),
    )

    @app.callback(
        Output("legend", "children"),
        Output("tiles", "children"),
        Output("by-field", "figure"),
        Output("heatmap", "figure"),
        Output("latency", "figure"),
        Output("cost", "figure"),
        Output("wrong-table", "data"),
        Input("runs", "value"),
        Input("scheme", "data"),
    )
    def update(selected, scheme):
        theme = scheme if scheme in THEMES else "light"
        selected = (selected or default)[:3]
        labels = run_labels(runs_df, selected)
        legend = [
            html.Span(
                className="key",
                children=[html.Span(className=f"dot run-{i}"), labels[r] + (" (in focus)" if i == 0 else "")],
            )
            for i, r in enumerate(selected)
        ]
        tiles = [tile(row) for row in tile_rows(runs_df, selected, cases_df)]
        wrong = fields_df[(fields_df.run_id.isin(selected)) & (fields_df.correct == 0)].copy()
        for col in ("value", "expected"):
            wrong[col] = wrong[col].map(_readable)
        wrong["removed_by_verification"] = wrong["removed_by_verification"].map({True: "Yes", False: "No"})
        return (
            legend,
            tiles,
            fig_accuracy_by_field(fields_df, selected, theme, labels),
            fig_heatmap(fields_df, selected, theme, labels),
            fig_latency(cases_df, selected, theme, labels),
            fig_cost(runs_df, selected, theme, labels),
            wrong.to_dict("records"),
        )

    def tile(row: dict):
        children = [
            html.Div(row["value"], className="tile-value"),
            html.Div(row["label"], className="tile-label"),
        ]
        if row["delta"]:
            tone = "flat" if row["good"] is None else ("good" if row["good"] else "bad")
            way = row["delta"].split(" ")[0]  # up, down or no
            children.append(
                html.Div(
                    className=f"tile-delta {tone}",
                    children=[html.Span(className=f"arrow {way}", **{"aria-hidden": "true"}), row["delta"]],
                )
            )
        return html.Div(className="tile", children=children)

    app.index_string = INDEX
    return app


INDEX = """<!DOCTYPE html>
<html lang="en"><head>{%metas%}<title>{%title%}</title>{%favicon%}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
{%css%}
<style>
  :root {
    color-scheme: light dark;
    --ground: #f5f5f2; --surface: #ffffff; --surface-2: #ecece8;
    --ink: #111214; --ink-2: #585d66; --ink-3: #868c96;
    --line: rgba(17,18,20,0.1); --line-2: rgba(17,18,20,0.18); --line-strong: rgba(17,18,20,0.92);
    --mark: #ffe45c; --pass: #13794a; --miss: #b5641a;
    --run-0: #111214; --run-1: #80868f; --run-2: #a7acb4;
    --shadow: 0 1px 2px rgba(17,18,20,0.06), 0 12px 40px -12px rgba(17,18,20,0.18);
    --font: Geist, 'Geist Variable', ui-sans-serif, system-ui, 'Helvetica Neue', Arial, sans-serif;
    --mono: 'Geist Mono', ui-monospace, Menlo, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ground: #0a0b0e; --surface: #121419; --surface-2: #1a1d24;
      --ink: #f2f3f5; --ink-2: #9aa1ac; --ink-3: #6e7581;
      --line: rgba(255,255,255,0.08); --line-2: rgba(255,255,255,0.16); --line-strong: rgba(255,255,255,0.92);
      --mark: #f3cf4a; --pass: #5dd39e; --miss: #f0b14c;
      --run-0: #f2f3f5; --run-1: #7d8490; --run-2: #4a505b;
      --shadow: 0 1px 2px rgba(0,0,0,0.5), 0 24px 60px -20px rgba(0,0,0,0.7);
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ground); color: var(--ink); font-family: var(--font); font-size: 15px;
    line-height: 1.55; -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 76rem; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
  .eyebrow { margin: 0 0 0.5rem; font-family: var(--mono); font-size: 0.75rem; letter-spacing: 0.04em;
    text-transform: uppercase; color: var(--ink-3); }
  h1, h2, h3 { font-weight: 500; letter-spacing: -0.022em; margin: 0; }
  h1 { font-size: 2.6rem; line-height: 1.05; }
  h2 { font-size: 1.4rem; margin: 3rem 0 0.75rem; }
  h3 { font-size: 0.95rem; letter-spacing: -0.01em; margin: 0 0 0.5rem; }
  .lede { color: var(--ink-2); max-width: 44rem; margin: 0.75rem 0 1.5rem; }
  ::selection { background: var(--mark); color: #111214; }
  .controls { display: grid; gap: 0.4rem; max-width: 40rem; margin-bottom: 1rem; }
  .controls label { font-size: 0.8rem; font-weight: 500; color: var(--ink-3); }
  .legend { display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; margin: 0 0 1.25rem; font-size: 0.85rem;
    color: var(--ink-2); }
  .key { display: inline-flex; align-items: center; gap: 0.5rem; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.run-0 { background: var(--run-0); } .dot.run-1 { background: var(--run-1); }
  .dot.run-2 { background: var(--run-2); }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr)); gap: 1px;
    background: var(--line); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; margin-bottom: 1.25rem; }
  .tile { background: var(--surface); padding: 1rem 1.1rem 1.1rem; display: grid; align-content: start; gap: 0.2rem; }
  .tile-value { font-size: 1.9rem; font-weight: 500; letter-spacing: -0.03em; line-height: 1.1; }
  .tile-label { font-size: 0.8rem; color: var(--ink-2); line-height: 1.35; }
  .tile-delta { margin-top: 0.35rem; font-size: 0.75rem; font-weight: 500; display: inline-flex; gap: 0.35rem;
    align-items: center; color: var(--ink-3); }
  .tile-delta.good { color: var(--pass); } .tile-delta.bad { color: var(--miss); }
  .tile-delta .arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; }
  .tile-delta .arrow.up { border-bottom: 6px solid currentColor; }
  .tile-delta .arrow.down { border-top: 6px solid currentColor; }
  .tile-delta .arrow.no { width: 8px; height: 2px; border: 0; background: currentColor; }
  .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem 0.75rem;
    box-shadow: var(--shadow); min-width: 0; }
  .card.wide { grid-column: 1 / -1; }
  @media (max-width: 52rem) { .grid { grid-template-columns: minmax(0, 1fr); } h1 { font-size: 2rem; } }
  /* Dash's own widgets in the same skin. Dash 4 themes its components through these variables; they are set on
     body so they also reach menus that open outside the app's container. */
  body {
    --Dash-Fill-Inverse-Strong: var(--surface);
    --Dash-Fill-Interactive-Strong: var(--ink);
    --Dash-Fill-Interactive-Weak: var(--surface-2);
    --Dash-Fill-Primary-Hover: var(--surface-2);
    --Dash-Fill-Primary-Active: var(--surface-2);
    --Dash-Fill-Disabled: var(--surface-2);
    --Dash-Stroke-Strong: var(--line-2);
    --Dash-Stroke-Weak: var(--line);
    --Dash-Text-Primary: var(--ink);
    --Dash-Text-Strong: var(--ink);
    --Dash-Text-Weak: var(--ink-2);
    --Dash-Text-Disabled: var(--ink-3);
    --Dash-Shading-Strong: rgba(0, 0, 0, 0.35);
    --Dash-Shading-Weak: rgba(0, 0, 0, 0.2);
  }
  .dash-dropdown, .dash-dropdown-options { font-family: var(--font); font-size: 14px; border-radius: 10px; }
  .dash-dropdown { min-height: 2.75rem; background: var(--surface); border: 1px solid var(--line-2); }
  .dash-dropdown-value-item { background: var(--surface-2); border-radius: 999px; padding: 0.1rem 0.6rem; }
  .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
  .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th { font-family: var(--font) !important; }
  .dash-table-container { border-top: 1px solid var(--line-strong); }
  .previous-next-container, .page-number { color: var(--ink-2); font-family: var(--font); }
  .previous-next-container button { background: var(--surface); color: var(--ink); border: 1px solid var(--line-2);
    border-radius: 999px; }
</style></head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""


def export_figures(results_dir: Path, out: Path) -> dict:
    """Plotly JSON for the latest live runs, up to three (as many as the charts draw), for the case study.

    Each trace carries its part in `meta.role` (run-0 is the latest run, run-1 the one before it, run-2 the one
    before that, connector, accuracy) and each highlight shape is named, so a page with its own palette can
    restyle them and pick which run to put in focus. The titles stay in the layout for pages that draw them
    from there.
    """
    runs = [r for r in load_runs(results_dir) if r["kind"] == "live"]
    if not runs:
        raise SystemExit("no live runs to export")
    runs_df, cases_df, fields_df = frames(runs)
    ids = list(runs_df.run_id[:3])
    labels = run_labels(runs_df, ids)
    latest = runs_df.iloc[0]
    figs = [
        ("by_field", "Fields right, by field", fig_accuracy_by_field(fields_df, ids, "light", labels)),
        (
            "heatmap",
            "Fields right, by field and kind of document",
            fig_heatmap(fields_df, ids, "light", labels),
        ),
        ("latency", "Seconds per document", fig_latency(cases_df, ids, "light", labels)),
        ("cost", "Cost per document, at list prices", fig_cost(runs_df, ids, "light", labels)),
    ]
    for _, title, fig in figs:
        fig.update_layout(title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 14}})
    payload = {
        "run_id": latest.run_id,
        "model": latest.model,
        "started_at": latest.started_at,
        "runs": [{"run_id": r, "label": labels[r]} for r in ids],
        "figures": [{"name": n, "title": t, "spec": json.loads(f.to_json())} for n, t, f in figs],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--export-figures", type=Path, default=None, help="write Plotly JSON for the site and exit"
    )
    args = ap.parse_args()
    if args.export_figures:
        payload = export_figures(RESULTS_DIR, args.export_figures)
        print(f"wrote {args.export_figures} ({len(payload['figures'])} figures for {payload['run_id']})")
        return
    app = build_app()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8050")), debug=False)


if __name__ == "__main__":
    main()
