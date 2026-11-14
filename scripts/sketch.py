#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import baseline_size, pct, period_path, read_json


def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build(period: Path) -> int:
    profile = read_json(period / "work" / "01_profiil.json")
    frame = pd.read_csv(period / "work" / "02_agregatsioonid" / "periood_toode.csv")
    period_column = str(profile["periood_veerg"])
    product_column = str(profile["toote_veerg"])
    periods = [str(value) for value in profile["perioodid"]]
    base_count = baseline_size(len(periods))
    baseline = periods[:base_count]
    after = periods[base_count:]
    products = [str(value) for value in frame[product_column].drop_duplicates()]
    events: list[dict[str, Any]] = []
    event_path = period / "work" / "01_sundmused.json"
    if event_path.is_file():
        loaded = json.loads(event_path.read_text(encoding="utf-8"))
        events = loaded if isinstance(loaded, list) else []

    width = 880
    height = 520
    colors = ("#1f4e79", "#b85c38", "#2f6f4e", "#6b4c9a", "#8a6a2f")
    rate_box = (48, 36, 400, 200)
    bar_box = (500, 36, 340, 200)
    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f4ef"/>',
        '<text x="48" y="24" font-family="sans-serif" font-size="16">Visand. Päris pildid tulevad kolmandas faasis.</text>',
    ]
    max_rate = max(float(value) for value in frame["maar"].dropna()) if frame["maar"].notna().any() else 0.01
    max_rate = max(max_rate, 0.01)
    left, top, box_width, box_height = rate_box
    lines.append(f'<text x="{left}" y="{top - 8}" font-family="sans-serif" font-size="13">Praakmäär kuude lõikes</text>')
    step = box_width / max(len(periods) - 1, 1)
    for index, product in enumerate(products):
        subset = frame[frame[product_column].astype(str) == product].set_index(period_column)
        points: list[tuple[float, float]] = []
        for slot, name in enumerate(periods):
            value = float(subset.loc[name, "maar"]) if name in subset.index else 0.0
            x = left + slot * step
            y = top + box_height - (value / max_rate) * box_height
            points.append((x, y))
        color = colors[index % len(colors)]
        rendered = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{rendered}"/>')
        lines.append(
            f'<text x="{left + box_width + 8}" y="{top + 14 + index * 16}" fill="{color}" '
            f'font-family="sans-serif" font-size="12">{escape(product)}</text>'
        )
    for slot, name in enumerate(periods):
        x = left + slot * step
        lines.append(
            f'<text x="{x}" y="{top + box_height + 16}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11">{escape(name)}</text>'
        )
        marks = [str(item["tekst"]) for item in events if str(item.get("kuu")) == name]
        if marks:
            lines.append(
                f'<text x="{x}" y="{top + box_height + 32}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="10">{escape(", ".join(marks))}</text>'
            )

    overruns: list[tuple[str, float]] = []
    for product in products:
        subset = frame[frame[product_column].astype(str) == product].set_index(period_column)
        base_cost = float(subset.loc[baseline, "euro_kokku"].sum()) if "euro_kokku" in subset.columns else 0.0
        after_cost = float(subset.loc[after, "euro_kokku"].sum()) if "euro_kokku" in subset.columns else 0.0
        overruns.append((product, after_cost - (base_cost / len(baseline)) * len(after)))
    bar_left, bar_top, bar_width, bar_height = bar_box
    lines.append(
        f'<text x="{bar_left}" y="{bar_top - 8}" font-family="sans-serif" font-size="13">Ülekulu toodete lõikes</text>'
    )
    maximum = max((abs(value) for _, value in overruns), default=1.0) or 1.0
    band = bar_height / max(len(overruns), 1)
    for index, (product, value) in enumerate(overruns):
        y = bar_top + index * band + 8
        length = abs(value) / maximum * (bar_width - 80)
        label = f"{escape(product)} {round(value)} €"
        lines.append(f'<rect x="{bar_left}" y="{y}" width="{length:.1f}" height="{band - 14:.1f}" fill="#1f4e79"/>')
        lines.append(
            f'<text x="{bar_left + length + 6:.1f}" y="{y + band - 18:.1f}" '
            f'font-family="sans-serif" font-size="12">{label}</text>'
        )
    lines.append(
        '<text x="48" y="500" font-family="sans-serif" font-size="11">'
        "Märgid kuude all on juhendi sündmused, mitte järeldused."
        "</text>"
    )
    lines.append("</svg>")
    target = period / "output" / "joonis.svg"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Joonis: {target.relative_to(period.parent.parent)}")
    print(f"Baas joonisel: {', '.join(baseline)}. Telje lagi on {pct(max_rate)}.")
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: sketch.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
