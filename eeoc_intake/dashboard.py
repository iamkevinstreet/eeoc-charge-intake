"""Evaluation dashboard (Plotly Dash): compare runs, see which fields fail on which documents.

    python -m eeoc_intake.dashboard            # http://127.0.0.1:8050

Reads every results file under eeoc_intake/evals/results/{live,smoke}/. The same tidy frames feed the CSV
export for Tableau (`python -m eeoc_intake.evals.export`), so the three views agree with each other.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

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

# Colour roles. Categorical slots validated for both surfaces (dataviz method); one sequential hue for magnitude.
INK, INK2, RULE, PAPER, PAPER2 = "#141b22", "#4f5b67", "#c6cfd8", "#f4f6f8", "#e9edf1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SEQUENTIAL = ["#e9edf1", "#b9cfe8", "#7fa6d6", "#3f79bf", "#1d4f8a"]


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


# ---------- figures ----------
def _base(fig, height: int):
    fig.update_layout(
        template="simple_white",
        height=height,
        margin={"l": 10, "r": 10, "t": 36, "b": 10},
        font={"family": "IBM Plex Sans, Helvetica Neue, Arial, sans-serif", "size": 13, "color": INK},
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        legend={"orientation": "h", "y": -0.15, "title": None},
        hoverlabel={"bgcolor": PAPER2, "font": {"color": INK}},
    )
    fig.update_xaxes(showgrid=True, gridcolor=PAPER2, zeroline=False, linecolor=RULE)
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor=RULE)
    return fig


def fig_accuracy_by_field(fields: pd.DataFrame, run_ids: list[str]):
    import plotly.graph_objects as go

    sub = fields[fields.run_id.isin(run_ids)]
    acc = sub.groupby(["run", "field"], sort=False)["correct"].mean().reset_index()
    order = [FIELD_LABELS[f] for f in SCORED_FIELDS]
    fig = go.Figure()
    runs = list(dict.fromkeys(sub.run))
    for i, run in enumerate(runs):
        a = acc[acc.run == run].set_index("field").reindex(order)
        fig.add_bar(
            y=order,
            x=a["correct"],
            name=run,
            orientation="h",
            marker={"color": SERIES[i % len(SERIES)], "line": {"width": 0}},
            text=[f"{v:.0%}" for v in a["correct"].fillna(0)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1%}<extra>%{fullData.name}</extra>",
        )
    fig.update_layout(
        title="Accuracy by field",
        barmode="group",
        bargap=0.5,
        bargroupgap=0.1,
        showlegend=len(runs) > 1,
        xaxis={"tickformat": ".0%", "range": [0, 1.08]},
        yaxis={"autorange": "reversed"},
    )
    return _base(fig, 70 + (16 + 12 * len(runs)) * len(order))


def fig_heatmap(fields: pd.DataFrame, run_id: str):
    import plotly.graph_objects as go

    sub = fields[fields.run_id == run_id]
    if sub.empty:
        return _base(go.Figure(layout={"title": "Accuracy by field and case kind"}), 300)
    pivot = sub.pivot_table(index="field", columns="case_kind", values="correct", aggfunc="mean")
    counts = sub.groupby("case_kind")["case_id"].nunique()
    pivot = pivot.reindex([FIELD_LABELS[f] for f in SCORED_FIELDS])
    cols = [c for c in KIND_LABELS.values() if c in pivot.columns]
    pivot = pivot[cols]
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[f"{c} ({counts[c]})" for c in cols],
            y=pivot.index,
            zmin=0,
            zmax=1,
            colorscale=[[i / (len(SEQUENTIAL) - 1), c] for i, c in enumerate(SEQUENTIAL)],
            xgap=2,
            ygap=2,
            text=[[f"{v:.0%}" if pd.notna(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont={"size": 12},
            colorbar={"tickformat": ".0%", "thickness": 10, "len": 0.8, "title": None},
            hovertemplate="%{y}, %{x}: %{z:.1%}<extra></extra>",
        )
    )
    fig.update_layout(title="Accuracy by field and case kind", yaxis={"autorange": "reversed"})
    fig.update_xaxes(tickangle=0, showgrid=False)
    return _base(fig, 90 + 34 * len(SCORED_FIELDS))


def fig_latency(cases: pd.DataFrame, run_ids: list[str]):
    import plotly.graph_objects as go

    sub = cases[cases.run_id.isin(run_ids)]
    fig = go.Figure()
    for i, run in enumerate(dict.fromkeys(sub.run)):
        c = sub[sub.run == run]
        fig.add_box(
            x=c["latency_ms"] / 1000,
            name=run,
            boxpoints="all",
            jitter=0.4,
            pointpos=0,
            marker={"color": SERIES[i % len(SERIES)], "size": 6},
            line={"color": SERIES[i % len(SERIES)], "width": 1.5},
            fillcolor="rgba(0,0,0,0)",
            hovertemplate="%{x:.1f} s<extra>%{text}</extra>",
            text=c["case_id"],
        )
    fig.update_layout(
        title="Seconds per document", showlegend=False, xaxis={"title": None, "rangemode": "tozero"}
    )
    return _base(fig, 120 + 50 * max(1, len(run_ids)))


def fig_cost(runs_df: pd.DataFrame, run_ids: list[str]):
    import plotly.graph_objects as go

    sub = runs_df[runs_df.run_id.isin(run_ids)]
    fig = go.Figure(
        go.Bar(
            y=sub["run"],
            x=sub["cost_per_case_usd"],
            orientation="h",
            marker={"color": [SERIES[i % len(SERIES)] for i in range(len(sub))], "line": {"width": 0}},
            text=[f"${v:.4f}" for v in sub["cost_per_case_usd"].fillna(0)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: $%{x:.4f} per document<extra></extra>",
        )
    )
    top = float(sub["cost_per_case_usd"].fillna(0).max() or 0)
    fig.update_layout(
        title="Cost per document (list prices)",
        bargap=0.5,
        xaxis={"tickprefix": "$", "tickformat": ".3f", "range": [0, max(0.01, top * 1.35)]},
    )
    return _base(fig, 120 + 40 * max(1, len(sub)))


# ---------- app ----------
def build_app(results_dir: Path = RESULTS_DIR):
    from dash import Dash, Input, Output, dash_table, dcc, html

    runs = load_runs(results_dir)
    runs_df, cases_df, fields_df = frames(runs)
    options = [{"label": r["run"], "value": r["run_id"]} for r in runs_df.to_dict("records")]
    default = [options[0]["value"]] if options else []

    app = Dash(__name__, title="EEOC charge intake: evaluation")
    app.layout = html.Div(
        className="wrap",
        children=[
            html.H1("EEOC charge intake: evaluation runs"),
            html.P(
                "Every run extracts the same generated documents and scores each field against the ground truth. "
                "Pick up to three runs to compare. Smoke runs answer from the ground truth and only check the pipeline.",
                className="lede",
            ),
            html.Div(
                className="controls",
                children=[
                    html.Label("Runs"),
                    dcc.Dropdown(id="runs", options=options, value=default, multi=True, clearable=False),
                ],
            ),
            html.Div(id="tiles", className="tiles"),
            dcc.Graph(id="by-field", config={"displayModeBar": False}),
            dcc.Graph(id="heatmap", config={"displayModeBar": False}),
            html.Div(
                className="row",
                children=[
                    dcc.Graph(id="latency", config={"displayModeBar": False}),
                    dcc.Graph(id="cost", config={"displayModeBar": False}),
                ],
            ),
            html.H2("Runs"),
            dash_table.DataTable(
                id="runs-table",
                columns=[
                    {"name": n, "id": i}
                    for i, n in [
                        ("run", "Run"),
                        ("cases", "Cases"),
                        ("failures", "Failures"),
                        ("field_accuracy", "Field accuracy"),
                        ("unsupported_rate", "Unsupported rate"),
                        ("false_abstentions", "False abstentions"),
                        ("guesses", "Guesses"),
                        ("latency_p50_ms", "p50 ms"),
                        ("latency_p95_ms", "p95 ms"),
                        ("cost_per_case_usd", "Cost per case"),
                    ]
                ],
                data=runs_df.round(4).to_dict("records"),
                style_as_list_view=True,
                style_cell={
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontSize": 13,
                    "padding": "6px 8px",
                    "textAlign": "left",
                },
                style_header={"fontWeight": "500", "borderBottom": f"2px solid {INK}"},
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
                        ("case_kind", "Case kind"),
                        ("field", "Field"),
                        ("value", "Returned"),
                        ("expected", "Expected"),
                        ("removed_by_verification", "Removed by verification"),
                    ]
                ],
                page_size=15,
                style_as_list_view=True,
                style_cell={
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "fontSize": 13,
                    "padding": "6px 8px",
                    "textAlign": "left",
                    "whiteSpace": "normal",
                },
                style_header={"fontWeight": "500", "borderBottom": f"2px solid {INK}"},
            ),
        ],
    )

    @app.callback(
        Output("tiles", "children"),
        Output("by-field", "figure"),
        Output("heatmap", "figure"),
        Output("latency", "figure"),
        Output("cost", "figure"),
        Output("wrong-table", "data"),
        Input("runs", "value"),
    )
    def update(selected):
        selected = (selected or default)[:3]
        primary = runs_df[runs_df.run_id == selected[0]].iloc[0] if selected else None
        tiles = []
        if primary is not None:
            tiles = [
                tile(f"{primary.field_accuracy:.1%}", "Field accuracy", primary.run),
                tile(f"{(primary.unsupported_rate or 0):.1%}", "Unsupported outputs removed"),
                tile(f"{(primary.false_abstentions or 0):.2f}", "False abstentions per document"),
                tile(f"{(primary.guesses or 0):.2f}", "Guesses per document"),
                tile(f"{primary.latency_p50_ms / 1000:.1f} s", "Median time per document"),
                tile(f"${(primary.cost_per_case_usd or 0):.4f}", "Cost per document"),
            ]
        wrong = fields_df[(fields_df.run_id.isin(selected)) & (fields_df.correct == 0)]
        return (
            tiles,
            fig_accuracy_by_field(fields_df, selected),
            fig_heatmap(fields_df, selected[0] if selected else ""),
            fig_latency(cases_df, selected),
            fig_cost(runs_df, selected),
            wrong.to_dict("records"),
        )

    def tile(value: str, label: str, note: str | None = None):
        return html.Div(
            className="tile",
            children=[html.Div(value, className="tile-value"), html.Div(label, className="tile-label")]
            + ([html.Div(note, className="tile-note")] if note else []),
        )

    app.index_string = INDEX
    return app


INDEX = """<!DOCTYPE html>
<html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
  body { margin: 0; background: #f4f6f8; color: #141b22; font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif; }
  .wrap { max-width: 68rem; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
  h1, h2 { font-family: 'Newsreader', 'Iowan Old Style', Georgia, serif; font-weight: 500; letter-spacing: -0.01em; }
  h1 { font-size: 1.9rem; margin: 0 0 0.5rem; } h2 { font-size: 1.3rem; margin: 2rem 0 0.5rem; }
  .lede { color: #4f5b67; max-width: 62ch; margin: 0 0 1rem; }
  .controls { max-width: 36rem; margin-bottom: 1rem; } .controls label { font-size: 0.85rem; color: #4f5b67; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 1rem 1.5rem; border-top: 2px solid #141b22; padding-top: 1rem; margin: 1rem 0; }
  .tile-value { font-family: 'Newsreader', Georgia, serif; font-size: 1.8rem; line-height: 1.1; }
  .tile-label { font-size: 0.85rem; } .tile-note { font-size: 0.78rem; color: #4f5b67; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; } @media (max-width: 50rem) { .row { grid-template-columns: 1fr; } }
</style></head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""


def export_figures(results_dir: Path, out: Path) -> dict:
    """Plotly JSON for the latest live run (and the one before it, for the comparison), for the case study."""
    runs = [r for r in load_runs(results_dir) if r["kind"] == "live"]
    if not runs:
        raise SystemExit("no live runs to export")
    runs_df, cases_df, fields_df = frames(runs)
    ids = list(runs_df.run_id[:2])
    latest = runs_df.iloc[0]
    figs = [
        ("by_field", "Accuracy by field", fig_accuracy_by_field(fields_df, ids)),
        ("heatmap", "Accuracy by field and case kind", fig_heatmap(fields_df, ids[0])),
        ("latency", "Seconds per document", fig_latency(cases_df, ids)),
        ("cost", "Cost per document", fig_cost(runs_df, ids)),
    ]
    payload = {
        "run_id": latest.run_id,
        "model": latest.model,
        "started_at": latest.started_at,
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
