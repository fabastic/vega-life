# Surroundings: what to add next, and how big each effect should be

Vega's surroundings today are a handful of 0–1 factors (neighbourhood safety, screen time, community ties, local
pollution, extreme weather, low walkability, housing). These proposals make the world around him more realistic
while keeping every effect tied to a published number, as CALIBRATION.md does.

## Proposed additions, with calibration targets

| Add | What it does to him | Calibrate against | Notes |
|---|---|---|---|
| **Green space near home** | Lowers adult psychiatric risk, dose-dependent on years of childhood exposure | Engemann et al. 2019 (PNAS, ~1M Danes): the least-green upbringing carried up to 55% higher risk than the greenest, with a range of 15–55% across disorders | Correlational, so model it as one weak protective pathway (stress load, mood), not a cure |
| **Neighbourhood opportunity, by years of exposure** | Moving to a better (or worse) area shifts adult outcomes by about 4% of the gap per year of childhood spent there, linear in age at the move, and ~0 after 18 | Chetty & Hendren 2018; Chetty, Hendren & Katz 2016 (MTO) | Turns a move into a dose of exposure instead of a one-off shock. It fits the new critical periods well |
| **Lead and toxic exposure** | Lowers cognition, steeply at low doses | Lanphear et al. 2005 pooled cohorts: ~3.9 IQ points from 2.4→10 µg/dL, and 6.9 points from 2.4→30 | Today `local_pollution` stands in for everything. Split lead out as an early-childhood-only hit |
| **Noise (aircraft, road)** | Slows reading and memory at school | RANCH (~2,800 children, 3 airports): aircraft noise linearly impairs reading comprehension; road noise affects episodic memory | Small per decibel, but it adds up over years of school |
| **Heat on school days** | Less learning in hot years unless the school has air conditioning | Park, Goodman et al. 2020: a 1°F hotter school year means about 1% less learning; air conditioning almost fully offsets it | Links `extreme_weather` and school quality to his language and problem-solving gains |
| **Urban versus rural upbringing** | Raises psychosis and paranoia risk with urbanicity | Vassos et al. 2012 meta-analysis: about 2.4× in the most urban areas against the most rural; not seen in low- and middle-income countries | Model as a slow rise in suspicion and anxiety, scaled by how many childhood years he spends there |
| **Family income, log scale** | Brain and skill differences are largest at the bottom of the income range | Noble et al. 2015 (n=1,099): small income gains matter most for the poorest | `ses` acts linearly now; make its effect on language and executive function logarithmic |
| **Commute** | Long commutes lower life satisfaction, and pay does not make up for it | Stutzer & Frey 2008: a 1-hour one-way commute needs about 40% more pay to break even | Adult-only. It costs time, sleep and stress load |
| **Social media (fix the current weight)** | Should be a very small average effect | Orben & Przybylski 2019: at most 0.4% of the variance in teen wellbeing | Check `screen_time` and `echo_chambers` against this. They may be too strong now |

## Structural improvements (beyond new factors)

1. **A place with coordinates.** Give him a home on a small map: home, school, park, workplace, friends' homes.
   Then green space, noise, heat, commute and walkability come from where he lives, and a move changes several at
   once, as a real one does.
2. **Exposure as dose over years.** Use a running integral per factor (years × intensity), so effects depend on
   how long and how early, matching the neighbourhood and green-space results above.
3. **Time use.** A typical weekday and weekend (sleep, school or work, commute, screens, outdoors, friends), drawn
   from the factors. Many effects act through time: commute takes sleep, screens take outdoor time.
4. **Seasons and weather.** Hot spells during school, dark winters (mood), storms (which already exist as
   disasters).
5. **Neighbours and community as people.** A few named adults (a coach, a shopkeeper, a neighbour) who can mentor,
   help or harm him, built the same way as friends.

Sources: Engemann et al. 2019 (PNAS); Chetty & Hendren 2018; Chetty, Hendren & Katz 2016 (AER); Lanphear et al.
2005 (EHP); Clark et al. 2006 (RANCH, AJE); Park, Goodman, Hurwitz & Smith 2020 (AEJ: Policy); Vassos et al. 2012
(Schizophr Bull); Noble et al. 2015 (Nat Neurosci); Stutzer & Frey 2008 (Scand J Econ); Orben & Przybylski 2019
(Nat Hum Behav).
