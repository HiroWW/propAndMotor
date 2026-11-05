# propAndMotor

Selection of the power-supply voltage, motor and ESC for a static (hover) thrust test of an
**APC 8×3.8SF** propeller on a **Tyto Robotics 1585** stand powered by a **Kikusui PWR401L**.
Includes the physics write-up (typst) and the Python models behind it.

- Explanation (Japanese): `docs/main.typ` → `docs/main.pdf`
- Interactive selection: `notebooks/selection.py` (VS Code, run `# %%` cells)
- Library: `src/propmotor/` (propeller data, motor/ESC/source models, operating-point solver,
  selection checks, plots)

## Setup

```bash
python3 -m venv .venv
PIP_USER=0 .venv/bin/pip install -e ".[dev,notebook]"   # PIP_USER=0: ~/.pip/pip.conf sets user=true
.venv/bin/pytest
```

## Regenerate the document

```bash
.venv/bin/python scripts/make_figures.py   # figures -> docs/figures, numbers -> docs/generated/*.json
typst compile docs/main.typ
```

## Data sources

- `src/propmotor/data/props/apc/PER3_8x38SF.dat` — APC performance file (theory), apcprop.com
- `src/propmotor/data/props/uiuc/apcsf_8x3.8_static_2777rd.txt` — UIUC Propeller Data Site Vol. 1 (measured)
- `src/propmotor/data/catalog/*.toml` — candidate motors / ESCs (datasheet values, collected 2026-11, with URLs)
  and manufacturer test points with the same propeller (used for model validation)
