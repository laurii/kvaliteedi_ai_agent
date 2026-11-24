#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import ROOT, baseline_size, euro, pct, period_path, read_json

RATE_DELTA_MIN = 0.005
PALETTE = ("#1f4e79", "#c47b2b", "#2f6f4e", "#8c3a3a", "#5c6b7a")


def point(value: float | None) -> str:
    if value is None:
        return "–"
    return f"{value:.1f}%".replace(".", ",")


def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def read_table(path: Path) -> pd.DataFrame | None:
    if not path.is_file():
        return None
    return pd.read_csv(path)


def finding(outlier: dict[str, Any]) -> dict[str, Any] | None:
    ranked = list(outlier.get("euro_pingerida") or [])
    if not ranked:
        ranked = list(outlier.get("tukkide_pingerida") or [])
    narrow = [item for item in ranked if ";" in str(item.get("loik", ""))]
    if narrow:
        return narrow[0]
    if ranked:
        return ranked[0]
    return None


def extra_column(item: dict[str, Any], product_column: str) -> str:
    for key in item.get("vordlus", {}):
        if key != product_column:
            return str(key)
    return ""


def product_rates(
    frame: pd.DataFrame,
    period_column: str,
    product_column: str,
    periods: list[str],
    baseline: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product, group in frame.groupby(product_column, sort=False):
        table = (
            group.groupby(period_column)[["tukke", "toodetud"]]
            .sum()
            .reindex(periods)
            .fillna(0.0)
        )
        series: list[float | None] = []
        for name in periods:
            produced = float(table.loc[name, "toodetud"])
            pieces = float(table.loc[name, "tukke"])
            series.append(None if produced == 0 else round(pieces / produced * 100, 1))
        base_produced = float(table.loc[baseline, "toodetud"].sum())
        last_produced = float(table.loc[periods[-1], "toodetud"])
        base_rate = None if base_produced == 0 else float(table.loc[baseline, "tukke"].sum()) / base_produced
        last_rate = None if last_produced == 0 else float(table.loc[periods[-1], "tukke"]) / last_produced
        rows.append(
            {
                "nimi": str(product),
                "seeria": series,
                "baas": base_rate,
                "viimane": last_rate,
            }
        )
    return rows


def product_overrun(
    frame: pd.DataFrame,
    period_column: str,
    product_column: str,
    baseline: list[str],
    after: list[str],
) -> list[tuple[str, int]]:
    ranked: list[tuple[str, int]] = []
    for product, group in frame.groupby(product_column, sort=False):
        table = group.groupby(period_column)[["euro_kokku"]].sum().reindex(baseline + after).fillna(0.0)
        base = float(table.loc[baseline, "euro_kokku"].sum())
        later = float(table.loc[after, "euro_kokku"].sum())
        ranked.append((str(product), round(later - (base / len(baseline)) * len(after))))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def line_option(title: str, periods: list[str], series: list[dict[str, Any]], marks: list[dict[str, str]]) -> dict[str, Any]:
    rendered = []
    for index, item in enumerate(series):
        row: dict[str, Any] = {
            "name": item["nimi"],
            "type": "line",
            "data": item["seeria"],
            "connectNulls": False,
            "lineStyle": {"width": 3},
            "symbolSize": 8,
            "itemStyle": {"color": PALETTE[index % len(PALETTE)]},
        }
        if marks and index == 0:
            row["markLine"] = {
                "symbol": "none",
                "label": {"formatter": "{b}"},
                "data": [{"name": mark["tekst"], "xAxis": mark["kuu"]} for mark in marks],
            }
        rendered.append(row)
    return {
        "title": {"text": title, "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 28},
        "grid": {"left": 48, "right": 24, "top": 72, "bottom": 32},
        "xAxis": {"type": "category", "data": periods},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value} %"}},
        "series": rendered,
    }


def bar_option(title: str, names: list[str], values: list[Any], horizontal: bool = False) -> dict[str, Any]:
    category = {"type": "category", "data": names}
    value = {"type": "value"}
    return {
        "title": {"text": title, "textStyle": {"fontSize": 15}},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 24, "top": 48, "bottom": 32, "containLabel": True},
        "xAxis": value if horizontal else category,
        "yAxis": category if horizontal else value,
        "series": [
            {
                "type": "bar",
                "data": values,
                "barMaxWidth": 36,
                "itemStyle": {"color": "#1f4e79"},
            }
        ],
    }


def rate_caption(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows:
        rose = (
            row["baas"] is not None
            and row["viimane"] is not None
            and row["viimane"] - row["baas"] >= RATE_DELTA_MIN
        )
        mark = "tõusis" if rose else "paigal"
        parts.append(f"{row['nimi']} {pct(row['baas'])} → {pct(row['viimane'])} ({mark})")
    return "Baas viimase kuu vastu: " + ", ".join(parts) + "."


def event_marks(events: list[dict[str, Any]], periods: list[str]) -> list[dict[str, str]]:
    grouped: dict[str, list[str]] = {}
    for event in events:
        month = str(event.get("kuu", ""))
        text = str(event.get("tekst", "")).strip()
        if month not in periods or not text:
            continue
        grouped.setdefault(month, []).append(text)
    return [{"kuu": month, "tekst": ", ".join(texts)} for month, texts in grouped.items()]


def defect_rows(table: pd.DataFrame, product: str, column: str) -> pd.DataFrame:
    subset = table[(table["toode"].astype(str) == product) & (table["veerg"].astype(str) == column)]
    return subset


def defect_caption(rows: pd.DataFrame) -> str:
    parts = []
    for _, row in rows.iterrows():
        parts.append(f"{row['vaartus']} {pct(row['baas_maar'])} → {pct(row['viimane_maar'])}")
    return ", ".join(parts) + "."


def month_caption(compare: pd.Series, months: pd.DataFrame) -> str:
    expensive = str(compare["kalleim_kuu"])
    jump = str(compare["suurim_hyppe_kuu"])
    expensive_row = months[months["kuu"].astype(str) == expensive]
    jump_row = months[months["kuu"].astype(str) == jump]
    expensive_euro = euro(float(expensive_row["ulekulu_vs_baas"].iloc[0])) if len(expensive_row) else "–"
    jump_euro = euro(float(jump_row["hype_euro"].iloc[0])) if len(jump_row) and pd.notna(jump_row["hype_euro"].iloc[0]) else "–"
    if expensive == jump:
        return (
            f"Kallim kuu ja suurim hüpe on mõlemad {expensive}, "
            f"ülekulu baasi vastu {expensive_euro} ja hüpe eelmisest kuust {jump_euro}."
        )
    return (
        f"Kallim kuu on {expensive}, ülekulu baasi vastu {expensive_euro}, "
        f"ja suurim hüpe on {jump}, {jump_euro}."
    )


def page(period_name: str, sections: list[dict[str, Any]], charts: list[dict[str, Any]]) -> str:
    blocks = []
    for section in sections:
        charts_html = []
        for chart in section["charts"]:
            charts_html.append(
                f'<div><div id="{escape(chart["id"])}" class="chart"></div><p>{escape(chart["caption"])}</p></div>'
            )
        klass = "pair" if len(section["charts"]) > 1 else "one"
        blocks.append(
            f'<section><h2>{escape(section["heading"])}</h2><div class="{klass}">{"".join(charts_html)}</div></section>'
        )
    payload = json.dumps(charts, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!DOCTYPE html>
<html lang="et">
<head>
  <meta charset="utf-8">
  <title>Koosoleku pildid {escape(period_name)}</title>
  <script src="echarts.min.js"></script>
  <style>
    body {{ font-family: sans-serif; max-width: 1100px; margin: 24px auto; color: #1c1c1c; padding: 0 16px; }}
    h1 {{ font-size: 22px; }}
    h2 {{ font-size: 16px; margin-bottom: 8px; }}
    .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .chart {{ height: 320px; }}
    p {{ margin: 4px 0 0; line-height: 1.4; }}
    @media (max-width: 800px) {{ .pair {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Koosoleku pildid {escape(period_name)}</h1>
  {"".join(blocks)}
  <script id="charts" type="application/json">{payload}</script>
  <script>
    const charts = JSON.parse(document.getElementById("charts").textContent);
    for (const chart of charts) {{
      echarts.init(document.getElementById(chart.id)).setOption(chart.option);
    }}
  </script>
</body>
</html>
"""


def build(period: Path) -> int:
    vendor = ROOT / "vendor" / "echarts.min.js"
    if not vendor.is_file():
        raise RuntimeError("Puudub vendor/echarts.min.js. Leht peab avanema ilma võrguta.")
    profile = read_json(period / "work" / "01_profiil.json")
    outlier = read_json(period / "work" / "03_outlierid.json")
    frame = read_table(period / "work" / "02_agregatsioonid" / "periood_toode.csv")
    if frame is None:
        raise RuntimeError("Puudub periood_toode.csv.")
    period_column = str(profile["periood_veerg"])
    product_column = str(profile["toote_veerg"])
    periods = [str(value) for value in profile["perioodid"]]
    baseline = [str(value) for value in outlier.get("baas") or periods[: baseline_size(len(periods))]]
    after = [name for name in periods if name not in baseline]
    chosen = finding(outlier)
    sections: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []

    rates = product_rates(frame, period_column, product_column, periods, baseline)
    if rates:
        option = line_option("Määr toodete lõikes", periods, rates, [])
        sections.append(
            {
                "heading": "Määr kuude lõikes",
                "charts": [{"id": "maarad", "option": option, "caption": rate_caption(rates)}],
            }
        )
        charts.append({"id": "maarad", "option": option})

    if "euro_kokku" in frame.columns and after:
        ranked = product_overrun(frame, period_column, product_column, baseline, after)
        option = bar_option(
            "Ülekulu toodete lõikes",
            [name for name, _ in ranked],
            [value for _, value in ranked],
        )
        top = ranked[0]
        sections.append(
            {
                "heading": "Ülekulu",
                "charts": [
                    {
                        "id": "ulekulu",
                        "option": option,
                        "caption": f"Suurim ülekulu on {top[0]}, {euro(top[1])}.",
                    }
                ],
            }
        )
        charts.append({"id": "ulekulu", "option": option})

    months = read_table(period / "work" / "05_koosolek" / "kuud.csv")
    if chosen and months is not None:
        focus = months[months["loik"].astype(str) == str(chosen["loik"])]
        if not focus.empty:
            ordered = focus.set_index("kuu").reindex(periods)
            series = [
                {
                    "nimi": str(chosen["loik"]),
                    "seeria": [
                        None if pd.isna(ordered.loc[name, "maar"]) else round(float(ordered.loc[name, "maar"]) * 100, 1)
                        for name in periods
                    ],
                }
            ]
            events: list[dict[str, Any]] = []
            event_path = period / "work" / "01_sundmused.json"
            if event_path.is_file():
                loaded = json.loads(event_path.read_text(encoding="utf-8"))
                events = loaded if isinstance(loaded, list) else []
            marks = event_marks(events, periods)
            option = line_option(str(chosen["loik"]), periods, series, marks)
            first = series[0]["seeria"][0]
            last = series[0]["seeria"][-1]
            sections.append(
                {
                    "heading": "Valitud leid",
                    "charts": [
                        {
                            "id": "leid",
                            "option": option,
                            "caption": (
                                f"{periods[0]} {point(first)} ja {periods[-1]} {point(last)}, "
                                "märgid kuude peal on juhendi sündmused."
                            ),
                        }
                    ],
                }
            )
            charts.append({"id": "leid", "option": option})

            parts = read_table(period / "work" / "05_koosolek" / "ulekulu_osad.csv")
            compared = read_table(period / "work" / "05_koosolek" / "kuude_vordlus.csv")
            pair: list[dict[str, Any]] = []
            if parts is not None:
                row = parts[parts["loik"].astype(str) == str(chosen["loik"])]
                if not row.empty:
                    current = row.iloc[0]
                    option = bar_option(
                        "Ülekulu jaotus",
                        ["Mahakandmine", "Ümbertegemine", "Kliendileid"],
                        [
                            int(current["mahakandmine"]),
                            int(current["umbertegemine"]),
                            int(current["kliendileid"]),
                        ],
                    )
                    pair.append(
                        {
                            "id": "osad",
                            "option": option,
                            "caption": (
                                f"Mahakandmine {euro(current['mahakandmine'])}, "
                                f"ümbertegemine {euro(current['umbertegemine'])}, "
                                f"kliendileid {euro(current['kliendileid'])}."
                            ),
                        }
                    )
                    charts.append({"id": "osad", "option": option})
            if compared is not None:
                match = compared[compared["loik"].astype(str) == str(chosen["loik"])]
                if not match.empty:
                    values = []
                    for name in periods:
                        amount = ordered.loc[name, "ulekulu_vs_baas"]
                        values.append(0 if pd.isna(amount) else int(amount))
                    option = bar_option("Kuude panus", periods, values)
                    pair.append(
                        {
                            "id": "kuud",
                            "option": option,
                            "caption": month_caption(match.iloc[0], ordered.reset_index()),
                        }
                    )
                    charts.append({"id": "kuud", "option": option})
            if pair:
                sections.append({"heading": "Ülekulu osad ja kuud", "charts": pair})

    stable = read_table(period / "work" / "05_koosolek" / "muutumatu.csv")
    column = extra_column(chosen, product_column) if chosen else ""
    product = str(chosen["vordlus"].get(product_column, "")) if chosen else ""
    if stable is not None and column and product:
        subset = defect_rows(stable, product, column)
        flat = subset[subset["staatus"] == "ei muutunud"]
        rose = subset[subset["staatus"].isin(["muutus", "uus"])]
        pair = []
        if not flat.empty:
            option = bar_option(
                "Paigal",
                [str(value) for value in flat["vaartus"]],
                [None if pd.isna(value) else round(float(value) * 100, 1) for value in flat["viimane_maar"]],
                horizontal=True,
            )
            pair.append({"id": "paigal", "option": option, "caption": "Paigal: " + defect_caption(flat)})
            charts.append({"id": "paigal", "option": option})
        if not rose.empty:
            option = bar_option(
                "Tõusis",
                [str(value) for value in rose["vaartus"]],
                [None if pd.isna(value) else round(float(value) * 100, 1) for value in rose["viimane_maar"]],
                horizontal=True,
            )
            pair.append({"id": "tousis", "option": option, "caption": "Tõusis: " + defect_caption(rose)})
            charts.append({"id": "tousis", "option": option})
        if pair:
            sections.append({"heading": "Mis jäi paigale", "charts": pair})

    target = period / "output" / "pildid.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(vendor, target.parent / "echarts.min.js")
    target.write_text(page(period.name, sections, charts), encoding="utf-8")
    print(f"Pildid: {target.relative_to(period.parent.parent)}")
    print(f"Pilte: {len(charts)}")
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: charts.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
