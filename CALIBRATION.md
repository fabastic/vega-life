# How realistic is his world?

The world model in `vegalife/world.py`, `character.py` and `memory.py` is calibrated against published findings
where good numbers exist. Run `python tools/calibrate.py` to simulate hundreds of lives (without the network)
and check them against the targets below. `tests/test_calibration.py` runs a cheap version in the test suite.

This is a coarse model of a life, not an epidemiological model. Where a number exists it sets the size of an
effect. Where it doesn't, the effect is kept small and marked weak or speculative.

## Calibration results (200 lives per condition)

Each check was run two ways:
- **choosing:** each month he faces his situations and picks at random, a stand-in for a network that has
  learned nothing. Their effects and delayed consequences count.
- **not choosing:** the world runs with nobody choosing.

All 8 checks are in range both ways.

| check | choosing | not choosing | target | source |
|---|---|---|---|---|
| life expectancy at birth | 78.4 y | 77.9 y | 78.4 (US 2023; men 75.8) | [CDC NCHS Data Brief 521](https://www.cdc.gov/nchs/products/databriefs/db521.htm) |
| poorest vs richest family | 13.6 y | 13.1 y | 14.6 y men / 10.1 y women, richest vs poorest 1% | [Chetty et al. 2016, JAMA](https://hcp.hms.harvard.edu/publication/association-between-income-and-life-expectancy-united-states-2001-2014) |
| strong vs weak social ties, survival to 80 | OR 1.33 | OR 1.59 | OR 1.50 | [Holt-Lunstad, Smith & Layton 2010](https://cdr.lib.unc.edu/concern/articles/7d2792359?locale=en) |
| heavy childhood adversity, death before 65 | RR 1.71 | RR 1.59 | +45% for 4+ ACEs; OR 1.8 in family data | [JTG Foundation summary of NICHD cohort](https://www.jtgfoundation.org/resource/with-data-spanning-more-than-50-years-new-study-links-number-and-type-of-aces-to-premature-mortality-in-mid-adulthood/) |
| heavy childhood adversity, distress at 30 | RR 4.1 | RR 4.7 | OR 3-6 for mental ill health | [Hughes et al. 2017, Lancet Public Health](https://doaj.org/article/8fe15a7d379d4d51a2cb895ae247a935) |
| unemployment, working-age death rate | HR 2.31 | HR 1.36 | HR 1.63 adjusted | [Roelfs et al. 2011](https://mcgill.ca/sociology/files/sociology/2011_--_social_science__medicine_0.pdf) |
| clean vs heavily polluted air | 3.3 y | 2.4 y | 0.98 y per 10 ug/m3 PM2.5 | [AQLI, via WEF](https://www.weforum.org/stories/2017/09/this-map-shows-how-many-years-could-be-added-to-you-life-if-the-air-you-breathe-was-less-polluted/) |
| night shift work, metabolic disease by 60 | RR 1.46 | RR 1.21 | OR 1.09 pooled; 1.44 usual nights | [shift work meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC5860836/), [UK Biobank](https://www.ukbiobank.ac.uk/publications/night-shift-work-genetic-risk-and-type-2-diabetes-in-the-uk-biobank/) |

Adult mortality follows a Gompertz curve: the risk of dying doubles about every 8 years
([Gompertz-Makeham law](https://en.wikipedia.org/wiki/Gompertz%E2%80%93Makeham_law_of_mortality)).

How the checks are measured, and what to keep in mind:
- **Distress and metabolic disease** are scored as probabilities from his state with a wide logistic, not as a
  hard cut-off. The state is a risk level, not a diagnosis. A cut-off on a model with little individual
  variation gives absurd ratios (it produced RR 40 before this change).
- **Pollution** is measured from his average log hazard, which is far less noisy than comparing ages at death.
- **Unemployment** with choosing is unadjusted, so it runs above the adjusted HR 1.63: stress and poverty add to
  the direct effect.
- **Slightly high:** pollution (3.3 y) and night shifts (RR 1.46) when choosing, by a little.

What calibration changed in the world model:
- **Choice effects fade.** Before, a random chooser's effects piled up month on month and swamped the long-run
  exposures: social ties and shift work stopped mattering. Now the effect of a single choice on fast-moving
  states (anxiety, friendships, friction, nihilism) wears off over a few months. Lasting consequences stay: money,
  jobs, housing, children, grades, skills and health risks.
- **Adult anxiety has its own dynamics** (stress load, neuroticism, support, conflict at home). Before, it
  stayed at whatever level childhood left.
- **Loneliness adds to adult health risk**, alongside isolation in old age.
- **The night-shift offer** no longer adds metabolic risk of its own; the shift-work factor already carries it.
- **Early antibiotics** add a smaller immune risk, following the evidence (see below).

## The factors and their evidence

Evidence grades: **strong** means meta-analyses with consistent effects. **moderate** means several studies,
with heterogeneity. **weak** means few or mixed studies. **speculative** means plausible but not established;
it is kept small here.

| factor | how it acts here | evidence |
|---|---|---|
| Family income (SES) | shifts most other exposures; sets the life-expectancy gradient | strong (Chetty 2016) |
| Microplastic placental transfer | raises inflammation at birth | **speculative**: microplastics are found in placentas, but health effects are not established |
| Early antibiotics | lowers microbiome diversity; adds a modest lasting immune risk | moderate for asthma (OR about 2) and allergy (1.2-1.4); weak for autoimmune disease ([meta-analysis](https://research-portal.uu.nl/en/publications/early-life-antibiotic-exposure-increases-the-risk-of-developing-a/)) |
| Caregiver phone distraction | fewer words heard, slower attachment | weak: the [JAMA Pediatrics review](https://jamanetwork.com/journals/jamapediatrics/article-abstract/2833506) links it to weaker cognitive outcomes, but no language effect size was found |
| Local pollution | switches risk genes on early; hazard x1.26 at the top of the range | strong for mortality (AQLI); weak for the methylation mechanism |
| Extreme weather | acute stress events | moderate |
| Smart nursery surveillance | anxious caregivers, anxiety passed on | **speculative** |
| Non-walkable neighbourhood | lower cardio and motor fitness | moderate |
| Frictionless technology | fewer problems to solve, so less practice | **speculative** (premise of the scenario) |
| Grandparents as caregivers | older behavioural template | weak |
| Chronic stress, housing instability, structural violence | allostatic load and faster telomere loss | moderate; telomere effects are contested ([Epel 2004](https://pmc.ncbi.nlm.nih.gov/articles/534658): 9-17 "years" of ageing in a small sample, mixed replication) |
| Endocrine disruptors | earlier puberty against a slower prefrontal cortex | weak-moderate |
| Crisis news | nihilism up, planning horizon down | weak |
| Echo chambers | rigid identity, household friction | weak |
| AI tool access | AI literacy, academic results | **speculative** |
| Fertility disruptors | lower fertility | moderate for stress and metabolic causes; weak for microplastics |
| Parasocial ties and AI companions | loneliness hidden, local support eroded | weak / speculative |
| Unaffordable housing | living with parents, slower autonomy | moderate |
| Algorithmic hiring | lower job odds | **speculative** |
| AI doing entry-level work | slower skill building | **speculative** |
| Shift work | insulin resistance, allostatic load, poor sleep | strong for sleep; moderate for diabetes (OR 1.09-1.44) |
| Skill obsolescence | identity crisis, lower skill value | weak |
| Boomerang children, parent care costs | wealth drain | moderate |
| Geographic entrapment | blocked moves | weak |
| AI scams | fraud losses, financial paranoia | moderate that older adults are targeted; weak for the AI-specific part |
| Loss of third spaces | isolation in old age | moderate for isolation and mortality (Holt-Lunstad) |
| Market-tied pensions and inflation | falling pension, a return to work | moderate |
| Digital-only services | missed care for the digitally illiterate | weak |
| Unemployment (state, not a factor) | hazard x1.63 in working age | strong (Roelfs 2011) |
| Bullying | anxiety, isolation, lost belonging | strong: adult depression OR 1.74-1.99 ([Ttofi et al.](https://pubmed.ncbi.nlm.nih.gov/23426798/)) |
| Social ties, friends, partner | everyday support; isolation raises mortality | strong (Holt-Lunstad 2010) |
| School quality, warmth, crowding | academic results, belonging, how much is taught | moderate |

## Human mechanisms (character.py, memory.py, present.py)

| mechanism | parameter | source |
|---|---|---|
| Loss aversion | lambda 1.5-2.1, rising with neuroticism | [Brown et al. 2024](https://wrap.warwick.ac.uk/185745) mean 1.96; [Walasek et al. 2018](https://healthcare-economist.com/2024/06/26/empirical-estimates-of-loss-aversion) 1.31 |
| Present bias | beta 0.5-0.95, rising with prefrontal maturity and conscientiousness | [Steinberg et al. 2009 and later work](https://pmc.ncbi.nlm.nih.gov/articles/PMC4684973) |
| Big Five | about 50% innate, the rest formed by life, drifting toward maturity | heritability 40-60% ([Power & Pluess](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5068715/)); maturity and stability ([Bleidorn et al. 2022](https://www.Gwern.net/doc/psychology/personality/2022-bleidorn.pdf)); life events ([Bleidorn, Hopwood & Lucas 2018](https://www.diw.de/de/diw_01.c.764344.de/s_11345.html)) |
| Language sensitive period | learning stays strong to 17, then declines | [Hartshorne, Tenenbaum & Pinker 2018](https://bcs.mit.edu/news/cognitive-scientists-define-critical-period-learning-language) |
| Sleep | impairs taking in new things; consolidation favours salient memories | encoding ([review](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2023.1134757/pdf)); prioritised replay is mostly rodent evidence ([Nature Communications 2023](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10710481/)) |
| Hedonic adaptation | mood relative to a 2-year adaptation level, adapting 70% of the way | partial adaptation ([Diener, Lucas & Scollon 2006](https://www.psychologicalscience.org/journals/current-directions/j.1467-8721.2007.00479.x/)) |
| Curiosity | novelty pull, scaled by openness and age | [Gottlieb, Oudeyer & Lopes](https://www.pyoudeyer.com/oudeyerGottliebLopesPBR16.pdf); better established in agents than in people |
| Stress and decisions | stress narrows the lived choice; poor sleep makes it noisier | overexploitation under stress ([Princeton](https://collaborate.princeton.edu/en/publications/chronic-and-acute-stress-promote-overexploitation-in-serial-decis/)); [Starcke & Brand 2012](https://library.alnap.org/node/67214) |
