#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MONTHS = ("Jaanuar", "Veebruar", "Märts", "Aprill", "Mai", "Juuni")
PRODUCED = {"Komponent X": 1000, "Komponent Y": 800, "Komponent Z": 5000}


def rows() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    number = 1
    for index, month in enumerate(MONTHS, start=1):
        records.append(record(number, month, index, "Komponent X", "Päevane", "Mõõt", 12, "Liinil", "", "Jah"))
        number += 1
        records.append(record(number, month, index, "Komponent Y", "Päevane", "Mõõt", 4, "Liinil", "", "Jah"))
        number += 1
        records.append(record(number, month, index, "Komponent Y", "Päevane", "Keevis", 8, "Liinil", "", "Jah"))
        number += 1
        if index >= 4:
            records.append(record(number, month, index, "Komponent Y", "Õhtune", "Keevis", 36, "Liinil", "", "Ei"))
            number += 1
            records.append(record(number, month, index, "Komponent Y", "Õhtune", "Keevis", 4, "Kliendi juures", "", "Ei"))
            number += 1
        records.append(record(number, month, index, "Komponent Z", "Päevane", "Kriimustus", 80, "Liinil", "", "Ei"))
        number += 1
        records.append(record(number, month, index, "Komponent X", "Päevane", "Pinnakate", 2, "Liinil", "Vana OÜ", "Jah"))
        number += 1
    for pieces in (9000, 8000, 7000):
        records.append(
            {
                "ID": None,
                "Kuupäev": None,
                "Kuu": None,
                "Toode": None,
                "Vahetus": None,
                "Defekti liik": None,
                "Tükke": pieces,
                "Avastamise koht": None,
                "Pinnatöötluse tarnija": None,
                "Ümber tehtud": None,
            }
        )
    return records


def record(
    number: int,
    month: str,
    index: int,
    product: str,
    shift: str,
    defect: str,
    pieces: int,
    place: str,
    supplier: str,
    redone: str,
) -> dict[str, object]:
    return {
        "ID": f"SM-{number:04d}",
        "Kuupäev": f"2025-{index:02d}-15",
        "Kuu": month,
        "Toode": product,
        "Vahetus": shift,
        "Defekti liik": defect,
        "Tükke": pieces,
        "Avastamise koht": place,
        "Pinnatöötluse tarnija": supplier or None,
        "Ümber tehtud": redone,
    }


def monthly(register: pd.DataFrame) -> pd.DataFrame:
    rows_out = []
    for month in MONTHS:
        for product, produced in PRODUCED.items():
            scrap = int(register.loc[(register["Kuu"] == month) & (register["Toode"] == product), "Tükke"].sum())
            rows_out.append(
                {
                    "Kuu": month,
                    "Toode": product,
                    "Toodetud tk": produced,
                    "Praak tk": scrap,
                    "Praak %": scrap / produced,
                }
            )
    return pd.DataFrame(rows_out)


def guide() -> pd.DataFrame:
    lines = [
        "Simuleeritud tehas, jaanuar–juuni 2025",
        "Kolm toodet. Failis on kuukokkuvõte ja kõrvalekallete register.",
        "Toode | Omahind | Ümbertegemise aeg",
        "Komponent X | 50 € | 30 min",
        "Komponent Y | 40 € | 24 min",
        "Komponent Z | 3 € | 6 min",
        "Tunnihind koos kaudsete kuludega | 30 €",
        "Kliendi juures avastatud defekt | +100 € juhtumi kohta",
        "Mahakantud toote puhul kaob kogu omahind",
        "Ümber tehtud | Jah tähendab ümbertegemist, Ei tähendab mahakandmist",
        "Avastamise koht | liinil või kliendi juures",
        "Mis perioodil toimus",
        "Märtsis tõusis terase hind 10%.",
        "Aprillis alustas õhtune vahetus.",
        "Mais vahetus lõppkontrolli juhend.",
        "Kõik sündmused ei ole seotud sellega, mida andmetest leiad.",
    ]
    body = [[line, ".", ".", "."] for line in lines]
    return pd.DataFrame([["", "", "", ""], *body])


def main() -> None:
    register = pd.DataFrame(rows())
    target = ROOT / "sample_data" / "sim_andmestik.xlsx"
    truth = ROOT / "sample_data" / "sim_truth.md"
    with pd.ExcelWriter(target) as writer:
        monthly(register.dropna(subset=["ID"])).to_excel(writer, sheet_name="Kuukokkuvõte", index=False)
        register.to_excel(writer, sheet_name="Kõrvalekalded", index=False)
        guide().to_excel(writer, sheet_name="Lugemisjuhend", index=False, header=False)
    truth.write_text(
        "\n".join(
            [
                "# Tõde",
                "",
                "Seda faili ei panda analüüsi input kausta.",
                "",
                "Leid on Komponent Y keevis. Jaanuarist märtsini on 8 tükki kuus, aprillist 48.",
                "Kasv on õhtusel vahetusel. Päevane keevis jääb 8 tüki peale.",
                "Komponent Z kriimustus on suur tükimaht ja ei muutu.",
                "Terase hind märtsis ja kontrolli juhend mais ei muuda määrasid.",
                "Pinnakate on stabiilne ja väike.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Andmestik: {target.relative_to(ROOT)}")
    print(f"Tõde: {truth.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
