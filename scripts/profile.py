#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import (
    MONTH_INDEX,
    ROOT,
    find_input_workbook,
    is_rate_series,
    period_path,
    slug,
    sort_periods,
    write_json,
)


def category_columns(df: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    row_count = max(len(df), 1)
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            continue
        unique = int(df[column].nunique(dropna=True))
        if unique <= 1 or unique >= row_count * 0.8:
            continue
        columns.append(str(column))
    return columns


def is_text_sheet(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    unnamed = sum(str(column).startswith("Unnamed") for column in df.columns)
    numeric = sum(bool(pd.api.types.is_numeric_dtype(df[column])) for column in df.columns)
    null_fraction = float(df.isna().to_numpy().mean())
    return unnamed > 0 or (numeric == 0 and null_fraction > 0.2)


def find_id_column(df: pd.DataFrame) -> str | None:
    best_score = 0.0
    best_column: str | None = None
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            continue
        values = df[column].dropna()
        if len(values) < 5:
            continue
        uniqueness = float(values.nunique() / len(values))
        if uniqueness < 0.9:
            continue
        score = uniqueness
        if str(column).strip().lower() in {"id", "kood", "nr", "number"}:
            score += 0.1
        if score > best_score:
            best_score = score
            best_column = str(column)
    return best_column


def find_date_column(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            return str(column)
    for column in df.columns:
        name = str(column).strip().lower()
        if "kuup" not in name and name not in {"date", "datetime"}:
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        if float(parsed.notna().mean()) > 0.8:
            return str(column)
    return None


def average_run(series: pd.Series) -> float:
    values = series.tolist()
    if not values:
        return 0.0
    runs = 1
    for previous, current in zip(values, values[1:]):
        if current != previous:
            runs += 1
    return len(values) / runs


def find_period_column(monthly: pd.DataFrame, shared: list[str]) -> str:
    for column in shared:
        values = [str(value).strip().lower() for value in monthly[column].dropna().unique()]
        if values and all(value in MONTH_INDEX for value in values):
            return column
    return max(shared, key=lambda column: average_run(monthly[column]))


def column_row(series: pd.Series) -> str:
    missing = int(series.isna().sum())
    unique = int(series.nunique(dropna=True))
    if pd.api.types.is_numeric_dtype(series) and series.notna().any():
        span = f"{series.min()} … {series.max()}"
    elif pd.api.types.is_datetime64_any_dtype(series) and series.notna().any():
        span = f"{series.min():%Y-%m-%d} … {series.max():%Y-%m-%d}"
    else:
        samples = [str(value) for value in series.dropna().unique()[:6]]
        span = ", ".join(samples)
    return f"| {series.name} | {series.dtype} | {missing} | {unique} | {span} |"


def sheet_table(df: pd.DataFrame) -> str:
    header = "| Veerg | Tüüp | Tühje | Unikaalseid | Vahemik või näited |"
    rule = "| --- | --- | --- | --- | --- |"
    rows = [column_row(df[column]) for column in df.columns]
    return "\n".join([header, rule, *rows])


def text_lines(path: Path, sheet: str) -> list[str]:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
    lines: list[str] = []
    for _, row in raw.iterrows():
        cells = ["" if pd.isna(value) else str(value).replace("\n", " ").strip() for value in row.tolist()]
        kept = [cell for cell in cells if cell]
        if kept:
            lines.append(" | ".join(kept))
    return lines


def stringify_dates(df: pd.DataFrame) -> pd.DataFrame:
    formatted: dict[str, pd.Series] = {}
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            formatted[str(column)] = df[column].dt.strftime("%Y-%m-%d")
    if not formatted:
        return df
    return df.assign(**formatted)


def match_counts(
    register: pd.DataFrame,
    monthly: pd.DataFrame,
    shared: list[str],
) -> dict[str, Any]:
    register_numbers = [
        str(column)
        for column in register.columns
        if pd.api.types.is_numeric_dtype(register[column]) and not is_rate_series(register[column])
    ]
    monthly_numbers = [
        str(column)
        for column in monthly.columns
        if pd.api.types.is_numeric_dtype(monthly[column]) and not is_rate_series(monthly[column])
    ]
    best: dict[str, Any] | None = None
    for register_column in register_numbers:
        grouped_register = register.groupby(shared, dropna=False)[register_column].sum()
        for monthly_column in monthly_numbers:
            grouped_monthly = monthly.groupby(shared, dropna=False)[monthly_column].sum()
            compared = pd.concat(
                [grouped_register.rename("register"), grouped_monthly.rename("kokkuvote")],
                axis=1,
            ).fillna(0)
            register_total = float(compared["register"].sum())
            monthly_total = float(compared["kokkuvote"].sum())
            relative = abs(register_total - monthly_total) / monthly_total if monthly_total else 1.0
            if best is None or relative < float(best["suhe"]):
                best = {
                    "tukid_veerg": register_column,
                    "praak_veerg": monthly_column,
                    "register_kokku": register_total,
                    "kokkuvote_kokku": monthly_total,
                    "suhe": relative,
                    "vordlus": compared,
                }
    if best is None:
        raise RuntimeError("Ei leidnud arvulisi veerge, mida omavahel võrrelda.")
    return best


def render(profile: dict[str, Any], sheets: dict[str, pd.DataFrame], lines: list[str]) -> str:
    parts = [
        "# Kirjeldus",
        "",
        f"Fail: `{profile['fail']}`.",
        "",
        f"Register: `{profile['register']}`. Kuukokkuvõte: `{profile['kuukokkuvote']}`.",
        "",
        (
            f"Välja jäetud read, millel tunnus ja kuupäev on tühjad: "
            f"{profile['valja_jaetud_read']} (tükke {profile['valja_jaetud_tukid']:g})."
        ),
        "",
        (
            f"Pärast puhastust on registris {profile['register_tukid']:g} tükki "
            f"ja kuukokkuvõttes {profile['kokkuvote_tukid']:g} tükki. "
            f"Suhteline vahe: {profile['suhteline_vahe'] * 100:.2f}%."
        ),
        "",
        "Klappimine: jah." if profile["klapib"] else "Klappimine: ei. Analüüs peatub.",
        "",
        (
            f"Määraveerg `{profile['maar_veerg']}` on suhe (0–1), mitte protsent."
            if profile["maar_on_suhe"]
            else "Eraldi määraveergu, mille väärtused on vahemikus 0–1, ei leitud. Määr arvutatakse tükkidest ja toodetud kogusest."
        ),
        "",
    ]
    if profile["duplikaatseid_tunnuseid"]:
        parts.append(f"Korduvaid tunnuseid: {profile['duplikaatseid_tunnuseid']}.")
        parts.append("")
    for name, frame in sheets.items():
        parts.extend([f"## {name}", "", f"Ridu: {len(frame)}.", "", sheet_table(frame), ""])
    if lines:
        parts.extend(["## Tekstileht", "", f"`{profile['tekstileht']}`", ""])
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts)


def build(period: Path) -> int:
    workbook = find_input_workbook(period)
    excel = pd.ExcelFile(workbook)
    raw_sheets = {
        name: pd.read_excel(workbook, sheet_name=name) for name in excel.sheet_names
    }
    text_names = [name for name, frame in raw_sheets.items() if is_text_sheet(frame)]
    fact_sheets = {
        name: frame for name, frame in raw_sheets.items() if name not in text_names
    }
    register_name = ""
    for name, frame in fact_sheets.items():
        if find_id_column(frame) and find_date_column(frame):
            register_name = name
            break
    if not register_name:
        raise RuntimeError("Ei leidnud registrilehte, millel on tunnus ja kuupäev.")
    other_names = [name for name in fact_sheets if name != register_name]
    if len(other_names) != 1:
        raise RuntimeError("Ei leidnud ühte kuukokkuvõtte lehte.")
    monthly_name = other_names[0]
    register = fact_sheets[register_name]
    monthly = fact_sheets[monthly_name]
    id_column = find_id_column(register)
    date_column = find_date_column(register)
    if id_column is None or date_column is None:
        raise RuntimeError("Registril puudub tunnus või kuupäev.")

    empty = register[id_column].isna() & register[date_column].isna()
    dropped = register.loc[empty].copy()
    kept = register.loc[~empty].copy()
    shared = [
        column
        for column in category_columns(monthly)
        if column in kept.columns and column not in {id_column, date_column}
    ]
    if len(shared) < 2:
        raise RuntimeError("Registril ja kuukokkuvõttel ei ole kahte ühist rühma, mille järgi klappida.")

    matched = match_counts(kept, monthly, shared)
    pieces_column = str(matched["tukid_veerg"])
    scrap_column = str(matched["praak_veerg"])
    dropped_pieces = float(pd.to_numeric(dropped[pieces_column], errors="coerce").fillna(0).sum()) if len(dropped) else 0.0
    period_column = find_period_column(monthly, shared)
    other_shared = [column for column in shared if column != period_column]
    product_column = other_shared[0] if len(other_shared) == 1 else ""
    number_columns = [
        str(column)
        for column in monthly.columns
        if pd.api.types.is_numeric_dtype(monthly[column]) and str(column) != scrap_column and not is_rate_series(monthly[column])
    ]
    produced_column = max(number_columns, key=lambda column: float(monthly[column].sum())) if number_columns else ""
    rate_columns = [str(column) for column in monthly.columns if is_rate_series(monthly[column])]
    rate_column = rate_columns[0] if rate_columns else ""
    rate_is_ratio = bool(rate_column)
    compared: pd.DataFrame = matched["vordlus"]
    both_zero = compared["register"].eq(0) & compared["kokkuvote"].eq(0)
    group_relative = (compared["register"] - compared["kokkuvote"]).abs() / compared["kokkuvote"].where(
        compared["kokkuvote"] != 0, 1
    )
    groups_match = bool((both_zero | group_relative.le(0.01)).all())
    totals_match = float(matched["suhe"]) <= 0.01
    agrees = totals_match and groups_match
    periods = sort_periods(monthly[period_column].astype(str).tolist())
    categories = [
        column
        for column in category_columns(kept)
        if column not in {id_column, date_column, period_column, product_column}
    ]
    duplicate_ids = int(kept[id_column].duplicated().sum())
    text_name = text_names[0] if text_names else ""
    guide = text_lines(workbook, text_name) if text_name else []

    table_dir = period / "work" / "01_tabelid"
    table_dir.mkdir(parents=True, exist_ok=True)
    register_file = f"{slug(register_name)}.csv"
    monthly_file = f"{slug(monthly_name)}.csv"
    stringify_dates(kept).to_csv(table_dir / register_file, index=False)
    stringify_dates(monthly).to_csv(table_dir / monthly_file, index=False)
    compared.reset_index().to_csv(table_dir / "klappimine.csv", index=False)

    profile: dict[str, Any] = {
        "fail": str(workbook.relative_to(ROOT)),
        "register": register_name,
        "kuukokkuvote": monthly_name,
        "tekstileht": text_name,
        "register_fail": f"work/01_tabelid/{register_file}",
        "kuukokkuvote_fail": f"work/01_tabelid/{monthly_file}",
        "id_veerg": id_column,
        "kuupaev_veerg": date_column,
        "tukid_veerg": pieces_column,
        "periood_veerg": period_column,
        "toote_veerg": product_column,
        "toodetud_veerg": produced_column,
        "praak_veerg": scrap_column,
        "maar_veerg": rate_column,
        "maar_on_suhe": rate_is_ratio,
        "kategooriad": categories,
        "perioodid": periods,
        "valja_jaetud_read": int(len(dropped)),
        "valja_jaetud_tukid": dropped_pieces,
        "register_tukid": float(matched["register_kokku"]),
        "kokkuvote_tukid": float(matched["kokkuvote_kokku"]),
        "suhteline_vahe": float(matched["suhe"]),
        "klapib": agrees,
        "duplikaatseid_tunnuseid": duplicate_ids,
    }
    write_json(period / "work" / "01_profiil.json", profile)
    description = render(profile, fact_sheets, guide)
    (period / "work" / "01_kirjeldus.md").write_text(description, encoding="utf-8")
    print(f"Kirjeldus: {period.relative_to(ROOT)}/work/01_kirjeldus.md")
    print(
        f"Välja jäetud read: {profile['valja_jaetud_read']}, "
        f"tükke {profile['valja_jaetud_tukid']:g}"
    )
    print(
        f"Klappimine: {profile['register_tukid']:g} vs {profile['kokkuvote_tukid']:g}, "
        f"vahe {profile['suhteline_vahe'] * 100:.2f}%"
    )
    print(f"Määr on suhe: {'jah' if rate_is_ratio else 'ei'}")
    if not agrees:
        print("Register ja kuukokkuvõte ei klapi. Sõnumit ei kirjutata.", file=sys.stderr)
        return 2
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: profile.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
