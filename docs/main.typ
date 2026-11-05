// APC 8x3.8SF 静止推力試験のための 電源・モータ・ESC 選定 — 物理と計算
// 図と数値は scripts/make_figures.py が生成する (docs/figures, docs/generated)。

#let val = json("generated/values.json")
#let cands = json("generated/candidates.json")
#let ref = val.reference

#let f(x, d: 2) = if x == none { "—" } else { str(calc.round(x, digits: d)) }
#let pct(x, d: 0) = if x == none { "—" } else { str(calc.round(x * 100, digits: d)) + " %" }

#set document(title: "APC 8×3.8SF 静止推力試験の電源・モータ・ESC選定")
#set page(paper: "a4", margin: (x: 20mm, y: 20mm), numbering: "1")
#set text(lang: "ja", font: ("Noto Serif CJK JP",), size: 10pt)
#set par(justify: true, leading: 0.8em, first-line-indent: 0em, spacing: 1.1em)
#set heading(numbering: "1.1")
#show heading: set text(font: ("Noto Sans CJK JP",), weight: "bold")
#show heading.where(level: 1): it => { pagebreak(weak: true); v(0.4em); it; v(0.3em) }
#set math.equation(numbering: "(1)")
#show figure.caption: set text(size: 9pt)
#set figure(gap: 0.8em)
#show figure: set block(spacing: 1.6em)
#show raw: set text(font: ("DejaVu Sans Mono",), size: 8.5pt)

#let note(body) = block(fill: rgb("#f4f3ef"), inset: 9pt, radius: 3pt, width: 100%, body)
#let key(body) = block(stroke: (left: 2.5pt + rgb("#2a78d6")), inset: (left: 10pt, y: 6pt), width: 100%, body)
#let fig(path, cap, w: 100%) = figure(image(path, width: w), caption: cap)

#align(center)[
  #text(size: 17pt, font: ("Noto Sans CJK JP",), weight: "bold")[APC 8×3.8SF 静止推力試験のための\ 電源電圧・モータ・ESC の選定]
  #v(0.3em)
  #text(size: 10.5pt)[— どういう物理で決まるのか、と その計算 —]
  #v(0.6em)
  #text(size: 9pt, fill: rgb("#52514e"))[数値・図は `scripts/make_figures.py` で生成（このPDFの数値はコードと同期）]
]

#v(1em)
#outline(depth: 2, indent: 1.5em)

= この文書の目的と前提

APC 8×3.8SF プロペラの静止（ホバ）状態の特性 — 推力 $T$・トルク $Q$・軸動力 $P$ を回転数の全域で — を
推力スタンドで測定したい。そのために、*電源電圧*、*モータ*、*ESC* をどう決めればよいかを、
物理から積み上げて整理し、計算で選定する。

#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: (x: 6pt, y: 4pt),
  table.hline(stroke: 0.6pt),
  [*項目*], [*前提*],
  table.hline(stroke: 0.4pt),
  [プロペラ], [APC 8×3.8SF（Slow Flyer, 直径 $D$ = 8 in = 0.2032 m, 2枚翼）],
  [試験範囲], [静止（前進速度 0）、回転数 0 〜 #f(val.rpm_limit, d: 0) rpm（APC の SF 上限 65,000/D）],
  [電源], [安定化電源 菊水 PWR401L（0–40 V, 0–40 A, 400 W）],
  [スタンド], [Tyto Robotics Series 1585（推力 ±5 kgf, トルク ±2 N·m, 50 V, 55 A）+ 光学式回転計],
  [調達], [モータと ESC は新規購入],
  [空気密度], [$rho$ = #f(val.rho, d: 3) kg/m³（20 °C, 101.3 kPa, 相対湿度 50 % を仮定。試験当日の値で再計算する）],
  table.hline(stroke: 0.6pt),
)

== 「選定」とは何をすることか

プロペラが決まると、各回転数で必要なトルクが決まる（負荷）。その負荷を、試験範囲の全域で、
*どの部品の定格も超えずに、余裕をもって* 作り出せる「電源電圧 × モータ × ESC」の組を見つけるのが選定である。
エネルギーと信号の流れは次の一本道になっている。

#figure(
  {
    let node(title, sub) = rect(radius: 3pt, inset: 7pt, stroke: 0.6pt + rgb("#898781"), width: 100%)[
      #align(center)[#text(font: ("Noto Sans CJK JP",), weight: "bold", size: 9.5pt)[#title] \ #text(size: 8.5pt)[#sub]]
    ]
    let arr(t) = align(center + horizon)[#text(size: 8pt)[#t] \ #text(size: 14pt)[→]]
    grid(
      columns: (1fr, 0.62fr, 1fr, 0.62fr, 1fr, 0.62fr, 1fr),
      align: center + horizon,
      node[電源][$V_"set"$, 配線 $R_s$],
      arr[$V_"in", I_"in"$],
      node[ESC][duty $d$, $R_"on"$],
      arr[$V_m, I_m$],
      node[モータ][$K_v, R, I_0$],
      arr[$Q, omega$],
      node[プロペラ][$C_T, C_P$],
    )
  },
  caption: [試験系のエネルギーの流れ。各矢印の上が、その境界で受け渡される量。スタンドは $V_"in", I_"in"$（電源側）、$T, Q, omega$ を測る。],
)

この文書の構成は、負荷側（@sec:prop プロペラ）→ 変換器（@sec:motor モータ, @sec:esc ESC）→ 供給側（@sec:source 電源）の順に物理を整理し、
@sec:select でそれらを連立させて選定する。@sec:test は試験計画への示唆である。

#key[
  *結論の先取り:* プロペラが要求する最大点（約 8,100 rpm, トルク 0.06–0.07 N·m, 軸動力 50–56 W）は
  モータの選び方に関係なく決まっている。モータの *大きさ*（モータ定数 $K_m$）が発熱を決め、*Kv* は電圧と電流の配分を決めるだけで、
  電源電圧は連続に選べる。したがって選定の中心は「Kv–電圧平面の成立領域」を描き、そこに候補を載せることになる。
]

= プロペラ: 負荷はどう決まるか <sec:prop>

== 運動量理論とフィギュア・オブ・メリット

静止状態のロータを、空気に圧力差を与える薄い円板（アクチュエータ・ディスク）とみなす。円板面積 $A = pi D^2 \/ 4$、
円板を通る誘導速度を $v_i$ とすると、質量流量は $dot(m) = rho A v_i$、後流の速度は $2 v_i$ になる（ベルヌーイと運動量保存から）。

$ T = dot(m) dot 2 v_i = 2 rho A v_i^2, quad P_"ideal" = T v_i = T^(3\/2) / sqrt(2 rho A) $ <eq:momentum>

これは損失のない理想ロータが推力 $T$ を出すのに必要な最小動力である。実際の動力 $P$ との比が
*フィギュア・オブ・メリット* FM で、静止ロータの効率を表す。

$ "FM" = P_"ideal" / P $ <eq:fm>

本プロペラでは $A$ = #f(val.disk_area, d: 4) m²。上限回転数で推力 #f(val.uiuc.thrust_n) N（実測ベース）を出すときの理想動力は
#f(val.p_ideal_lim, d: 1) W、実際の動力は #f(val.uiuc.power_w, d: 1) W なので FM ≈ #f(val.uiuc.fm_lim). 残りは翼の形状抗力・翼端損失・旋回流などである。

== 無次元係数と相似則

推力は $rho$, 回転数 $n$ [rev/s], 直径 $D$ と、レイノルズ数 Re・翼端マッハ数 M・前進率 $J = V\/(n D)$ で決まる。次元解析から

$ T = C_T rho n^2 D^4, quad P = C_P rho n^3 D^5, quad Q = P / omega = C_P / (2 pi) rho n^2 D^5 $ <eq:coef>

と書け、$C_T, C_P$ は $(J, "Re", M)$ の関数である。静止試験では $J = 0$。翼端マッハ数は上限回転数でも
#f(val.tip_mach_lim) 程度なので圧縮性は無視できる。残るのは *レイノルズ数（＝回転数）依存性* だけである。
$C_T, C_P$ が一定なら $T, Q prop n^2$, $P prop n^3$、したがって $P prop T^(3\/2)$ となる。
推力を 2 倍にするには回転数 $sqrt(2)$ 倍、動力 2.8 倍が要る。FM は無次元係数で書くと

$ "FM" = C_T^(3\/2) / (sqrt(pi \/ 2) thin C_P) $ <eq:fmcoef>

== データ: APC 公表値と UIUC 実測値

使えるデータは 2 種類ある。

- *APC 公表値*（`PER3_8x38SF.dat`, v2022-0915）: APC 社が翼素理論・渦理論と翼型極曲線で計算した *理論値*。1,000–29,000 rpm。
- *UIUC 実測値*（Propeller Data Site Vol. 1, `apcsf_8x3.8_static_2777rd`）: 風洞スタンドでの *実測*。#f(val.uiuc.rpm_range.at(0), d: 0)–#f(val.uiuc.rpm_range.at(1), d: 0) rpm。

#fig("figures/prop_coefficients.svg")[静止状態の $C_T$, $C_P$, FM。橙は APC の理論値、青は UIUC 実測（点が実測値、点線は範囲外の外挿: 上側は高回転側 6 点の直線当てはめ、下側は端の値で保持）。]

#fig("figures/prop_dimensional.svg")[推力・トルク・軸動力（有次元）。点は APC 上限 #f(val.rpm_limit, d: 0) rpm での値。]

二つは大きく食い違う。7,000 rpm で $C_T$ は APC #f(val.apc.ct_7000, d: 4) に対し実測 #f(val.uiuc.ct_7000, d: 4)（APC が約
#f((val.apc.ct_7000 / val.uiuc.ct_7000 - 1) * 100, d: 0) % 大きい）、$C_P$ は #f(val.apc.cp_7000, d: 4) に対し #f(val.uiuc.cp_7000, d: 4)（約 #f((val.apc.cp_7000 / val.uiuc.cp_7000 - 1) * 100, d: 0) % 大きい）。
また実測では $C_T, C_P$ が回転数とともに増える（低レイノルズ数で翼型の揚抗比が悪いため。Re は 75 % 半径で 10⁴–10⁵ のオーダ）のに対し、理論値はほぼ一定である。
理論は静止状態の小型プロペラの性能を楽観的に見積もりがちで、FM も理論 #f(val.apc.fm_lim) に対し実測ベース #f(val.uiuc.fm_lim) である。

#key[
  *使い分け:* 部品の大きさを決める（定格を超えないか、上限回転に届くか）ときは、トルク・推力が大きい側を取る *設計モデル*
  （両データの各点最大値。本プロペラでは結果的に APC 値）を使う。試験結果の *予測* には実測ベースの *公称モデル*（UIUC。7,015 rpm 以上は外挿）を使う。
]

上限回転数 #f(val.rpm_limit, d: 0) rpm での負荷は次のとおり。これが「試験系が作り出さなければならない最大点」である。

#align(center, table(
  columns: 5,
  align: (left, right, right, right, right),
  stroke: none,
  table.hline(stroke: 0.6pt),
  [], [推力], [トルク], [軸動力], [FM],
  table.hline(stroke: 0.4pt),
  [公称（UIUC 外挿）], [#f(val.uiuc.thrust_gf, d: 0) gf], [#f(val.uiuc.torque_nm * 1000, d: 1) mN·m], [#f(val.uiuc.power_w, d: 1) W], [#f(val.uiuc.fm_lim)],
  [設計（APC）], [#f(val.apc.thrust_gf, d: 0) gf], [#f(val.apc.torque_nm * 1000, d: 1) mN·m], [#f(val.apc.power_w, d: 1) W], [#f(val.apc.fm_lim)],
  table.hline(stroke: 0.6pt),
))

#note[
  *回転数上限について:* APC は Slow Flyer 系の最大回転数を「65,000 / 直径[in]」と定めている（8 in で 8,125 rpm、APC は "suggested" と表現）。
  SF は薄く柔らかい低速機用プロペラで、遠心力と曲げで破損・変形するためである。試験はこの上限まで、スタンドのセーフティ・カットオフをこの値に設定し、
  エンクロージャ内で行う。系としては上限より上まで回せる余力を持たせる（制御余裕）が、実際に回すのは上限まで。
]

== 独立なデータでの検証

どちらのデータが正しいかは、第三者の測定と比べれば分かる。モータメーカー（Scorpion, Cobra, SunnySky）は、
*同じ APC 8×3.8SF* を自社モータで回した試験値を公表している。測定された回転数で、推力と（全開点の）電流をモデルで計算して比べた。

#fig("figures/validation.svg")[メーカー試験値に対するモデルの比。推力は回転数だけで決まるのでプロペラモデルの直接の検証になる。電流はプロペラの $C_P$ とモータモデル（$I = Q K_v + I_0$）の両方の検証になる（全開点のみ: 電源電流 ≈ モータ電流）。]

UIUC 実測ベースのモデルは推力で −3 〜 +1.5 %、電流で −2 〜 +6 % に収まる。APC 理論値は推力を 9–16 % 過大に見積もる。
これにより、「予測は UIUC ベース、部品の大きさは APC ベース（保守側）」という使い分けが裏付けられる。
なお、部分スロットル点（SunnySky）の電源入力電力はモデルのモータ入力より 15–17 % 大きい。これは本モデルが扱っていない
ESC のスイッチング損失・電流リップル分と考えられる（スタンドで $I_"in"$ を予測するときは、この程度の上振れを見込む）。

== プロペラの取り付け

APC 8×3.8SF の質量は 0.25 oz（約 7.1 g）、ハブ径 0.50 in、ハブ厚 0.30 in、軸穴 1/4 in で、裏側に直径 8 mm の座ぐりがある。
モータ軸径に合わせて APC のアダプタリングを入れて芯出しする（LPARM12SF: 3/5/6 mm、外径 8 mm。LPAR18SF: 6 mm と 3/16 in）。
候補モータの多くは M5 ねじのプロペラアダプタなので *5 mm リング* を使う（T-Motor AT2312 は M6 → 6 mm リング）。穴を広げる場合はドリルではなくテーパリーマで行う。

= モータ: 電気を回転に変える <sec:motor>

== ブラシレスモータの 1 次モデル

ドローン用の外転型ブラシレスモータは、ESC と組み合わせると直流モータと同じ式で扱える（Drela の 1 次モデル）。
線間の量で、

$ V_m = E + I R, quad E = omega / K_v $ <eq:motorv>

$ Q = K_t (I - I_0), quad K_t = 1 / K_v $ <eq:motorq>

ここで $K_v$ は速度定数（SI では rad/s/V。カタログの rpm/V に $pi\/30$ を掛ける）、$R$ は巻線の線間抵抗、$I_0$ は無負荷電流。
$K_t = 1\/K_v$ は電力の保存から出る: 逆起電力 $E$ に逆らって流す電流 $I$ がする仕事 $E I$ は、電磁トルク×角速度 $Q_"em" omega$ に等しい。
$E = omega\/K_v$ を代入すると $Q_"em" = I \/ K_v$。カタログ値で書けば

$ K_t ["N·m/A"] = 60 / (2 pi K_v ["rpm/V"]) = 9.549 / K_v ["rpm/V"] $

無負荷電流 $I_0$ は、鉄損（ヒステリシス損 $prop omega$、渦電流損 $prop omega^2$）、軸受摩擦、ロータの風損をまとめて電流に換算したもので、
カタログでは「10 V での値」として与えられることが多い。本ソフトでは既定で一定値とする（速度依存も設定可能。購入後に無負荷スイープで同定する）。

#note[
  *カタログ値の信頼性:* $R$ は多くが線間値だが、表記が明示されないメーカーもある（SunnySky と Cobra は線間と明記）。
  AXI は同じ Kv で旧カタログと現行ページの $R$ が 1.7 倍違う。$I_0$ は測定電圧（8, 8.4, 10, 12 V）がメーカーごとに違い、電圧とともに増える。
  したがってカタログ値は *公称値* として選定に使い、購入後にスタンドで $K_v$（無負荷回転数/電圧）、$R$（4 端子法、線間）、$I_0(omega)$ を測り直す。
]

== 損失と効率

入力 $V_m I$ は、軸出力・銅損・無負荷損に分かれる。

$ V_m I = underbrace(Q omega, "軸出力") + underbrace(I^2 R, "銅損") + underbrace(I_0 E, "無負荷損"), quad
  eta_m = (1 - I_0 / I)(1 - (I R) / V_m) $ <eq:motoreta>

電流が小さいと $I_0$ の割合が大きく、電流が大きいと $I R$ の割合が大きい。その間に効率最大点がある。

== 運転点 = モータ特性線とプロペラ負荷線の交点

ESC が duty $d$ でモータに平均電圧を与えると、@eq:motorv と @eq:motorq から、その duty でのモータの「出せるトルク–回転数」の関係は
右下がりの直線になる（モータ特性線）。一方プロペラは @eq:coef の $Q prop n^2$ の放物線を要求する（負荷線）。
定常運転点はこの二つの交点である。

#fig("figures/matching.svg")[運転点の決まり方（基準モータ: #ref.motor, 電源 #f(ref.v_set, d: 1) V）。灰色の直線が duty 一定のモータ特性線、色付きの曲線がプロペラ負荷線、点が運転点。]

モータ特性線の傾きは $-1\/(K_v^2 R_"tot")$ で、巻線抵抗が小さいモータでは非常に急（回転数が負荷であまり落ちない）。
そのため回転数はほぼ $K_v d V_"in"$ で決まり、負荷トルクは主に *電流* を決める。

== Kv は何を決めるか: 同じ大きさのモータの巻き替え

同じステータ・磁石（同じフレーム）で巻数 $N$ だけ $k$ 倍に変えると、逆起電力は $N$ に比例するので $K_v -> K_v \/ k$、
線長が $k$ 倍・線断面が $1\/k$ 倍になるので $R -> k^2 R$。すると

$ K_m eq.def K_t / sqrt(R) quad "は不変", quad P_"cu" = I^2 R approx (Q / K_m)^2 $ <eq:km>

つまり *銅損はフレームの大きさ（$K_m$）とトルクだけで決まり、Kv には依存しない。* 鉄損も同じ回転数なら同じである。
Kv を変えると変わるのは「同じ機械出力を、高い電圧・小さい電流で作るか、低い電圧・大きい電流で作るか」だけである。

#fig("figures/kv_tradeoff.svg")[同じフレームで Kv だけ変えたときの必要電圧・電流・損失（上限回転、設計 duty 80 %）。損失は一定で、電圧と電流が入れ替わるだけ。]

したがってモータ選定は二段に分かれる。

+ *フレーム（大きさ）*: 最大トルクでの損失 $(Q\/K_m)^2 + I_0 E$ が発熱として許容できるか。本プロペラの最大トルク
  #f(val.apc.torque_nm * 1000, d: 0) mN·m に対し、2212 級（$K_m approx$ 0.03 N·m/√W）で銅損 5–6 W と小さく、2208–2216 級で十分である。
+ *巻線（Kv）*: 電源・ESC の電圧範囲に、必要電圧が収まるように選ぶ。安定化電源は電圧を連続に変えられるので、Kv の自由度は大きい。

#fig("figures/efficiency_map.svg")[基準モータの効率マップと、プロペラ負荷線（実測ベース）。試験は負荷線の上だけを動く。]

= ESC: 直流を三相に、電圧を duty に <sec:esc>

== 6 ステップ駆動とセンサレス

ホビー用 ESC は 6 個の MOSFET で三相ブリッジを作り、常に 2 相に通電して 60° ごとに切り替える（6 ステップ駆動）。
モデルで線間抵抗を使うのはこのためである。切替のタイミングは、通電していない 1 相の逆起電力のゼロクロスで検出する（センサレス）。
逆起電力は回転数に比例するので、*極低速では検出できない*。始動は開ループで行い、ある程度の回転数から閉ループになる。
試験の低回転端（ここでは #f(val.spec.rpm_min, d: 0) rpm）で duty が小さすぎると、回転が不安定になりやすい。

== PWM と平均化モデル

ESC は通電相の電圧を PWM（周期 数十 µs）で刻み、duty $d$ で平均電圧を調整する。モータのインダクタンスで電流は平滑化されるので、
1 周期で平均すると ESC は降圧（バック）コンバータとして振る舞う。

$ V_m = d V_"in" - I_m R_"on", quad I_"in" = d I_m + I_q $ <eq:esc>

$R_"on"$ は導通している 2 個の MOSFET と配線の抵抗、$I_q$ は ESC 自身の消費電流。重要なのは
*電源側電流 $I_"in"$ はモータ電流 $I_m$ の約 $d$ 倍*（部分スロットルでは小さい）であること。
スタンドが測るのは $V_"in", I_"in"$ で、モータの定格や銅損に関係するのは $I_m$ である。

#fig("figures/throttle.svg")[duty に対する回転数・推力・電流（基準モータ、電源 #f(ref.v_set, d: 1) V）。回転数は duty にほぼ比例する。電流は推力と同じく 2 乗的に増える。]

== ESC に求める要件

#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: (x: 6pt, y: 4pt),
  table.hline(stroke: 0.6pt),
  [*項目*], [*要件と理由*],
  table.hline(stroke: 0.4pt),
  [入力電圧], [設定電圧が定格上限の 90 % 以下（減速時の回生・配線インダクタンスによる跳ね上がりの余裕）],
  [電流], [最大回転時のモータ電流が連続定格の 60 % 以下（試験は長時間・繰り返しの定常運転）],
  [入力信号], [標準サーボ PWM（1000–2000 µs）を受け付けること。1585 本体の ESC 出力は *50 Hz・5 V の PWM 固定*（DShot 等は別売の RC Control Board が必要）。Bluejay（DShot 専用）に書き換えた BLHeli_S は不可。BLHeli_32 は高速 MCU だと 50 Hz PWM の下限に注意],
  [設定], [回転方向、スロットル範囲の校正（Hobbywing は既定 1100–1940 µs）、ブレーキ/アクティブフリーホイールの OFF（回生の有無に関係、@sec:regen）、低電圧カットの無効化],
  [BEC], [不要。BEC 付き ESC を使うときは、1585 の 5 V ジャンパ（ESC 給電用、最大 100 mA）と 5 V がぶつからないよう配線を確認する],
  [テレメトリ], [不要（回転数は光学式で測る）],
  table.hline(stroke: 0.6pt),
)

= 電源: 安定化電源で試験するときの注意 <sec:source>

== テブナン等価回路

電源は「開放電圧 $V_"set"$ と直列抵抗 $R_s$」で表す。$R_s$ は配線・コネクタ・スタンドのシャント抵抗（バッテリなら内部抵抗も）。

$ V_"in" = V_"set" - I_"in" R_s $ <eq:source>

安定化電源は電流制限（CC）を持ち、設定電流を超えると電圧を下げる。試験では、最大点の $I_"in"$ より少し上に電流制限をかけておくと、
異常時（ロック・短絡）の保護になる。バッテリと違い、試験中に電圧が下がっていかないので、スイープの再現性が高い。

PWR401L 固有の注意（取扱説明書 IB035086 より）:

- *前面端子は約 10–11 A で過電流保護（FOCP）が働く*。仕様は背面端子に対するものなので、背面端子から配線する。
- リモートセンシングで配線の電圧降下（片側約 1.5 V まで）を補償できる。ESC 入力端で電圧を一定にしたい場合に使う（ただし逆流防止ダイオードとは併用不可）。
- OVP は 4–44.8 V で設定可能。設定電圧＋数 V に設定しておく。

== 回生: 電源は電流を吸い込めない <sec:regen>

回転体（プロペラ＋ロータ）は運動エネルギー $E_k = J omega^2 \/ 2$ を持つ。ESC がブレーキ（相補 PWM・アクティブフリーホイール・停止時ブレーキ）で減速させると、
モータは発電機になり、エネルギーが直流母線に戻る（回生）。バッテリなら充電されるだけだが、
*一般的な安定化電源は電流を吸い込めない* ので、戻った電荷が ESC の入力コンデンサを充電し、電圧が跳ね上がる。

$ V_"after" = sqrt(V_0^2 + 2 eta_r E_k / C) $ <eq:regen>

#fig("figures/regen.svg")[左: 上限回転から急減速したとき、回生エネルギーを母線容量 $C$ だけで受けた場合の電圧（$J$ = #f(val.regen.j_gcm2, d: 0) g·cm² は概算）。右: 空力トルクだけで減速する速さ。]

回転体のエネルギーは上限回転で約 #f(val.regen.energy_lim_j, d: 1) J と小さく見えるが、ESC の入力コンデンサ（数百 µF）で受けると数十 V に達しうる。対策は次の 3 つ。

+ *ゆっくり下げる*: プロペラは空力トルクで自然に速く減速する（右図）。指令をそれより遅く下げれば、モータは常に駆動側にいて回生は起きない。
  1585 のスクリプトで、下げ方向のステップをゆっくりにする。
+ *吸収先を作る*: 電源の吸い込み（ブリーダ）機能を使う、母線に大容量コンデンサや、バッテリ・ブレーキ抵抗＋ツェナ等を並列に置く。
+ *ESC 設定*: 停止時ブレーキを無効にする。非常停止（指令 0）で惰性回転させる。

#note[
  *PWR401L について確認できたこと:* 取扱説明書に「逆電流を吸収できない。回生負荷を接続すると出力電圧が上昇して不安定になり、故障の原因になる」と明記されている。
  ブリーダ（強ブリーダ HYP）の吸い込みは 12–15 V で約 0.5 A（6–8 W）しかなく、回生の吸収先にはならない。
  メーカーの推奨は、負荷と並列のバイパス抵抗、または逆流防止ダイオード。Tyto も「ESC の入力側にコンデンサバンクを足す、ダイオードやコンデンサを緩衝に使う」としている。
  本試験では *対策 1 と 3（回生を起こさない運転と設定）を基本* とし、保険として回生クランプ（maxon DSR 70/30）を入れ、非常停止は PWR401L の J1 端子で出力を切る構成とする。詳細と部品表は別冊 `safety.pdf`。
]

= 選定 <sec:select>

== 解き方

@eq:coef, @eq:motorv, @eq:motorq, @eq:esc, @eq:source を連立させる。回転数を与えると、プロペラから $Q$、モータ式から $I_m, V_m$ が直接決まり、
残る未知数 duty $d$ は次の 2 次方程式の小さい方の根になる（実根がなければ電源が電力を出せない）。

$ -I_m R_s thin d^2 + (V_"set" - I_q R_s) thin d - (V_m + I_m R_"on") = 0 $ <eq:duty>

逆に duty を与えたときの回転数は、$d("rpm")$ が単調なので 1 次元の求根（Brent 法）で求める。

== 制約と余裕

#table(
  columns: (auto, 1fr, auto),
  stroke: none,
  inset: (x: 6pt, y: 4pt),
  table.hline(stroke: 0.6pt),
  [*制約*], [*内容*], [*種類*],
  table.hline(stroke: 0.4pt),
  [上限回転に届く], [設計モデルで #f(val.rpm_limit, d: 0) rpm に必要な duty ≤ #pct(val.spec.duty_design_max)], [必須],
  [電圧が高すぎない], [公称モデルで上限回転の duty ≥ #pct(val.spec.duty_nominal_min)（低いと分解能・電流リップル・低速安定性が悪化）], [推奨],
  [低回転端], [#f(val.spec.rpm_min, d: 0) rpm での duty ≥ #pct(val.spec.duty_low_min)], [推奨],
  [モータ電流], [最大点の相電流 ≤ 定格の #pct(val.spec.motor_i_frac)（巻線 #f(val.spec.winding_temp_c, d: 0) °C で評価）], [必須],
  [ESC], [電圧範囲（上限 × #pct(val.spec.esc_v_frac)）、電流 ≤ 定格の #pct(val.spec.esc_i_frac)、PWM 入力], [必須],
  [電源], [40 V, 40 A, 400 W 以内], [必須],
  [スタンド], [推力 5 kgf, トルク 2 N·m, 電流 55 A, 電圧 50 V 以内], [必須],
  table.hline(stroke: 0.6pt),
)

推奨電圧は、設計モデルで上限回転の duty が #pct(val.spec.duty_target) になる電圧（0.1 V 切り上げ）とする。

== 選定マップ

@eq:km より、同じフレームなら Kv と電圧だけが自由度である。上の制約のうち電圧に関係するものを、Kv–電圧平面に描くと次の図になる。

#fig("figures/kv_v_map.svg")[選定マップ。色の付いた帯が成立領域（色は上限回転での公称 duty）、破線が推奨電圧。下の灰色は上限回転に届かない領域、上の灰色は電圧が高すぎる領域。横線は各セル数用 ESC の電圧上限（×0.9）。黒い縦棒が候補モータの成立電圧範囲、白抜きの点が推奨電圧。]

読み方: 候補モータの縦棒が、手持ち（購入予定）の ESC の横線より下に入っていればよい。帯はどの Kv でも存在する。
つまり Kv を決めると電圧が決まり、ESC のセル数クラスが決まる、という順で決まる。

== 候補の比較

#if cands.len() == 0 [
  #note[候補モータのカタログ（`src/propmotor/data/catalog/motors.toml`）を作成中。作成後 `make_figures.py` を再実行するとこの節に表と図が入る。]
] else [
  *国内で購入できる*（Amazon.co.jp、国内ラジコン通販、メーカー日本向け通販）ことを条件に、モータ #val.n_motors 個・ESC #val.n_escs 個を評価した
  （調査 2026-11、カタログ値。はんだ付けが必要な基板型 ESC は除外）。各モータには、必須条件をすべて満たし、推奨条件の違反が最少で、
  電流定格が最小の ESC を組み合わせている（大きすぎる ESC は電流分解能とコストの点で不利なだけ）。
  #let yen(x) = if x == none { "—" } else { "¥" + str(x) }
  #figure(
    text(size: 8.3pt, table(
      columns: 9,
      align: (right, left, right, right, right, right, right, right, left),
      stroke: none,
      inset: (x: 3.2pt, y: 2.6pt),
      table.hline(stroke: 0.6pt),
      [*No.*], [*モータ（入手先）*], [*Kv*], [*R* \[Ω\]], [*I₀* \[A\]], [*推奨 V*], [*$I_m$* \[A\]], [*損失* \[W\]], [*組み合わせ ESC*],
      table.hline(stroke: 0.4pt),
      ..cands.enumerate().map(((i, c)) => (
        [#(i + 1)], [#c.motor \ #text(size: 7pt, fill: rgb("#52514e"))[#c.jp_shop #yen(c.price_jpy)]], [#f(c.kv, d: 0)],
        [#f(c.r_ohm, d: 3)], [#f(c.i0_a, d: 2)], [#f(c.v_set, d: 1)], [#f(c.i_motor, d: 1)], [#f(c.p_motor_loss, d: 1)],
        [#c.esc.replace("Hobbywing ", "")],
      )).flatten(),
      table.hline(stroke: 0.6pt),
    )),
    caption: [国内入手可能な候補（No. は選定マップの番号）。$I_m$ と損失（銅損＋無負荷損）は設計モデル・巻線 60 °C、上限回転時。],
  )
  #fig("figures/compatibility.svg")[モータ × ESC の適合表（国内入手可能品）。Skywalker 20A（2–3S）は電圧上限（12.6 V × 0.9）のため Kv 1150 のモータとしか組めない。「注意」は回生（ブレーキ/フリーホイール）を OFF にできるか未確認、またはモータ側コネクタの付いていない ESC。]
  #fig("figures/candidates.svg")[候補ごとの主要指標（上限回転。電圧・電流・損失は設計モデル、効率は公称モデル）。縦線は電流定格の 70 %。]
  #fig("figures/candidates_power.svg", w: 78%)[候補ごとの、上限回転での電力の行き先（公称モデル）。]
]

== 推奨構成と、判断の根拠 <sec:recommend>

どの候補も必須条件は満たす（この試験は 2212 級には軽い負荷である）。差が出るのは次の二次的な観点で、ここは人の判断になる。

+ *回生の扱い*: PWR401L は逆電流を吸えないので、ブレーキとアクティブフリーホイールを *OFF にできることが取扱説明書で確認できる* ESC を選ぶ
  （Hobbywing Skywalker V2、OK模型 TAHMAZO R-30）。詳細は `safety.pdf`。
+ *はんだ付けなしで組める*: ESC のモータ側に 3.5 mm バレットが付いていて、モータ側も 3.5 mm バレットなら挿すだけ。ESC の電源側が裸線でも、レバー式コネクタ（WAGO 221 等）で XT60 付きケーブルにつなげる。
+ *発熱の余裕*: モータ定数 $K_m$ が大きいほど損失が小さく、長いスイープでも巻線温度とその変化（$R$ の変化）が小さい。
+ *取付*: 1585 は M2–M4、ピッチ 56 mm 以下。候補は 16×16 または 16×19 mm・M3 で問題ない。プロペラはモータのアダプタ軸径に合う APC SF リング（LPARM12SF: 3/5/6 mm）。
+ *入手性・価格*。

#key[
  *推奨:* *#ref.motor*（#ref.motor_shop、¥#ref.motor_price_jpy）＋ *#ref.esc*（#ref.esc_shop、¥#ref.esc_price_jpy）、電源 *#f(ref.v_set, d: 1) V*（成立範囲 #f(ref.v_band.at(0), d: 1)–#f(ref.v_band.at(1), d: 1) V）。
  - 国内候補で $K_m$ が最大級（#f(ref.km * 1000, d: 1) mN·m/√W、2316 サイズ）で、上限回転のモータ損失が小さい。
  - モータの 3.5 mm バレットが ESC のモータ側バレットにそのまま挿さる。ESC は取説でブレーキ Disabled（出荷時）・アクティブフリーホイール OFF が設定できる。
  - 上限回転でのモータ電流 #f(ref.design.i_motor, d: 1) A（設計モデル）、電源電流 #f(ref.nominal.i_in, d: 1) A、入力 #f(ref.nominal.p_in, d: 0) W。PWR401L・1585 の定格に対して十分小さい。
  - 対抗馬: SunnySky X2216-880（$K_m$ 最大、Amazon。類似品に注意）、T-Motor AS2312-1150 ＋ Skywalker 20A V2（約 10 V。3S の ESC で済む）。
  - 要確認: モータ付属のプロペラアダプタの軸径（→ APC リングの径）。ESC のプログラムは別売の PG-CARD（セキド ¥1,760）が楽。
]

#fig("figures/power_breakdown.svg")[基準構成（#ref.motor, #f(ref.v_set, d: 1) V）の上限回転での電力の行き先。]

= 試験計画への示唆 <sec:test>

== スタンドの計測不確かさ

1585 の推力・トルクの公差は「読み値の 0.5 % ∓ 0.001（kgf, N·m）」である。本プロペラのトルクは最大でも 0.06 N·m 台なので、
*絶対項 0.001 N·m が効いて、低回転のトルク（$C_P$）の精度が悪い*。

#fig("figures/measurement_uncertainty.svg")[予測トルクと公差（左、対数軸）、$C_T$・$C_P$ の相対不確かさ（右）。公差は偏りとして扱い、平均化で減らないものとした。]

- $C_P$ が ±10 % 以内に入るのはおおむね 4,000 rpm 以上。低回転側は参考値として扱う。
- 各スイープの前後で、ゼロ点（風のない静止状態）を記録してドリフトを差し引く。トルクは付属の校正治具で校正する。
- 電気入力 $V_"in" I_"in"$ は精度よく測れるので、モータモデル（次項で同定）で軸動力を推定し、トルク計測とクロスチェックできる。

== プロペラなしスイープ（タレ）

測定されるトルクは「プロペラのトルク＋ロータ（ベル）の風損」である（軸受摩擦はロータ–ステータ間の内力なので、スタンドの反力には現れない）。
プロペラを外して同じ回転数スイープを行うと、ロータ風損と $I_0(omega)$ が同時に得られる。前者はプロペラ試験の値から差し引き、後者はモータモデルの同定に使う。

== 実施上の注意

- 回転数の各ステップで 2–3 秒以上保持し、定常値を平均する（スタンドのサンプリングは最大 80 Hz 程度）。
- 気温・気圧・湿度を記録して $rho$ を求め、係数化に使う。
- セーフティ・カットオフ: 回転数 #f(val.rpm_limit, d: 0) rpm、電流は最大予測値の 1.5 倍程度、モータ温度。
- プロペラは床・壁から十分離し（直径の数倍）、エンクロージャ内で回す。

= ソフトウェアの使い方

#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: (x: 6pt, y: 4pt),
  table.hline(stroke: 0.6pt),
  [*ファイル*], [*役割*],
  table.hline(stroke: 0.4pt),
  [`src/propmotor/propeller.py`], [APC `.dat`・UIUC 実測の読み込み、$C_T(n), C_P(n)$、FM、設計用包絡],
  [`motor.py`, `esc.py`, `source.py`], [モータ 1 次モデル、ESC 平均化モデル、電源（PSU・LiPo）],
  [`system.py`], [運転点ソルバ（回転数→duty、duty→回転数、到達最大回転数、所要電圧）],
  [`selection.py`], [試験仕様 `TestSpec`、制約チェック `evaluate`、選定マップ `kv_voltage_map`],
  [`stand.py`, `regen.py`], [1585 の定格と公差モデル、回生の見積り],
  [`plotting.py`], [この文書の図すべて],
  [`notebooks/selection.py`], [VS Code で `# %%` セルごとに実行して、図を見ながら選定する],
  [`scripts/make_figures.py`], [この文書の図と数値を再生成],
  table.hline(stroke: 0.6pt),
)

```
PIP_USER=0 .venv/bin/pip install -e ".[dev,notebook]"   # ~/.pip/pip.conf の user=true を回避
.venv/bin/python scripts/make_figures.py                # 図と数値を再生成
typst compile docs/main.typ                             # この PDF
.venv/bin/pytest                                        # 物理モデルのテスト
```

= 付録

== 記号

#table(
  columns: (auto, 1fr, auto),
  stroke: none,
  inset: (x: 6pt, y: 3pt),
  table.hline(stroke: 0.6pt),
  [*記号*], [*意味*], [*単位*],
  table.hline(stroke: 0.4pt),
  [$n, omega$], [回転数（$omega = 2 pi n$）], [rev/s, rad/s],
  [$D, A$], [プロペラ直径、円板面積], [m, m²],
  [$C_T, C_P$], [推力係数、パワー係数（$n$ 基準）], [—],
  [$K_v, K_t, K_m$], [速度定数、トルク定数 $= 1\/K_v$、モータ定数 $K_t\/sqrt(R)$], [rad/s/V, N·m/A, N·m/√W],
  [$R, I_0$], [巻線線間抵抗、無負荷電流], [Ω, A],
  [$d$], [ESC の duty], [—],
  [$V_"set", R_s$], [電源設定電圧、電源〜ESC 間の直列抵抗], [V, Ω],
  [$V_"in", I_"in"$], [ESC 入力（スタンドが測る電気量）], [V, A],
  [$V_m, I_m$], [モータ端子の平均電圧、モータ（相）電流], [V, A],
  table.hline(stroke: 0.6pt),
)

== 参考文献・データ

+ M. Drela, "First-Order DC Electric Motor Model," MIT Aero & Astro, 2007.
+ J. G. Leishman, _Principles of Helicopter Aerodynamics_, 2nd ed., Cambridge Univ. Press, 2006（運動量理論、FM）.
+ J. B. Brandt, R. W. Deters, G. K. Ananda, O. D. Dantsker, M. S. Selig, UIUC Propeller Data Site, Vol. 1, https://m-selig.ae.illinois.edu/props/propDB.html
+ APC Propellers, Performance data `PER3_8x38SF.dat`; RPM limits, https://www.apcprop.com/technical-information/rpm-limits
+ Tyto Robotics, Series 1585 Thrust Stand Datasheet, V2.4, 2024.
+ 菊水電子工業, PWR-01 シリーズ 取扱説明書.
