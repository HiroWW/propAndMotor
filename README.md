# propAndMotor

Selection of the power-supply voltage, motor and ESC for a static (hover) thrust test of an
**APC 8×3.8SF** propeller on a **Tyto Robotics 1585** stand powered by a **Kikusui PWR401L**.
Includes the physics write-up (typst) and the Python models behind it.

- Explanation (Japanese): `docs/main.typ` → `docs/main.pdf` (physics and selection)
- Safety / power-chain design (Japanese): `docs/safety.typ` → `docs/safety.pdf` (regeneration, E-stop, BOM)
- Wiring review and source links (Japanese): [docs/wiring_review.md](docs/wiring_review.md)
  (Tyto terminals, optical RPM, J1 assembly, and the outstanding E-stop minimum-load qualification)
- Interactive selection: `notebooks/selection.py` (VS Code, run `# %%` cells)
- Library: `src/propmotor/` (propeller data, motor/ESC/source models, operating-point solver,
  selection checks, plots)

## Setup

```bash
python3 -m venv .venv
PIP_USER=0 .venv/bin/pip install -e ".[dev,notebook]"   # PIP_USER=0: ~/.pip/pip.conf sets user=true
.venv/bin/pytest
```

## Fonts

The documents and figures use the same fonts as the weekly-report template
(Futura PT, FTT-Cezanne, FTT-TsukuOldGothic). They are commercial fonts and are **not** in this
repository; copy them locally, e.g. from the Windows user font folder:

```bash
mkdir -p ~/.local/share/fonts/windows
cp /mnt/c/Users/$USER/AppData/Local/Microsoft/Windows/Fonts/{TT_Cezanne-*.ttf,FuturaPT-*.otf,TT_TsukuOldGothic-*.ttf} ~/.local/share/fonts/windows/
```

Without them typst and matplotlib fall back to other fonts.

## Regenerate the document

```bash
.venv/bin/python scripts/make_figures.py   # figures -> docs/figures, numbers -> docs/generated/*.json
.venv/bin/python scripts/make_wiring.py    # wiring + J1 detail -> docs/figures/{wiring,estop_wiring}.{png,svg}
typst compile docs/main.typ
typst compile docs/safety.typ
```

## Data sources

- `src/propmotor/data/props/apc/PER3_8x38SF.dat` — APC performance file (theory), apcprop.com
- `src/propmotor/data/props/uiuc/apcsf_8x3.8_static_2777rd.txt` — UIUC Propeller Data Site Vol. 1 (measured)
- `src/propmotor/data/catalog/*.toml` — candidate motors / ESCs (datasheet values, collected 2026-11, with URLs)
  and manufacturer test points with the same propeller (used for model validation)
