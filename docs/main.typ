#import "template.typ": *

#let val = json("generated/values.json")
#let cands = json("generated/candidates.json")
#let ref = val.reference
#let vs = val.validation_summary
#let sp = val.spec

#show: report.with(
  title: [APC 8×3.8SF 静止推力試験の駆動系選定],
  subtitle: [電源電圧・モータ・ESC を物理から決める],
  date: [2026.11.5],
)

= 序論

本書の目的は、APC 8×3.8SF プロペラの静止状態における推力 $T$ とトルク $Q$ を、回転数 0 から APC の許容上限
#fmt(val.rpm_limit, d: 0) rpm までの全域で測定するために、電源電圧・モータ・ESC を決めることである。
測定には Tyto Robotics Series 1585 推力スタンドを用い、電源には菊水 PWR401L（0–40 V, 0–40 A, 400 W）を用いる。
モータと ESC は国内で購入できる市販品から選ぶ。

選定の筋道は次のとおりである。試験中のエネルギーは電源から ESC、モータを経てプロペラへ流れ、
隣り合う要素は電力の保存と回路方程式で結ばれている。そこで、まずプロペラが各回転数で要求するトルクを求め（@sec:prop）、
次にそのトルクを生むためにモータが要求する電流と電圧を求め（@sec:motor）、さらにその電圧を作るために ESC が要求する
duty と電源電圧を求める（@sec:esc）。こうして運転点が電源電圧・モータ定数・duty の関数として閉じた形で表せるので、
各部品の定格と制御上の余裕を不等式として課せば、成立する組合せの範囲が選定基準として得られる（@sec:select）。
回生と非常停止を含む安全設計は別冊「推力試験の安全設計」にまとめた。

#figure(
  table(
    columns: (22%, 1fr),
    toprule,
    [項目], [条件],
    midrule,
    [プロペラ], [APC 8×3.8SF（直径 $D$ = 0.2032 m、2 枚翼）],
    [試験範囲], [前進速度 0、回転数 0–#fmt(val.rpm_limit, d: 0) rpm],
    [電源], [菊水 PWR401L],
    [推力スタンド], [Tyto Robotics Series 1585（推力 ±5 kgf、トルク ±2 N·m、50 V、55 A）、光学式回転計],
    [空気密度], [$rho$ = #fmt(val.rho, d: 3) kg/m³（20 °C、101.3 kPa、相対湿度 50 %。試験当日の値で計算し直す）],
    botrule,
  ),
  caption: [前提条件],
)

= プロペラが要求する負荷 <sec:prop>

== 運動量理論と理想動力

静止したロータを、面積 $A = pi D^2 \/ 4$ の円板が空気に一様な圧力差を与えるものとみなす（アクチュエータ・ディスク）。
円板を通過する流速を $v_i$、十分下流の後流速度を $w$ とすると、質量流量は $dot(m) = rho A v_i$ である。
円板と後流を囲む検査体積に運動量保存則を適用すると推力は $T = dot(m) w$、エネルギー保存則を適用すると円板が空気にする仕事率は
$P = dot(m) w^2 \/ 2$ となる。一方、円板上の仕事率は推力と通過速度の積 $T v_i$ でもあるから、$dot(m) w v_i = dot(m) w^2 \/ 2$ より
$w = 2 v_i$ を得る。これらを組み合わせると

$ T = 2 rho A v_i^2, quad P_"ideal" = T v_i = T^(3\/2) / sqrt(2 rho A) $ <eq:momentum>

となる。@eq:momentum は損失のない理想ロータが推力 $T$ を出すのに必要な最小の動力であり、実際の軸動力 $P$ はこれより大きい。
その比

$ "FM" = P_"ideal" / P $ <eq:fm>

をフィギュア・オブ・メリットと呼び、静止ロータの効率を表す。本プロペラでは $A$ = #fmt(val.disk_area, d: 4) m² であり、
上限回転数における推力 #fmt(val.uiuc.thrust_n) N に対して $P_"ideal"$ = #fmt(val.p_ideal_lim, d: 1) W、実際の軸動力は
#fmt(val.uiuc.power_w, d: 1) W であるから FM ≈ #fmt(val.uiuc.fm_lim) となる。残りは翼の形状抗力、翼端損失、旋回流によって失われる。

== 無次元係数と相似則

推力は空気密度 $rho$、回転数 $n$ [rev/s]、直径 $D$、前進速度 $V$、粘性係数 $mu$、音速 $a$ で決まる。
基本次元は質量・長さ・時間の 3 つであるから、バッキンガムの $Pi$ 定理により 7 変数の関係は 4 個の無次元数の関係に縮約され、

$ C_T eq.def T / (rho n^2 D^4) = f(J, "Re", M), quad C_P eq.def P / (rho n^3 D^5) = g(J, "Re", M) $ <eq:coef>

と書ける。ここで $J = V \/ (n D)$ は前進率、Re はレイノルズ数、$M$ はマッハ数である。静止試験では $J = 0$ であり、
上限回転数でも翼端マッハ数は #fmt(val.tip_mach_lim) にとどまるから圧縮性は無視できる。したがって形状の決まったプロペラでは
$C_T$ と $C_P$ はレイノルズ数、すなわち回転数だけの関数になる。トルクは $Q = P \/ (2 pi n)$ より

$ T = C_T rho n^2 D^4, quad Q = C_P / (2 pi) rho n^2 D^5, quad P = C_P rho n^3 D^5 $ <eq:load>

で与えられる。$C_T$ と $C_P$ の変化が小さい範囲では $T$ と $Q$ は $n^2$ に、$P$ は $n^3$ に比例するので、$P prop T^(3\/2)$ となり
@eq:momentum と同じ次数を持つ。また @eq:momentum と @eq:coef から FM を係数で表すと

$ "FM" = C_T^(3\/2) / (sqrt(pi \/ 2) thin C_P) $ <eq:fmcoef>

となる。

== 係数のデータとその検証

$C_T(n)$ と $C_P(n)$ の値として、APC 社が翼素理論と翼型極曲線から計算した公表値（`PER3_8x38SF.dat`）と、
イリノイ大学の風洞スタンドで測定された値（UIUC Propeller Data Site Vol. 1、#fmt(val.uiuc.rpm_range.at(0), d: 0)–#fmt(val.uiuc.rpm_range.at(1), d: 0) rpm）が得られる。
@fig:coef に両者を示す。7,000 rpm において APC の値は実測に比べ $C_T$ で
#fmt((val.apc.ct_7000 / val.uiuc.ct_7000 - 1) * 100, d: 0) %、$C_P$ で #fmt((val.apc.cp_7000 / val.uiuc.cp_7000 - 1) * 100, d: 0) % 大きい。
また実測の $C_T$ と $C_P$ は回転数とともに増加するが、理論値はほぼ一定である。翼弦長基準のレイノルズ数は $10^4$–$10^5$ の範囲にあり、
この領域では翼型の揚抗比がレイノルズ数とともに大きく改善するので、実測の傾向はこれと整合する。

#figure(image("figures/prop_coefficients.svg", width: 100%),
  caption: [静止状態の $C_T$、$C_P$、FM。橙は APC 公表値、青は UIUC 実測値（点）。点線は測定範囲外で、高回転側は最上位 6 点の直線による外挿、低回転側は端の値を保持したもの。]) <fig:coef>

どちらのデータが正しいかは、独立な第三者の測定と比べれば判定できる。Scorpion、Cobra、SunnySky の各社は同じ APC 8×3.8SF を
自社モータで回した試験値を公表している。推力は @eq:load により回転数だけで決まるので、測定された回転数で推力を計算すれば
プロペラモデルを直接検証できる。また全開運転では電源電流がモータ電流にほぼ等しいので、@sec:motor の
モータモデルと組み合わせて電流を比べれば $C_P$ も検証できる。@fig:valid に結果を示す。UIUC 実測に基づくモデルは
推力で #fmt(vs.uiuc_thrust.at(0) * 100, d: 1)–+#fmt(vs.uiuc_thrust.at(1) * 100, d: 1) %、電流で
#fmt(vs.uiuc_current.at(0) * 100, d: 1)–+#fmt(vs.uiuc_current.at(1) * 100, d: 1) % の範囲でメーカー値と一致し、
APC の値は推力を #fmt(vs.apc_thrust.at(0) * 100, d: 0)–#fmt(vs.apc_thrust.at(1) * 100, d: 0) % 過大に見積もる。

#figure(image("figures/validation.svg", width: 100%),
  caption: [同じプロペラを用いたメーカー試験値に対するモデルの比（$rho$ = 1.2 kg/m³ を仮定）。]) <fig:valid>

この結果から、試験結果の予測には UIUC 実測に基づくモデルを用い、これを公称モデルと呼ぶ。一方、@sec:select で課す不等式は
いずれもトルクが大きいほど厳しくなる（電流と所要電圧がトルクとともに増える）ので、部品の大きさを決める際には各回転数で
二つのデータの大きい方を採る設計モデルを用いる。本プロペラでは設計モデルは結果的に APC 公表値と一致する。

== 試験の最大点

APC は Slow Flyer 系プロペラの最大回転数を $65,000 \/ D["in"]$ rpm と定めており、8 in では #fmt(val.rpm_limit, d: 0) rpm となる。
SF 系は薄く柔らかい低速機用の翼であり、遠心力と曲げ変形によって破損する回転数が低いためである。試験はこの回転数までとする。
@eq:load から求めたこの回転数での負荷を @tab:max に、回転数全域の負荷を @fig:load に示す。この最大点が、
試験系が作り出さなければならない最も厳しい運転点である。

#figure(
  table(
    columns: 5,
    align: (left, right, right, right, right),
    toprule,
    [], [推力], [トルク], [軸動力], [FM],
    midrule,
    [公称モデル（UIUC）], [#fmt(val.uiuc.thrust_gf, d: 0) gf], [#fmt(val.uiuc.torque_nm * 1000, d: 1) mN·m], [#fmt(val.uiuc.power_w, d: 1) W], [#fmt(val.uiuc.fm_lim)],
    [設計モデル（APC）], [#fmt(val.apc.thrust_gf, d: 0) gf], [#fmt(val.apc.torque_nm * 1000, d: 1) mN·m], [#fmt(val.apc.power_w, d: 1) W], [#fmt(val.apc.fm_lim)],
    botrule,
  ),
  caption: [上限回転数 #fmt(val.rpm_limit, d: 0) rpm における負荷],
) <tab:max>

#figure(image("figures/prop_dimensional.svg", width: 100%),
  caption: [推力・トルク・軸動力。縦線は APC の上限回転数。]) <fig:load>

プロペラの質量は 7.1 g、ハブの軸穴は 1/4 in で、裏面に直径 8 mm の座ぐりがある。モータのプロペラアダプタの軸径に合わせて
APC の SF 用アダプタリング（LPARM12SF、3/5/6 mm）を挿入して芯出しする。

= モータ <sec:motor>

== 1 次モデルの導出

ブラシレスモータを ESC で整流すると、線間の平均量について直流モータと同じ関係が成り立つ。巻線が角速度 $omega$ で磁界を横切ると、
ファラデーの法則により回転数に比例する逆起電力 $E = k_e omega$ が生じる。同じ巻線に電流 $I$ が流れると、ローレンツ力により
電流に比例する電磁トルク $Q_"em" = k_t I$ が生じる。電気から機械へ変換される電力は $E I$ と $Q_"em" omega$ の両方で表されるので、
$k_e omega I = k_t I omega$ から $k_t = k_e$ が導かれる。カタログに記載される速度定数 $K_v$ はこの逆数であり（rpm/V の値に $pi \/ 30$ を掛けると SI 単位の rad/s/V になる）、

$ E = omega / K_v, quad K_t = 1 / K_v $ <eq:kt>

である。端子電圧 $V_m$ は逆起電力と巻線抵抗 $R$ の電圧降下の和であり、軸トルクは電磁トルクから鉄損・軸受摩擦・ロータ風損による
損失トルクを引いたものになる。損失トルクを電流 $I_0$（無負荷電流）に換算して書くと、

$ V_m = omega / K_v + I R, quad Q = K_t (I - I_0) $ <eq:motor>

を得る（Drela の 1 次モデル）。入力 $V_m I$ に @eq:motor を代入すると $V_m I = Q omega + I^2 R + I_0 E$ となり、入力は軸出力・銅損・無負荷損に分かれる。
したがって効率は

$ eta_m = (Q omega) / (V_m I) = (1 - I_0 / I)(1 - (I R) / V_m) $ <eq:eta>

である。電流が小さいと第 1 因子が、大きいと第 2 因子が効率を下げる。

== 運転点

ESC がモータに電圧 $V_m$ を与えているとき、@eq:motor から $I$ を消去すると、モータが出せるトルクは

$ Q_m (omega) = K_t [(V_m - omega \/ K_v) / R - I_0] $ <eq:line>

であり、回転数とともに直線的に減少する。一方、プロペラが要求するトルク $Q_p (omega)$ は @eq:load より回転数の 2 乗で増加する。
定常状態ではロータの角運動量が一定なので $Q_m = Q_p$ が成り立ち、減少関数と増加関数の交点として運転点がただ一つ定まる（@fig:match）。
@eq:line の傾きの大きさは $K_t \/ (K_v R) = 1 \/ (K_v^2 R)$ であり、巻線抵抗の小さいホビー用モータでは非常に大きい。
そのため回転数は負荷にほとんど依存せず $omega approx K_v V_m$ で決まり、負荷トルクは主として電流を決める。

#figure(image("figures/matching.svg", width: 80%),
  caption: [モータ特性線（duty 一定、灰色）とプロペラ負荷線の交点としての運転点（#ref.motor、電源 #fmt(ref.v_set, d: 1) V）。]) <fig:match>

== 巻線の相似則と Kv の意味

同じステータと磁石を用い、巻数 $N$ だけを $k$ 倍に変えたモータを考える。逆起電力は巻数に比例するので $K_v$ は $1 \/ k$ 倍になる。
同じ巻線スペースに $k$ 倍の巻数を収めると、線の長さが $k$ 倍、断面積が $1 \/ k$ 倍になるので、$R$ は $k^2$ 倍になる。したがって
モータ定数

$ K_m eq.def K_t / sqrt(R) $ <eq:km>

は巻数に依存しない。銅損は @eq:motor で $I_0$ を無視すると $I^2 R = (Q \/ K_t)^2 R = (Q \/ K_m)^2$ となるから、同じトルクを出すときの
銅損は $K_m$ だけで決まる。鉄損も同じ回転数では巻数によらない。つまり、ステータの大きさ（$K_m$）が損失と発熱を決め、
Kv は同じ機械出力を高電圧・小電流で作るか低電圧・大電流で作るかの配分を決めるにすぎない（@fig:kvtrade）。
安定化電源は電圧を連続に設定できるので、どの Kv に対しても所要電圧を合わせることができる。ここから選定は二段に分かれる。
第一に最大トルクでの損失 $(Q \/ K_m)^2 + I_0 E$ が許容できる大きさのモータを選び、第二に所要電圧が ESC と電源の範囲に入るように Kv を選ぶ。
本プロペラの最大トルク #fmt(val.apc.torque_nm * 1000, d: 0) mN·m に対し、$K_m approx$ 0.03 N·m/√W の 2212 級モータで銅損は約 5 W であり、
2212–2316 級で十分である。

#figure(image("figures/kv_tradeoff.svg", width: 100%),
  caption: [同じフレームで巻数だけを変えたときの所要電源電圧・電流・損失（上限回転数、設計 duty 80 %）。損失は一定で、電圧と電流が入れ替わる。]) <fig:kvtrade>

#figure(image("figures/efficiency_map.svg", width: 80%),
  caption: [#ref.motor の効率マップとプロペラ負荷線。試験中の運転点は負荷線の上を移動する。]) <fig:effmap>

カタログ値の扱いについて述べておく。$R$ は多くのメーカーで線間値であるが表記の曖昧なものがあり、$I_0$ は測定電圧（8–12 V）が
メーカーごとに異なる。そこで本書ではカタログ値を公称値として選定に用い、購入後にスタンドで $K_v$、$R$（4 端子法、線間）、$I_0 (omega)$
を測定し直すことを前提とする。

= ESC と電源 <sec:esc>

== ESC の平均化モデル

ESC は 6 個の MOSFET からなる三相ブリッジで常に 2 相に通電し、通電相を 60° ごとに切り替える。通電相の電圧は数十 µs 周期の PWM で
刻まれ、デューティ比 $d$ で平均電圧が調整される。モータのインダクタンスによって電流は PWM 周期内でほぼ一定に保たれるので、
1 周期で平均すると、モータに加わる平均電圧は入力電圧の $d$ 倍から導通経路の電圧降下を引いたものになる。導通している 2 個の MOSFET
と配線の抵抗を $R_"on"$ とすると、

$ V_m = d V_"in" - I_m R_"on" $ <eq:escv>

である。ESC 内部に電力を蓄える要素はないので、入力電力は出力電力と ESC の損失の和に等しい。@eq:escv を用いると
$V_"in" I_"in" = (V_m + I_m R_"on") I_m + V_"in" I_q = d V_"in" I_m + V_"in" I_q$ となり、

$ I_"in" = d I_m + I_q $ <eq:esci>

を得る（$I_q$ は制御回路の消費電流）。すなわち部分スロットルでは電源側の電流はモータ電流より小さい。スタンドが測るのは
$V_"in"$ と $I_"in"$ であり、モータの定格と銅損に関係するのは $I_m$ である。

== 電源と系の閉じ方

電源は開放電圧 $V_"set"$ と、配線・コネクタ・スタンドのシャント抵抗をまとめた直列抵抗 $R_s$ で表す。

$ V_"in" = V_"set" - I_"in" R_s $ <eq:src>

回転数を与えると、@eq:load から $Q$ が、@eq:motor から $I_m$ と $V_m$ が直接決まる。残る未知数 $d$ は、@eq:escv から @eq:src を
連立して $V_"in"$ と $I_"in"$ を消去すると

$ -I_m R_s thin d^2 + (V_"set" - I_q R_s) thin d - (V_m + I_m R_"on") = 0 $ <eq:duty>

の小さい方の根として求まる。実根がなければ、その回転数に必要な電力を電源が供給できないことを意味する。逆に duty を与えたときの
回転数は、$d$ が回転数の単調増加関数であることから 1 次元の求根で求まる。@fig:throttle に duty に対する回転数・推力・電流を示す。
@sec:motor で述べたとおり回転数は duty にほぼ比例し、推力と電流はその 2 乗で増える。

#figure(image("figures/throttle.svg", width: 100%),
  caption: [duty に対する回転数・推力・電流（#ref.motor、電源 #fmt(ref.v_set, d: 1) V）。実線はモータ電流 $I_m$、点線は電源側電流 $I_"in"$。]) <fig:throttle>

ESC は 1585 から標準サーボ PWM（50 Hz、1000–2000 µs）で駆動されるので、この信号を受け付けることが必要である。また
PWR401L は電流を吸い込めないため、ESC が回生しない設定（ブレーキとアクティブフリーホイールの無効化）を持つことが必要である。
この条件の導出は別冊の安全設計で行う。

= 選定基準 <sec:select>

== 最大点に課す不等式

前節までで、運転点は電源電圧 $V_"set"$、モータ定数 $(K_v, R, I_0)$、duty の関数として求まった。ここに試験の要求と部品の定格を
不等式として課す。まず、試験の最大回転数 $n_"max"$ を設計モデルの負荷で duty $d_1$ 以下で実現できなければならない。

$ d(n_"max"; "設計") <= d_1 = #sp.duty_design_max $ <eq:c1>

$d_1 < 1$ とする理由は、外挿した $C_P$、カタログ値の $R$、配線抵抗の不確かさに対して制御の余裕を残すためである。@eq:motor と @eq:escv
で $R_s$ を無視すると、@eq:c1 は電源電圧の下限

$ V_"set" >= (n_"max" \/ K_v + I_m (R + R_"on")) / d_1, quad I_m = Q_"max" K_v + I_0 $ <eq:vlow>

を与える。次に、電源電圧が高すぎると最大回転数でも duty が小さくなり、スロットル分解能が下がるうえ、PWM 電流リップル
（$prop V_"in" d (1 - d)$）とスイッチング損失が増え、低回転端ではセンサレス制御が不安定になる。そこで公称モデルの最大点で

$ d(n_"max"; "公称") >= d_2 = #sp.duty_nominal_min $ <eq:c2>

を課す。これは電源電圧の上限を与える。電流については、@eq:motor と @eq:kt から最大点のモータ電流が $I_m = Q_"max" K_v + I_0$ となり、
Kv に比例して増えることが分かる。試験は定常運転を長時間繰り返すので、モータの定格電流の #pct(sp.motor_i_frac)、ESC の連続定格の
#pct(sp.esc_i_frac) 以下とする（巻線温度 #fmt(sp.winding_temp_c, d: 0) °C の抵抗で評価する）。最後に、設定電圧は ESC の定格電圧の
#pct(sp.esc_v_frac) 以下、電源とスタンドの定格以内とする。推奨電圧は、設計モデルで最大回転数の duty が #pct(sp.duty_target) になる電圧とした。

== 選定マップ

@eq:c1 と @eq:c2 は電源電圧の下限と上限を与え、@eq:km の相似則により同じ大きさのモータでは Kv と電圧だけが自由度である。
したがって Kv–電圧平面に両方の境界を描くと、成立する組合せは帯状の領域になる（@fig:map）。下限は @eq:vlow のとおりおおよそ
$1 \/ K_v$ に比例する。帯は任意の Kv に存在するので、Kv を決めると電圧が決まり、電圧が決まると ESC のセル数クラスが決まる。

#figure(image("figures/kv_v_map.svg", width: 92%),
  caption: [選定マップ。色の帯が成立領域（色は最大回転数での公称 duty）、破線が推奨電圧。横線は各セル数用 ESC の定格電圧の 90 %。黒い縦棒は候補モータの成立電圧範囲、白抜きの点は推奨電圧で、番号は @tab:cand に対応する。]) <fig:map>

== 国内入手可能品の評価

国内で購入できる（Amazon.co.jp、国内ラジコン通販、メーカーの日本向け通販で扱いがある）ことを条件に、モータ #val.n_motors 個と
ESC #val.n_escs 個を評価した。各モータには、必須条件をすべて満たし、推奨条件の違反が最も少なく、電流定格が最も小さい ESC を組み合わせた。
推奨条件には、回生を無効化できることが取扱説明書で確認できることと、モータ側の配線がはんだ付けなしで接続できることを含めた。
結果を @tab:cand と @fig:compat に示す。

#let yen(x) = if x == none { "—" } else { "¥" + str(x) }
#figure(
  text(size: 8.5pt, table(
    columns: 9,
    align: (right, left, right, right, right, right, right, right, left),
    inset: (x: 3.2pt, y: 2.8pt),
    toprule,
    [No.], [モータ（入手先）], [Kv], [$R$ [Ω]], [$I_0$ [A]], [推奨 V], [$I_m$ [A]], [損失 [W]], [組み合わせる ESC],
    midrule,
    ..cands.enumerate().map(((i, c)) => (
      [#(i + 1)], [#c.motor \ #text(size: 7pt, fill: rgb("#52514e"))[#c.jp_shop #yen(c.price_jpy)]], [#fmt(c.kv, d: 0)],
      [#fmt(c.r_ohm, d: 3)], [#fmt(c.i0_a, d: 2)], [#fmt(c.v_set, d: 1)], [#fmt(c.i_motor, d: 1)], [#fmt(c.p_motor_loss, d: 1)],
      [#c.esc.replace("Hobbywing ", "")],
    )).flatten(),
    botrule,
  )),
  caption: [国内入手可能な候補。$I_m$ と損失（銅損と無負荷損の和）は設計モデル・巻線 60 °C での最大点の値。],
) <tab:cand>

#figure(image("figures/compatibility.svg", width: 100%),
  caption: [モータと ESC の適合。NG は必須条件の違反、注意は推奨条件の違反を表す。Skywalker 20A V2 は 2–3S 用で電圧上限が 11.3 V となるため、Kv 1150 のモータとしか組めない。]) <fig:compat>

#figure(image("figures/candidates.svg", width: 100%),
  caption: [候補ごとの主要指標（最大点）。縦線は電流定格の 70 %。]) <fig:candm>

== 推奨構成

すべての候補が必須条件を満たした。これは本試験の負荷が 2212 級のモータにとって軽いことによる。したがって候補の優劣は二次的な観点で決まる。
まず ESC は、PWR401L が電流を吸い込めない以上、ブレーキとアクティブフリーホイールを無効化できることが取扱説明書で確認できる
Hobbywing Skywalker V2 系が望ましい。Kv 880–980 のモータでは所要電圧が 12–14 V となり 4S 対応品が必要なので、Skywalker 40A V2 になる。
この ESC はモータ側に 3.5 mm のバレットコネクタが付いており、同径のバレットを持つモータならはんだ付けなしで接続できる。
電源側は裸線であるが、レバー式コネクタ（WAGO 221）で XT60 付きのケーブルに接続できる。次にモータは、損失が小さく長時間の試験で
巻線温度とその変化が小さいもの、すなわち $K_m$ の大きいものが望ましい。

以上から、#ref.motor（#ref.motor_shop、¥#ref.motor_price_jpy）と #ref.esc（#ref.esc_shop、¥#ref.esc_price_jpy）の組合せを推奨し、
電源電圧を #fmt(ref.v_set, d: 1) V（成立範囲 #fmt(ref.v_band.at(0), d: 1)–#fmt(ref.v_band.at(1), d: 1) V）とする。
このモータは $K_m$ = #fmt(ref.km * 1000, d: 1) mN·m/√W で国内候補中最大級であり、3.5 mm バレットを備える。最大点でのモータ電流は
#fmt(ref.design.i_motor, d: 1) A（設計モデル）、電源電流は #fmt(ref.nominal.i_in, d: 1) A、入力電力は #fmt(ref.nominal.p_in, d: 0) W であり、
PWR401L と 1585 の定格に対して十分小さい。損失の内訳を @fig:power に示す。対抗案は、$K_m$ が同等で Amazon で購入できる
SunnySky X2216-880（類似品に注意）と、約 10 V で 3S 用 ESC が使える T-Motor AS2312-1150 と Skywalker 20A V2 の組合せである。
なお Dualsky のプロペラアダプタ軸径は公表されていないため、購入後に測定してアダプタリングの径を決める。

#figure(image("figures/power_breakdown.svg", width: 85%),
  caption: [推奨構成の最大点における電力の行き先。]) <fig:power>

= 測定精度 <sec:accuracy>

係数は測定値から $C_T = T \/ (rho n^2 D^4)$、$C_P = 2 pi Q \/ (rho n^2 D^5)$ として求めるので、誤差の伝播則により相対不確かさは

$ (delta C_T) / C_T = sqrt(((delta T) / T)^2 + (2 (delta n) / n)^2 + ((delta rho) / rho)^2) $ <eq:unc>

となり、$C_P$ についても $T$ を $Q$ に置き換えた同じ式が成り立つ。1585 の推力とトルクの公差は「読み値の 0.5 % と 0.001（kgf、N·m）の和」
であり、絶対項 0.001 N·m は本プロペラの低回転のトルクに比べて無視できない。@fig:unc に示すように、$C_P$ の不確かさが 10 % を下回るのは
およそ 4,000 rpm 以上であり、それより低い回転数の $C_P$ は参考値として扱う。$C_T$ は 2,000 rpm 以上で 5 % 以内に収まる。
また測定されるトルクにはプロペラのトルクに加えてロータ（ベル）の風損が含まれる（軸受摩擦はロータとステータの間の内力なので
スタンドの反力には現れない）。プロペラを外した同じ回転数のスイープを行えば、この風損と $I_0 (omega)$ を同時に求めることができる。

#figure(image("figures/measurement_uncertainty.svg", width: 100%),
  caption: [予測トルクと 1585 の公差（左、対数軸）および係数の相対不確かさ（右）。回転数 0.2 %、密度 1 % を仮定。]) <fig:unc>

#heading(numbering: none)[付録 A　記号]

#table(
  columns: (auto, 1fr, auto),
  toprule,
  [記号], [意味], [単位],
  midrule,
  [$n, omega$], [回転数（$omega = 2 pi n$）], [rev/s, rad/s],
  [$D, A$], [プロペラ直径、円板面積], [m, m²],
  [$C_T, C_P$], [推力係数、パワー係数（$n$ 基準）], [—],
  [$K_v, K_t, K_m$], [速度定数、トルク定数、モータ定数], [rad/s/V, N·m/A, N·m/√W],
  [$R, I_0$], [巻線の線間抵抗、無負荷電流], [Ω, A],
  [$d$], [ESC の duty], [—],
  [$V_"set", R_s$], [電源の設定電圧、電源から ESC までの直列抵抗], [V, Ω],
  [$V_"in", I_"in"$], [ESC の入力電圧・電流（スタンドが測る量）], [V, A],
  [$V_m, I_m$], [モータ端子の平均電圧、モータ電流], [V, A],
  botrule,
)

#heading(numbering: none)[付録 B　ソフトウェア]

本書の数値と図はすべて `scripts/make_figures.py` が `src/propmotor` のモデルから生成したものである。プロペラデータの読み込みは
`propeller.py`、モータ・ESC・電源のモデルは `motor.py`、`esc.py`、`source.py`、@eq:duty による運転点の計算は `system.py`、
@sec:select の判定と選定マップは `selection.py` にある。候補の追加は `src/propmotor/data/catalog/*.toml` に記入し、
`notebooks/selection.py` を VS Code でセルごとに実行すると、図を見ながら候補を比較できる。

#heading(numbering: none)[参考文献]

#set enum(numbering: "[1]")
+ M. Drela, "First-Order DC Electric Motor Model," MIT Aero & Astro, 2007.
+ J. G. Leishman, _Principles of Helicopter Aerodynamics_, 2nd ed., Cambridge University Press, 2006.
+ J. B. Brandt, R. W. Deters, G. K. Ananda, O. D. Dantsker, M. S. Selig, UIUC Propeller Data Site, Vol. 1.
+ APC Propellers, performance data `PER3_8x38SF.dat` and RPM limits.
+ Tyto Robotics, Series 1585 Thrust Stand Datasheet, V2.4, 2024.
+ 菊水電子工業, PWR-01 シリーズ 取扱説明書 IB035086.
