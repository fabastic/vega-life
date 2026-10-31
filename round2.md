# Round 2: what was built, what is left, what could come next

Status at the end of round 2 (2026-10-31):
- **Tests:** 149 in total. The full run found 2 failures:
  - Neuroticism no longer fell with age, because lasting event effects piled up to their cap. They now fade, with a half-life of about 5 years.
  - A degree test assumed no apprenticeship.

  Both are fixed, and their test files pass. The rest passed in the full run.
- **GPU:** checked with a `tiny` life (`runs/round2-check`, seed 2026, 2.4M parameters), stopped at 11.2 years and
  resumable. It is not yet a full `laptop_xl` life (see "Left over").
- **Nothing in round 2 is committed yet.**

---

## Round 1 leftovers: what happened to each

### Events that now change his life

| Round 1 leftover | Round 2 | Where |
|---|---|---|
| An affair changed nothing | Monthly guilt through his conscience. Discovery odds rise as trust falls; discovery drops trust, brings contempt and a 6-month crisis, and can end the relationship | `bonds.py` `_affair` |
| A divorce late in life was text only | Separating splits the household. Married partners take about 45% of wealth, cohabiting partners 20%, and half the time he loses the home. The partner becomes an `ex_partner`, still there if they share children | `family.py` `separate` |
| Moving in and the wedding had no state | Moving in pools money (partner's pay, lower spending). Marriage comes after moving in, or first in strict cultures, and halves the separation hazard | `family.py` `_household`, `world.py` |
| A care home didn't change where he lives | `residence = "care_facility"`: no work, independence capped at 0.35, family visits warm bonds and missed visits cool them | `seasons.py` `_care_home` |
| Dyslexia and glasses were text | Dyslexia (about 7%, more in boys) slows reading grades unless diagnosed or tutored. Short-sightedness is a silent condition that hurts schoolwork until it is noticed | `mental.py`, `schooling.py`, `illness.py` |
| Friends' and family's events never reached him | Friends' and siblings' divorces, illnesses, babies, losses, prison and debt arrive, and he shows up for them or doesn't. Three absences and a friend drifts away | `bonds.py` `their_event` |
| Teen pregnancy skipped the outcomes | Goes through the whole pregnancy, including miscarriage and stillbirth | `family.py` `conceive` |
| Seasonal moments that only printed text | Removed or given an `act` callable that changes state | `seasons.py` `Moment.act` |

### Not modelled in round 1, now modelled

| Round 1 gap | Round 2 | Where |
|---|---|---|
| Choosing to emigrate | Push from his region (war, poverty, repression). Destination, migrant background and minority status change; 2–6 years of work below his skills; homesickness. About 5% of lives | `economy.py` `_emigrate` |
| Long COVID | 6% of pandemic infections | `illness.py` |
| Frailty care at the very end | Frailty as a condition, with swallowing and pressure-sore struggles; it can lead to a care home | `illness.py` |
| Grown children's own lives | Good and bad events from adult children. Trouble follows how poor their childhood was and how much they trust him | `family.py` `_grown` |
| Pets as individuals | Each pet has a temperament fixed by its name | `seasons.py` `_pet` |
| Poverty passing down generations | **Partly.** Inheritance scales with family SES and grown children's trouble follows childhood wealth. There is no lasting "poverty trap" state yet | `family.py` |

### Review plan: fixes required now

| Plan item | Round 2 | Where |
|---|---|---|
| 1. Wire dead-state events | Done (tables above) | |
| 2. Replace number scraping | Self-answers scored by meaning: numbers anywhere, in digits or words (1 / 0.4 / 0 / −0.3), blended 60/40 with how close his own hidden state is to the true answer's embedding | `selftalk.py` `score_self`, `model.py` `Mind.embed` |
| 2. Replace template thoughts | Template thoughts fade from 100% at age 3 to 0% at 6. After that he gets a raw `Feel:` vector, and his own network puts it into words (an inner voice that is generated, not trained on) | `conscious.py`, `trainer.py` `inner_voice` |
| 3. Mood drift | Mood baseline adapts down at 1/8 a month and up at 1/24. Good-mood months 67% → 71% (Gallup 74%) | `character.py` |
| 3. Death drift | Every death has a named cause (weighted among his serious conditions, with a test). Life expectancy 76.5 → 77.5. Blood pressure and stroke re-based, with pollution and cortisol terms | `illness.py` `cause`, `world.py` |
| 4. Brain map at scale | A network map of macro-regions (input, attention and feed-forward per layer, output). It records activity variance and gradient norms through hooks, saved to `cortex.json`, drawn at `/cortex`. Built ourselves, no graph library | `cortex.py`, `ui/cortex.html` |

### Review plan: what to add next

| Plan item | Round 2 | Where |
|---|---|---|
| 1. Sleep and memory replay | Each month: the top 5 recent salient memories plus 3 core memories are trained again with no new input, and a dream is generated from that replay | `trainer.py` `sleep` |
| 2. Big Five that keep changing | Lasting events nudge traits (`formed`, ±0.25), weighted by plasticity: full until 18, falling to 0.15 by 30 | `character.py` `plasticity`, `nudge` |
| 3. Fork-and-ablate lab | Named `experiment.py` (the plan said `experiment_runner.py`). It forks a life from its checkpoint into arms (state changes, factor changes, ablations of conscience, memory or replay, or removing a relative), runs them one after another, and compares. It refuses the GPU while a life runs there. Launching is CLI only; the UI shows results | `experiment.py`, `index.html` Lab tab |
| 4. Career and money loop | Occupations by field and tier, from credential, IQ and record, pushed down by hiring bias. Pay paths, automation exposure, burnout. Money stress from cash flow; where care is paid for, stress makes care harder to get | `economy.py`, `world.py` `care` |

### Also from before
- **`SURROUNDINGS.md`:** built as `surroundings.py`.
  - childhood opportunity shifting adult pay (Chetty)
  - green space, lead (IQ, Lanphear), noise (reading), heat at school, urbanicity (psychosis)
  - the commute (mood, sleep)
  - a weekday time budget
  - named adults around him (coach, teacher, neighbour, shopkeeper) who mentor him
- **A self-knowledge probe:** a ridge regression from his hidden states to mood, anxiety, grief, loneliness and joy, scored on held-out later months (R²).
- **UI:**
  - tabs: Life / Mind / Body / World / Talk / Lab / All
  - new cards: work and money, inner voice and dreams, experiments
  - a link to the network map
  - fixed a duplicate card id that hid the schooling-by-region card
- **Bugs fixed:**
  - Dream and inner-voice generation crashed on CUDA: they passed a CPU generator. They now use the device RNG, which is saved in the checkpoint.
  - The scam moment crashed for people older than every scam's age range.

---

## Current calibration (100–150 simulated lives)

| Measure | Now | Target / source |
|---|---|---|
| Life expectancy | 77.5 | about 78 (US) |
| Adult months in a good mood | 71% | 74% (Gallup) |
| Ever had an affair | about 16% | 15–20% of married people (GSS) |
| Ever married | 70–75% | about 70% |
| Divorced or separated from a partner | about 41% | 40–45% of first marriages |
| Emigrated | 5–6% | about 3.6% are international migrants (UN, current) |
| Dyslexia | 7% | 5–10% |
| Short-sighted | 41% | 30–50% of adults, region dependent |
| Frailty by death | 9–16% | 10–15% of over-65s |
| Ends life in a care home | 6–11% | about 5% of over-65s at any time, more at the end |
| Leading causes of death | cancer 20%, heart 19%, dementia 11%, stroke 7% | CDC: heart and cancer about 20% each, dementia and stroke about 5–6% |

---

## Left over from round 2

### Not verified
- **A full `laptop_xl` GPU life on round 2 code.** The tiny check life ran on the GPU after the generator fix and reached 11.2 years. Dreams, the inner voice, `cortex.json` and the probe all work: self-knowledge R² was 0.34, and the network map and the UI tabs render with no errors. At 2.4M parameters, though, the inner voice and dreams are mostly babble ("Tay in maths."). His chat replies mostly copy the "Now" line's feeling sentence ("Good. I feel happy and full of energy."), which shows he is copying from the prompt, not that he talks about himself. Whether a 1B mind does better is the real test.
- **Experiments on a real life.** The fork lab has only been run in tests, on a tiny life of half a year.

### Known imperfections
- Money stress in the 20s is high: a mean of 0.48, and 55% of months above 0.5. That looks too high next to surveys of young adults (still to be checked against a sourced figure). Starting wages are probably too low against the cost of living.
- Dementia is about 11% of deaths, about twice the CDC share. It may be named too often when it is only one of several conditions.
- Short-sightedness has only a region term. It doesn't yet follow time outdoors, even though the weekday budget now tracks that (outdoor time protects: Rose 2008).
- Emigration runs slightly high against the UN stock figure, though a lifetime rate should be higher than a stock.
- Poverty passing down generations is only partial (above).
- The experiments UI only reads results. There is no "what if" button yet.
- The map is a network map, not a map of the world with coordinates, places and travel.

---

## More that could be done (researched)

### The model and how he learns
- **Replay against forgetting at scale.**
  - Sleep-like replay, unsupervised and with no new data, recovered tasks a network had forgotten (Tadros et al., 2022, *Nature Communications*, "Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks").
  - Next: measure forgetting directly. Hold out early-life memories and track loss on them across years, with replay on vs. off in the fork lab.
- **What wins in small-data language learning.**
  - The 2024 BabyLM Challenge was won in both tracks by GPT-BERT, a hybrid of causal and masked language modelling in one network (findings: arXiv 2504.08165).
  - Curriculum learning was the most common attempt (13 teams) and was largely unsuccessful.
  - So: try a hybrid causal/masked objective on his speech data. Treat age-graded curricula as something to test in the lab, not as a given.
- **Opening up what he has learned.**
  - Sparse autoencoders on his hidden states split them into features a person can interpret (Bricken et al., 2023, Anthropic, "Towards Monosemanticity").
  - Train one per decade of his life and see which features appear: "mother", "school", "fear".
- **Space and time inside him.**
  - Linear probes find world coordinates and dates in LLM activations (Gurnee & Tegmark, 2023, "Language Models Represent Space and Time").
  - Add probes for "how old am I" and "where am I" next to the self-knowledge probe.
- **Theory of mind, tested properly.**
  - False-belief tasks are claimed to emerge in LLMs (Kosinski, 2023), but small changes to the task break them (Ullman, 2023).
  - Add verifiable false-belief questions about his own people, each with an Ullman-style variant, as a reward and a test.
- **A comparison with prompted agents.** Run the same life on a prompted, off-the-shelf "generative agent" (Park et al., 2023) as a baseline, to show what being raised adds.

### Life and calibration
- **ACE scores.**
  - Four or more adverse childhood experiences go with roughly 4 to 12 times the risk of alcoholism, drug abuse, depression and suicide attempts (Felitti et al., 1998).
  - Compute an ACE score from his childhood and check the adult risks against that gradient.
- **Mobility.**
  - In the US, the rank-rank slope between parents' and children's income is about 0.34 (Chetty et al., 2014).
  - Run many lives and fit the slope, to calibrate passing poverty down and make it a lasting state.
- **Dementia's modifiable risks.**
  - The Lancet Commission (2024) lists 14 risk factors accounting for about 45% of dementia. It newly adds untreated vision loss and high LDL cholesterol.
  - Most factors exist in the simulation already. Wire them into dementia risk, which also corrects the over-share of dementia deaths.
- **Graduating into a recession.**
  - Graduating in a recession costs about 9% of earnings at first, fading over 8–10 years. The cost lasts longer for the least advantaged (Oreopoulos, von Wachter & Heisz, 2012).
  - Needs the world timeline: dated recessions hitting his whole cohort.
- **Young people's wellbeing.**
  - In the World Happiness Report 2024, the US ranks 62nd for under-30s but much higher for older ages.
  - Check his youth wellbeing by region against this.
- **Parenting styles.**
  - A meta-analysis of 428 studies found authoritative parenting linked with the best outcomes across cultures, and harsher styles with worse outcomes (Pinquart & Kauser, 2018).
  - Give his parents a style, and him one as a parent.
- **Phones at school.**
  - School phone bans showed no difference in wellbeing or sleep, though total phone time mattered (Goodyear et al., 2025, *Lancet Regional Health – Europe*).
  - Phone rules at home matter more than at school, which matches `digital.py`. Keep the school effect small.
- **AI companions.**
  - Heavy daily chatbot use went with more loneliness and less real socialising (OpenAI & MIT Media Lab, 2025).
  - Add AI companions to his online life, with that dose response.

### Interface and tooling
- A world map with coordinates: where he was born, where he moved, where his people live.
- A time-use view built from the weekday budget.
- Launch experiments from the UI, plus a "what if" button that forks at the current age.
- Population validation runs: 1,000 tiny lives that produce a report of every calibration line above.
- A life timeline strip with one lane per module, a family tree coloured by bond health, and a life-story export written in his own words.
