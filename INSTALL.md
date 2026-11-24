# Install

Run these steps from the project root. The analysis scripts use `.venv/bin/python`. Do not install the packages into the system Python.

This project is set up with Python 3.14.

## Virtual environment

```bash
python3 -m venv .venv
```

That creates `.venv/` in the project root. The folder stays local. It is not part of the analysis data.

Check the interpreter:

```bash
.venv/bin/python -V
```

You do not need to activate the environment. The commands below call the venv Python by path. If you prefer a shell prompt inside the environment:

```bash
source .venv/bin/activate
```

## Requirements

```bash
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` pins the versions:

| Package | Used for |
| --- | --- |
| `pandas` | Tables, cleaning, aggregates, rankings |
| `openpyxl` | Reading the Excel workbook |
| `numpy` | Numeric work behind pandas |
| `requests` | Installed, not used by this step |
| `bs4` | Installed, not used by this step |

Confirm the imports:

```bash
.venv/bin/python -c "import pandas, openpyxl, numpy"
```

No output means the install is ready. After that, follow `README.md` for `/create-folder` and `/analyse-data`.
