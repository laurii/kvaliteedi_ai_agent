#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from create_folder import ROOT, create_period

LABEL = "ee.kvaliteet.esmaspaev"
INBOX = ROOT / "inbox"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG = ROOT / "logs" / "esmaspaev.log"


def meeting_monday(today: date) -> date:
    return today + timedelta(days=(0 - today.weekday()) % 7)


def period_name(today: date | None = None) -> str:
    day = today or date.today()
    return meeting_monday(day).strftime("%Y_%m_%d")


def workbooks(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    found: list[Path] = []
    for path in sorted(folder.iterdir()):
        if path.name.startswith("~$"):
            continue
        if path.suffix.lower() in {".xlsx", ".xls"}:
            found.append(path)
    return found


def copy_input(period: Path) -> str:
    target = period / "input"
    existing = workbooks(target)
    if existing:
        return f"Inputis on juba {existing[0].name}. Seda ei kirjutatud üle."
    INBOX.mkdir(exist_ok=True)
    found = workbooks(INBOX)
    if not found:
        return f"Pane Excel kausta {INBOX.relative_to(ROOT)}/."
    if len(found) > 1:
        names = ", ".join(path.name for path in found)
        return f"Inboxis on mitu faili: {names}. Jäta alles üks."
    destination = target / found[0].name
    shutil.copy2(found[0], destination)
    return f"Kopeeritud: {found[0].name} → {destination.relative_to(ROOT)}"


def notify(period: str) -> None:
    message = f"Kaust {period} on valmis. Käivita /analyse-data {period}"
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{message}" with title "Kvaliteedi esmaspäev"',
        ],
        check=False,
    )


def prepare(today: date | None = None) -> int:
    name = period_name(today)
    created = create_period(name)
    if created != 0:
        return created
    period = ROOT / "analyses" / name
    print(copy_input(period))
    print(f"Järgmine samm Cursoris: /analyse-data {name}")
    notify(name)
    return 0


def plist_text() -> str:
    python = ROOT / ".venv" / "bin" / "python"
    script = Path(__file__).resolve()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python}</string>
    <string>{script}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{ROOT}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{LOG}</string>
  <key>StandardErrorPath</key>
  <string>{LOG}</string>
</dict>
</plist>
"""


def install() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist_text(), encoding="utf-8")
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(PLIST)], check=False)
    loaded = subprocess.run(["launchctl", "bootstrap", domain, str(PLIST)])
    if loaded.returncode != 0:
        print("Ajastus ei läinud käima. Plist on kirjas.", file=sys.stderr)
        return loaded.returncode
    print(f"Iga esmaspäev kell 9: {PLIST}")
    print(f"Logi: {LOG.relative_to(ROOT)}")
    return 0


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--install":
        sys.exit(install())
    if len(sys.argv) != 1:
        print("Kasutus: monday.py [--install]", file=sys.stderr)
        sys.exit(1)
    sys.exit(prepare())


if __name__ == "__main__":
    main()
