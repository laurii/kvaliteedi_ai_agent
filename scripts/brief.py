#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import baseline_size, blank, euro, pct, period_path, read_json

MEASURES = ("tukke", "juhtumeid", "euro_mahakandmine", "euro_umbertegemine", "euro_kliendileid", "euro_kokku")
META = {"tukke", "juhtumeid", "toodetud", "maar", *MEASURES}
RATE_DELTA_MIN = 0.005
ASSUMPTION = (
    "Kui sama defekt avastataks liinil, jäävad mahakandmine ja ümbertegemine alles "
    "ning kliendijuhtumi lisakulu on 0."
)


def segments(period: Path, outlier: dict[str, Any]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in outlier.get("euro_pingerida", []):
        if item["loik"] in seen:
            continue
        seen.add(item["loik"])
        chosen.append(item)
    return chosen


def monthly_frame(period: Path, item: dict[str, Any], period_column: str, periods: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(period / str(item["fail"]))
    for key, value in item["vordlus"].items():
        frame = frame[frame[key].astype(str) == str(value)]
    present = [column for column in MEASURES if column in frame.columns]
    grouped = frame.groupby(period_column, dropna=False)[present].sum()
    grouped = grouped.reindex(periods).fillna(0.0)
    if "toodetud" in frame.columns and not frame.empty:
        produced = frame.groupby(period_column)["toodetud"].max().reindex(periods).fillna(0.0)
    else:
        produced = pd.Series(0.0, index=periods)
    ratio = grouped["tukke"] / produced.where(produced != 0, pd.NA)
    return grouped.assign(toodetud=produced, maar=ratio)


def effects(frame: pd.DataFrame, baseline: list[str], after: list[str]) -> dict[str, float]:
    base = frame.loc[baseline]
    later = frame.loc[after]
    produced_base = float(base["toodetud"].sum())
    pieces_base = float(base["tukke"].sum())
    cost_base = float(base["euro_kokku"].sum())
    produced_after = float(later["toodetud"].sum())
    pieces_after = float(later["tukke"].sum())
    cost_after = float(later["euro_kokku"].sum())
    overrun = cost_after - (cost_base / len(baseline)) * len(after)
    per_produced = cost_base / produced_base if produced_base else 0.0
    per_piece = cost_base / pieces_base if pieces_base else 0.0
    volume = (produced_after - (produced_base / len(baseline)) * len(after)) * per_produced
    rate = (pieces_after - (pieces_base / produced_base) * produced_after) * per_piece if produced_base else 0.0
    mix = overrun - volume - rate
    parts = {
        "mahakandmine": float(later["euro_mahakandmine"].sum()) - (float(base["euro_mahakandmine"].sum()) / len(baseline)) * len(after),
        "umbertegemine": float(later["euro_umbertegemine"].sum()) - (float(base["euro_umbertegemine"].sum()) / len(baseline)) * len(after),
        "kliendileid": float(later["euro_kliendileid"].sum()) - (float(base["euro_kliendileid"].sum()) / len(baseline)) * len(after),
    }
    return {
        "ulekulu": overrun,
        "maht": volume,
        "maar": rate,
        "segu": mix,
        "kliendileid_parast": float(later["euro_kliendileid"].sum()),
        **parts,
    }


def rounded_parts(total: int, values: dict[str, float]) -> dict[str, int]:
    names = list(values)
    rounded = [round(values[name]) for name in names]
    rounded[-1] += total - sum(rounded)
    return dict(zip(names, rounded))


def write_table(path: Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def category_files(period: Path) -> list[tuple[str, pd.DataFrame]]:
    folder = period / "work" / "02_agregatsioonid"
    found = []
    for path in sorted(folder.glob("periood_toode__*.csv")):
        found.append((path.name, pd.read_csv(path)))
    return found


def extra_columns(frame: pd.DataFrame, period_column: str, product_column: str) -> list[str]:
    return [column for column in frame.columns if column not in META and column not in {period_column, product_column}]


def score_frame(
    frame: pd.DataFrame,
    keys: list[str],
    period_column: str,
    periods: list[str],
    baseline: list[str],
    after: list[str],
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    if not keys:
        return scored
    for key, rows in frame.groupby(keys, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        if any(blank(value) for value in key):
            continue
        label = "; ".join(f"{column} = {value}" for column, value in zip(keys, key))
        product = str(key[0])
        table = rows.groupby(period_column)[list(MEASURES)].sum().reindex(periods).fillna(0.0)
        produced = rows.groupby(period_column)["toodetud"].max().reindex(periods).fillna(0.0)
        table["toodetud"] = produced
        values = effects(table, baseline, after)
        base_rate = rate(table, baseline)
        last_rate = rate(table, [periods[-1]])
        if base_rate is None or last_rate is None:
            continue
        scored.append(
            {
                "loik": label,
                "toode": product,
                "ulekulu": values["ulekulu"],
                "baas_maar": base_rate,
                "viimane_maar": last_rate,
                "maar_muutus": last_rate - base_rate,
            }
        )
    return scored


def rate(frame: pd.DataFrame, periods: list[str]) -> float | None:
    produced = float(frame.loc[periods, "toodetud"].sum())
    if produced == 0:
        return None
    return float(frame.loc[periods, "tukke"].sum() / produced)


def baseline_rows(
    period: Path,
    profile: dict[str, Any],
    periods: list[str],
) -> list[dict[str, Any]]:
    period_column = str(profile["periood_veerg"])
    product_column = str(profile["toote_veerg"])
    rows: list[dict[str, Any]] = []
    main = pd.read_csv(period / "work" / "02_agregatsioonid" / "periood_toode.csv")
    files = [("toode", main, [product_column])]
    for name, frame in category_files(period):
        extras = extra_columns(frame, period_column, product_column)
        files.append((name, frame, [product_column, *extras]))
    for size in (1, 2, 3):
        if size >= len(periods):
            continue
        baseline = periods[:size]
        after = periods[size:]
        scored: list[dict[str, Any]] = []
        for _, frame, keys in files:
            scored.extend(score_frame(frame, keys, period_column, periods, baseline, after))
        rising = [item for item in scored if item["maar_muutus"] >= RATE_DELTA_MIN and item["ulekulu"] > 0]
        narrow = [item for item in rising if ";" in item["loik"]]
        rising.sort(key=lambda item: item["ulekulu"], reverse=True)
        narrow.sort(key=lambda item: item["ulekulu"], reverse=True)
        if not rising:
            continue
        top = narrow[0] if narrow else rising[0]
        rows.append(
            {
                "baas_kuude_arv": size,
                "baas": ", ".join(baseline),
                "toode": top["toode"],
                "loik": top["loik"],
                "lisakulu": round(top["ulekulu"]),
                "baas_maar": round(top["baas_maar"], 4),
                "viimane_maar": round(top["viimane_maar"], 4),
            }
        )
    return rows


def build(period: Path) -> int:
    profile = read_json(period / "work" / "01_profiil.json")
    outlier = read_json(period / "work" / "03_outlierid.json")
    if "euro_kokku" not in pd.read_csv(period / "work" / "02_agregatsioonid" / "periood_toode.csv", nrows=0).columns:
        raise RuntimeError("Euroveerud puuduvad. Koosoleku lahtivõtt vajab 01_hinnad.json ja aggregate.py uuesti.")
    period_column = str(profile["periood_veerg"])
    periods = [str(value) for value in profile["perioodid"]]
    base_count = baseline_size(len(periods))
    baseline = periods[:base_count]
    after = periods[base_count:]
    focus = segments(period, outlier)
    if not focus:
        raise RuntimeError("Eurode pingereas ei ole lõiku.")

    output = period / "work" / "05_koosolek"
    output.mkdir(parents=True, exist_ok=True)
    part_rows: list[dict[str, Any]] = []
    driver_rows: list[dict[str, Any]] = []
    month_rows: list[dict[str, Any]] = []
    month_notes: list[dict[str, Any]] = []
    stable_rows: list[dict[str, Any]] = []
    counter_rows: list[dict[str, Any]] = []

    for item in focus:
        table = monthly_frame(period, item, period_column, periods)
        values = effects(table, baseline, after)
        overrun = round(values["ulekulu"])
        parts = rounded_parts(
            overrun,
            {
                "mahakandmine": values["mahakandmine"],
                "umbertegemine": values["umbertegemine"],
                "kliendileid": values["kliendileid"],
            },
        )
        part_rows.append({"loik": item["loik"], "ulekulu": overrun, **parts})
        drivers = rounded_parts(
            overrun,
            {"maht": values["maht"], "maar": values["maar"], "segu": values["segu"]},
        )
        driver_rows.append({"loik": item["loik"], "ulekulu": overrun, **drivers})

        previous_euro: float | None = None
        previous_rate: float | None = None
        jumps: list[tuple[str, float]] = []
        costs: list[tuple[str, float]] = []
        for name in periods:
            row = table.loc[name]
            cost = float(row["euro_kokku"])
            current_rate = None if pd.isna(row["maar"]) else float(row["maar"])
            jump_euro = None if previous_euro is None else cost - previous_euro
            jump_rate = None if previous_rate is None or current_rate is None else current_rate - previous_rate
            month_rows.append(
                {
                    "loik": item["loik"],
                    "kuu": name,
                    "tukke": round(float(row["tukke"])),
                    "toodetud": round(float(row["toodetud"])),
                    "maar": None if current_rate is None else round(current_rate, 4),
                    "euro": round(cost),
                    "ulekulu_vs_baas": round(cost - float(table.loc[baseline, "euro_kokku"].sum()) / len(baseline)),
                    "hype_euro": None if jump_euro is None else round(jump_euro),
                    "hype_maar": None if jump_rate is None else round(jump_rate, 4),
                }
            )
            costs.append((name, cost))
            if jump_euro is not None:
                jumps.append((name, jump_euro))
            previous_euro = cost
            previous_rate = current_rate
        expensive = max(costs, key=lambda pair: pair[1])[0]
        biggest = max(jumps, key=lambda pair: pair[1])[0] if jumps else ""
        month_notes.append(
            {
                "loik": item["loik"],
                "kalleim_kuu": expensive,
                "suurim_hyppe_kuu": biggest,
                "sama_kuu": expensive == biggest,
            }
        )
        counter = overrun - round(values["kliendileid_parast"])
        counter_rows.append(
            {
                "loik": item["loik"],
                "kliendileid_parast": round(values["kliendileid_parast"]),
                "ulekulu": overrun,
                "ulekulu_kui_liinil": counter,
                "vahe": overrun - counter,
                "eeldus": ASSUMPTION,
            }
        )

    product_column = str(profile["toote_veerg"])
    focus_product = str(focus[0]["vordlus"].get(product_column, ""))
    for name, frame in category_files(period):
        extras = extra_columns(frame, period_column, product_column)
        if not extras or not focus_product:
            continue
        column = extras[0]
        subset = frame[frame[product_column].astype(str) == focus_product]
        for value, rows in subset.groupby(column, dropna=False):
            if blank(value):
                continue
            table = rows.groupby(period_column)[["tukke"]].sum().reindex(periods).fillna(0.0)
            produced = rows.groupby(period_column)["toodetud"].max().reindex(periods).fillna(0.0)
            table = table.assign(toodetud=produced)
            base_rate = rate(table, baseline)
            last_rate = rate(table, [periods[-1]])
            base_pieces = float(table.loc[baseline, "tukke"].sum())
            after_pieces = float(table.loc[after, "tukke"].sum())
            if base_pieces == 0 and after_pieces > 0:
                status = "uus"
                delta = None
            elif base_rate is None or last_rate is None:
                continue
            else:
                delta = last_rate - base_rate
                status = "muutus" if delta >= RATE_DELTA_MIN else "ei muutunud"
            stable_rows.append(
                {
                    "toode": focus_product,
                    "veerg": column,
                    "vaartus": value,
                    "baas_maar": None if base_rate is None else round(base_rate, 4),
                    "viimane_maar": None if last_rate is None else round(last_rate, 4),
                    "maar_muutus": None if delta is None else round(delta, 4),
                    "staatus": status,
                    "fail": f"work/02_agregatsioonid/{name}",
                }
            )

    bases = baseline_rows(period, profile, periods)
    write_table(output / "ulekulu_osad.csv", part_rows)
    write_table(output / "maht_vs_maar.csv", driver_rows)
    write_table(output / "kuud.csv", month_rows)
    write_table(output / "kuude_vordlus.csv", month_notes)
    write_table(output / "muutumatu.csv", stable_rows)
    write_table(output / "kliendileid_liinil.csv", counter_rows)
    write_table(output / "baas.csv", bases)

    same_cut = len({row["loik"] for row in bases}) <= 1
    same_product = len({row["toode"] for row in bases}) <= 1
    lines = [
        "# Koosoleku lahtivõtt",
        "",
        f"Vaikimisi baas: {', '.join(baseline)}.",
        "Ülekulu = baasijärgne kulu − baasi keskmine kuu × baasijärgsete kuude arv.",
        "Maht on see osa, mis tuleb suuremast toodangust vana määra ja vana tükihinnaga.",
        "Määr on see osa, mis tuleb kõrgemast praakmäärast vana tükihinnaga.",
        "Segu on see osa, mis tuleb sellest, et üks defektne tükk maksab teisiti kui baasis.",
        "",
        "## Failid",
        "",
        "- `ulekulu_osad.csv` — mahakandmine, ümbertegemine, kliendileid.",
        "- `maht_vs_maar.csv` — maht, määr ja segu.",
        "- `kuud.csv` — iga kuu tükid, määr ja eurod.",
        "- `kuude_vordlus.csv` — kõige kallim kuu ja suurim hüpe.",
        "- `muutumatu.csv` — mis fookustootel ei liikunud.",
        "- `kliendileid_liinil.csv` — sama defekt, kui see oleks jäänud liinile.",
        "- `baas.csv` — esimene kuu, kaks kuud ja kolm kuud.",
        "",
        "## Kuu",
        "",
    ]
    for note in month_notes:
        if note["sama_kuu"]:
            lines.append(f"- {note['loik']}: kallim kuu ja suurim hüpe on {note['kalleim_kuu']}.")
        else:
            lines.append(
                f"- {note['loik']}: kallim kuu on {note['kalleim_kuu']}, "
                f"suurim hüpe on {note['suurim_hyppe_kuu']}."
            )
    lines.extend(["", "## Baas", ""])
    if bases and same_cut:
        lines.append(f"Leid jääb samaks: {bases[0]['loik']}.")
    elif bases and same_product:
        lines.append(f"Toode jääb samaks: {bases[0]['toode']}. Kitsam lõige vahetub.")
        for row in bases:
            unit = "kuu" if row["baas_kuude_arv"] == 1 else "kuud"
            lines.append(f"- {row['baas_kuude_arv']} {unit}: {row['loik']}, {euro(row['lisakulu'])}.")
    elif bases:
        lines.append("Toode vahetub, kui baasi pikkus muutub.")
        for row in bases:
            unit = "kuu" if row["baas_kuude_arv"] == 1 else "kuud"
            lines.append(f"- {row['baas_kuude_arv']} {unit}: {row['loik']}, {euro(row['lisakulu'])}.")
    lines.append("")
    (output / "index.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Koosolek: {output.relative_to(period.parent.parent)}")
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: brief.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
