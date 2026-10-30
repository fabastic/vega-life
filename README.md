# Vega Life

A language model that is born, not spawned. It starts as a ~0.5M-parameter byte-level transformer with random
weights. It hears the language around it, faces what each stage of life throws at it, and learns from every
situation through reinforcement learning from verifiable rewards. Its network grows with age, to about 1B
parameters by 30 on the full profile.

Everything around him is a separate factor (`vegalife/factors.py`). Each factor is seeded from the run's seed and
the family he is born into, or set by you before birth, scheduled for a given age, or changed live.

## How a month works (`vegalife/trainer.py`)
1. **The world acts.** `world.Person.step_month` applies every factor to his body, mind, relationships and money.
   Each block of that function is labelled with the factor it implements. Examples:
   - Microplastic placental transfer sets his inflammatory baseline at birth.
   - Early antibiotic courses cut microbiome diversity and add permanent autoimmune risk.
   - Pollution and extreme weather switch loaded risk genes on through methylation, mostly in early life.
   - Chronic stress, housing instability and structural violence shorten telomeres.
   - Endocrine disruptors bring puberty forward against a slower prefrontal cortex.
   - Shift work raises insulin resistance.
   - Late-life epigenetic wear sets the speed of neurodegeneration.
2. **He grows, then hardens.** At the age milestones in `growth.py`, delayed by early adversity, the network grows
   like a brain: front-loaded. Width is final by 6 (~386M), one association layer a year goes on top until 18
   (~848M), and only four executive layers come after (~1.0B at 30). Growth is function-preserving: right after it,
   the model computes exactly what it did before. Each layer has a critical period: fully plastic when it forms,
   then down to a tenth of the learning rate (core layers close at 7-12, association layers ~7 years after they
   form, the last at ~25), then frozen and lightly pruned in adulthood. Executive layers stay open. So adult
   experience has to work through a hardened childhood instead of flowing into fresh weights.
3. **He hears language** (`speech.py`). This is his pretraining data, and the factors set how much there is and
   what it is like:
   - Caregiver phone distraction means fewer words reach him.
   - Parents' education sets how rich they are.
   - Crisis news becomes text he reads.
   - Work emails and AI-companion messages arrive in adulthood.

   Optional `.txt` files in a corpus folder become reading from school age on.
4. **Life throws things at him** (`scenarios.py`). He meets two kinds:
   - **Situations** with choices A-D: the hungry infant, the frozen tablet, the doom feed, the resume filter, the
     night-shift offer, the AI scam call in his grandson's voice, and others.
   - **Problems** with one checkable answer: counting, arithmetic, budgets, percentages.

   Factors set how often each occurs. Frictionless technology, for example, cuts the number of problems, so he
   gets fewer chances to learn to solve them.
5. **RLVR on each one** (`rlvr.py`). The model samples a group of answers and the simulator scores each:
   - A problem is right or wrong.
   - A situation is scored by how much the choice changes his wellbeing when its effect is applied to a copy of
     his state.

   The update is GRPO with group-normalised advantages. The first sample is the one he lives: its effect is
   applied to his real state.
6. **Measured, not simulated.** Three state values are measured on the network itself:
   - **language:** his loss on held-out speech.
   - **problem solving:** his success rate on verifiable problems.
   - **cognition:** his loss after neurodegeneration damage.

   In late life the weights are damaged and plasticity falls, so the decline happens in the model, not only in a
   number.

## What makes him human
Every number below comes from published research; `CALIBRATION.md` has the sources and how strong each is.
- **Personality formed by his life** (`character.py`). The Big Five are about half innate (a seed you can set)
  and half formed by what he goes through. They drift toward maturity and settle by about 25, and life events
  nudge them. They act through how he feels outcomes, not through text.
- **Feeling versus reality** (`rlvr.py`). He learns from outcomes as he feels them:
  - losses weigh 1.5 to 2.1 times as much as gains
  - later consequences are discounted, more so when young (present bias)
  - untried choices pull a little (curiosity)

  What actually happens to him, now and later, is the real outcome. Some choices bite months later: partying
  shows up at exam time, learning the craft pays off a year on.
- **Sleep, mood, stress.** Sleep sets how well he takes in new things and how well the month's salient memories
  consolidate. Mood adapts partly to his circumstances. The answer he actually lives is narrowed by stress and
  loosened by tiredness; his learning samples keep a fixed spread.
- **Sensitive period.** Language learning stays strongest to about 17, then slows.
- **Memory and the present.** Episodes fade, blur and get rewritten (`memory.py`). Every decision opens with
  the moment he is in (`present.py`).

## His brain map (`brainmap.py`, `ui/brain.html`)
Everything in his life is recorded as a graph of what led to what. It's built here with no outside tools.
- **What's in it:** factors, states, traits, situations, choices, later consequences, events, memories, people,
  skills and growth milestones.
- **Exact links** are recorded where they happen:
  - a choice changed these states
  - it led to this consequence months later
  - it was remembered as this, and that memory was recalled in this later decision
  - being bullied shifted his neuroticism
  - this factor made that situation likelier
- **Estimated links** are slow influences: each factor's average push per month on his states, measured against
  the same month with the factor at its average.
- **Viewer:** open the Brain map tab. The overview groups repeats. You can switch to every moment, search,
  filter by age, and trace what led to anything or what came of it.
- **Without the GPU:** `python -m vegalife.lifesim runs/<name>` builds a whole life's map in seconds, with random
  choices.

## A world that behaves like the real one
`python tools/calibrate.py` simulates hundreds of lives without the network and checks them against published
figures. Life expectancy is 78.4 against 78.4 (US 2023). The other checks:
- the income gap between the poorest and richest families
- social ties and survival
- childhood adversity
- unemployment
- air pollution
- night shifts

All 8 are in range both when he chooses at random each month and when nobody chooses. `CALIBRATION.md` has
both result sets and grades the evidence behind each factor. Several of the original factors
(smart nurseries, algorithmic hiring, frictionless technology, microplastics) are speculative, so their effects
are kept small.

## Education, friends and surroundings
All of it is set on the Setup tab, and every setting says what it does.
- **School** (`factors.py`, 16 factors): quality, teacher warmth, class crowding, rigour, homework, ability tracking,
  bullying, clubs, tutoring, AI policy, the path after school (none, vocational, university), student debt, and four
  curriculum weights (maths, reading, feelings, arts and play). They drive his results, stress, belonging, the lessons
  he hears and how many problems he is set. A degree takes four years, costs money and raises job odds.
- **Friends** (`people.py`): named people with their own traits (closeness, kindness, risk, studiousness, online-only).
  List them yourself, with the age they arrive and leave, or seed them from the friend factors. They give support,
  pull his results up or down, dare him, notice when he is low, and show up in his language and his situations by
  name. You can add a friend mid-life from the Live tab.
- **Surroundings:** siblings, neighbourhood safety, screen time, cultural strictness, healthcare access, job
  security, partner support and community ties.

To change a school or a friend group over time, schedule a change ("at 12, school quality = 0.9").

## Run it
`.venv` is a venv that reuses the CUDA PyTorch already installed in Python 3.12 (torch 2.6.0+cu124):
`C:\Users\Vairaj Malhotra\AppData\Local\Programs\Python\Python312\python.exe -m venv --system-site-packages .venv`, then `pip install pytest`.
```
cd vega-life
.venv\Scripts\python.exe ui\server.py          # then open http://127.0.0.1:8765
```
Set the factors on the Setup tab and press **Give birth**, then watch the Live tab. Without the UI:
```
mkdir runs\test & copy configs\example.json runs\test\config.json
.venv\Scripts\python.exe -m vegalife.trainer runs\test
```
Tests: `.venv\Scripts\python.exe -m pytest tests`

## Profiles and hardware
| profile | cap | optimiser | where |
|---|---|---|---|
| `tiny`, `tiny_lean` | ~3M | AdamW fp32 / lean | quick tests |
| `laptop` | ~158M (stops at the 4-year milestone) | AdamW fp32 | 8 GB GPU |
| `laptop_xl` | **~1.0B at 30** (the whole path) | lean bf16, checkpointed | 8 GB GPU, peak 5.2 GB |
| `full` | ~1.0B at 30 | AdamW fp32 | 24-48 GB GPU |

All profiles follow the same growth path. A capped profile simply stops growing at its cap.

### The lean optimiser (`vegalife/optim.py`)
AdamW in fp32 needs about 16 bytes per parameter. The lean one needs about 4, which is what lets 1B fit in 8 GB:
bf16 weights updated with stochastic rounding, each weight updated during backward so gradients never exist
all at once, a factored second moment, a bf16 momentum, and recomputed (checkpointed) blocks. In a controlled test
it learned as well as AdamW (addition 0.92 against 0.86 after 1,500 steps).

Measured on an RTX 4060 laptop GPU (8,188 MiB), batch 16 x 256 bytes, with a language step and a GRPO step:

| network | AdamW fp32 | lean |
|---|---|---|
| 202M | 6.9 GB | 1.3 GB |
| 680M | does not fit | 3.7 GB |
| 1.0B (age 30) | does not fit | 5.2 GB, 3.1 s per language step |
| 1.3B | does not fit | 6.7 GB |
| 1.5B | does not fit | 7.5 GB (no margin) |
| 1.8B | does not fit | 8.9 GB: spills out of GPU memory, 14x slower |

So about 1.3B is the practical ceiling on this GPU. Run `python tools/memtest.py <width> <layers> lean` to measure a
shape and `python tools/growtest.py` to grow through every milestone.

A whole life is ~1,000 months. On `laptop_xl` the months after 20 are the cost (a language step is 2-3 s), so
expect roughly half a day for 90 years. Adults take in less new material, so after 30 the number of learning steps
per month falls to a quarter.


## His people, his body, his work, and talking to him

Each of these is its own module, calibrated against published numbers. The calibration scripts are run across
hundreds of simulated lives, and `tests/test_life_events.py` keeps them there.

| Module | What it adds | Calibrated against |
|---|---|---|
| `family.py` | Parents, grandparents, siblings, a pet, a partner and children, all with their own ages. They die at life-table rates, or when you schedule it. Some losses are not deaths: divorce, a break-up, dementia. Each loss starts its own grief path: resilient, recovering or prolonged. It swings month to month and comes back on anniversaries. | Bonanno 2002 (about half resilient, ~16% chronic); Lundorff 2017 (prolonged grief ~10%); Moon 2011 (widowhood mortality ×1.41, then ×1.14); Mostofsky 2012; Margolis & Myrskylä 2015 (the first year of parenthood) |
| `chemistry.py` | Dopamine, oxytocin, serotonin, endorphins, cortisol, adrenaline and melatonin, released by everyday good moments and by stress. Dopamine follows surprise, serotonin follows daylight, and touch damps cortisol. Together they make up `joy`, which colours his mood. The brightest moment of a month can become a memory. | Positive more than negative on ~74% of days (Gallup/Diener); Ditzen 2007; Lambert 2002; a flattened cortisol rhythm carries ~1.3× mortality |
| `career.py` | Job hunting (applications, rejections, the scar a long search leaves), hours and the grind, promotions, burnout and time off, and retirement. | Lucas 2004; Kivimäki 2015 (55+ hours: stroke ×1.33); retirement lowers depression risk by ~20% |
| `selftalk.py` | Every month someone asks him about his life and the true answer is said back. Some of these questions have a checkable number (his age, his children, his friends) and are put to him as verifiable problems. | Rewarded only when the answer is true |
| `chat.py` | Talking to him from the UI. He answers with his own network, from the moment he is in and a memory your words bring back. He tries a few answers and keeps the one his network finds most fluent. Talking never changes his life. | |

Before birth, the New life page shows everything the seed gives him: every factor, his family and his friends.
Any of it can be moved. A seed can be a number or any words.

## Where he grows up, who he is to others, his phone, and his mental health

Five more parts of his life, each in its own module and each shown as a card in the live view. Rates are checked
against surveys in `tests/test_world_more.py`.

- **Schooling by region (`schooling.py`).** You pick one of 11 world regions, his IQ (70-145) and how well he adapts.
  The region sets the school start age, exam pressure (gaokao, CSAT, JEE/NEET), how common tutoring is (80% in Korea),
  how many people go to university and what it costs. He is drawn to subjects by temperament and success, picks
  three at 16, sits his region's big exam, and wants a particular course at 18. Whether he gets it depends on his
  result, his family's money, family pressure toward medicine, engineering and law, and gender expectations. The
  card says why he got what he got. Dropping out is likelier when the course was not his choice.
- **Relationships (`bonds.py`).** Every parent, sibling, partner, child and friend has trust, conflict and a ratio of
  good to bad moments (Gottman's 5:1). As the ratio falls, conflict sours through criticism, defensiveness and
  contempt (or pursue-withdraw). Rows are timed to life stage (parent and teen conflict peaks around 12-16) and
  mended by apologies, talking, time or counselling. Long contempt ends in estrangement (27% of lives, matching
  Pillemer) or a break-up. Rifts can heal years later.
- **Phone and internet (`digital.py`).** He gets a first phone at around 11, later under strict rules. Screen hours
  follow Common Sense figures by age. Every month a feed is simulated: an engagement-ranked algorithm learns what
  holds him, likes come on a variable schedule, and habit, sleep loss, comparison, outrage, cyberbullying and
  breaks from the apps follow. The card shows that month's feed on a phone.
- **Mental health (`mental.py`).**
  - Autism and ADHD are present from birth and diagnosed late or never, more often for girls and poorer families.
  - Episodes of depression, anxiety, PTSD, OCD, bipolar disorder, eating disorders, alcohol use and psychosis start at
    survey rates (lifetime: depression ~23%, anxiety ~31%, PTSD ~7%) and recur.
  - Treatment depends on healthcare access and stigma.
  - His family and friends have conditions of their own that shape his life.
- **Prejudice (`prejudice.py`).**
  - What he faces depends on who he is (ethnicity, migrant background, sexuality, sex, class, weight,
    neurodivergence, age) and on how prejudiced society is.
  - Each incident adds stress (Pascoe & Richman). Hiring bias cuts his callbacks (Quillian).
  - He also absorbs bias from home, society and outrage feeds, and loses it through diverse friends (Pettigrew &
    Tropp). He sometimes acts on it, and his conscience can catch it. Or he stands up for someone.

All five feed his thoughts, so he can talk about them in chat.

## The seasons of a life (`seasons.py`)

Most of a life is small moments. About 90 of them are tied to the age they belong to and to his circumstances. They
are drawn from developmental research and from what people write about their own lives on Reddit (r/AskOldPeople,
"the struggle nobody talks about at 30").

- **Infancy and childhood:** a first smile, separation anxiety, losing a tooth, being picked last.
- **Adolescence:** a first kiss, a first heartbreak, hating the mirror, a driving test.
- **Early adulthood:** a first pay cheque, feeling behind his old classmates, eating alone in a new city, friends
  drifting after 25.
- **Midlife:** "is this it?", the sandwich years, a health scare.
- **Old age:** giving up the car, a fall, a week without speaking to anyone, unexpected peace.
- **Every year:** birthdays, with the round ones marked.

Life events with research behind them:

- **Pregnancy (`family.py`).** About 15% of known pregnancies end in miscarriage, more with age. Stillbirth is about
  1 in 175 (CDC). Maternal death is rare. About 1 in 6 people face infertility (WHO); for them a year of trying
  brings no pregnancy, and some go on to IVF. A father's grief over a lost pregnancy gets little support.
- **Fatherhood.** Testosterone falls 26-34%, more with hands-on care (Gettler 2011), and oxytocin rises. Postnatal
  depression strikes about 10% of fathers (Paulson 2010) and 13% of mothers.
- **Identity.** The empty nest hits hardest for parents who lived for parenting, and is often followed by
  rediscovering their partner. Other losses of role are retirement, widowhood and giving up driving.
- **Scams.** Scam types change with age: parcel texts, fake jobs, crypto investments, romance, tech support and AI
  voice clones. Losses grow with age (FTC). About 1 in 20 is ruinous, shame keeps most victims quiet, and about
  41% of lives are hit at least once.
- **Regret.** Each year he looks back. Regrets follow Pink's four kinds:
  - foundation: money, health
  - boldness: the course he never fought for, never living as himself
  - moral: harm he did
  - connection: an estranged parent, friends he let drift, missing his children's early years

  Regrets about what he did not do grow with time (Gilovich). They weigh on his mood in old age and become his
  thoughts.
- **Yearnings.** What he longs for depends on his age and situation: "someone who understands me" as a teenager, "a
  home of my own" or "time" in midlife, "to be remembered kindly" in old age.
- **The shape of a life.** There is a gentle midlife dip and a calmer old age (Blanchflower; Carstensen). His
  twenties are still his lowest decade, which matches recent surveys that find the young now least happy.

## Illness at every age (`illness.py`)

About 45 diseases, each tied to the ages it strikes, a sex difference and risk factors from his life. Each one
changes his sleep, pain, health and mood, and brings everyday struggles of its own:
- an inhaler in PE
- finger-pricks before every meal
- a partner moving to the spare room because of his snoring
- relearning words after a stroke

Silent conditions (high blood pressure, sleep apnoea, type 2 diabetes) often go unnoticed until someone checks, and
treatment softens their effects. He has an `adiposity` level, with about 40% of adults above the obesity line, that
drives apnoea, diabetes, blood pressure, arthritis and gout.

**Calibrated against published rates:**
- childhood asthma and eczema
- migraine (women ~3x) and IBS
- high blood pressure: 7.5%, 33% and 63% by age band (CDC)
- type 2 diabetes ~25% over 65
- cancer ~40% over a life
- stroke ~1 in 4 (GBD 2016)
- arthritis at about half of over-65s
- cataracts, enlarged prostate and osteoporosis

**Chronic pain, insomnia and apnoea** cost him sleep and raise the risk of depression and anxiety.

**Death:**
- The life table already includes these diseases. Illness moves risk onto the sick, normalised by age, so life
  expectancy stays about 77.
- A heart attack, a stroke or pneumonia can kill within the month it happens.
- When he dies, the cause is named.

## Hormones and the body over a life (`hormones.py`)

**Childhood and puberty:**
- Mini-puberty in the first months.
- His own melatonin and cortisol rhythm arriving at about 3 months.
- Adrenarche at 6-8: body odour and first spots.
- Puberty on his own timing, with a growth spurt to a genetic adult height, a first period (average about 12.6
  here) or a breaking voice and a first shave.
- Early puberty in girls raises anxiety; late puberty in boys brings teasing.

**The teenage years:**
- A body clock about 2 hours later than school allows, which costs sleep.
- A peak in how much rewards lift him (dopamine gain), fading after 40.
- Sharper reactions to being judged.

**Bone and muscle:**
- Bone density peaks around 30, then falls: faster after menopause, and it drives osteoporosis.
- Muscle loss after 50 is slower if he stays active.
- He shrinks about 1 cm a decade after 50.

**If female:**
- A monthly cycle: premenstrual symptoms in about 30%, PMDD in about 5%, severe period pain in about 15%.
- Pregnancy: morning sickness, and third-trimester sleep loss.
- After a birth: the baby blues, and the oxytocin and prolactin of breastfeeding.
- Perimenopause, then menopause at an average of 51. Hot flushes in about 75% for about 7 years. HRT eases it.

**If male:**
- Testosterone falls with age and with fatherhood. Symptomatic low testosterone affects a few percent of older men.
- Couvade: sympathetic pregnancy symptoms.

**At any age:**
- The dopamine high of a new relationship, then oxytocin attachment.
- Seasonal depression: about 3-5% overall, more at high latitudes and in women.

**In old age:** earlier and more broken sleep.

These feed his sleep and mood (`character.py`), how much rewards lift him (`chemistry.py`), osteoporosis risk
(`illness.py`) and depression risk (`mental.py`).

## Hardships and faith (`hardships.py`)

These are hardships that can come at any age.

**Substances:**
- Smoking, mostly started before 18. It feeds cancer, COPD, heart attack and stroke risk in `illness.py`, and
  quitting lowers that risk.
- Vaping.
- Cannabis: heavy teenage use raises psychosis risk.
- Phone gambling: chasing losses drains money.
- Opioid dependence after painkillers: overdose risk, highest in North America.

**Road crashes:** most only injure, and young men are at the highest risk.

**Crime he suffers:** muggings and assaults, more in unsafe neighbourhoods, and sexual assault. Both can lead to PTSD.

**Crime he commits:** offending peaks at 15-25, driven by risk-taking friends, poverty, untreated ADHD and leaving
school, and is checked by his conscience. It can lead to a record or prison, and a record halves job callbacks.

**Other hardships:**
- A debt crisis.
- War and displacement, by region.
- One pandemic in a lifetime: months of loneliness, hardest on the young and old.

**Suicide loss:** about 30% of sudden deaths of people aged 15-64 in his family or among his friends are suicides,
and that grief is more often prolonged.

**Faith:**
- How religious he is depends on his region and how strict his family is.
- Attending services brings community support.
- He may lose his faith as a young adult, or find it in his worst year.
- He has moments of awe.

`seasons.py` gained about 60 more moments from `LIFE_SEASONS.md`:
- colic and potty training, and jealousy of a new baby
- glasses and braces
- climate fear
- homesickness in the first term away
- "when are you having kids?"
- the childcare bill
- redundancy
- affairs and divorce late in life
- becoming the oldest generation
- care homes and financial abuse of the old
- great-grandchildren
- small everyday joys and annoyances: money in an old coat, a stubbed toe, the first warm day, a message from the
  right person

**More from `LIFE_SEASONS.md`:**
- **Self-harm.** In adolescence and young adulthood, almost always alongside depression or anxiety, and kept
  hidden. About 1 in 5 girls and 1 in 16 boys here, close to UK cohort figures. Someone noticing and getting help
  ends it.
- **Teen pregnancy.** Rates vary by region: about 1.3% a year in the US, about 10% a year in Sub-Saharan Africa.
- **Decline at the end of life.** Wellbeing sinks over the last years of life as health fails (Gerstorf). Here,
  mood drops from about 0.57 to 0.45.
- **Disability after a bad crash.** He may be left using a wheelchair, and then faces disability prejudice
  (`prejudice.py`).
- **About 45 more moments**, for example sleep regressions, a late talker, an imaginary friend, a first lie,
  walking to school alone, the "imaginary audience" of early adolescence, a first sexual experience, a pregnancy
  scare, house parties, moving in together, wedding season, housework fights, writing a will, erectile changes,
  first screenings, school reunions, "overqualified", senior discounts, clearing a parent's house, video calls with
  grandchildren, volunteering, stairlifts, a dementia diagnosis, hay fever, concussion, two jobs, legal fights, a
  missing person, the national team winning.
