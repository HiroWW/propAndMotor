"""Candidate motor / ESC catalogs (TOML) -> Motor / ESC objects.

Datasheet numbers are *nominal*: hobby-motor R and I0 values are often rounded or
measured differently between brands. Every entry keeps its source URL and notes so
the provenance stays visible; after purchase, identify Kv, R, I0 on the stand.
"""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

from .esc import ESC
from .motor import Motor

LIPO_CELL_MAX = 4.2


def _default(name: str) -> Path:
    return Path(str(resources.files("propmotor").joinpath("data", "catalog", name)))


def _cells_max(cells: str | None) -> int | None:
    if not cells:
        return None
    try:
        return int(str(cells).upper().replace("S", "").split("-")[-1])
    except ValueError:
        return None


def load_motors(path: str | Path | None = None) -> list[Motor]:
    data = tomllib.loads(Path(path or _default("motors.toml")).read_text())
    out = []
    for d in data.get("motor", []):
        if d.get("kv") is None or d.get("r_ohm") is None or d.get("i0_a") is None:
            continue  # cannot be modelled without the three basic constants
        cmax = _cells_max(d.get("cells"))
        out.append(Motor(
            name=d.get("label") or f'{d["manufacturer"]} {d["model"]}',
            kv=float(d["kv"]), r_ohm=float(d["r_ohm"]), i0_a=float(d["i0_a"]),
            i0_ref_v=float(d.get("i0_ref_v", 10.0)),
            i_max_a=d.get("i_max_a"), p_max_w=d.get("p_max_w"),
            v_max=d.get("v_max") or (cmax * LIPO_CELL_MAX if cmax else None),
            mass_g=d.get("mass_g"), poles=d.get("poles"), shaft_mm=d.get("shaft_mm"),
            mount=d.get("mount", ""), price=str(d.get("price", "")), url=d.get("url", ""),
            notes=d.get("notes", ""), meta=d,
        ))
    return out


def load_escs(path: str | Path | None = None) -> list[ESC]:
    data = tomllib.loads(Path(path or _default("escs.toml")).read_text())
    out = []
    for d in data.get("esc", []):
        cmin = _cells_max(str(d.get("cells_min"))) if d.get("cells_min") else None
        cmax = _cells_max(d.get("cells"))
        v_min = d.get("v_min") or (cmin * 3.0 if cmin else 5.0)
        v_max = d.get("v_max") or (cmax * LIPO_CELL_MAX if cmax else None)
        if v_max is None or d.get("i_cont_a") is None:
            continue
        out.append(ESC(
            name=d.get("label") or f'{d["manufacturer"]} {d["model"]}',
            v_min=float(v_min), v_max=float(v_max), i_cont_a=float(d["i_cont_a"]),
            i_burst_a=d.get("i_burst_a"), r_on_ohm=float(d.get("r_on_ohm", 0.010)),
            firmware=d.get("firmware", ""), pwm_input=d.get("pwm_input"),
            braking_configurable=d.get("braking_configurable"), mass_g=d.get("mass_g"),
            price=str(d.get("price", "")), url=d.get("url", ""), notes=d.get("notes", ""), meta=d,
        ))
    return out
