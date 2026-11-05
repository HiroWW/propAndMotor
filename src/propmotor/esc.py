"""ESC (sensorless 6-step inverter) averaged model.

The ESC chops the DC input with duty d. Averaged over a PWM period (and assuming
continuous motor current) it behaves like an ideal DC/DC buck converter in front of
the motor:

    V_m  = d V_in - I_m R_on          (R_on: two conducting MOSFETs + traces)
    I_in = d I_m + I_q                (I_q: quiescent/logic current)

so the input (supply-side) current is *smaller* than the motor (phase) current at
part throttle: P_in = V_in I_in ~= V_m I_m + I_m^2 R_on. A thrust stand measures I_in;
the motor current rating and copper loss concern I_m.

Switching losses and current ripple are not modelled (second order at this power
level) but grow when d is small at high V_in; this is one of the reasons to match
the supply voltage so that full speed is reached at a high duty.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ESC:
    name: str
    v_min: float  # [V]
    v_max: float  # [V] (e.g. 4S -> 16.8 V)
    i_cont_a: float  # continuous phase current rating [A]
    i_burst_a: float | None = None
    r_on_ohm: float = 0.010  # effective series resistance in the motor path [ohm]
    d_max: float = 0.98  # highest effective duty it can apply
    i_q_a: float = 0.03  # quiescent current [A]
    firmware: str = ""
    pwm_input: bool | None = None  # accepts standard 1000-2000 us servo PWM
    motor_bullet_mm: float | None = None  # bullet connectors fitted on the motor leads
    battery_connector: str = ""  # "XT60" / "Deans" / "bare"
    braking_configurable: bool | None = None
    mass_g: float | None = None
    price: str = ""
    url: str = ""
    notes: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def cells(self) -> str:
        return f"{self.v_min:.1f}-{self.v_max:.1f} V"


def generic_esc(v_max: float = 25.2, i_cont_a: float = 30.0, name: str | None = None) -> ESC:
    """Placeholder ESC used for design-space maps before a concrete product is chosen."""
    return ESC(name=name or f"generic {i_cont_a:.0f}A / {v_max:.1f}V", v_min=5.0, v_max=v_max, i_cont_a=i_cont_a)
