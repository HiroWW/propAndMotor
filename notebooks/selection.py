# %% [markdown]
# # APC 8×3.8SF 静止推力試験: 電源電圧・モータ・ESC の選定
#
# VS Code で開き、各 `# %%` セルの「Run Cell」で上から実行する(Interactive Window に図が出る)。
# カーネルはリポジトリの `.venv` を選ぶ。理論の説明は `docs/main.pdf`。
#
# 流れ: 試験条件 → プロペラ(負荷) → モデル検証 → 候補の一括評価 → 選定マップ → 個別候補の what-if

# %%
import matplotlib.pyplot as plt
import numpy as np

import propmotor as pm
from propmotor import plotting as P
from propmotor.catalog import load_escs, load_motors
from propmotor.selection import TestSpec, best_esc, compatibility, evaluate, kv_voltage_map
from propmotor.stand import TYTO_1585
from propmotor.validation import load_tests

# %matplotlib inline

# ---- 試験条件(当日の値に書き換える) ----
ROOM = dict(temp_c=20.0, pressure_pa=101_325.0, rel_humidity=0.5)
rho = pm.air_density(**ROOM)
rpm_limit = pm.apc_rpm_limit(8.0)  # APC SF: 65,000 / D[in]
spec = TestSpec(rpm_max=rpm_limit, rpm_min=1500, rho=rho)

apc = pm.apc_8x3_8sf_theory()  # APC 公表値(理論)
uiuc = pm.apc_8x3_8sf_measured()  # UIUC 実測 -> 公称モデル(予測用)
design = pm.apc_8x3_8sf_design()  # 各点最大 -> 設計モデル(サイジング用)
print(f"rho = {rho:.4f} kg/m3,  rpm_max = {rpm_limit:.0f}")
print(spec)

# %% [markdown]
# ## 1. プロペラが要求する負荷
# APC 理論値は実測より C_T で約 20 %、C_P で約 13 % 大きい。上限回転での推力・トルク・動力が「系が作るべき最大点」。

# %%
P.fig_prop_coefficients([uiuc, apc], rpm_limit)
P.fig_prop_dimensional([uiuc, apc], rho, rpm_limit)
for ds in (uiuc, apc):
    print(f"{ds.label:14s} T={float(ds.thrust(rpm_limit, rho)):.2f} N  Q={float(ds.torque(rpm_limit, rho)) * 1e3:.1f} mN·m  "
          f"P={float(ds.power(rpm_limit, rho)):.1f} W  FM={float(ds.figure_of_merit(rpm_limit)):.3f}")
plt.show()

# %% [markdown]
# ## 2. モデルの検証(メーカーが同じプロペラで測った値)

# %%
P.fig_validation(load_tests(), [uiuc, apc])
plt.show()

# %% [markdown]
# ## 3. 候補を一括評価
# `src/propmotor/data/catalog/motors.toml`, `escs.toml` に候補を追加すればここに反映される。
# JP_ONLY=True で国内入手可能品(jp_available = true)だけに絞る。はんだ付けが必要な基板型 ESC は既定で除外。

# %%
JP_ONLY = True
REFERENCE = "Dualsky ECO 2316C-V2 (880)"
motors, escs = load_motors(jp_only=JP_ONLY), load_escs(jp_only=JP_ONLY)
evals = [best_esc(m, escs, spec, uiuc, design) for m in motors]
for i, ev in enumerate(evals, 1):
    flag = "成立" if ev.feasible else "不成立"
    warn = ", ".join(c.name for c in ev.warnings)
    print(f"{i:2d} {ev.motor.name:28s} {flag:4s} V={ev.v_set:5.1f} ({ev.v_band[0]:.1f}-{ev.v_band[1]:.1f})  "
          f"Im={ev.design['i_motor']:5.2f} A  loss={ev.design['p_cu'] + ev.design['p_noload']:5.1f} W  "
          f"Km={ev.motor.km * 1e3:4.1f}  ESC={ev.esc.name}  {warn}")

# %%
P.fig_compatibility(compatibility(motors, escs, spec, uiuc, design), motors, escs)
plt.show()

# %% [markdown]
# ## 4. 選定マップ(Kv × 電源電圧)
# 色帯 = 成立領域。黒い縦棒 = 各候補の成立電圧範囲、白抜き点 = 推奨電圧。番号は上の一覧の番号。

# %%
ref = next(e for e in evals if e.motor.name == REFERENCE)
km = kv_voltage_map(ref.motor, pm.generic_esc(), spec, uiuc, design, kv=np.linspace(400, 2000, 41),
                    v=np.linspace(4, 40, 73))
cands = [(str(i), e.motor.kv, e.v_band[0], e.v_set, e.v_band[1]) for i, e in enumerate(evals, 1)]
P.fig_kv_v_map(km, spec, candidates=cands,
               esc_lines=[("2S", 8.4 * 0.9), ("3S", 12.6 * 0.9), ("4S", 16.8 * 0.9), ("6S", 25.2 * 0.9)])
plt.show()

# %% [markdown]
# ## 5. 個別候補の what-if(スライダー)
# モータ・ESC・電源電圧を変えると、制約チェック表・運転点の図・スロットル特性が更新される。

# %%
import ipywidgets as W  # noqa: E402
from IPython.display import display  # noqa: E402

motor_dd = W.Dropdown(options=[(m.name, i) for i, m in enumerate(motors)],
                      value=[m.name for m in motors].index(ref.motor.name), description="モータ")
esc_dd = W.Dropdown(options=[(e.name, i) for i, e in enumerate(escs)],
                    value=[e.name for e in escs].index(ref.esc.name), description="ESC")
v_sl = W.FloatSlider(value=ref.v_set, min=5, max=30, step=0.1, description="電源 [V]", continuous_update=False)
out = W.Output()


def update(*_):
    m, e, v = motors[motor_dd.value], escs[esc_dd.value], v_sl.value
    out.clear_output(wait=True)
    with out:
        ev = evaluate(m, e, v, spec, uiuc, design)
        print(ev.table())
        src = pm.DCSource("PSU", v_open=v, r_series=spec.r_leads, i_limit=40.0)
        dts = [pm.Drivetrain(prop=uiuc, motor=m, esc=e, source=src, rho=rho),
               pm.Drivetrain(prop=apc, motor=m, esc=e, source=src, rho=rho)]
        P.fig_matching(dts, rpm_limit=rpm_limit)
        P.fig_throttle_curve(dts, rpm_limit=rpm_limit)
        plt.show()


for w in (motor_dd, esc_dd, v_sl):
    w.observe(update, names="value")
display(W.VBox([W.HBox([motor_dd, esc_dd]), v_sl, out]))
update()

# %% [markdown]
# ## 6. 自作パラメータで試す(購入後に測った Kv, R, I0 を入れる)

# %%
kv_sl = W.FloatSlider(value=ref.motor.kv, min=400, max=2000, step=5, description="Kv", continuous_update=False)
r_sl = W.FloatSlider(value=ref.motor.r_ohm, min=0.02, max=0.5, step=0.001, readout_format=".3f", description="R [Ω]",
                     continuous_update=False)
i0_sl = W.FloatSlider(value=ref.motor.i0_a, min=0.1, max=2.0, step=0.01, description="I0 [A]", continuous_update=False)
v2_sl = W.FloatSlider(value=ref.v_set, min=5, max=30, step=0.1, description="電源 [V]", continuous_update=False)
out2 = W.Output()


def update2(*_):
    m = pm.Motor("custom", kv=kv_sl.value, r_ohm=r_sl.value, i0_a=i0_sl.value)
    e = pm.generic_esc()
    out2.clear_output(wait=True)
    with out2:
        ev = evaluate(m, e, v2_sl.value, spec, uiuc, design)
        print(f"成立電圧範囲 {ev.v_band[0]:.2f}-{ev.v_band[1]:.2f} V,  Km = {m.km * 1e3:.1f} mN·m/√W")
        print(ev.table())
        src = pm.DCSource("PSU", v_open=v2_sl.value, r_series=spec.r_leads)
        dt = pm.Drivetrain(prop=uiuc, motor=m, esc=e, source=src, rho=rho)
        P.fig_efficiency_map(dt, rpm_limit=rpm_limit)
        plt.show()


for w in (kv_sl, r_sl, i0_sl, v2_sl):
    w.observe(update2, names="value")
display(W.VBox([kv_sl, r_sl, i0_sl, v2_sl, out2]))
update2()

# %% [markdown]
# ## 7. 試験計画: 計測不確かさと回生

# %%
P.fig_measurement_uncertainty(uiuc, TYTO_1585, rho, rpm_max=rpm_limit)
from propmotor.regen import prop_inertia_estimate, rotor_inertia_estimate  # noqa: E402

j = prop_inertia_estimate(0.0071, uiuc.diameter_m) + rotor_inertia_estimate(0.020, 0.014)
P.fig_regen(uiuc, rho, j, v0=ref.v_set, v_limit=ref.esc.v_max, rpm_from=rpm_limit)
plt.show()
