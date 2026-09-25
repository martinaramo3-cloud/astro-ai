"""Build the blind twelve-pair calibration table.

Section 1 is what an astrologer sees: the chart contacts between two people,
and an empty column for her own lean. Section 2, which she opens only after
writing that column, holds the scores, the six dimensions, the lean the engine
produced and the sentence Zoli would open with.

The point is that she judges the charts, not the output — otherwise the scores
anchor her and the exercise proves nothing.

Everyone here is invented.

    ./venv/bin/python training/area2/calibration.py
"""
from __future__ import annotations

import html, json, os, pathlib, random, sys, tempfile
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "c.db"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytz  # noqa: E402
from app.astrology_engine import (  # noqa: E402
    add_house_to_planets, get_houses_and_ascendant, get_planet_positions_from_utc)
from app.compatibility_service import (  # noqa: E402
    _bucketize_index, _relative_shape, build_synastry_engine, get_synastry_aspects)
from app.friendship_service import describe_lean, score_friendship  # noqa: E402

CITIES = [("Sofia", 42.70, 23.32, "Europe/Sofia"), ("Milan", 45.46, 9.19, "Europe/Rome"),
          ("London", 51.51, -0.13, "Europe/London"), ("New York", 40.71, -74.01, "America/New_York"),
          ("Lisbon", 38.72, -9.14, "Europe/Lisbon"), ("Tokyo", 35.68, 139.69, "Asia/Tokyo"),
          ("Sydney", -33.87, 151.21, "Australia/Sydney"), ("Tirana", 41.33, 19.82, "Europe/Tirane")]
NAMES = ["Ana", "Luka", "Sam", "Noa", "Iris", "Theo", "Mira", "Kai", "Elif", "Jonas",
         "Vera", "Rui", "Lena", "Omar", "Tess", "Dani", "Nadia", "Pol", "Yara", "Emre",
         "Ines", "Bruno", "Sofia", "Milo"]


def a_person(rng, name):
    city, lat, lon, zone = rng.choice(CITIES)
    born = datetime(1990, 1, 1) + timedelta(days=rng.randrange(0, 365 * 18),
                                            minutes=rng.randrange(0, 1440))
    utc = pytz.timezone(zone).localize(born).astimezone(pytz.utc)
    planets = get_planet_positions_from_utc(utc)
    houses = get_houses_and_ascendant(utc, lat, lon)
    return {"name": name, "born": born.strftime("%d %b %Y, %H:%M"), "city": city,
            "planet_positions": add_house_to_planets(planets, houses["houses"]),
            "houses": houses["houses"]}


def assess(one, two):
    aspects = get_synastry_aspects(one["planet_positions"], two["planet_positions"])
    engine = build_synastry_engine(one, two, aspects)
    friends = score_friendship(one, two, aspects)
    lean = describe_lean(friends["friendship_score"], friends["friendship_band"],
                         engine["indices"]["attraction_band"])
    return aspects, engine, friends, lean


def profile_of(engine, friends):
    f, a = friends["friendship_band"], engine["indices"]["attraction_band"]
    strong_f, strong_a = f in ("high", "exceptional"), a in ("high", "exceptional")
    if engine["indices"]["toxicity_band"] in ("high", "exceptional"):
        return "high friction"
    if strong_f and not strong_a:
        return "friendship, little romance"
    if strong_f and strong_a:
        return "friendship with attraction"
    if strong_a and f == "low":
        return "attraction, thin friendship"
    return "mixed"


WANTED = ["friendship, little romance", "friendship with attraction",
          "attraction, thin friendship", "high friction", "mixed"]


def main():
    rng = random.Random(4924)
    chosen, seen = [], {p: 0 for p in WANTED}
    target = {"friendship, little romance": 3, "friendship with attraction": 2,
              "attraction, thin friendship": 3, "high friction": 2, "mixed": 2}
    tries = 0
    while len(chosen) < 12 and tries < 4000:
        tries += 1
        a, b = rng.sample(NAMES, 2)
        one, two = a_person(rng, a), a_person(rng, b)
        aspects, engine, friends, lean = assess(one, two)
        profile = profile_of(engine, friends)
        if seen[profile] >= target[profile]:
            continue
        seen[profile] += 1
        chosen.append((one, two, aspects, engine, friends, lean, profile))

    pathlib.Path(__file__).parent.joinpath("calibration.html").write_text(render(chosen))
    print(f"{len(chosen)} pairs after {tries} draws")
    for i, (_, _, _, _, _, _, profile) in enumerate(chosen, 1):
        print(f"  {i:>2}. {profile}")


def contacts_table(aspects, one, two):
    rows = []
    for c in sorted(aspects, key=lambda x: x.get("orb") or 99)[:9]:
        rows.append(f"<tr><td>{html.escape(one['name'])}&rsquo;s {c['person_1_planet']}</td>"
                    f"<td>{c['aspect']}</td>"
                    f"<td>{html.escape(two['name'])}&rsquo;s {c['person_2_planet']}</td>"
                    f"<td class='n'>{c.get('orb', 0):.1f}&deg;</td></tr>")
    return "".join(rows)


def overlays_table(engine, one, two):
    rows = []
    for o in (engine.get("top_house_overlays") or [])[:6]:
        who = one["name"] if o.get("direction") == "person_1_to_person_2" else two["name"]
        whose = two["name"] if o.get("direction") == "person_1_to_person_2" else one["name"]
        rows.append(f"<tr><td>{html.escape(who)}&rsquo;s {o.get('planet')}</td>"
                    f"<td>in {html.escape(whose)}&rsquo;s</td><td>{o.get('house')}th house</td></tr>")
    return "".join(rows) or "<tr><td colspan='3' class='muted'>no birth time on one side</td></tr>"


def render(chosen):
    s1, s2 = [], []
    for i, (one, two, aspects, engine, friends, lean, profile) in enumerate(chosen, 1):
        s1.append(f"""
<section class="pair">
  <h3>Pair {i} &mdash; {html.escape(one['name'])} &amp; {html.escape(two['name'])}</h3>
  <p class="born">{html.escape(one['name'])}: {one['born']}, {one['city']} &nbsp;&middot;&nbsp;
     {html.escape(two['name'])}: {two['born']}, {two['city']}</p>
  <div class="cols">
    <div>
      <h4>Closest contacts</h4>
      <table><tbody>{contacts_table(aspects, one, two)}</tbody></table>
    </div>
    <div>
      <h4>House overlays</h4>
      <table><tbody>{overlays_table(engine, one, two)}</tbody></table>
      <h4 class="ask">Your lean</h4>
      <div class="write"></div>
      <p class="hint">friendship / friendship with attraction / attraction with a thin
         friendship / mixed &mdash; and a word on why</p>
    </div>
  </div>
</section>""")

        dims = "".join(
            f"<tr><td>{k.replace('_', ' ')}</td><td class='n'>{v['score']}</td>"
            f"<td class='muted'>{html.escape(', '.join(v['evidence'][:2]))}</td></tr>"
            for k, v in friends["dimensions"].items())
        idx = engine["indices"]
        s2.append(f"""
<section class="pair">
  <h3>Pair {i} &mdash; {html.escape(one['name'])} &amp; {html.escape(two['name'])}
      <span class="tag">{html.escape(profile)}</span></h3>
  <p class="lean"><strong>Engine&rsquo;s lean:</strong> {html.escape(lean['lean'])}</p>
  <div class="cols">
    <div>
      <h4>Friendship {friends['friendship_score']} &mdash; {friends['friendship_band']}</h4>
      <table><tbody>{dims}</tbody></table>
    </div>
    <div>
      <h4>The other axis</h4>
      <table><tbody>
        <tr><td>attraction</td><td class="n">{idx['attraction']}</td><td>{idx['attraction_band']}</td></tr>
        <tr><td>emotional</td><td class="n">{idx['emotional']}</td><td>{idx['emotional_band']}</td></tr>
        <tr><td>staying power</td><td class="n">{idx['long_term']}</td><td>{idx['long_term_band']}</td></tr>
        <tr><td>friction</td><td class="n">{idx['toxicity']}</td><td>{idx['toxicity_band']}</td></tr>
      </tbody></table>
      <p class="say"><strong>How Zoli would open:</strong><br>
        &ldquo;{html.escape(opening(lean, engine, friends))}&rdquo;</p>
    </div>
  </div>
</section>""")

    return TEMPLATE.replace("{{SECTION1}}", "".join(s1)).replace("{{SECTION2}}", "".join(s2))


def opening(lean, engine, friends):
    shape = _relative_shape(engine["indices"])
    friction = engine["indices"]["toxicity_band"]
    line = {
        "a friendship, with little romantic emphasis":
            f"This reads as a real friendship — what carries it is {shape['leads_on']}, and there's little romantic weight in it.",
        "a friendship that also carries attraction":
            f"There's a genuine friendship here and an attraction running alongside it; {shape['leads_on']} is the strongest part.",
        "strong attraction on a thin friendship base":
            f"The pull is the loudest thing between you. What's thinner is the ordinary friendship underneath it.",
        "mostly a friendship, with some pull":
            f"Mostly a friendship, with a thread of something else. {shape['leads_on'].capitalize()} is what it runs on.",
        "mostly attraction, with a workable friendship":
            f"The pull leads, but there's a workable friendship under it — {shape['leads_on']} especially.",
    }.get(lean["lean"], f"What stands out is {shape['leads_on']}; nothing here settles what this is on its own.")
    if friction in ("high", "exceptional"):
        line += " It also takes more repair than most."
    return line


TEMPLATE = """<title>Zoli friendship calibration</title>
<style>
 :root{--ink:#241f19;--ink2:#5c5346;--ink3:#8e8474;--gold:#9a7128;--line:rgba(36,31,25,.14);--bg:#fbf6ec;--card:#fffdf8}
 @media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ink:#ecedf4;--ink2:#afb7ca;--ink3:#7f889d;--gold:#ebcf9b;--line:rgba(236,237,244,.16);--bg:#121826;--card:#1a2233}}
 body{background:var(--bg);color:var(--ink);font:400 15px/1.55 ui-serif,Georgia,serif;margin:0}
 .wrap{max-width:900px;margin:0 auto;padding:34px 20px 80px}
 h1{font-size:30px;font-weight:400;margin:0 0 6px}
 .sub{color:var(--ink2);max-width:62ch;margin:0 0 20px}
 .tabs{display:flex;gap:8px;margin:0 0 22px;border-bottom:1px solid var(--line)}
 .tabs button{font:inherit;font-size:13px;letter-spacing:.06em;text-transform:uppercase;background:none;border:0;border-bottom:2px solid transparent;color:var(--ink3);padding:9px 14px;cursor:pointer}
 .tabs button[aria-selected=true]{color:var(--gold);border-bottom-color:var(--gold)}
 .warn{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:0 10px 10px 0;padding:13px 16px;margin:0 0 24px;color:var(--ink2);font-size:14px}
 .pair{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:0 0 16px}
 h3{font-size:19px;font-weight:500;margin:0 0 3px}
 .tag{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin-left:8px}
 .born{color:var(--ink3);font-size:13px;margin:0 0 12px}
 .cols{display:grid;grid-template-columns:1fr 1fr;gap:22px}
 @media(max-width:700px){.cols{grid-template-columns:1fr}}
 h4{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);margin:0 0 7px;font-weight:500}
 h4.ask{margin-top:16px;color:var(--gold)}
 table{width:100%;border-collapse:collapse;font-size:13.5px}
 td{padding:4px 6px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
 td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 .muted{color:var(--ink3);font-size:12.5px}
 .write{border:1px dashed var(--line);border-radius:8px;height:62px}
 .hint{color:var(--ink3);font-size:12px;margin:5px 0 0}
 .lean{margin:0 0 12px}
 .say{margin:14px 0 0;color:var(--ink2);font-size:14px;line-height:1.6}
 [hidden]{display:none!important}
</style>
<div class="wrap">
  <h1>Friendship calibration</h1>
  <p class="sub">Twelve invented pairs. Read the contacts, write your own lean in the box,
     and only then open the second tab. The scores are there to be disagreed with &mdash;
     where you disagree, say why, and the weights change.</p>
  <div class="tabs" role="tablist">
    <button role="tab" aria-selected="true" onclick="show(1)">1 &middot; The charts</button>
    <button role="tab" aria-selected="false" onclick="show(2)">2 &middot; What the engine said</button>
  </div>
  <div id="p1">
    <p class="warn">Everyone here is fictional. No real user&rsquo;s chart is in this file.</p>
    {{SECTION1}}
  </div>
  <div id="p2" hidden>
    <p class="warn">Equal weights, unreviewed. Friendship bands are cut at the 25th, 75th
      and 90th percentiles of 1,000 random pairs, so &ldquo;high&rdquo; means high among
      pairs in general.</p>
    {{SECTION2}}
  </div>
</div>
<script>
 function show(n){
   document.getElementById('p1').hidden = n!==1;
   document.getElementById('p2').hidden = n!==2;
   document.querySelectorAll('.tabs button').forEach((b,i)=>b.setAttribute('aria-selected', String(i===n-1)));
 }
</script>"""

if __name__ == "__main__":
    main()
