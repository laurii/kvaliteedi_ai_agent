from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PERIOD_RE = re.compile(r"^[0-9A-Za-z_\u00C0-\u017F][0-9A-Za-z_\u00C0-\u017F-]*$")
MONTH_INDEX = {
    "jaanuar": 1,
    "veebruar": 2,
    "märts": 3,
    "marts": 3,
    "aprill": 4,
    "mai": 5,
    "juuni": 6,
    "juuli": 7,
    "august": 8,
    "september": 9,
    "oktoober": 10,
    "november": 11,
    "detsember": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def period_path(name: str) -> Path:
    if not PERIOD_RE.fullmatch(name):
        raise ValueError(f"Vigane nimi: {name}. Lubatud on tähed, numbrid, _ ja -.")
    path = ROOT / "analyses" / name
    if not path.is_dir():
        raise FileNotFoundError(
            f"Kataloogi ei ole: analyses/{name}. Enne käivita /create-folder {name}."
        )
    return path


def find_input_workbook(period: Path) -> Path:
    folder = period / "input"
    files = [
        path
        for path in sorted(folder.iterdir())
        if path.is_file()
        and path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}
        and not path.name.startswith("~$")
    ]
    if not files:
        raise FileNotFoundError(f"Kaustas {folder.relative_to(ROOT)} ei ole tabelifaili.")
    if len(files) > 1:
        names = ", ".join(path.name for path in files)
        raise FileNotFoundError(f"Inputis on mitu tabelifaili: {names}. Jäta alles üks.")
    return files[0]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9a-z_\u00e4\u00f6\u00f5\u00fc\u0161\u017e]+", "", text)
    return text or "veerg"


def is_rate_series(series: pd.Series) -> bool:
    values = series.dropna()
    if len(values) < 3 or not pd.api.types.is_numeric_dtype(values):
        return False
    if int(values.nunique(dropna=True)) <= 2:
        return False
    return bool(values.between(0, 1).all())


def sort_periods(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value)
        if text not in seen:
            seen.append(text)
    if seen and all(value.strip().lower() in MONTH_INDEX for value in seen):
        return sorted(seen, key=lambda value: MONTH_INDEX[value.strip().lower()])
    return seen


def baseline_size(period_count: int) -> int:
    if period_count >= 4:
        return max(2, period_count // 3)
    if period_count >= 2:
        return 1
    return 0


def pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "–"
    return f"{value * 100:.1f}%".replace(".", ",")


def euro(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "–"
    return f"{round(float(value)):,.0f} €".replace(",", " ")


def blank(value: object) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return str(value).strip() in {"", "(tühi)", "nan", "None"}
