// 推力試験の安全設計と電源系の構成 — 回生・過電流・非常停止
// 数値・図は scripts/make_figures.py が生成する (docs/generated/values.json, docs/figures/)。

#let val = json("generated/values.json")
#let sf = val.safety
#let ref = val.reference

#let f(x, d: 2) = if x == none { "—" } else { str(calc.round(x, digits: d)) }

#set document(title: "推力試験の安全設計と電源系の構成")
#set page(paper: "a4", margin: (x: 20mm, y: 20mm), numbering: "1")
#set text(lang: "ja", font: ("Noto Serif CJK JP",), size: 10pt)
#set par(justify: true, leading: 0.8em, spacing: 1.1em)
#set heading(numbering: "1.1")
#show heading: set text(font: ("Noto Sans CJK JP",), weight: "bold")
#show heading.where(level: 1): it => { v(0.6em); it; v(0.2em) }
#set math.equation(numbering: "(1)")
#show figure.caption: set text(size: 9pt)
#show raw: set text(font: ("DejaVu Sans Mono",), size: 8.5pt)

#let note(body) = block(fill: rgb("#f4f3ef"), inset: 9pt, radius: 3pt, width: 100%, body)
#let key(body) = block(stroke: (left: 2.5pt + rgb("#2a78d6")), inset: (left: 10pt, y: 6pt), width: 100%, body)
#let warn(body) = block(stroke: (left: 2.5pt + rgb("#d03b3b")), inset: (left: 10pt, y: 6pt), width: 100%, body)
#let fig(path, cap, w: 100%) = figure(image(path, width: w), caption: cap)
#let tbl(..args) = text(size: 9pt, table(stroke: none, inset: (x: 5pt, y: 3.5pt), ..args))

#align(center)[
  #text(size: 16pt, font: ("Noto Sans CJK JP",), weight: "bold")[推力試験の安全設計と電源系の構成]
  #v(0.2em)
  #text(size: 10.5pt)[— 回生・過電流・非常停止。市販品の組み合わせで作る —]
  #v(0.4em)
  #text(size: 9pt, fill: rgb("#52514e"))[対象: APC 8×3.8SF 静止推力試験（Tyto 1585、安定化電源、2212 級モータ、ホビー用 ESC）。選定の本体は `main.pdf`。]
]

#v(0.6em)
#outline(depth: 1, indent: 1em)

// <<SUMMARY>>

= 何が危ないか

#tbl(
  columns: (auto, 1fr, 1fr, auto),
  table.hline(stroke: 0.6pt),
  [*ハザード*], [*原因*], [*起きること*], [*主な対策層*],
  table.hline(stroke: 0.4pt),
  [プロペラ破損・飛散], [過回転、締結不良、疲労、異物], [破片が高速で飛ぶ（最も重い人的被害）], [機械的防護、回転数カットオフ],
  [回転体への接触], [不意の始動（ESC アーム）、作業中の誤操作], [切傷], [手順、信号の管理],
  [過電流・短絡], [配線ミス、モータロック、ESC 故障], [配線発熱・発火、電源・ESC 損傷], [電源の電流制限、ヒューズ],
  [*過電圧（回生）*], [ESC が能動的に減速させ、回転体のエネルギーが母線に戻る], [ESC・電源の破損（PWR401L は逆電流を吸えない）], [ESC 設定、運転手順、母線の吸収先],
  [逆接続], [電源極性の取り違え], [ESC の即死], [極性の決まったコネクタ（XT60）],
  [過熱], [長時間の高負荷、冷却不足], [モータ・ESC の劣化、測定値のドリフト], [温度監視、インターバル],
  table.hline(stroke: 0.6pt),
)

= 「ヒューズ＋非常停止」で守れるもの・守れないもの

#tbl(
  columns: (auto, 1fr, 1fr),
  table.hline(stroke: 0.6pt),
  [*装置*], [*守れるもの*], [*守れないもの・注意*],
  table.hline(stroke: 0.4pt),
  [ヒューズ], [短絡・大電流による配線の発火（電源の電流制限が効かなかったときの最後の砦）],
    [*過電圧には無力*（回生は電流が逆向きに小さく流れるだけで、ヒューズは切れない）。溶断に時間がかかるので、電子機器の保護にはならない],
  [非常停止（電源を切る）], [人が「止めたい」ときに確実にエネルギー供給を断つ],
    [プロペラはすぐには止まらない（惰性で約 1 秒）。大電流の直流を普通のスイッチで切るとアークが出る → 直流定格の部品か、電源の出力 OFF 機能を使う],
  [電源の電流制限（CC）], [ロック・短絡時の電流を抑える（最も速く効く過電流保護）], [逆電流・過電圧は防げない],
  table.hline(stroke: 0.6pt),
)

#key[
  つまり *ヒューズと非常停止は「過電流」と「人の判断による停止」の対策で、回生による過電圧には効かない*。
  回生は次節のとおり、*発生源（ESC の設定と運転の仕方）で止める* のが基本で、母線の吸収先は保険として加える。
]

= 回生: いつ・どれだけ起きるか

== しくみ

ESC がモータの電圧 $d V_"in"$ を逆起電力 $E$ より低くすると、モータは発電機になり電流が逆向きに流れる。
ただし逆電流が流れるのは、ESC が *相補 PWM*（BLHeli の "damped light"、Hobbywing の "active freewheeling/DEO"）で
ローサイド・ハイサイドの両方を能動的に切り替えているときだけである。ダイオードで還流する方式（フリーホイール OFF）では、
電流はゼロで止まり、逆には流れない。

- スロットルを *0* にした場合: ホビー用 ESC は全スイッチを OFF にして惰性回転させる（またはブレーキ設定ならモータを短絡して巻線で熱にする）。*どちらも母線には戻らない*。
- スロットルを *急に低い値（0 ではない）* にした場合: 相補 PWM の ESC は回転を能動的に落とし、エネルギーを母線へ押し戻す。*これが危険な場面*。

== シミュレーション

運転点ソルバに回転体の慣性（プロペラ＋ベル、$J approx$ #f(val.regen.j_gcm2, d: 0) g·cm²）と母線の静電容量を加え、
上限回転（duty #f(sf.d0 * 100, d: 0) %）から duty 5 % へ絞ったときの母線電圧を計算した（#ref.motor、電源 #f(sf.v_set, d: 1) V）。

#fig("figures/regen_transient.svg")[左: スロットルを一気に絞ったときの母線電圧。右: 下げきるまでの時間を変えたときの最大値（対策なし）。]

#tbl(
  columns: (1fr, auto),
  table.hline(stroke: 0.6pt),
  [*条件*], [*母線電圧の最大値*],
  table.hline(stroke: 0.4pt),
  ..sf.peaks.pairs().map(((k, x)) => ([#k], [#f(x, d: 1) V])).flatten(),
  [段階的に下げる: 1 段 5 % / 10 % / 20 % / 40 %],
    [#f(sf.step_vpeak.at("0.05"), d: 1) / #f(sf.step_vpeak.at("0.10"), d: 1) / #f(sf.step_vpeak.at("0.20"), d: 1) / #f(sf.step_vpeak.at("0.40"), d: 1) V],
  [スロットル 0（惰性）/ 0（ブレーキ）], [#f(sf.coast_vpeak, d: 1) / #f(sf.brake_vpeak, d: 1) V],
  [非常停止で電源出力を OFF（スロットルはそのまま）], [上昇しない（回転とともに低下）],
  table.hline(stroke: 0.6pt),
)

読み取れること:

+ 何も対策せずにスロットルを急に絞ると、母線は *#f(sf.peak_list.at(0), d: 0) V* に達し、ESC の定格（#f(sf.esc_vmax, d: 1) V）を大きく超える。
  モータには瞬間的に #f(-sf.i_motor_min, d: 0) A の逆電流が流れる。
+ 0.1–0.3 s で下げると、一気に下げるより *悪い*（下げる途中の duty が大きいほど、逆電流が母線に多く流れ込む）。0.7 s 以上かければ影響はない。
+ ESC のフリーホイール（相補 PWM）を OFF にすれば、どう操作しても回生は起きない。*最も効く対策で、費用ゼロ。*
+ 非常停止で電源を切る・スロットルを 0 にする、は回生の点でも安全。

#note[
  モデルの前提: PWM 周期で平均化、モータのインダクタンスは無視、ESC は指令に即応、電源は吸い込み不可（ブリーダ約 0.35 A のみ）。
  実際の ESC には内部の変化率制限があり、ここまで急峻にはならないことが多いが、対策の要否を判断する上では安全側の見積りである。
]

= 対策の比較

#tbl(
  columns: (auto, 1fr, auto, auto),
  table.hline(stroke: 0.6pt),
  [*対策*], [*効果*], [*費用*], [*手間*],
  table.hline(stroke: 0.4pt),
  [ESC 設定: ブレーキ OFF・フリーホイール OFF], [回生の発生源を断つ（決定的）], [0], [設定のみ],
  [運転手順: 下げるときは 1 段 10 % 以下、または 0.7 s 以上かける。止めるときは 0 へ], [回生をほぼゼロにする], [0], [スクリプト],
  [1585 の電圧カットオフ（設定電圧 +1.5 V）], [異常に気づいた瞬間にスロットル 0（惰性）→ 回生停止], [0], [設定のみ],
  [母線コンデンサの追加（低 ESR 電解、35 V 以上）], [短時間の跳ね上がりを緩和（単独では不十分）], [数百円〜], [コネクタ付き品なら無し],
  [電子負荷を CV モードで並列（クランプ）], [設定電圧以上を確実に吸収する（電流は数 A で足りる）], [数万円〜], [配線のみ],
  [吸い込み可能な電源（双方向・2 象限）に変更], [電源自体が回生を吸収する], [数十万円〜], [—],
  [逆流防止ダイオード（電源と母線の間）], [電源を逆電流から守る。ただし回生は ESC 側に閉じ込められ電圧はむしろ上がる → 単独では不可], [数千円], [配線のみ],
  table.hline(stroke: 0.6pt),
)

// <<ARCHITECTURE>>

= 設定値の一覧

#tbl(
  columns: (auto, auto, 1fr),
  table.hline(stroke: 0.6pt),
  [*機器*], [*項目*], [*設定・理由*],
  table.hline(stroke: 0.4pt),
  [電源], [出力電圧], [#f(sf.v_set, d: 1) V（`main.pdf` の推奨。モータ・ESC の組で変わる）],
  [], [電流制限 (CC)], [10 A（最大点の電源電流 #f(sf.i_in_max, d: 1) A の約 2 倍。ロック時の電流を抑える）],
  [], [OVP], [設定電圧 +3 V（回生などの異常で出力を止め、警報にする）],
  [], [出力端子], [*背面端子*（前面は約 10 A で FOCP が動作）],
  [ESC], [ブレーキ], [OFF（Disabled）],
  [], [フリーホイール / DEO / damped light], [OFF（できない ESC は避ける）],
  [], [スロットル範囲], [1585 の 1000–2000 µs に合わせて校正],
  [], [低電圧カット], [OFF（安定化電源なので不要。誤作動の原因になる）],
  [1585], [回転数カットオフ], [8,300 rpm（試験の最高点は 8,100 rpm 程度にする）],
  [], [電流カットオフ], [予測最大の 1.5 倍程度（例: 8 A）],
  [], [電圧カットオフ], [設定電圧 +1.5 V（回生の兆候）],
  [], [温度カットオフ], [モータ 80 °C（温度プローブを使う場合）],
  [], [スロットルの下げ方], [1 段 10 % 以下、またはランプ 0.7 s 以上。停止は 0 へ],
  table.hline(stroke: 0.6pt),
)

= 試験手順のチェックリスト

*準備*
- プロペラの外観（割れ・欠け）、アダプタリングの径、ナットの締結を確認する。プロペラの回転面に人・物がない配置にする。
- 配線: 電源（背面）→ ヒューズ → 非常停止 → 1585 電源ボード → ESC。極性を確認し、電源出力 OFF の状態で接続する。
- 電源を設定（電圧、CC、OVP）してから出力 OFF のまま待機。1585 のカットオフを設定する。

*開始*
- ソフトでスロットル 0 を確認 → 電源出力 ON → ESC のアーム音を確認。
- 低回転で数秒回し、振動・異音がないことを確認してからスイープを開始する。

*スイープ中*
- 回転面の延長線上に立たない。非常停止に手が届く位置にいる。
- 上げは任意のステップ、下げは 1 段 10 % 以下。終わりはスロットル 0。

*異常時*
- 非常停止（電源を断つ）またはソフトのスロットル 0。どちらも回生の点では安全。プロペラが止まるまで近づかない。

*終了*
- スロットル 0 → 回転停止を確認 → 電源出力 OFF → 配線を外す。

// <<REFERENCES>>
