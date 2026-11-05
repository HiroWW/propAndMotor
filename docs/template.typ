// 文書テンプレート (m1WeeklyReport/template/template.typ の書式に合わせたもの)。
// 和文: 本文・見出し -> セザンヌ / タイトル -> 筑紫オールドゴシック
// 英文: 本文・見出し -> Futura PT
// フォントはリポジトリに含めない (~/.local/share/fonts などにインストールしておく)。

#let maintext = ("Futura PT", "FTT-Cezanne")
#let headingtext = ("Futura PT", "FTT-Cezanne")
#let titletext = ("Futura PT", "FTT-TsukuOldGothic")

#let report(
  title: [],
  subtitle: [],
  date: [],
  authors: [藤原啓明],
  body,
) = {
  set document(title: title)

  set page(
    paper: "a4",
    margin: (bottom: 1.75cm, top: 2.5cm, left: 2cm, right: 2cm),
    header: context [
      #if counter(page).get() != (1,) {
        set align(right)
        set text(10pt, font: "Futura PT", style: "italic", weight: 300)
        date
      }
    ],
    footer: context [
      #set align(center)
      #set text(10pt, font: "Futura PT", style: "italic", weight: 500)
      #counter(page).display("1")
    ],
  )
  set par(leading: 0.7em, first-line-indent: 1em, justify: true, spacing: 0.8em)
  set text(size: 10pt, font: maintext, weight: 450, kerning: true, lang: "en")

  show figure.where(kind: table): set figure.caption(position: top)
  show figure.where(kind: table): set figure(supplement: [表])
  show figure.where(kind: image): set figure(supplement: [図])
  show figure.caption: set text(size: 9pt)
  set figure(gap: 0.7em)
  show figure: set block(spacing: 1.4em)

  set math.equation(numbering: "(1)", supplement: [式])
  show math.equation: it => h(0.25em, weak: true) + it + h(0.25em, weak: true)

  show link: underline
  show link: set text(fill: rgb("#125ee0"))
  set list(marker: ([•], [‣]))
  set enum(numbering: "(1)")

  set heading(numbering: "1.")
  // 見出しへの参照を「2 章」「2.3 節」と表示する。
  show ref: it => {
    let el = it.element
    if el != none and el.func() == heading {
      let num = numbering("1.1", ..counter(heading).at(el.location()))
      link(el.location(), if el.level == 1 [#num 章] else [#num 節])
    } else { it }
  }
  show heading: it => {
    set text(15pt, font: headingtext, weight: 550) if it.level == 1
    it
    v(0.3em)
  }
  show heading.where(level: 2): set text(13pt, font: headingtext, weight: 550)
  show heading: it => {
    set text(11.5pt, font: headingtext, weight: 550) if it.level > 2
    it
  }

  show raw: set text(font: ("DejaVu Sans Mono",), size: 8.5pt)
  set table(stroke: none, inset: (x: 5pt, y: 3.5pt), align: left)

  align(center, text(23pt, font: titletext, weight: 450, title))
  v(10pt, weak: true)
  align(center, text(12pt, font: headingtext, subtitle))
  v(14pt, weak: true)
  align(center, text(11pt, font: headingtext, authors + h(1.5em) + date))
  v(10pt)
  outline(title: "目次", depth: 2, indent: auto)
  body
}

// 表の罫線 (上下と見出し下の 3 本線)
#let toprule = table.hline(stroke: 0.7pt)
#let midrule = table.hline(stroke: 0.4pt)
#let botrule = table.hline(stroke: 0.7pt)

#let fmt(x, d: 2) = if x == none { "—" } else { str(calc.round(x, digits: d)) }
#let pct(x, d: 0) = if x == none { "—" } else { str(calc.round(x * 100, digits: d)) + " %" }
#let fig(path, cap, w: 100%) = figure(image(path, width: w), caption: cap)
