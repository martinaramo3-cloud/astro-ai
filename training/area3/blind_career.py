"""Build the blind career table for the co-founder.

Twelve invented charts. Tab one shows the chart details her rules ask for and
gives her somewhere to write her own top three professional themes and top
three earning routes, with a download button. Tab two shows what the engine
produced — both rankings, the timing it chose and why, the profection, and the
counterevidence — so the two can be compared after she has committed.

Blind, and in that order, on purpose: seeing the engine's answer first is how
you end up agreeing with it.

    ./venv/bin/python training/area3/blind_career.py
"""
from __future__ import annotations

import html
import os
import pathlib
import random
import sys
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from career_distribution import timeline_for  # noqa: E402
from route_distribution import a_chart  # noqa: E402

from app.career_reading_service import build_career_reading  # noqa: E402
from app.earning_routes_service import ROUTES  # noqa: E402
from app.orb_policy import describe as orb_policy  # noqa: E402
from app.professional_themes_service import THEMES  # noqa: E402

QUESTION = "What career suits me, and how am I most likely to earn?"


def esc(text) -> str:
    return html.escape(str(text))


def ordinal(number) -> str:
    if not number:
        return "—"
    if number in (11, 12, 13):
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def _items(values) -> str:
    return "".join(f"<li>{esc(v)}</li>" for v in values) or "<li>—</li>"


def build(count: int = 12):
    rng = random.Random(4242)
    charts = []
    for number in range(1, count + 1):
        chart = a_chart(rng)
        reading = build_career_reading(
            chart, QUESTION, timeline=timeline_for(chart),
            birth_date=chart["_born"][:10])
        charts.append((number, chart, reading))
    return render(charts)


def blind_card(number: int, chart: dict, reading: dict) -> str:
    natal = reading["natal_evidence"]
    rulers = natal["rulers"]
    second, tenth = natal["second_ruler"], natal["tenth_ruler"]

    ruler_rows = "".join(
        f"<tr{' class=key' if house in (2, 10) else ''}>"
        f"<td>{ordinal(house)}</td><td>{esc(row['cusp_sign'])}</td>"
        f"<td><b>{esc(row['ruler'])}</b></td>"
        f"<td>{ordinal(row['ruler_in_house'])}</td>"
        f"<td>{esc(row['ruler_in_sign'])}</td>"
        f"<td>{esc(row['ruler_dignity'] or '—')}</td>"
        f"<td>{esc(', '.join(natal['planets_in_those_houses'].get(house, [])) or '—')}</td>"
        f"<td>{esc(', '.join(p['planet'] for p in natal['planets_conjunct_those_cusps'].get(house, [])) or '—')}</td>"
        f"</tr>"
        for house, row in rulers.items())

    ruler_aspects = "".join(
        f"<li>{esc(a['planet_1'])} {esc(a['aspect'])} {esc(a['planet_2'])} "
        f"<span class=orb>{a['orb']}° · counts {a['exactness']}</span> "
        f"<span class=which>{esc(', '.join(a['involves']))}</span></li>"
        for a in natal["aspects_involving_those_rulers"][:14]) or "<li>—</li>"

    angle_aspects = "".join(
        f"<li>{esc(a['planet_1'])} {esc(a['aspect'])} {esc(a['planet_2'])} "
        f"<span class=orb>{a['orb']}° · counts {a['exactness']}</span></li>"
        for a in natal["aspects_to_the_midheaven_and_ascendant"]) or "<li>—</li>"

    profection = reading["annual_profection"]
    theme_options = "".join(
        f'<option value="{esc(t["label"])}">{esc(t["label"])}</option>'
        for t in THEMES.values())
    route_options = "".join(
        f'<option value="{esc(r["label"])}">{esc(r["label"])}</option>'
        for r in ROUTES.values())

    picks = ""
    for kind, options in (("theme", theme_options), ("route", route_options)):
        rows = "".join(f'''
        <label><span>{place}</span>
          <select data-chart="{number}" data-slot="{kind}{place}">
            <option value="">—</option>{options}
          </select></label>''' for place in (1, 2, 3))
        title = ("Top three professional themes — what the WORK is"
                 if kind == "theme" else
                 "Top three earning routes — HOW the money arrives")
        picks += f'<div class="pickgroup"><h5>{title}</h5><div class="picks">{rows}</div></div>'

    return f"""
<article class="chart" id="chart-{number}">
  <header>
    <h3>Chart {number}</h3>
    <p class="meta">Invented · born {esc(chart['_born'])} · {esc(chart['_where'])}
      · Rising {esc(natal['ascendant']['sign'])} · MC {esc(natal['midheaven']['sign'])}</p>
  </header>

  <div class="traced">
    <p><span class="tag">money</span> The <b>2nd</b> is ruled by
      <b>{esc(second['planet'])}</b> in {esc(second['sign'])}, in the
      <b>{ordinal(second['in_house'])}</b>{
        f", {esc(second['dignity'])}" if second['dignity'] else ""}{
        ", retrograde" if second['retrograde'] else ""}.</p>
    <p><span class="tag">career</span> The <b>10th / MC</b> is ruled by
      <b>{esc(tenth['planet'])}</b> in {esc(tenth['sign'])}, in the
      <b>{ordinal(tenth['in_house'])}</b>{
        f", {esc(tenth['dignity'])}" if tenth['dignity'] else ""}{
        ", retrograde" if tenth['retrograde'] else ""}.</p>
    <p><span class="tag">year</span> Age {profection.get('age_at_last_birthday', '—')},
      so a <b>{ordinal(profection.get('profected_house'))}-house year</b>,
      ruled by <b>{esc(profection.get('time_lord') or '—')}</b>.</p>
  </div>

  <table class="rulers">
    <thead><tr><th>House</th><th>Cusp</th><th>Ruler</th><th>Ruler in</th>
      <th>Sign</th><th>Dignity</th><th>Planets IN it</th><th>ON the cusp</th></tr></thead>
    <tbody>{ruler_rows}</tbody>
  </table>

  <div class="aspects">
    <div><h4>Every aspect involving those six rulers</h4>
      <ul class="asp">{ruler_aspects}</ul></div>
    <div><h4>Aspects to the MC and Ascendant</h4>
      <ul class="asp">{angle_aspects}</ul></div>
  </div>

  <fieldset class="yours">
    <legend>Your reading</legend>
    {picks}
    <label class="note"><span>Why, and anything the engine is likely to miss</span>
      <textarea rows="3" data-chart="{number}" data-slot="note"
        placeholder="e.g. the 2nd ruler is cadent and besieged, so I would not call any route strong here"></textarea></label>
    <div class="picks">
      <label><span>Confidence</span>
        <select data-chart="{number}" data-slot="confidence">
          <option value="">—</option><option>high</option>
          <option>moderate</option><option>low</option></select></label>
      <label><span>Would you give a date?</span>
        <select data-chart="{number}" data-slot="timing">
          <option value="">—</option><option>yes, the indicators converge</option>
          <option>no, the timing is unclear</option></select></label>
    </div>
  </fieldset>
</article>"""


def engine_card(number: int, reading: dict) -> str:
    themes, routes = reading["professional_themes"], reading["earning_routes"]

    def ranked_block(entries, kind):
        blocks = []
        for place, entry in enumerate(entries, start=1):
            evidence = "".join(
                f"<li><b>{e['counts_as']}</b> "
                f"<span class=raw>({e['points']} × {e['weight']})</span> "
                f"{esc(e['why'])}</li>" for e in entry["evidence"][:5])
            against = "".join(f"<li>{esc(c)}</li>"
                              for c in entry["counterevidence"][:4]) or "<li>—</li>"
            blocks.append(f"""
      <div class="route">
        <div class="rank">{place}</div>
        <div class="body">
          <h4>{esc(entry['label'])}
            {'<span class="strong">strong</span>' if entry['strong']
             else '<span class="weak">not strong</span>'}</h4>
          <p class="means">{esc(entry.get('work') or entry.get('means'))}</p>
          <p class="nums">score <b>{entry['score']}</b> ·
            more pronounced than <b>{entry['how_unusual']:.0%}</b> of charts ·
            {entry['signals']} signal{'s' if entry['signals'] != 1 else ''}</p>
          <div class="cols">
            <div><h5>Evidence</h5><ul>{evidence}</ul></div>
            <div><h5>Counterevidence</h5><ul class="against">{against}</ul></div>
          </div>
        </div>
      </div>""")
        return "".join(blocks) or "<p class='means'>nothing ranked</p>"

    timing = reading["timing"]
    if timing.get("windows"):
        windows = "".join(f"""
      <div class="window">
        <p class="wtitle"><b>{esc(w['transit'])}</b>
          <span class="weak">{esc(w['reads_as'])}</span></p>
        <p class="nums">{esc(' · '.join(p['window'] for p in w['passes'][:2]))}
          {'· exact ' + esc(', '.join(w['exact_days'])) if w['exact_days'] else ''}</p>
        <ul class="why">{_items(w['why_this_window'])}</ul>
      </div>""" for w in timing["windows"])
    else:
        windows = "<p class='means'>no window activated this question's factors</p>"

    dims = "".join(
        f"<tr><td>{esc(name.replace('_', ' '))}</td>"
        f"<td><b>{esc(r['reads_as'])}</b></td>"
        f"<td>{esc(' · '.join(r['evidence']) or '—')}</td></tr>"
        for name, r in routes.get("dimensions", {}).items())

    return f"""
<article class="chart" id="engine-{number}">
  <header><h3>Chart {number}</h3>
    <p class="meta">{esc(reading['question_type'].replace('_', ' '))}
      · {esc(reading['confidence'])}</p></header>
  <p class="plain">{esc(reading['plain_language'])}</p>

  <h4 class="section">Professional themes — what the work is</h4>
  {ranked_block(themes.get('themes', []), 'theme')}
  {f'<p class="combined">{esc(themes["combined_reading"])}</p>'
   if themes.get('combined_reading') else ''}

  <h4 class="section">Earning routes — how the money arrives</h4>
  {ranked_block(routes.get('ranking', []), 'route')}
  {'<p class="combined">The top two are complementary.</p>'
   if routes.get('complementary') else ''}

  <h4 class="section">Timing{' — UNCLEAR, no date' if timing.get('timing_is_unclear')
                             else ''}</h4>
  <p class="nums">{esc(timing.get('how_chosen', ''))}
    Considered {timing.get('considered', 0)}.</p>
  {windows}

  <h4 class="section">Dimensions</h4>
  <table class="dims"><tbody>{dims}</tbody></table>
</article>"""


def render(charts) -> str:
    blind = "".join(blind_card(n, c, r) for n, c, r in charts)
    engine = "".join(engine_card(n, r) for n, _c, r in charts)
    policy = orb_policy()
    return TEMPLATE.format(
        blind=blind, engine=engine, count=len(charts),
        orb_note=esc(policy["note"]))


TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Career reading — blind review</title>
<style>
  :root {{
    --ink:#241f1a; --ink-2:#5b524a; --ink-3:#8d8279; --line:#e4ddd3;
    --paper:#fbf8f3; --card:#fff; --key:#f3ece0; --accent:#8a6a3b;
    --good:#2f6b4f; --against:#8d5140;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font:15px/1.55 "Iowan Old Style","Palatino Linotype",Georgia,serif; }}
  header.top {{ padding:34px 22px 16px; max-width:1080px; margin:0 auto; }}
  h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.01em; }}
  .sub {{ color:var(--ink-2); max-width:62ch; margin:0 0 5px; }}
  nav {{ position:sticky; top:0; z-index:5; background:var(--paper);
    border-bottom:1px solid var(--line); padding:0 22px; }}
  nav .inner {{ max-width:1080px; margin:0 auto; display:flex; gap:6px;
    align-items:center; flex-wrap:wrap; padding:9px 0; }}
  button.tab {{ font:inherit; font-size:14px; border:1px solid var(--line);
    background:var(--card); color:var(--ink-2); border-radius:999px;
    padding:7px 15px; cursor:pointer; }}
  button.tab[aria-selected=true] {{ background:var(--ink); color:var(--paper);
    border-color:var(--ink); }}
  button.dl {{ margin-left:auto; font:inherit; font-size:14px; cursor:pointer;
    border:1px solid var(--accent); color:#fff; background:var(--accent);
    border-radius:999px; padding:7px 16px; }}
  main {{ max-width:1080px; margin:0 auto; padding:20px 22px 70px; }}
  [hidden] {{ display:none !important; }}
  .chart {{ background:var(--card); border:1px solid var(--line);
    border-radius:13px; padding:20px 22px; margin:0 0 20px; }}
  .chart h3 {{ margin:0; font-size:19px; }}
  .meta {{ margin:3px 0 14px; color:var(--ink-3); font-size:13px; }}
  .traced {{ background:var(--key); border-radius:9px; padding:11px 14px;
    margin-bottom:14px; }}
  .traced p {{ margin:2px 0; font-size:14.5px; }}
  .tag {{ display:inline-block; min-width:56px; font-size:11px;
    letter-spacing:.13em; text-transform:uppercase; color:var(--accent); }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  .rulers th {{ text-align:left; font-weight:600; color:var(--ink-3);
    font-size:11px; letter-spacing:.07em; text-transform:uppercase;
    border-bottom:1px solid var(--line); padding:5px 6px; }}
  .rulers td {{ padding:4px 6px; border-bottom:1px solid #f2ede5; }}
  .rulers tr.key td {{ background:var(--key); }}
  .aspects {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr));
    gap:16px; margin-top:15px; }}
  .aspects h4, .section {{ margin:0 0 5px; font-size:11.5px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--ink-3); font-weight:600; }}
  .section {{ margin:20px 0 6px; border-top:1px solid var(--line); padding-top:13px; }}
  ul.asp {{ margin:0; padding-left:17px; font-size:13.5px; }}
  ul.asp li {{ margin-bottom:2px; }}
  .orb {{ color:var(--ink-3); font-size:12px; }}
  .which {{ color:var(--accent); font-size:11.5px; }}
  fieldset.yours {{ margin:18px 0 0; border:1px dashed var(--line);
    border-radius:10px; padding:13px 15px 15px; }}
  legend {{ font-size:11.5px; letter-spacing:.13em; text-transform:uppercase;
    color:var(--accent); padding:0 6px; }}
  .pickgroup {{ margin-bottom:12px; }}
  .pickgroup h5 {{ margin:0 0 5px; font-size:12.5px; color:var(--ink-2);
    font-weight:600; }}
  .picks {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
  .picks label {{ display:flex; align-items:center; gap:6px; }}
  .picks span {{ color:var(--ink-3); font-size:13px; }}
  select, textarea {{ font:inherit; font-size:13.5px; border:1px solid var(--line);
    border-radius:7px; padding:6px 8px; background:var(--paper);
    color:var(--ink); max-width:100%; }}
  label.note {{ display:block; margin:10px 0; }}
  label.note span {{ display:block; font-size:12.5px; color:var(--ink-3);
    margin-bottom:3px; }}
  label.note textarea {{ width:100%; resize:vertical; }}
  .plain {{ font-size:16px; background:var(--key); border-radius:9px;
    padding:11px 14px; margin:0 0 6px; }}
  .route {{ display:flex; gap:13px; padding:12px 0;
    border-top:1px solid #f2ede5; }}
  .rank {{ flex:0 0 26px; height:26px; border-radius:50%; background:var(--ink);
    color:var(--paper); display:grid; place-items:center; font-size:13px; }}
  .route h4 {{ margin:2px 0; font-size:15.5px; }}
  .strong {{ font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
    color:var(--good); border:1px solid var(--good); border-radius:999px;
    padding:1px 7px; margin-left:5px; vertical-align:2px; }}
  .weak {{ font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
    color:var(--ink-3); border:1px solid var(--line); border-radius:999px;
    padding:1px 7px; margin-left:5px; vertical-align:2px; }}
  .means {{ margin:0 0 3px; color:var(--ink-2); font-size:13.5px; }}
  .nums {{ margin:0 0 7px; color:var(--ink-3); font-size:12.5px; }}
  .raw {{ color:var(--ink-3); font-size:11.5px; }}
  .cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:14px; }}
  .cols h5 {{ margin:0 0 3px; font-size:11px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--ink-3); font-weight:600; }}
  .cols ul, ul.why {{ margin:0; padding-left:17px; font-size:13px; }}
  .against li {{ color:var(--against); }}
  .combined {{ background:var(--key); border-radius:8px; padding:8px 12px;
    font-size:14px; margin:8px 0 0; }}
  .window {{ border-top:1px solid #f2ede5; padding:10px 0; }}
  .wtitle {{ margin:0 0 2px; font-size:14.5px; }}
  .dims td {{ padding:4px 6px; border-bottom:1px solid #f2ede5;
    vertical-align:top; }}
  .dims td:first-child {{ color:var(--ink-3); width:155px; }}
  .dims td:last-child {{ color:var(--ink-3); font-size:12.5px; }}
  .warn {{ background:#fff6e8; border:1px solid #e8d4ac; border-radius:9px;
    padding:11px 14px; margin:0 0 20px; font-size:14px; }}
</style>

<header class="top">
  <h1>Career reading — blind review</h1>
  <p class="sub">Twelve invented charts. Random dates, times and cities; nobody
    real is in here.</p>
  <p class="sub">Two rankings per chart, because they are two questions: what
    the <b>work</b> is, and how the <b>money</b> arrives. Fill in both, then
    download. Only then open tab two.</p>
  <p class="sub"><b>Orb policy, for your approval:</b> {orb_note}</p>
</header>

<nav><div class="inner">
  <button class="tab" id="t1" aria-selected="true" onclick="show(1)">1 · The charts</button>
  <button class="tab" id="t2" aria-selected="false" onclick="show(2)">2 · What the engine said</button>
  <button class="dl" onclick="download()">Download my answers</button>
</div></nav>

<main>
  <section id="pane1">{blind}</section>
  <section id="pane2" hidden>
    <div class="warn"><b>Only after tab one is filled in and downloaded.</b>
      Scores are internal: a ranking aid, never a probability and never a
      promise of income. They do not reach a reader.</div>
    {engine}
  </section>
</main>

<script>
  const KEY = "zoli-career-blind-v1";
  const SLOTS = ["theme1","theme2","theme3","route1","route2","route3",
                 "confidence","timing","note"];

  function show(n) {{
    document.getElementById("pane1").hidden = n !== 1;
    document.getElementById("pane2").hidden = n !== 2;
    document.getElementById("t1").setAttribute("aria-selected", n === 1);
    document.getElementById("t2").setAttribute("aria-selected", n === 2);
    window.scrollTo(0, 0);
  }}

  function collect() {{
    const answers = {{}};
    document.querySelectorAll("[data-chart]").forEach(function (el) {{
      const chart = el.dataset.chart;
      answers[chart] = answers[chart] || {{}};
      answers[chart][el.dataset.slot] = el.value;
    }});
    return answers;
  }}

  // This browser only, so a half-finished pass survives a reload. Wrapped
  // because some contexts block storage entirely.
  function save() {{
    try {{ localStorage.setItem(KEY, JSON.stringify(collect())); }} catch (e) {{}}
  }}

  function restore() {{
    let saved = null;
    try {{ saved = JSON.parse(localStorage.getItem(KEY) || "null"); }} catch (e) {{}}
    if (!saved) return;
    document.querySelectorAll("[data-chart]").forEach(function (el) {{
      const row = saved[el.dataset.chart];
      if (row && row[el.dataset.slot]) el.value = row[el.dataset.slot];
    }});
  }}

  function download() {{
    const answers = collect();
    const cell = function (v) {{
      return '"' + String(v || "").replace(/"/g, '""') + '"';
    }};
    let csv = "chart," + SLOTS.join(",") + "\\n";
    for (let n = 1; n <= {count}; n++) {{
      const row = answers[n] || {{}};
      csv += [n].concat(SLOTS.map(function (s) {{ return cell(row[s]); }})).join(",") + "\\n";
    }}
    const blob = new Blob([csv], {{ type: "text/csv" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "career-blind-review.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  }}

  document.addEventListener("input", save);
  document.addEventListener("change", save);
  restore();
</script>
"""


if __name__ == "__main__":
    out = HERE / "blind_career.html"
    out.write_text(build(12))
    print(f"wrote {out}")
