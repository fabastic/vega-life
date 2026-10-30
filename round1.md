# Round 1: what was built, what is left, what could come next

Status at the end of round 1 (2026-10-30):
- **Tests:** all 131 pass on the final code.
- **GPU:** nothing in this round has been run in a real laptop_xl life yet.
- **vega-9:** stopped at 79.5 years and resumable.

---

## Built this round

### His mind and how he talks
- **Consciousness (`conscious.py`).**
  - A global workspace: 1–3 thoughts win his attention each month.
  - A self-model ("I am shy", "I am a father").
  - Metacognition ("I think…", "I'm not sure, but…").
  - Every new module below feeds its own thoughts in, so he can talk about it in chat.
- **Conscience.**
  - A moral sense that grows with age, warmth, agreeableness and maturity.
  - Harming someone brings guilt, helping brings pride, and both enter the reward he learns from.
  - It catches his biased acts and his offending.
- **Communication training.**
  - Learning weights his own replies more heavily.
  - About 40 phrasings of each self-question, and multi-turn practice conversations.
  - Answers in the first person ("my", "I have").
  - Self-questions are scored by the first number in the reply.

### Interface
- **3D brain map.** Our own canvas renderer, with nodes spread out so the connections show. You can orbit, pan and
  zoom, and it spins when idle.
- **Factors in real units.** Sliders replaced by:
  - steppers: siblings, friends, risk genes
  - choices: sex, region, parents' education, path after school, minority status, migrant background
  - real scales: income percentile, IQ, µg/m³ of pollution, hours of screens, pupils per class
- **New live cards.** His relationships, His schooling, His phone (a scrolling feed), His mental health, What he
  faces, This season of his life, His health, His body and hormones, Hardships and faith.

### Life systems (each calibrated against published figures)

| Module | What it covers | Checked against |
|---|---|---|
| `schooling.py` | 11 regions; school start age; exam pressure; tutoring; university entry and cost; IQ and adaptability; subjects; the course he wants vs. gets (blocked by grades, money or family) | OECD, Statistics Korea |
| `bonds.py` | Trust, conflict and good-to-bad ratio per person; Gottman's sequence (criticism, defensiveness, contempt, stonewalling); pursue-withdraw; repair; estrangement and reconciliation | Gottman; Pillemer (27% estranged) |
| `digital.py` | First phone at about 11; screen hours by age; a simulated engagement-ranked feed; likes on a variable schedule; habit; comparison; outrage; cyberbullying; app breaks | Common Sense census; Pew |
| `mental.py` | Autism and ADHD from birth (often diagnosed late); 8 conditions that come in episodes, at survey rates; treatment and stigma by region; conditions in the people around him; self-harm | CDC ADDM, NSCH, Solmi 2021 |
| `prejudice.py` | Ethnicity, migrant background, sexuality and coming out, sex, class, weight, neurodivergence, age, disability; hiring bias; bias absorbed and unlearned; standing up for others | Quillian; Pascoe & Richman; Pettigrew & Tropp |
| `seasons.py` | About 150 moments tied to particular ages; pregnancy loss and infertility; a father's hormones and postnatal depression; empty nest; scams; regrets (Pink's four kinds); yearnings; midlife dip; decline before death; teen pregnancy | Paulson; Gettler; FTC; Gilovich; Blanchflower; Gerstorf |
| `illness.py` | About 45 diseases tied to age, each with its own struggles; an adiposity (weight) level; conditions that go unnoticed vs. diagnosed; named causes of death; mortality normalised so life expectancy is kept | CDC; GBD stroke; Peppard |
| `hormones.py` | Mini-puberty, adrenarche, puberty timing, height, teen body clock, dopamine gain by age, bone and muscle, the cycle and PMS/PMDD, pregnancy and the baby blues, perimenopause, menopause and HRT, low testosterone, couvade, the dopamine of new love, seasonal depression, sleep in old age | SWAN; Gettler; Carskadon |
| `hardships.py` | Smoking and vaping, cannabis, gambling, opioids; car crashes; assault and sexual assault; offending and prison; debt; war and displacement; a pandemic; faith and awe; disability after a crash | various (see module docstring) |
| `family.py` additions | Miscarriage, stillbirth, maternal death, infertility and IVF, suicide loss, mothers' birth wording | ACOG, CDC, WHO |

### Documents
- `LIFE_SEASONS.md`: every age group with its hormones, pros and cons, joys, little joys, struggles and sorrows,
  plus minor details. A "built since" list sits at the top.
- `README.md`: a section for every module above.

---

## Left over from round 1

### Not verified
1. **A real GPU life.** Run a new laptop_xl life on all of this code. Check that he actually talks about his
   thoughts, regrets, illnesses and relationships in chat, and that the brain map copes with the new event types.
2. **The final full test run** on the latest code (it was in progress when this was written).

### Moments that happen but don't yet change his life
- **An affair:** his partner never finds out, and the bond is unaffected.
- **Divorce late in life:** only text; the partner stays in his family.
- **Moving into a care home:** lowers independence, but where he lives does not change.
- **Moving in together or a wedding:** no state change apart from a brief happy boost from the wedding (no shared
  money, no commitment).
- **Dyslexia and glasses:** there is no lasting learning-difficulty or eyesight state behind them.
- **Seasons and bonds:** these moments do not create a bond event yet (for example, a friend's divorce).

### Not modelled yet
- Choosing to emigrate (only fleeing war exists), and losing a homeland.
- Long COVID; frailty care at the very end (swallowing, pressure sores).
- Poverty as a lasting trap that passes down generations, rather than a one-off moment.
- His grown children's own lives: their addictions, prison, divorces and successes, as they affect him.
- Pets as individuals with their own personalities (they exist only as family members who die).

### Known imperfections
- Life expectancy is about 76.5 against about 78 in the US.
- About 30% of deaths are recorded as "natural causes".
- High blood pressure and stroke run slightly high.
- Mood is positive in about 67% of adult months (Gallup's figure is 74%).
- Teen pregnancy is set directly and skips the pregnancy-loss outcomes.
- The main page now has many cards and needs a layout pass, for example tabs or a Simple/Lab split for the new
  cards.

### Review plan: fixes required now

This section is a review plan added after round 1. Where it overlaps with code that already exists, a **Now:** line
says what is there today, so the work starts from the right place.

#### 1. Wire the "dead-state" events (moments that only emit text)
Text that does not change his state trains the model on things that did not happen. Each item below needs a real
state change.

**Affair (`bonds.py`, `seasons.py`)**
- Add an `active_affair` flag, with a monthly chance of discovery: `base_rate * (1 - partner_trust)`.
- On discovery:
  - trust drops by 0.65
  - the bond moves to contempt and defensiveness
  - the chance of divorce rises to about 0.75 over the next 6 months
- Every undiscovered month adds guilt through the conscience.

**Divorce late in life (`family.py`, `bonds.py`)**
- The ex-partner leaves the household.
- Shared income and expenses are split, and savings are divided by a settlement factor.
- The bond becomes `ex_partner`, with some conflict left over.

**Wedding and moving in (`family.py`)**
- The couple merge into one household and pool income, which buffers against poverty in `hardships.py`.
- Leaving becomes harder (a higher friction threshold before the bond can break).

**Care home (`illness.py`, `seasons.py`)**
- Set `residence_type = "care_facility"`.
- His daily work and travel routines stop, and his autonomy is capped.
- Each month, his bonds with family who don't visit weaken.

**Dyslexia and glasses (`schooling.py`, `illness.py`)**
- Dyslexia becomes a trait he is born with, like ADHD and autism in `mental.py`. It slows reading and exam progress
  by about 20% unless he has tutoring or accommodations after diagnosis.
- Uncorrected short-sightedness holds back his schooling until he gets glasses.

**Bond triggers across modules (`seasons.py` to `bonds.py`)**
- When a friend or sibling has a major event (divorce, illness, a birth), `bonds.py` gets a callback.
- He either invests time and empathy, which strengthens the bond at a cost to his energy and screen hours, or
  ignores it, and the bond drifts toward estrangement.

#### 2. Replace number scraping and template thoughts (`conscious.py`, `selftalk.py`)
- **Scoring self-questions.** Today a reply is scored by the first number in it, which rewards putting a number
  first rather than being right. Replace this with one of:
  - a linear probe on the model's hidden state
  - cosine similarity between the reply's embedding and the true state vector

  **Now:** the score is verifiable but shallow. A probe or embedding score must stay verifiable, so no judge model.
- **Template thoughts.** Fade the template lines ("I am shy") from always used at 3 years to never used by 6. After
  that, the global workspace passes the modules' numbers to the network, and he writes his own inner monologue.

  **Now:** every thought is a template at every age.

#### 3. Fix how mood and deaths drift (`illness.py`, `mental.py`, `character.py`)
**Mood is positive in 67% of months against Gallup's 74%.** Add a return to his usual mood: negative deltas shrink
(×0.75 a month), so small hardships fade within 3-6 months.

**Now:**
- `character.py` already pulls his mood baseline back over about 24 months.
- `world.py` fades the effects of lived choices.
- The new modules' `apply(..., fades=True)` calls fade only the states listed in `FADE`.

So the fix is to extend fading to every new negative effect, and to check that recovery takes 3-6 months.

**30% of deaths are "natural causes", and life expectancy is 76.5.**
- Replace the catch-all with a Gompertz-Makeham hazard tied to wear in `illness.py`: heart and blood vessels,
  metabolic syndrome, frailty. Every death then has a named cause.
- Lower the baseline rates of high blood pressure and stroke by 12-15%. Make them depend on adiposity, pollution
  (µg/m³) and chronic cortisol.

**Now:** the hazard is Gompertz with multipliers from health, and illness moves risk onto the sick through
`mortality_norm`.

**Teen pregnancy** should go through the same pregnancy steps in `family.py`: miscarriage, stillbirth, maternal
complications and the hormonal crash after birth. **Now:** it sets `expecting` directly.

#### 4. Brain map at scale
- Group the map into 64-128 large clusters, one per region or module.
- Drive edge thickness and glow from how much each cluster's activity varies and how much gradient flows through it.
- Use instanced rendering.

**Now:** the map draws his *life graph* (events, choices, people, states), not the network's weights, and caps it at
about 250 nodes in detail view. A view of the network's weights would be a second, separate map. That second map is
what this item describes.

### Review plan: what to add next (systems for the experiments)

#### 1. Sleep and memory replay (needed for scaling toward 1B)
Between months, run an offline consolidation pass:
1. Take the 5 most salient memories of the month (highest reward, guilt or trauma).
2. Recombine them with older core memories.
3. Run 50-100 fast training steps with no new input.

This steadies the weights, moves recent experience into long-term parameters, and produces a distorted "dream"
text stream.

**Now:** `memory.py` strengthens salient memories during sleep, but the network does not train on replay.

#### 2. Big Five that keep changing (trait vs. state)
A 5-number personality (openness, conscientiousness, extraversion, agreeableness, neuroticism) that starts from
inherited priors and changes over his life:

`Δtrait = η(age) · salience · event_vector`

- η is high before 18 and falls sharply toward 30.
- Severe childhood bullying permanently shifts neuroticism and agreeableness.
- Becoming a parent nudges conscientiousness and warmth.

**Now:** `character.py` already has innate Big Five seeds (about half the trait) plus a part formed by his
circumstances, with plasticity that falls with age. What's missing is the event-driven, salience-weighted part.

#### 3. A fork-and-ablate lab (`experiment_runner.py`)
- **Snapshot and fork:** at any month (for example, vega-9 at 14), save the exact Python state and the network
  weights together.
- **Counterfactual branches:** run a control branch and an intervention branch from the same seed and weights, in
  parallel. Example interventions: sudden poverty, removing a parent, turning off the conscience reward.
- **Measure** how far they diverge: his self-model, his speech, and the brain map.

**Now:** `resume.pt` already saves the whole life and the weights, and resuming is bit-identical. Forking means
copying a resume point into two run folders and applying an override to one.

The GPU fits one training run at a time, so branches run one after the other, or as small models on the CPU.

#### 4. A career and money loop across generations (`economy.py`)
- Map his finished education, IQ and hiring bias (`prejudice.py`) to an occupation tier. The tier sets his income
  path, autonomy, burnout rate and layoff chance.
- Household cash flow becomes a continuous financial-stress level. Chronic shortfall:
  - blocks healthcare, leaving conditions undiagnosed
  - forces cheaper housing with more pollution
  - feeds anxious thoughts into `conscious.py`

**Now:** `career.py` has hours, promotion levels and burnout, but no occupations or fields. Wealth and income are
single numbers.

**Lower priority until these are in:** cosmetic features such as pets with personalities or the cost of climate
insurance.

### From before this round
- The `SURROUNDINGS.md` proposals are unbuilt.
- You install taste-skill and impeccable yourself; I don't download third-party code.

---

## More that could be done

### Making him more human
- **Personality that changes through events:** a lasting rise in neuroticism after trauma, more agreeableness after
  becoming a parent. Measured by Big Five shifts over a life.
- **Values and life goals** (Schwartz values): he chooses goals, pursues them, and achieves or abandons them.
  Regret and pride follow.
- **Humour, playfulness and boredom** as states, with boredom pushing him toward novelty or toward his phone.
- **Moral development stages** (Kohlberg), showing up in why he gives the answers he gives.
- **Dreams:** each night's consolidation produces a dream line drawn from salient memories. These become part of
  his speech.
- **Inner speech in his own voice:** generate his "Thought:" lines with his own network rather than templates once
  he is old enough to speak, so his thoughts become truly his.

### Relationships
- **Friends as full people:** their own life events (weddings, babies, illnesses, moving away) seen through him.
- **Romantic life in depth:** dating, attraction, compatibility, the arc of a relationship, cohabiting, marriage,
  infidelity being discovered, divorce with custody and money.
- **His children growing up:** their personalities, his parenting style (authoritative, permissive, authoritarian,
  neglectful) shaping them, and their outcomes coming back to him.
- **Grandparenting** as a role in his week, not just a moment.
- **Neighbours, colleagues and a boss:** workplace relationships, office politics, mentors.

### Work and money
- **Careers by field:** what he studied leads into an occupation with its own pay, hours, risks and automation
  exposure. Promotions, career changes, starting a business, failing.
- **Housing ladder:** renting, mortgage, negative equity, eviction, homelessness risk.
- **Inheritance and wealth passing down generations;** class mobility over his life.

### World and history
- **A world timeline:** recessions, booms, elections, wars, tech shifts (AI, VR) and pandemics as dated events that
  hit everyone in his cohort at once.
- **Generational identity:** he is born in a year and belongs to a cohort with its own music, slang and norms.
- **Culture:** language spoken at home, bilingualism, festivals, food, migration stories.
- **Climate over his lifetime:** rising heat, worsening disasters and insurance costs, with region-specific
  trajectories.

### Learning and the model
- **Run the brain-map A/B tests:** memory on vs. off, conscience on vs. off. Do they change what he learns?
- **Measure chat quality over age** with the self-question score (verifiable). Plot it in the UI as "how well he
  talks" over his life.
- **Curriculum of conversation:** practice dialogues that get harder with age: small talk, then explaining,
  arguing and comforting someone.
- **Long-term memory retrieval in chat:** tie the Memory line to his real episodic memories by topic.
- **Several lives raised in parallel on CPU** with tiny models, to compare how different upbringings change what
  the network says. This is research tooling for the "second brain" goal.

### Interface
- **A life timeline view:** scroll his whole life as a strip, with each module's events on its own lane.
- **A "what if" button:** fork the life at an age, change one factor, and run both side by side.
- **A family tree view** with bonds coloured by health.
- **An exportable life story:** a generated biography in his own words, chapter by chapter.
- **Better phone simulation:** a real feed you can scroll, with his likes and his dwell time.
