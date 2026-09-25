"""Build the blind earning-route table for the co-founder.

Twelve invented charts. Tab one shows the chart details that matter for her
framework and gives her somewhere to write her own top three, with a download
button. Tab two shows what the engine ranked, with its evidence and its
counterevidence, so the two can be compared after she has committed.

Blind on purpose, and in that order on purpose: seeing the engine's answer
first is how you end up agreeing with it.

    ./venv/bin/python training/area3/blind_routes.py
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import random
import sys
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from route_distribution import a_chart  # noqa: E402

from app.angle_aspects_service import conjunct_cusp, get_angle_aspects  # noqa: E402
from app.aspect_services import get_aspects  # noqa: E402
from app.chart_analysis_service import get_house_rulers  # noqa: E402
from app.earning_routes_service import (  # noqa: E402
    ROUTES, describe_routes, score_earning_routes,
)

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def ordinal(number: int) -> str:
    if number in (11, 12, 13):
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def chart_sheet(chart: dict) -> dict:
    """Only what her framework asks for, and nothing that gives the game away."""
    planets = chart["planet_positions"]
    houses = chart["houses"]
    rulers = {r["house"]: r for r in get_house_rulers(houses, planets)}
    tenants: dict[int, list[str]] = {}
    for planet in planets:
        if planet.get("house"):
            tenants.setdefault(planet["house"], []).append(planet["planet"])
    aspects = get_aspects(planets)
    angle_aspects = get_angle_aspects(
        planets, ascendant=chart.get("ascendant"),
        midheaven=chart.get("midheaven"), houses=houses)
    second, tenth = rulers[2]["ruler"], rulers[10]["ruler"]
    house_of = {p["planet"]: p.get("house") for p in planets}

    def about(planet):
        return [a for a in aspects
                if planet in (a["planet_1"], a["planet_2"]) and a["orb"] <= 4.0]

    return {
        "born": chart["_born"], "where": chart["_where"],
        "ascendant": chart["ascendant"]["sign"],
        "midheaven": chart["midheaven"]["sign"],
        "rulers": [
            {"house": h, "cusp_sign": rulers[h]["cusp_sign"],
             "ruler": rulers[h]["ruler"],
             "ruler_in_house": rulers[h]["ruler_in_house"],
             "ruler_in_sign": rulers[h]["ruler_in_sign"],
             "dignity": rulers[h].get("ruler_dignity") or "—"}
            for h in range(1, 13)
        ],
        "tenants": {h: tenants.get(h, []) for h in range(1, 13)},
        "second_ruler": second,
        "tenth_ruler": tenth,
        "money_ruler_aspects": [
            f"{a['planet_1']} {a['aspect']} {a['planet_2']} ({a['orb']}°)"
            for a in about(second)],
        "career_ruler_aspects": [
            f"{a['planet_1']} {a['aspect']} {a['planet_2']} ({a['orb']}°)"
            for a in about(tenth)],
        "on_the_mc": [f"{a['planet_1']} {a['aspect']} MC ({a['orb']}°)"
                      for a in angle_aspects if a["planet_2"] == "Midheaven"],
        "on_second_cusp": [f"{p['planet']} ({p['orb']}°)"
                           for p in conjunct_cusp(planets, houses, 2)],
        "second_ruler_house": house_of.get(second),
        "tenth_ruler_house": house_of.get(tenth),
    }


def build(count: int = 12) -> str:
    rng = random.Random(4242)
    pairs = []
    for number in range(1, count + 1):
        chart = a_chart(rng)
        result = score_earning_routes(chart)
        pairs.append((number, chart_sheet(chart), result, describe_routes(result)))
    return render(pairs)


def esc(text) -> str:
    return html.escape(str(text))


def render(pairs) -> str:
    route_names = [ROUTES[k]["label"] for k in ROUTES]
    options = "".join(f'<option value="{esc(name)}">{esc(name)}</option>'
                      for name in route_names)

    blind_cards = []
    for number, sheet, _result, _plain in pairs:
        ruler_rows = "".join(
            f"<tr{' class=key' if row['house'] in (2, 10) else ''}>"
            f"<td>{ordinal(row['house'])}</td><td>{esc(row['cusp_sign'])}</td>"
            f"<td><b>{esc(row['ruler'])}</b></td>"
            f"<td>{ordinal(row['ruler_in_house']) if row['ruler_in_house'] else '—'}</td>"
            f"<td>{esc(row['ruler_in_sign'])}</td><td>{esc(row['dignity'])}</td>"
            f"<td>{esc(', '.join(sheet['tenants'][row['house']]) or '—')}</td></tr>"
            for row in sheet["rulers"])
        blind_cards.append(f"""
<article class="chart" id="chart-{number}">
  <header>
    <h3>Chart {number}</h3>
    <p class="meta">Invented · born {esc(sheet['born'])} · {esc(sheet['where'])}
       · Rising {esc(sheet['ascendant'])} · MC {esc(sheet['midheaven'])}</p>
  </header>

  <div class="traced">
    <p><span class="tag">money</span> The <b>2nd</b> is ruled by
       <b>{esc(sheet['second_ruler'])}</b>, in the
       <b>{ordinal(sheet['second_ruler_house']) if sheet['second_ruler_house'] else '—'}</b>.</p>
    <p><span class="tag">career</span> The <b>10th</b> is ruled by
       <b>{esc(sheet['tenth_ruler'])}</b>, in the
       <b>{ordinal(sheet['tenth_ruler_house']) if sheet['tenth_ruler_house'] else '—'}</b>.</p>
  </div>

  <table class="rulers">
    <thead><tr><th>House</th><th>Cusp</th><th>Ruler</th><th>Ruler in</th>
      <th>Sign</th><th>Dignity</th><th>Planets in house</th></tr></thead>
    <tbody>{ruler_rows}</tbody>
  </table>

  <div class="aspects">
    <div><h4>Aspects to the 2nd ruler <span>(within 4°)</span></h4>
      <ul>{_list(sheet['money_ruler_aspects'])}</ul></div>
    <div><h4>Aspects to the 10th ruler <span>(within 4°)</span></h4>
      <ul>{_list(sheet['career_ruler_aspects'])}</ul></div>
    <div><h4>Aspects to the MC</h4>
      <ul>{_list(sheet['on_the_mc'])}</ul></div>
    <div><h4>On the 2nd cusp <span>(within 3°)</span></h4>
      <ul>{_list(sheet['on_second_cusp'])}</ul></div>
  </div>

  <fieldset class="yours">
    <legend>Your top three</legend>
    <div class="picks">
      {"".join(f'''
      <label><span>{place}</span>
        <select data-chart="{number}" data-slot="{place}">
          <option value="">—</option>{options}
        </select>
      </label>''' for place in (1, 2, 3))}
    </div>
    <label class="note"><span>Why, and anything the engine is likely to miss</span>
      <textarea rows="3" data-chart="{number}" data-slot="note"
        placeholder="e.g. the 2nd ruler is cadent, so I would not call this strong"></textarea>
    </label>
    <label class="note"><span>Confidence</span>
      <select data-chart="{number}" data-slot="confidence">
        <option value="">—</option><option>high</option>
        <option>moderate</option><option>low</option>
      </select>
    </label>
  </fieldset>
</article>""")

    engine_cards = []
    for number, _sheet, result, plain in pairs:
        rows = []
        for place, route in enumerate(result["ranking"], start=1):
            evidence = "".join(f"<li><b>+{e['points']}</b> {esc(e['why'])}</li>"
                               for e in route["evidence"][:5])
            against = "".join(f"<li>{esc(c)}</li>"
                              for c in route["counterevidence"][:4]) or "<li>—</li>"
            rows.append(f"""
      <div class="route">
        <div class="rank">{place}</div>
        <div class="body">
          <h4>{esc(route['label'])}
            {'<span class="strong">strong</span>' if route['strong']
             else '<span class="weak">not strong</span>'}</h4>
          <p class="means">{esc(route['means'])}</p>
          <p class="nums">score <b>{route['score']}</b> ·
             more pronounced than <b>{route['how_unusual']:.0%}</b> of charts ·
             {route['signals']} independent signal{'s' if route['signals'] != 1 else ''}</p>
          <div class="cols">
            <div><h5>Evidence</h5><ul>{evidence}</ul></div>
            <div><h5>Counterevidence</h5><ul class="against">{against}</ul></div>
          </div>
        </div>
      </div>""")
        dims = "".join(
            f"<tr><td>{esc(name.replace('_', ' '))}</td>"
            f"<td><b>{esc(reading['reads_as'])}</b></td>"
            f"<td>{esc(' · '.join(reading['evidence']) or '—')}</td></tr>"
            for name, reading in result["dimensions"].items())
        engine_cards.append(f"""
<article class="chart" id="engine-{number}">
  <header>
    <h3>Chart {number}</h3>
    <p class="meta">{esc(result['confidence'])}
      {' · top two complementary' if result['complementary'] else ''}</p>
  </header>
  <p class="plain">{esc(plain)}</p>
  {''.join(rows)}
  <h4 class="dimtitle">Dimensions</h4>
  <table class="dims"><tbody>{dims}</tbody></table>
</article>""")

    return TEMPLATE.format(
        blind="".join(blind_cards), engine="".join(engine_cards),
        count=len(pairs))


def _list(items) -> str:
    return "".join(f"<li>{esc(i)}</li>" for i in items) or "<li>—</li>"


TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Earning routes — blind review</title>
<style>
  :root {{
    --ink:#241f1a; --ink-2:#5b524a; --ink-3:#8d8279; --line:#e4ddd3;
    --paper:#fbf8f3; --card:#fff; --key:#f3ece0; --accent:#8a6a3b;
    --good:#2f6b4f; --against:#8d5140;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font:15px/1.55 "Iowan Old Style","Palatino Linotype",Georgia,serif; }}
  header.top {{ padding:34px 22px 18px; max-width:1040px; margin:0 auto; }}
  h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.01em; }}
  .sub {{ color:var(--ink-2); max-width:60ch; margin:0 0 4px; }}
  nav {{ position:sticky; top:0; z-index:5; background:var(--paper);
    border-bottom:1px solid var(--line); padding:0 22px; }}
  nav .inner {{ max-width:1040px; margin:0 auto; display:flex; gap:6px;
    align-items:center; flex-wrap:wrap; padding:9px 0; }}
  button.tab {{ font:inherit; font-size:14px; border:1px solid var(--line);
    background:var(--card); color:var(--ink-2); border-radius:999px;
    padding:7px 15px; cursor:pointer; }}
  button.tab[aria-selected=true] {{ background:var(--ink); color:var(--paper);
    border-color:var(--ink); }}
  button.dl {{ margin-left:auto; font:inherit; font-size:14px; cursor:pointer;
    border:1px solid var(--accent); color:#fff; background:var(--accent);
    border-radius:999px; padding:7px 16px; }}
  main {{ max-width:1040px; margin:0 auto; padding:20px 22px 70px; }}
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
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
  .rulers th {{ text-align:left; font-weight:600; color:var(--ink-3);
    font-size:11.5px; letter-spacing:.08em; text-transform:uppercase;
    border-bottom:1px solid var(--line); padding:5px 7px; }}
  .rulers td {{ padding:4px 7px; border-bottom:1px solid #f2ede5; }}
  .rulers tr.key td {{ background:var(--key); }}
  .aspects {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr));
    gap:14px; margin-top:15px; }}
  .aspects h4 {{ margin:0 0 4px; font-size:12px; letter-spacing:.07em;
    text-transform:uppercase; color:var(--ink-3); font-weight:600; }}
  .aspects h4 span {{ text-transform:none; letter-spacing:0; }}
  .aspects ul {{ margin:0; padding-left:17px; font-size:13.5px; }}
  fieldset.yours {{ margin:18px 0 0; border:1px dashed var(--line);
    border-radius:10px; padding:13px 15px 15px; }}
  legend {{ font-size:11.5px; letter-spacing:.13em; text-transform:uppercase;
    color:var(--accent); padding:0 6px; }}
  .picks {{ display:flex; gap:10px; flex-wrap:wrap; }}
  .picks label {{ display:flex; align-items:center; gap:6px; }}
  .picks span {{ color:var(--ink-3); font-size:13px; }}
  select, textarea {{ font:inherit; font-size:14px; border:1px solid var(--line);
    border-radius:7px; padding:6px 8px; background:var(--paper);
    color:var(--ink); max-width:100%; }}
  label.note {{ display:block; margin-top:10px; }}
  label.note span {{ display:block; font-size:12.5px; color:var(--ink-3);
    margin-bottom:3px; }}
  label.note textarea {{ width:100%; resize:vertical; }}
  .plain {{ font-size:16px; background:var(--key); border-radius:9px;
    padding:11px 14px; margin:0 0 15px; }}
  .route {{ display:flex; gap:13px; padding:13px 0;
    border-top:1px solid #f2ede5; }}
  .rank {{ flex:0 0 27px; height:27px; border-radius:50%; background:var(--ink);
    color:var(--paper); display:grid; place-items:center; font-size:13px; }}
  .route h4 {{ margin:2px 0 2px; font-size:16px; }}
  .strong {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase;
    color:var(--good); border:1px solid var(--good); border-radius:999px;
    padding:1px 7px; margin-left:5px; vertical-align:2px; }}
  .weak {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase;
    color:var(--ink-3); border:1px solid var(--line); border-radius:999px;
    padding:1px 7px; margin-left:5px; vertical-align:2px; }}
  .means {{ margin:0 0 3px; color:var(--ink-2); font-size:14px; }}
  .nums {{ margin:0 0 8px; color:var(--ink-3); font-size:12.5px; }}
  .cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
    gap:14px; }}
  .cols h5 {{ margin:0 0 3px; font-size:11.5px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--ink-3); font-weight:600; }}
  .cols ul {{ margin:0; padding-left:17px; font-size:13.5px; }}
  .against li {{ color:var(--against); }}
  .dimtitle {{ margin:17px 0 5px; font-size:11.5px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--ink-3); }}
  .dims td {{ padding:4px 7px; border-bottom:1px solid #f2ede5;
    vertical-align:top; }}
  .dims td:first-child {{ color:var(--ink-3); width:150px; }}
  .dims td:last-child {{ color:var(--ink-3); font-size:12.5px; }}
  .warn {{ background:#fff6e8; border:1px solid #e8d4ac; border-radius:9px;
    padding:11px 14px; margin:0 0 20px; font-size:14px; }}
  @media (max-width:640px) {{ .rulers {{ font-size:12px; }} }}
</style>

<header class="top">
  <h1>Earning routes — blind review</h1>
  <p class="sub">Twelve invented charts. Random dates, times and cities; nobody
    real is in here.</p>
  <p class="sub">Read tab one, write your own top three for each chart, then
    download. Only then open tab two. Seeing the engine's answer first is how
    you end up agreeing with it.</p>
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
      The scores are internal — a consistency device, not a probability. They
      never reach a reader.</div>
    {engine}
  </section>
</main>

<script>
  const KEY = "zoli-earning-routes-v1";

  function show(n) {{
    document.getElementById("pane1").hidden = n !== 1;
    document.getElementById("pane2").hidden = n !== 2;
    document.getElementById("t1").setAttribute("aria-selected", n === 1);
    document.getElementById("t2").setAttribute("aria-selected", n === 2);
    window.scrollTo(0, 0);
  }}

  function fields() {{
    return document.querySelectorAll("[data-chart]");
  }}

  function collect() {{
    const answers = {{}};
    fields().forEach(function (el) {{
      const chart = el.dataset.chart;
      answers[chart] = answers[chart] || {{}};
      answers[chart][el.dataset.slot] = el.value;
    }});
    return answers;
  }}

  // Kept in this browser only, so a half-finished pass survives a reload.
  function save() {{
    try {{ localStorage.setItem(KEY, JSON.stringify(collect())); }} catch (e) {{}}
  }}

  function restore() {{
    let saved = null;
    try {{ saved = JSON.parse(localStorage.getItem(KEY) || "null"); }} catch (e) {{}}
    if (!saved) return;
    fields().forEach(function (el) {{
      const row = saved[el.dataset.chart];
      if (row && row[el.dataset.slot]) el.value = row[el.dataset.slot];
    }});
  }}

  function download() {{
    const answers = collect();
    let csv = "chart,first,second,third,confidence,note\\n";
    for (let n = 1; n <= {count}; n++) {{
      const row = answers[n] || {{}};
      const cell = function (v) {{
        return '"' + String(v || "").replace(/"/g, '""') + '"';
      }};
      csv += [n, cell(row["1"]), cell(row["2"]), cell(row["3"]),
              cell(row.confidence), cell(row.note)].join(",") + "\\n";
    }}
    const blob = new Blob([csv], {{ type: "text/csv" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "earning-routes-blind.csv";
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
    out = HERE / "blind_routes.html"
    out.write_text(build(12))
    print(f"wrote {out}")
