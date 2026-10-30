# Round 1: what was built, what is left, what could come next

Status at the end of round 1 (2026-10-30):
- **Tests:** 127+ pass. The final full run on the very latest code was still going when this was written.
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
