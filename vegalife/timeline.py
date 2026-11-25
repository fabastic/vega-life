"""The world's own timeline (round 3, C3): dated recessions, a pandemic and new technology, hitting everyone born in
the same year at the same age.

  birth year   the factor `birth_year` (0 = 1950 .. 1 = 2010); the calendar year is birth year + his age.
  recessions   US recessions dated by the NBER business-cycle committee. In a recession year layoffs rise.
  scarring     finishing education into a recession costs pay: about 9% at first for a 5-point rise in
               unemployment, fading to nothing over 8-10 years, and lasting longer for the less advantaged
               (Oreopoulos, von Wachter & Heisz 2012). Here: a cut that starts at SCAR and fades linearly over
               SCAR_YEARS, larger for a poorer start.
  technology   the year the internet, smartphones and social feeds reach most homes, so a child of 1960 meets
               them as an adult and a child of 2005 grows up with them.

Everything is a function of the year: no random generator, so it never shifts his world.
"""
from __future__ import annotations

from typing import List, Optional

FIRST, LAST = 1950, 2010
# (start, end) calendar years, end inclusive, and how deep (0..1, 1 = the 2008 Great Recession)
RECESSIONS = [(1953, 1954, 0.4), (1957, 1958, 0.5), (1960, 1961, 0.3), (1969, 1970, 0.3), (1973, 1975, 0.7),
              (1980, 1982, 0.8), (1990, 1991, 0.4), (2001, 2001, 0.3), (2008, 2009, 1.0), (2020, 2020, 0.6)]
EVENTS = [(1969, "people walk on the Moon; the whole world watches"),
          (1989, "the Berlin Wall comes down"),
          (1995, "the internet arrives in ordinary homes"),
          (2001, "planes hit the towers in New York"),
          (2007, "smartphones arrive; soon everyone carries one"),
          (2008, "the banks crash and the world falls into recession"),
          (2010, "social media feeds take over everyone's evenings"),
          (2020, "a pandemic shuts the world indoors"),
          (2023, "AI that talks back arrives in everyone's pocket")]
PANDEMIC = {2020, 2021}
SCAR, SCAR_YEARS = 0.09, 9.0


def birth_year(F) -> int:
    return round(FIRST + (LAST - FIRST) * F["birth_year"])


def year_of(F, age_months: int) -> int:
    return birth_year(F) + age_months // 12


def recession(year: int) -> float:
    """How deep the economy is in recession this year (0 none .. 1 the worst on record here)."""
    return max((d for a, b, d in RECESSIONS if a <= year <= b), default=0.0)


class Timeline:
    def __init__(self, F):
        self.born = birth_year(F)
        self.ses = F["ses"]
        self.entered: Optional[int] = None      # the year he first joined the labour market
        self.entry_depth = 0.0                  # how deep the recession was then
        self.seen: List[int] = []               # years of EVENTS already lived

    def scar(self, year: int) -> float:
        """The share of pay lost this year from having started work in a recession."""
        ses = self.ses
        if self.entered is None or not self.entry_depth:
            return 0.0
        fade = SCAR_YEARS * (1.0 + 0.6 * max(0.0, 0.5 - ses))      # longer for the less advantaged
        left = max(0.0, 1.0 - (year - self.entered) / fade)
        return SCAR * self.entry_depth * left * (1.0 + 0.5 * max(0.0, 0.5 - ses))

    def step(self, p, F) -> List[dict]:
        y = year_of(F, p.age)
        out = []
        if self.entered is None and p.s["employed"] > 0.5 and p.years >= 16:
            self.entered, self.entry_depth = y, recession(y)
            if self.entry_depth >= 0.5:
                out.append({"text": "starts work in the middle of a recession; good jobs are scarce",
                            "valence": -0.3, "arousal": 0.4, "who": [], "key": "recession", "deltas": {}})
        for when, text in EVENTS:
            if when == y and when not in self.seen and p.age % 12 == 0 and p.years >= 4:
                self.seen.append(when)
                out.append({"text": f"{text} (he is {int(p.years)})", "valence": 0.0, "arousal": 0.5, "who": [],
                            "key": "world", "deltas": {}})
        return out

    def to_json(self, F, age_months: int) -> dict:
        y = year_of(F, age_months)
        return {"born": self.born, "year": y, "recession": recession(y), "entered_work": self.entered,
                "entry_recession": self.entry_depth}
