#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from common import period_path, read_json, slug


def load_prices(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    prices = read_json(path)
    required = [
        "toote_veerg",
        "umber_veerg",
        "umber_jah",
        "umber_ei",
        "kliendileiu_veerg",
        "kliendileiu_vaartus",
        "tunnihind",
        "kliendijuhtumi_kulu",
        "tooted",
    ]
    missing = [key for key in required if prices.get(key) in (None, "", {})]
    if missing:
        raise RuntimeError("01_hinnad.json puuduvad väljad: " + ", ".join(missing))
    return prices


def add_costs(register: pd.DataFrame, prices: dict[str, Any], pieces_column: str) -> pd.DataFrame:
    products: dict[str, dict[str, Any]] = prices["tooted"]
    product_column = str(prices["toote_veerg"])
    names = register[product_column].astype(str)
    unknown = sorted(set(names) - set(products))
    if unknown:
        raise RuntimeError("Hinnakirjas puuduvad tooted: " + ", ".join(unknown))

    rework_flag = register[str(prices["umber_veerg"])].astype(str).str.strip()
    pieces = pd.to_numeric(register[pieces_column], errors="coerce").fillna(0.0)
    unit_cost = names.map({name: float(info["omahind"]) for name, info in products.items()})
    minutes = names.map(
        {name: float(info["umbertegemise_minutid"]) for name, info in products.items()}
    )
    if unit_cost.isna().any() or minutes.isna().any():
        raise RuntimeError("Mõnel tootel puudub omahind või ümbertegemise minutid.")
    hourly = float(prices["tunnihind"])
    is_rework = rework_flag.eq(str(prices["umber_jah"]).strip())
    is_scrap = rework_flag.eq(str(prices["umber_ei"]).strip())
    detected = (
        register[str(prices["kliendileiu_veerg"])]
        .astype(str)
        .str.strip()
        .eq(str(prices["kliendileiu_vaartus"]).strip())
    )
    scrap = pieces * unit_cost * is_scrap.astype(float)
    rework = pieces * (minutes / 60.0) * hourly * is_rework.astype(float)
    customer = detected.astype(float) * float(prices["kliendijuhtumi_kulu"])
    return register.assign(
        euro_mahakandmine=scrap,
        euro_umbertegemine=rework,
        euro_kliendileid=customer,
        euro_kokku=scrap + rework + customer,
    )


def aggregate_keys(
    register: pd.DataFrame,
    keys: list[str],
    pieces_column: str,
    has_cost: bool,
) -> pd.DataFrame:
    named: dict[str, tuple[str, str]] = {"tukke": (pieces_column, "sum"), "juhtumeid": (pieces_column, "size")}
    if has_cost:
        for column in ("euro_mahakandmine", "euro_umbertegemine", "euro_kliendileid", "euro_kokku"):
            named[column] = (column, "sum")
    grouped = register.groupby(keys, dropna=False).agg(**named).reset_index()
    return grouped


def attach_produced(
    grouped: pd.DataFrame,
    monthly: pd.DataFrame,
    period_column: str,
    product_column: str,
    produced_column: str,
) -> pd.DataFrame:
    produced = monthly[[period_column, product_column, produced_column]].rename(
        columns={produced_column: "toodetud"}
    )
    merged = grouped.merge(produced, on=[period_column, product_column], how="left")
    return merged.assign(maar=merged["tukke"] / merged["toodetud"])


def sort_output(frame: pd.DataFrame, period_column: str, periods: list[str]) -> pd.DataFrame:
    order = {period: index for index, period in enumerate(periods)}
    other = [column for column in frame.columns if column != period_column]
    ordered = frame.assign(_order=frame[period_column].map(order))
    return ordered.sort_values(["_order", *other[:2]]).drop(columns="_order")


def formula(prices: dict[str, Any] | None) -> str:
    if prices is None:
        return "Euroveerge ei lisatud, sest work/01_hinnad.json puudub."
    return (
        f"euro_mahakandmine = tükid, kus {prices['umber_veerg']} = {prices['umber_ei']}, × omahind. "
        f"euro_umbertegemine = tükid, kus {prices['umber_veerg']} = {prices['umber_jah']}, "
        f"× ümbertegemise minutid / 60 × tunnihind {prices['tunnihind']}. "
        f"euro_kliendileid = juhtumite arv, kus {prices['kliendileiu_veerg']} = {prices['kliendileiu_vaartus']}, "
        f"× {prices['kliendijuhtumi_kulu']}. "
        "Määr = tükid / toodetud ja on suhe, mitte protsent."
    )


def build(period: Path) -> int:
    profile_path = period / "work" / "01_profiil.json"
    if not profile_path.is_file():
        raise FileNotFoundError("Puudub work/01_profiil.json. Enne käivita profile.py.")
    profile = read_json(profile_path)
    if not profile.get("klapib"):
        raise RuntimeError("Register ja kuukokkuvõte ei klapi. Agregaate ei tehta.")

    register = pd.read_csv(period / str(profile["register_fail"]))
    monthly = pd.read_csv(period / str(profile["kuukokkuvote_fail"]))
    prices = load_prices(period / "work" / "01_hinnad.json")
    pieces_column = str(profile["tukid_veerg"])
    period_column = str(profile["periood_veerg"])
    product_column = str(profile["toote_veerg"])
    produced_column = str(profile["toodetud_veerg"])
    if not product_column or not produced_column:
        raise RuntimeError("Profiilist puudub toote või toodetud koguse veerg.")

    if prices is not None:
        register = add_costs(register, prices, pieces_column)
    filled = {column: register[column].fillna("(tühi)") for column in profile["kategooriad"]}
    register = register.assign(**filled)

    output_dir = period / "work" / "02_agregatsioonid"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*"):
        if old.is_file():
            old.unlink()

    base_keys = [period_column, product_column]
    frames: list[tuple[str, str, pd.DataFrame]] = [("periood_toode.csv", "Kuu ja toode.", aggregate_keys(register, base_keys, pieces_column, prices is not None))]
    for column in profile["kategooriad"]:
        name = f"periood_toode__{slug(column)}.csv"
        frames.append(
            (
                name,
                f"Kuu, toode ja {column}.",
                aggregate_keys(register, [*base_keys, column], pieces_column, prices is not None),
            )
        )

    index_lines = ["# Agregatsioonid", "", formula(prices), ""]
    periods = [str(value) for value in profile["perioodid"]]
    for filename, meaning, frame in frames:
        finished = attach_produced(frame, monthly, period_column, product_column, produced_column)
        finished = sort_output(finished, period_column, periods)
        finished.to_csv(output_dir / filename, index=False)
        index_lines.append(f"- `{filename}` — {meaning}")
    (output_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Agregatsioonid: {output_dir.relative_to(period.parent.parent)} ({len(frames)} faili)")
    print("Eurod: jah." if prices is not None else "Eurod: ei, hinnad puuduvad.")
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: aggregate.py <periood>", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(build(period_path(sys.argv[1])))
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
