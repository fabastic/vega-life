"""His life as something to look at and read: lanes for a timeline, places on a map, and a written life story.

  timeline   every happening, with its age, feeling and a lane (family, love, friends, school, work and money, body,
             mind, world), written by the trainer to timeline.jsonl. Older lives only have events.jsonl, so their
             lanes are guessed from words in the text
  places     where he was born, where he lives now, and where his people are, as real cities with coordinates.
             The city is fixed by the seed within his region; emigration moves him to a city in the new region
  story      a biography in chapters by life stage: the most felt events of each stage, the people who mattered,
             and (where the network has spoken) his own inner voice and dreams. Exported as Markdown
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional

LANES = ["family", "love", "friends", "school", "work", "body", "mind", "world"]
LANE_LABEL = {"family": "Family", "love": "Love", "friends": "Friends", "school": "School", "work": "Work and money",
              "body": "Body", "mind": "Mind", "world": "World"}

KEY_LANE = {
    "partner": "love", "wedding": "love", "moving_in": "love", "affair": "love", "own_divorce": "love",
    "breakup": "love", "first_sex": "love", "dating": "love",
    "child": "family", "death": "family", "divorce": "family", "estranged": "family", "pregnancy": "family",
    "infertility": "family", "teen_pregnancy": "family", "grandchild": "family", "care": "family", "pet": "family",
    "friend": "friends", "fight": "friends", "repair": "friends", "bond": "friends", "there_for": "friends",
    "absent": "friends", "their_trouble": "friends", "bullied": "friends", "cyberbullied": "friends",
    "mentor": "friends",
    "study": "school", "school": "school", "exam": "school",
    "work": "work", "money": "work", "debt": "work", "scam": "work", "emigrate": "work", "hardship": "work",
    "illness": "body", "health": "body", "injury": "body", "hormone": "body", "puberty": "body",
    "mental": "mind", "recover": "mind", "self_harm": "mind", "regret": "mind", "dream": "mind",
    "prejudice": "world", "disaster": "world", "move": "world", "war": "world", "pandemic": "world",
    "prison": "world", "online": "world", "body": "body", "world": "world", "recession": "work", "ace": "family",
}
GENERIC = {"joy", "sorrow"}                  # small everyday moments: placed by their words, else in the mind lane
WORDS = [("love", ("falls in love", "marries", "moves in with", "partner", "divorce", "breaks up", "kiss", "date")),
         ("family", ("mum", "dad", "mother", "father", "grand", "sister", "brother", "baby", "son", "daughter",
                     "funeral", "dies", "pregnan", "pet", "dog", "cat")),
         ("friends", ("friend", "bullied", "party", "teammate", "neighbour", "coach")),
         ("school", ("school", "exam", "teacher", "class", "university", "degree", "grade", "homework", "gcse")),
         ("work", ("job", "work", "boss", "promot", "salary", "pay", "money", "debt", "rent", "laid off", "hired",
                   "retire", "emigrat", "moves to")),
         ("body", ("diagnos", "hospital", "pain", "sick", "ill", "injur", "surgery", "glasses", "heart", "cancer",
                   "sleep", "puberty", "period")),
         ("mind", ("depress", "anxi", "panic", "therap", "thinks", "feels", "regret", "lonely", "guilt", "proud"))]


def lane_of(key: str, text: str = "") -> str:
    if key in KEY_LANE:
        return KEY_LANE[key]
    t = text.lower()
    for lane, words in WORDS:
        if any(re.search(r"\b" + re.escape(w), t) for w in words):      # at the start of a word
            return lane
    return "mind" if key in GENERIC else "world"


# --- places ---------------------------------------------------------------------------------------------------------
# (city, latitude, longitude): a few real cities per region; which one is fixed by the seed.
CITIES: Dict[str, List[tuple]] = {
    "North America": [("Chicago", 41.9, -87.6), ("Toronto", 43.7, -79.4), ("Houston", 29.8, -95.4),
                      ("Seattle", 47.6, -122.3), ("Atlanta", 33.7, -84.4)],
    "Latin America": [("Mexico City", 19.4, -99.1), ("São Paulo", -23.6, -46.6), ("Bogotá", 4.7, -74.1),
                      ("Lima", -12.0, -77.0), ("Buenos Aires", -34.6, -58.4)],
    "Western Europe": [("Manchester", 53.5, -2.2), ("Lyon", 45.8, 4.8), ("Rotterdam", 51.9, 4.5),
                       ("Munich", 48.1, 11.6), ("Madrid", 40.4, -3.7)],
    "Nordic countries": [("Gothenburg", 57.7, 12.0), ("Oslo", 59.9, 10.8), ("Aarhus", 56.2, 10.2),
                         ("Tampere", 61.5, 23.8)],
    "Eastern Europe": [("Kraków", 50.1, 19.9), ("Bucharest", 44.4, 26.1), ("Kyiv", 50.5, 30.5),
                       ("Brno", 49.2, 16.6)],
    "Middle East and North Africa": [("Cairo", 30.0, 31.2), ("Amman", 31.9, 35.9), ("Casablanca", 33.6, -7.6),
                                     ("Tehran", 35.7, 51.4), ("Dubai", 25.2, 55.3)],
    "Sub-Saharan Africa": [("Lagos", 6.5, 3.4), ("Nairobi", -1.3, 36.8), ("Accra", 5.6, -0.2),
                           ("Johannesburg", -26.2, 28.0), ("Addis Ababa", 9.0, 38.7)],
    "South Asia": [("Delhi", 28.6, 77.2), ("Mumbai", 19.1, 72.9), ("Dhaka", 23.8, 90.4), ("Lahore", 31.5, 74.3),
                   ("Chennai", 13.1, 80.3)],
    "East Asia": [("Seoul", 37.6, 127.0), ("Osaka", 34.7, 135.5), ("Chengdu", 30.7, 104.1),
                  ("Taipei", 25.0, 121.6)],
    "Southeast Asia": [("Manila", 14.6, 121.0), ("Jakarta", -6.2, 106.8), ("Ho Chi Minh City", 10.8, 106.7),
                       ("Bangkok", 13.8, 100.5)],
    "Oceania": [("Melbourne", -37.8, 145.0), ("Auckland", -36.8, 174.8), ("Brisbane", -27.5, 153.0)],
}


def city(region: str, seed: int, salt: str = "") -> dict:
    opts = CITIES.get(region) or CITIES["Western Europe"]
    name, lat, lon = random.Random(f"{seed}:{region}:{salt}").choice(opts)
    return {"city": name, "region": region, "lat": lat, "lon": lon}


def places(L: dict, seed: int) -> dict:
    """Where his life happened, from a live.json: born, lives now, and his people's places."""
    from .factors import REGION_NAMES
    region = (L.get("factors") or {}).get("region")
    e = (L.get("economy") or {}).get("emigrated")
    here_name = None
    if isinstance(region, dict):
        region = region.get("value")
    if isinstance(region, (int, float)):
        here_name = REGION_NAMES[int(round(float(region) * (len(REGION_NAMES) - 1)))]
    born_region = (e or {}).get("from") or here_name or "Western Europe"
    now_region = (e or {}).get("to") or here_name or born_region
    born = city(born_region, seed, "born")
    now = born if now_region == born_region else city(now_region, seed, "moved")
    people = []
    for x in (L.get("family") or {}).get("people", []):
        rel = x.get("relation", "")
        far = bool(e) and rel in ("mother", "father", "grandparent", "sibling", "aunt", "uncle", "cousin")
        at = born if far else now
        people.append({"name": x.get("name"), "relation": rel, "alive": x.get("alive", True), "city": at["city"],
                       "lat": at["lat"], "lon": at["lon"]})
    moves = [{"from": born, "to": now, "at": e.get("at")}] if e else []
    return {"born": born, "now": now, "moves": moves, "people": people, "care_home": L.get("residence") == "care_facility"}


# --- the timeline ---------------------------------------------------------------------------------------------------
SKIP = ("born.", "resumed", "brain grows", "critical period", "scheduled", "intervention", "ignored", "stopped",
        "it pays off", "pays the price", "consequence")
NOISE = ("switched on by methylation",)


def timeline(run_dir: Path, limit: int = 4000) -> List[dict]:
    """[{age, text, lane, v}] from timeline.jsonl, or guessed from events.jsonl for older lives."""
    rows: List[dict] = []
    t = run_dir / "timeline.jsonl"
    if t.exists():
        for line in t.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            rows.append({"age": r["age"], "text": r["text"], "lane": r.get("lane") or lane_of(r.get("key", ""), r["text"]),
                         "v": r.get("v", 0.0), "a": r.get("a", 0.4)})
    else:
        f = run_dir / "events.jsonl"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                text = r.get("event")
                if not text or text.startswith(SKIP) or any(w in text for w in NOISE):
                    continue
                rows.append({"age": r.get("age", 0.0), "text": text, "lane": lane_of("", text), "v": None, "a": 0.4})
    if len(rows) > limit:                         # keep the most felt, then put back in order
        rows = sorted(sorted(rows, key=lambda r: -abs(r["v"] or 0.3))[:limit], key=lambda r: r["age"])
    return rows


# --- the life story ---------------------------------------------------------------------------------------------------
CHAPTERS = [("Infancy", 0, 3), ("Childhood", 3, 12), ("Adolescence", 12, 19), ("Early adulthood", 19, 36),
            ("Middle adulthood", 36, 56), ("Late adulthood", 56, 200)]


def _sentence(age: float, text: str, he: str = "he") -> str:
    t = text.strip().rstrip(".")
    first = t.split(" ", 1)[0]
    if t[:1].islower() and first not in ("the", "his", "her", "a", "an", "their", "one", "two", "it"):
        return f"At {int(age)} {he} {t}."
    return f"At {int(age)}: {t[:1].upper() + t[1:]}."


def story_markdown(run_dir: Path, per_chapter: int = 9) -> str:
    live = {}
    f = run_dir / "live.json"
    if f.exists():
        try:
            live = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            live = {}
    cfg = {}
    if (run_dir / "config.json").exists():
        cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8-sig"))
    rows = timeline(run_dir)
    sex = ((live.get("factors") or {}).get("sex") or {})
    female = (sex.get("value") if isinstance(sex, dict) else sex) is not None and \
        float(sex.get("value") if isinstance(sex, dict) else sex) < 0.5
    he, him = ("she", "her") if female else ("he", "him")
    years = live.get("age_years") or (rows[-1]["age"] if rows else 0)
    pl = places(live, int(cfg.get("seed", 1))) if live else None
    out = [f"# A life: {run_dir.name}", ""]
    intro = f"Seed {cfg.get('seed', '?')}" + (f" (“{cfg['seed_phrase']}”)" if cfg.get("seed_phrase") else "")
    if pl:
        intro += f". Born in {pl['born']['city']}, {pl['born']['region']}"
        if pl["now"]["city"] != pl["born"]["city"]:
            intro += f"; later lived in {pl['now']['city']}, {pl['now']['region']}"
    intro += f". {'Died' if live.get('alive') is False else 'Now'} at {years:.1f} years"
    if live.get("cause_of_death"):
        intro += f", of {live['cause_of_death']}"
    out += [intro + ".", ""]
    for title, a, b in CHAPTERS:
        chunk = [r for r in rows if a <= r["age"] < b]
        if not chunk:
            continue
        if any(r["v"] is not None for r in chunk):
            felt = sorted(chunk, key=lambda r: -abs(r["v"] or 0) * (0.5 + r.get("a", 0.4)))
            keep, seen = [], set()
            for r in felt:                                     # the most felt, each told once
                if r["text"] not in seen:
                    keep.append(r)
                    seen.add(r["text"])
                if len(keep) >= per_chapter:
                    break
        else:                                                  # no feelings recorded: spread across the stage
            uniq = list({r["text"]: r for r in chunk}.values())
            step = max(1, len(uniq) // per_chapter)
            keep = uniq[::step][:per_chapter]
        keep.sort(key=lambda r: r["age"])
        lanes: Dict[str, int] = {}
        for r in chunk:
            lanes[r["lane"]] = lanes.get(r["lane"], 0) + 1
        top = ", ".join(LANE_LABEL[k].lower() for k, _ in sorted(lanes.items(), key=lambda t: -t[1])[:3])
        out += [f"## {title} ({a}–{min(b, int(years) + 1) if b > 100 else b})", "",
                f"*Most of what happened was about {top}.*", ""]
        out += [_sentence(r["age"], r["text"], he) for r in keep]
        out.append("")
    dreams = live.get("dreams") or []
    inner = (live.get("mind") or {}).get("inner")
    if inner or dreams:
        out += [f"## In {'her' if female else 'his'} own words", "",
                f"*Generated by {'her' if female else 'his'} own network (not templates): the inner voice and "
                "the dreams.*", ""]
        if inner:
            out.append(f"> {inner.strip()}")
            out.append("")
        for a, t in dreams[-5:]:
            out.append(f"- at {int(a)}: *{str(t).strip()}*")
        out.append("")
    people = [x for x in (live.get("family") or {}).get("people", []) if x.get("closeness", 0) >= 0.7]
    if people:
        out += [f"## The people closest to {him}", ""]
        out += [f"- {x['name']} ({x['relation'].replace('_', ' ')})"
                + ("" if x.get("alive", True) else f", who died when {he} was {x.get('died_at_his_age')}") for x in people]
        out.append("")
    return "\n".join(out)
