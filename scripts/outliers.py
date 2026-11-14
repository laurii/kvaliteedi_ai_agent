#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import baseline_size, blank, euro, pct, period_path, read_json, write_json

RATE_DELTA_MIN = 0.005
MATERIAL_SHARE = 0.20
TOP_N = 5
CARRIER_SHARE = 0.65
MEASURES = [
    "tukke",
    "juhtumeid",
    "euro_mahakandmine",
    "euro_umbertegemine",
    "euro_kliendileid",
    "euro_kokku",
]
META = {
    "tukke",
    "juhtumeid",
    "toodetud",
    "maar",
    *MEASURES,
}


def number(value: object) -> float | None:
    """Tühi või NaN ei tohi jsonis muutuda määraks 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def produced_lookup(frame: pd.DataFrame, period_column: str, product_column: str) -> dict[tuple[str, str], float]:
    """Defekti lõik kasutab toote toodangut, mitte enda ridade toodangut."""
    lookup: dict[tuple[str, str], float] = {}
    for record in frame.to_dict(orient="records"):
        lookup[(str(record[period_column]), str(record[product_column]))] = float(record["toodetud"])
    return lookup


def expand(
    rows: pd.DataFrame,
    period_column: str,
    periods: list[str],
    product: str,
    produced: dict[tuple[str, str], float],
    measures: list[str],
) -> pd.DataFrame:
    """Puuduv kuu on 0, muidu uus väärtus kaoks kuude reast."""
    current = rows.groupby(period_column, dropna=False)[measures].sum()
    current = current.reindex(index=periods, columns=measures).fillna(0.0)
    produced_values = [produced.get((period, product), 0.0) for period in periods]
    return current.assign(toodetud=produced_values)


def rate_of(frame: pd.DataFrame, periods: list[str]) -> float | None:
    """Määr on tükid jagatud toodanguga. Nulltoodangul määra ei ole."""
    part = frame.loc[periods]
    produced = float(part["toodetud"].sum())
    if produced == 0:
        return None
    return float(part["tukke"].sum() / produced)


def extra_of(frame: pd.DataFrame, baseline: list[str], after: list[str], column: str) -> tuple[float, float, float]:
    """Ülekulu on baasijärgne summa miinus baasi kuutempo korda baasijärgsed kuud."""
    base = float(frame.loc[baseline, column].sum())
    after_sum = float(frame.loc[after, column].sum())
    per_month = base / len(baseline)
    return after_sum - per_month * len(after), per_month, after_sum


def rounded_gap(after_sum: float, per_month: float, months: int) -> tuple[int, int, int]:
    """Juhatuse valem kasutab ümardatud osi, et lahutamine annaks sama numbri."""
    after_rounded = round(after_sum)
    month_rounded = round(per_month)
    return after_rounded - month_rounded * months, after_rounded, month_rounded


def segment_pairs(frame: pd.DataFrame, product_column: str, extra_columns: list[str]):
    """Üks lõik on toode, või toode ja üks kategooria väärtus."""
    keys = [product_column, *extra_columns]
    grouped = frame.groupby(keys, dropna=False)
    for key, rows in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        values = {product_column: key[0]}
        for column, value in zip(extra_columns, key[1:]):
            values[column] = value
        yield values, rows


def build_record(
    values: dict[str, object],
    expanded: pd.DataFrame,
    baseline: list[str],
    after: list[str],
    last: str,
    source: str,
    has_euro: bool,
) -> dict[str, Any]:
    """Ühe lõigu määrad, tükid ja eurod kujul, mille sõnum kopeerib."""
    base_rate = rate_of(expanded, baseline)
    last_rate = rate_of(expanded, [last])
    piece_extra, _, _ = extra_of(expanded, baseline, after, "tukke")
    record: dict[str, Any] = {
        "loik": "; ".join(f"{key} = {value}" for key, value in values.items()),
        "vordlus": {key: None if blank(value) else str(value) for key, value in values.items()},
        "baas_maar": number(base_rate),
        "viimane_maar": number(last_rate),
        "maar_muutus": None if base_rate is None or last_rate is None else last_rate - base_rate,
        "lisatukid": piece_extra,
        "baas_tukke": float(expanded.loc[baseline, "tukke"].sum()),
        "parast_tukke": float(expanded.loc[after, "tukke"].sum()),
        "tukke_kokku": float(expanded["tukke"].sum()),
        "kuude_tukid": {period: int(expanded.loc[period, "tukke"]) for period in expanded.index},
        "fail": source,
    }
    if has_euro:
        euro_extra, per_month, after_sum = extra_of(expanded, baseline, after, "euro_kokku")
        rounded_extra, after_rounded, month_rounded = rounded_gap(after_sum, per_month, len(after))
        record["lisakulu"] = euro_extra
        record["lisakulu_ymardatud"] = rounded_extra
        record["baas_euro_kuus"] = per_month
        record["baas_euro_kuus_ymardatud"] = month_rounded
        record["parast_euro"] = after_sum
        record["parast_euro_ymardatud"] = after_rounded
        record["parast_kuude_arv"] = len(after)
        record["osad"] = {}
        for column, label in (
            ("euro_mahakandmine", "mahakandmine"),
            ("euro_umbertegemine", "umbertegemine"),
            ("euro_kliendileid", "kliendileid"),
        ):
            part_extra, part_month, part_after = extra_of(expanded, baseline, after, column)
            record["osad"][label] = {
                "lisakulu_ymardatud": rounded_gap(part_after, part_month, len(after))[0],
                "baas_euro_kuus_ymardatud": round(part_month),
                "parast_euro_ymardatud": round(part_after),
            }
    return record


def carriers(record: dict[str, Any], children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kandja on väärtus, millel on suurem osa baasijärgsetest tükkidest."""
    product_values = record["vordlus"]
    after_pieces = float(record["parast_tukke"])
    if after_pieces <= 0:
        return []
    found: list[dict[str, Any]] = []
    columns = {column for child in children for column in child["vordlus"] if column not in product_values}
    for column in sorted(columns):
        best: dict[str, Any] | None = None
        best_pieces = -1.0
        for child in children:
            if column not in child["vordlus"]:
                continue
            if any(child["vordlus"].get(key) != value for key, value in product_values.items()):
                continue
            if blank(child["vordlus"].get(column)):
                continue
            pieces = float(child["parast_tukke"])
            if pieces > best_pieces:
                best_pieces = pieces
                best = child
        if best is None:
            continue
        share = best_pieces / after_pieces
        if share < CARRIER_SHARE:
            continue
        found.append(
            {
                "veerg": column,
                "vaartus": best["vordlus"][column],
                "parast_tukke": best_pieces,
                "osakaal": share,
            }
        )
    return found


def material(items: list[dict[str, Any]], field: str, total: float) -> list[dict[str, Any]]:
    """Pingerisse jääb viis esimest või lõik, mis on vähemalt viiendik toote tõusust."""
    ranked = sorted((item for item in items if float(item[field]) > 0), key=lambda item: float(item[field]), reverse=True)
    kept: list[dict[str, Any]] = []
    for index, item in enumerate(ranked, start=1):
        share = float(item[field]) / total if total else 0.0
        if index <= TOP_N or share >= MATERIAL_SHARE:
            copied = dict(item)
            copied["osakaal_muutusest"] = share
            kept.append(copied)
    return kept


def monthly_text(pieces: dict[str, int]) -> str:
    """Kuude rida, mida saab sõnumis ette lugeda."""
    return ", ".join(f"{period} {count}" for period, count in pieces.items())


def section(title: str, items: list[dict[str, Any]], money: bool) -> list[str]:
    """Üks pingerida. Eurovalem on ainult eurode pingereas."""
    lines = [f"## {title}", ""]
    if not items:
        lines.extend(["Ühtegi lõiku ei tõusnud esile.", ""])
        return lines
    for index, item in enumerate(items, start=1):
        lines.append(f"### {index}. {item['loik']}")
        lines.append(
            f"- Määr: {pct(item['baas_maar'])} → {pct(item['viimane_maar'])} "
            f"(muutus {pct(item['maar_muutus'])})."
        )
        lines.append(f"- Lisatükid baasi tempo vastu: {item['lisatukid']:.0f}.")
        if money:
            lines.append(
                f"- Lisakulu: {euro(item['lisakulu_ymardatud'])} = "
                f"{euro(item['parast_euro_ymardatud'])} − "
                f"{euro(item['baas_euro_kuus_ymardatud'])} × {item['parast_kuude_arv']}."
            )
            parts = item["osad"]
            lines.append(
                "- Sellest mahakandmine "
                f"{euro(parts['mahakandmine']['lisakulu_ymardatud'])}, ümbertegemine "
                f"{euro(parts['umbertegemine']['lisakulu_ymardatud'])}, kliendileid "
                f"{euro(parts['kliendileid']['lisakulu_ymardatud'])}."
            )
        lines.append(f"- Tükid kuude kaupa: {monthly_text(item['kuude_tukid'])}.")
        if item.get("kandjad"):
            rendered = ", ".join(
                f"{carrier['veerg']} = {carrier['vaartus']} ({carrier['osakaal'] * 100:.0f}% baasijärgsetest tükkidest)"
                for carrier in item["kandjad"]
            )
            lines.append(f"- Kasvu kannab: {rendered}.")
        lines.append(f"- Allikas: `{item['fail']}`, filter {item['loik']}.")
        lines.append("")
    return lines


def render(result: dict[str, Any]) -> str:
    """Markdown, mida agent loeb. Suur stabiilne maht ei ole leid."""
    baseline = ", ".join(result["baas"])
    lines = [
        "# Erindid",
        "",
        f"Baas: {baseline}. Viimane periood: {result['viimane']}.",
        "Lisakulu = baasijärgne kulu − baasi keskmine kuu × baasijärgsete kuude arv.",
        "Eraldi on tükkide ja eurode pingerida. Stabiilne suur lõik ei ole leid.",
        "",
    ]
    lines.extend(section("Eurode pingerida", result["euro_pingerida"], True))
    lines.extend(section("Tükkide pingerida", result["tukkide_pingerida"], False))
    lines.extend(["## Stabiilsed suured lõigud", "", "Need paistavad mahu järgi, aga määr baasi suhtes ei muutu. Sõnumisse ei lähe.", ""])
    if not result["stabiilsed"]:
        lines.append("Ei leidnud.")
        lines.append("")
    for item in result["stabiilsed"]:
        lines.append(
            f"- {item['loik']}: {item['tukke_kokku']:.0f} tükki, määr {pct(item['baas_maar'])} → {pct(item['viimane_maar'])}. "
            f"Allikas: `{item['fail']}`."
        )
    lines.extend(["", "## Uued väärtused", "", "Baasis tükke ei olnud. Uus väärtus ei ole iseenesest põhjus.", ""])
    if not result["uued_vaartused"]:
        lines.append("Ei leidnud.")
    for item in result["uued_vaartused"]:
        lines.append(
            f"- {item['loik']}: esimene kuu {item['esimene_periood']}, tükid {monthly_text(item['kuude_tukid'])}."
        )
    lines.append("")
    return "\n".join(lines)


def build(period: Path) -> int:
    """Eraldab tõusu, stabiilse mahu ja uue väärtuse. Nullbaas ei lähe rahapingesse."""
    profile = read_json(period / "work" / "01_profiil.json")
    folder = period / "work" / "02_agregatsioonid"
    main_path = folder / "periood_toode.csv"
    if not main_path.is_file():
        raise FileNotFoundError("Puudub work/02_agregatsioonid/periood_toode.csv. Enne käivita aggregate.py.")

    period_column = str(profile["periood_veerg"])
    product_column = str(profile["toote_veerg"])
    periods = [str(value) for value in profile["perioodid"]]
    base_count = baseline_size(len(periods))
    if base_count == 0:
        raise RuntimeError("Perioode on liiga vähe, et baasi võtta.")
    baseline = periods[:base_count]
    after = periods[base_count:]
    last = periods[-1]
    main = pd.read_csv(main_path)
    produced = produced_lookup(main, period_column, product_column)
    has_euro = "euro_kokku" in main.columns
    measures = [column for column in MEASURES if column in main.columns or column in {"tukke", "juhtumeid"}]

    frames = [("work/02_agregatsioonid/periood_toode.csv", main)]
    for path in sorted(folder.glob("periood_toode__*.csv")):
        frames.append((f"work/02_agregatsioonid/{path.name}", pd.read_csv(path)))

    records: list[dict[str, Any]] = []
    new_values: list[dict[str, Any]] = []
    for source, frame in frames:
        extra_columns = [
            column
            for column in frame.columns
            if column not in META and column not in {period_column, product_column}
        ]
        for values, rows in segment_pairs(frame, product_column, extra_columns):
            if any(blank(value) for value in values.values()):
                continue
            product = str(values[product_column])
            expanded = expand(rows, period_column, periods, product, produced, measures)
            record = build_record(values, expanded, baseline, after, last, source, has_euro)
            if record["baas_tukke"] == 0 and record["parast_tukke"] > 0:
                first = next(period for period in periods if record["kuude_tukid"][period] > 0)
                record["esimene_periood"] = first
                new_values.append(record)
                continue
            records.append(record)

    changed = [
        record
        for record in records
        if record["maar_muutus"] is not None and record["maar_muutus"] >= RATE_DELTA_MIN
    ]
    product_changed = [record for record in changed if set(record["vordlus"]) == {product_column}]
    piece_total = sum(record["lisatukid"] for record in product_changed if record["lisatukid"] > 0)
    piece_ranked = material(changed, "lisatukid", piece_total)
    euro_ranked: list[dict[str, Any]] = []
    if has_euro:
        euro_total = sum(record["lisakulu"] for record in product_changed if record["lisakulu"] > 0)
        euro_ranked = material(changed, "lisakulu", euro_total)

    children = [record for record in records + new_values if set(record["vordlus"]) != {product_column}]
    for record in euro_ranked:
        if set(record["vordlus"]) == {product_column}:
            record["kandjad"] = carriers(record, children)

    stable = [
        record
        for record in records
        if record["maar_muutus"] is not None and abs(record["maar_muutus"]) < RATE_DELTA_MIN and record["baas_tukke"] > 0
    ]
    stable = sorted(stable, key=lambda record: record["tukke_kokku"], reverse=True)[:TOP_N]
    new_values = [
        record
        for record in sorted(new_values, key=lambda record: record["parast_tukke"], reverse=True)
        if record["parast_tukke"] >= 10
    ][:8]

    result = {
        "baas": baseline,
        "viimane": last,
        "parast_baasi": after,
        "euro_pingerida": euro_ranked,
        "tukkide_pingerida": piece_ranked,
        "stabiilsed": [
            {
                "loik": record["loik"],
                "tukke_kokku": record["tukke_kokku"],
                "baas_maar": record["baas_maar"],
                "viimane_maar": record["viimane_maar"],
                "fail": record["fail"],
            }
            for record in stable
        ],
        "uued_vaartused": [
            {
                "loik": record["loik"],
                "esimene_periood": record["esimene_periood"],
                "kuude_tukid": record["kuude_tukid"],
                "fail": record["fail"],
            }
            for record in new_values
        ],
    }
    write_json(period / "work" / "03_outlierid.json", result)
    (period / "work" / "03_outlierid.md").write_text(render(result), encoding="utf-8")
    print(f"Erindid: euro {len(euro_ranked)}, tükid {len(piece_ranked)}, stabiilsed {len(stable)}, uued {len(result['uued_vaartused'])}")
    print(f"Baas: {', '.join(baseline)}")
    return 0


def main() -> None:
    """Käsurea sisend on perioodi kausta nimi."""
    if len(sys.argv) != 2:
        print("Kasutus: outliers.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
