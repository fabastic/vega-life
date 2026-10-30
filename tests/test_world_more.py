"""School by region, mental health, the phone, relationship dynamics and prejudice: each behaves as the research
says, at roughly the rates surveys report."""
import collections

from vegalife import factors as fx
from vegalife.people import Circle
from vegalife.character import Character
from vegalife.world import Person


def _live(seed, years=85, overrides=None):
    F = fx.sample(seed, overrides)
    p = Person(F, seed, Circle(F, seed))
    ch = Character(p, F)                                 # as a real life runs: character shapes him each month
    while p.alive and p.age < years * 12:
        p.step_month(F)
        ch.step(p, F)
        p.happenings.clear()
    return p, F


def test_new_factors_have_real_units_and_old_seeds_keep_their_values():
    F = fx.sample(5)
    ui = {c["key"]: c["ui"] for c in fx.catalogue()}
    assert ui["region"]["kind"] == "choice" and len(ui["region"]["options"]) == len(fx.REGION_NAMES)
    assert ui["iq"]["kind"] == "scale" and ui["iq"]["lo"] == 70
    assert F["minority_status"] in (0.0, 0.5, 1.0)
    old = fx.FactorSet({"ses": 0.5}, {"ses": "seeded"})
    assert old["iq"] == fx.ALL["iq"].mean            # a life saved before a factor existed gets its average


def test_school_follows_the_region_and_the_course_decision_explains_itself():
    p, F = _live(3, years=20, overrides={"region": 1.0 * 8 / 10})       # East Asia
    sc = p.school
    assert sc.region == "East Asia" and sc.exam is not None and sc.wanted
    assert sc.why and len(sc.chosen) == 3


def test_rates_match_surveys():
    N = 60
    life = collections.Counter()
    estranged = 0
    for seed in range(200, 200 + N):
        p, _ = _live(seed)
        for c in {h[0] for h in p.mind.history} | set(p.mind.active):
            life[c] += 1
        estranged += any(b.estranged_at is not None for b in p.bonds.bonds.values())
    assert 0.1 <= life["depression"] / N <= 0.4          # ~20-30% over a life
    assert 0.15 <= life["anxiety"] / N <= 0.45           # ~30%
    assert life["PTSD"] / N <= 0.2                       # ~7%
    assert 0.08 <= estranged / N <= 0.45                 # ~27% (Pillemer)


def test_the_feed_learns_and_a_phone_arrives_around_eleven():
    p, F = _live(7, years=16, overrides={"phone_rules": 0.0, "echo_chambers": 1.0})
    o = p.online
    assert o.has_phone and 6 <= o.phone_at / 12 <= 14
    assert len(o.feed) >= 12 and all("topic" in x and "seconds" in x for x in o.feed)
    assert o.hours > 3


def test_conscience_judges_bias_and_repairs():
    p, F = _live(11, years=20)
    cs = p.conscious
    assert cs.judge("laugh at a joke about a classmate's accent") < 0
    assert cs.judge("mock a colleague he assumes got the job to fill a quota") < 0
    assert cs.judge("stand up for someone being picked on") > 0 and cs.judge("apologise to Rose") > 0


def test_hiring_bias_cuts_callbacks_for_a_visible_minority():
    F = fx.sample(1, {"minority_status": 1.0, "prejudice_climate": 0.4})
    p = Person(F, 1, Circle(F, 1))
    assert 0.6 < p.prejudice.callback(F) < 0.8          # ~1 in 3 fewer callbacks (Quillian 2017)
    F2 = fx.sample(1, {"minority_status": 0.0, "migrant_background": 0.0})
    assert Person(F2, 1, Circle(F2, 1)).prejudice.callback(F2) == 1.0


def test_old_lives_get_the_new_parts():
    F = fx.sample(2)
    p = Person(F, 2, Circle(F, 2))
    p.age = 40 * 12
    for k in Person.PARTS:
        delattr(p, k)
    p.upgrade(F, 2)
    assert p.school.stage == "done" and p.bonds.bonds == {}
    p.step_month(F)


def test_seasons_rates_match_research():
    N = 60
    infertile = ppd = parents = scammed = loss = 0
    for seed in range(400, 400 + N):
        p, _ = _live(seed, years=90)
        z = p.seasons
        infertile += z.counts.get("infertility", 0) > 0 or any(
            "trying for a baby" in t[1] for t in z.recent)
        parents += z.counts.get("newborn", 0) > 0
        ppd += z.counts.get("postnatal", 0) > 0
        scammed += z.scams > 0
        loss += p.family.pregnancy_losses > 0
    assert parents >= 15
    assert ppd / parents <= 0.35                          # ~10% per birth (Paulson 2010)
    assert 0.15 <= scammed / N <= 0.7
    assert loss / N <= 0.45


def test_fatherhood_lowers_testosterone_and_ages_bring_their_own_moments():
    F = fx.sample(9, {"sex": 1.0})
    p = Person(F, 9, Circle(F, 9))
    while p.age < 17 * 12:
        p.step_month(F)
        p.happenings.clear()
    teen = p.seasons.testosterone
    assert teen > 0.4
    assert {"first_steps", "tooth"} & p.seasons.done
    assert any(t for t in p.seasons.recent)
    from vegalife.family import Relative
    p.age = 30 * 12
    p.family.people.append(Relative("Ivy", "child", p.age, 0.9, joined=p.age))
    for _ in range(18):
        p.step_month(F)
        p.happenings.clear()
    assert p.seasons.fatherhood_drop > 0.15 and p.seasons.testosterone < teen


def test_regrets_of_inaction_grow():
    p, F = _live(21, years=60)
    for r in p.seasons.regrets.values():
        assert r["kind"] in ("foundation", "boldness", "moral", "connection") and r["text"].startswith("I wish")


def test_illness_follows_age_and_survey_rates():
    N = 80
    bp50 = bp70 = n50 = n70 = asthma_kids = n10 = cancer = 0
    for seed in range(600, 600 + N):
        F = fx.sample(seed)
        p = Person(F, seed, Circle(F, seed))
        ch = Character(p, F)
        while p.alive and p.age < 90 * 12:
            p.step_month(F)
            ch.step(p, F)
            p.happenings.clear()
            if p.age == 10 * 12:
                n10 += 1
                asthma_kids += "asthma" in p.illness.active
            if p.age == 50 * 12:
                n50 += 1
                bp50 += "high blood pressure" in p.illness.active
            if p.age == 72 * 12:
                n70 += 1
                bp70 += "high blood pressure" in p.illness.active
        cancer += "cancer" in p.illness.done
    assert asthma_kids / n10 <= 0.2                      # ~8% of children
    assert bp50 / n50 < bp70 / n70                       # rises with age (CDC: 33% at 40-59, 63% at 60+)
    assert 0.2 <= bp50 / n50 <= 0.6 and 0.5 <= bp70 / n70 <= 0.95
    assert 0.2 <= cancer / N <= 0.6                      # ~40% over a life


def test_sleep_apnoea_and_insomnia_cost_sleep():
    from vegalife.illness import Illness
    F = fx.sample(4)
    p = Person(F, 4, Circle(F, 4))
    ch = Character(p, F)
    while p.age < 45 * 12:
        p.step_month(F)
        ch.step(p, F)
    q = p.clone()
    q.illness = Illness(4)
    q.illness.active.update({"insomnia": q.age, "sleep apnoea": q.age})
    q.illness.known.update({"insomnia": True, "sleep apnoea": False})
    for _ in range(6):
        p.step_month(F); ch.step(p, F)
        q.step_month(F); ch.step(q, F)
    assert q.illness.sleep_now >= 0.18 and q.s["sleep"] < p.s["sleep"]


def test_hormones_follow_the_life_course():
    girl, F = _live(31, years=60, overrides={"sex": 0.0})
    h = girl.hormones
    assert h.menarche is not None and 10 <= h.menarche <= 15.5
    assert abs(h.height - h.target_height) < 4             # grown to her genetic height, a little shrunk by 60
    assert h.levels["estrogen"] < 0.3                     # after menopause
    boy, G = _live(32, years=17, overrides={"sex": 1.0})
    assert boy.hormones.levels["testosterone"] > 0.4 and boy.hormones.done & {"voice", "spurt"}
    assert boy.hormones.dopamine_gain(16) > boy.hormones.dopamine_gain(30) > boy.hormones.dopamine_gain(80)


def test_bone_peaks_around_thirty_then_falls_faster_after_menopause():
    p, F = _live(33, years=30, overrides={"sex": 0.0})
    peak = p.s["bone_density"]
    from vegalife.character import Character as C
    ch = C(p, F)
    while p.age < (p.hormones.menopause_age + 6) * 12:
        p.step_month(F)
        ch.step(p, F)
        p.happenings.clear()
    assert p.s["bone_density"] < peak - 0.05


def test_hardships_rates_and_consequences():
    N = 60
    smoked = prison = assault = 0
    for seed in range(800, 800 + N):
        p, F = _live(seed, years=70)
        h = p.hardships
        smoked += h.ever_smoked
        prison += h.counts.get("prison", 0) > 0
        assault += h.counts.get("assault", 0) > 0
    assert 0.15 <= smoked / N <= 0.65
    assert prison / N <= 0.15
    assert assault / N <= 0.5
    F = fx.sample(1)
    q = Person(F, 1, Circle(F, 1))
    q.hardships.record = True
    assert q.hardships.hiring() == 0.5


def test_smoking_raises_lung_disease_risk():
    from vegalife.illness import BY
    F = fx.sample(2)
    p = Person(F, 2, Circle(F, 2))
    p.age = 60 * 12
    base = BY["COPD"].risk(p, F, p.illness)
    p.hardships.smoker = p.hardships.ever_smoked = True
    assert BY["COPD"].risk(p, F, p.illness) > base + 1.5


def test_last_years_bring_a_decline_in_wellbeing():
    from vegalife.seasons import Seasons
    F = fx.sample(3)
    p = Person(F, 3, Circle(F, 3))
    p.age = 80 * 12
    z = Seasons(3)
    p.s["health"] = 0.9
    z.step(p, F)
    well = z.shape
    p.s["health"] = 0.2
    z.step(p, F)
    assert z.shape > well + 0.05


def test_self_harm_only_alongside_low_mood_and_more_in_girls():
    girls = boys = 0
    for seed in range(1000, 1060):
        g, _ = _live(seed, years=25, overrides={"sex": 0.0})
        b, _ = _live(seed, years=25, overrides={"sex": 1.0})
        girls += getattr(g.mind, "self_harmed", False)
        boys += getattr(b.mind, "self_harmed", False)
    assert girls >= boys and girls / 60 <= 0.4
