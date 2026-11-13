#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

PERIOD_RE = re.compile(r"^[0-9A-Za-z_\u00C0-\u017F][0-9A-Za-z_\u00C0-\u017F-]*$")
ROOT = Path(__file__).resolve().parent.parent
SUBDIRS = (
    "input",
    "work/01_tabelid",
    "work/02_agregatsioonid",
    "work/kusimused",
    "output",
)


def create_period(name: str) -> int:
    if not PERIOD_RE.fullmatch(name):
        print(
            f"Vigane nimi: {name}. Lubatud on tähed, numbrid, _ ja -.",
            file=sys.stderr,
        )
        return 1

    period = ROOT / "analyses" / name
    relative = period.relative_to(ROOT)
    if period.exists():
        print(f"Kataloog on juba olemas: {relative}. Midagi ei kustutatud.")
        return 0

    for subdir in SUBDIRS:
        (period / subdir).mkdir(parents=True)
    print(f"Loodud: {relative}")
    for subdir in SUBDIRS:
        print(f"  {subdir}/")
    print(
        f"Kopeeri fail kausta {relative}/input/ ja käivita /analyse-data {name} <fail>."
    )
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print("Kasutus: create_folder.py <periood>", file=sys.stderr)
        sys.exit(1)
    sys.exit(create_period(sys.argv[1]))


if __name__ == "__main__":
    main()
