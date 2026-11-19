# Round 4 (final round): a whole human, in a whole society

Rounds 1–3 built one life, made its numbers real and taught him to talk. Round 4 is the big one. Every life becomes a
full person, with every major trait and how it comes about, born into a specific society. That society has its own
rules, prejudices, laws and struggles. The life covers sexual orientation and gender identity, and what living them
costs or gives, depending on where he is born.

After round 4, the life simulation should be essentially finished. The next phase moves to the psychological side:
how all of this shapes the mind he becomes.

**Ground rules (kept from rounds 1–3):**
- Every rate comes from a published source and is checked by the population report.
- No judge model; rewards stay verifiable.
- Everything is built ourselves.
- Sensitive parts are modelled as lived experience with honest data. They are not moral verdicts, and where evidence is contested, the plan says so.

---

## 0. How anything about a person is determined

All traits in round 4 follow one rule:

**trait = genes + shared family environment + his own unique experiences + chance**

with weights taken from twin research.

- **Polderman et al. (2015, *Nature Genetics*):** a meta-analysis of 17,804 traits from about 14.5 million twin pairs. The average heritability is **49%**. For about two-thirds of traits the pattern fits purely additive genes, and the shared family environment is usually small.
- **Turkheimer's "three laws" (2000):**
  1. Everything is somewhat heritable.
  2. Growing up in the same family matters less than genes.
  3. A large part of every trait is neither: it comes from his own unique experiences and chance.
- **The Wilson effect** (Bouchard 2013): the heritability of IQ rises from about 20% in infancy to about 70–80% in adulthood, as people choose environments that fit their genes.
- **Gene × environment:** genes matter more where the environment allows them to. For example, IQ heritability is lower in poor families (Turkheimer 2003; mainly in US samples).

**Build:** a new `genome.py`. Each life gets a vector of polygenic scores, one per trait, drawn from its parents' scores (a mid-parent value plus random segregation). Siblings and children then really resemble each other. Every trait module reads its score with a weight set from the heritability literature. The population report gains **twin and sibling checks**: we simulate twin pairs and confirm the trait correlations come out right.

---

## 1. Every human trait, and what sets it

Each row says what the trait is, roughly how heritable it is, what shapes the rest, and how it plays out over a life.

### 1.1 Personality and temperament

| Trait | Heritability | What shapes the rest | In his life |
|---|---|---|---|
| Big Five (already modelled) | about 40–50% | unique experience; maturity with age | extend to the **HEXACO** model's sixth factor, **honesty–humility** (Ashton & Lee), which feeds his conscience |
| Infant temperament (easy / slow-to-warm / difficult; Thomas & Chess) | moderate | parents' fit to the child ("goodness of fit") | sets the early Big Five and how parents react to him |
| Behavioural inhibition (Kagan) | moderate | gentle exposure over time | shy toddler → anxious teen risk |
| Sensation seeking and impulsivity | about 40–60% | peaks in the teens (Steinberg dual-systems model) | risk taking, crime, accidents, addiction |
| Empathy (affective and cognitive) | about 30% | warmth, attachment | feeds bonds, prosocial acts, conscience |
| Dark Triad (Machiavellianism, narcissism, psychopathy) | about 30–70% | harsh parenting, peers | manipulation, crime, short relationships |
| Grit, conscientiousness, delay of gratification | about 30–40% | household structure | school and work outcomes |
| Humour style, playfulness, boredom proneness | moderate | culture, peers | friendships; boredom pushes him toward his phone or novelty |
| Optimism and explanatory style | about 25% | how setbacks were explained to him | depression risk, health |
| Religiosity | low in childhood; about 40% in adults | family, culture | community, rules, meaning, conflict |
| Political orientation | about 40% (Hatemi et al. 2014) | region, generation, events | family arguments, bonds, identity |
| Chronotype (morning/evening) | about 50% | age (latest in the late teens) | school fit, sleep, mood |
| Handedness | about 25% | culture (forced right-hand use) | small effects |

### 1.2 Body and appearance

| Trait | Heritability | Notes |
|---|---|---|
| Height | about 80% | nutrition and childhood illness matter, by region; a pay premium for taller men |
| Weight and BMI | about 40–70% | food environment, sleep, stress; weight stigma |
| Attractiveness | moderate | a "beauty premium" in pay and hiring (Hamermesh); prejudice for and against |
| Skin tone | high | **colourism** in hiring and marriage, by region (South Asia, Latin America, the US) |
| Puberty timing | about 50–80% | early puberty in girls → mental-health risk; early in boys → status |
| Voice, build, sex characteristics | high | ties to gender identity (section 3) |
| Disability: congenital and acquired | varies | sensory, physical and intellectual; access by region and wealth |
| Chronic illness genetics | varies | already in `illness.py`, now via `genome.py` |

### 1.3 Mind and ability

| Trait | Heritability | Notes |
|---|---|---|
| IQ (g) | 20% → 70–80% with age | Wilson effect; lower in poverty; schooling adds about 1–5 points a year (Ritchie & Tucker-Drob 2018) |
| Specific abilities (verbal, spatial, numeric, musical, motor) | moderate | interests follow strengths |
| Creativity | moderate | openness; boosted by bilingualism and travel |
| Memory span and processing speed | moderate | decline with age |
| Neurodivergence (autism, ADHD, dyslexia; already modelled) | about 70–80% | add **dyscalculia**, **dyspraxia**, **Tourette's** and **giftedness** |
| Sensory processing sensitivity | about 47% | overwhelm, but also depth |
| Interoception and emotional awareness (alexithymia) | moderate | how well he can name his own feelings, which feeds the Feel vector and the psychology phase |

### 1.4 Social and relational

- **Attachment style** (secure / anxious / avoidant / disorganised):
  - mostly environmental, from caregiving
  - about 25% stable from infancy to adulthood (meta-analyses)
  - drives partner choice, conflict and grief
- **Social status seeking, dominance vs. prestige.**
- **Loneliness proneness** (about 37% heritable).
- **Trust in strangers:** strongly cultural (World Values Survey).

---

## 2. Region-specific lives and society

Today the world has 11 broad regions. Round 4 replaces this with about 25 **society archetypes**. Each is a bundle of
measured settings, drawn from real indices, so that a life in rural Bihar, inner-city Chicago, suburban Seoul,
Lagos, Oslo or a Gulf labour camp is genuinely different.

### 2.1 What each society is made of

| Dimension | Source to calibrate from |
|---|---|
| Values: traditional vs. secular, survival vs. self-expression | Inglehart–Welzel cultural map (World Values Survey) |
| Individualism, power distance, uncertainty avoidance, long-term orientation | Hofstede |
| Tight vs. loose (how strictly norms are enforced) | Gelfand et al. 2011 (33 nations) |
| Honour, dignity or face cultures | Leung & Cohen 2011 |
| Religion mix and how strict it is | Pew Global Religious Landscape |
| Family form: nuclear, extended, joint; arranged vs. chosen marriage; dowry or bride price | UN, DHS surveys |
| Gender norms and the law | World Bank *Women, Business and the Law*; UN Gender Inequality Index |
| LGBTQ+ law and attitudes | ILGA World *Laws on Us*; Pew global acceptance surveys |
| Caste, tribe or ethnic hierarchy | India NFHS, national censuses |
| Corruption, rule of law, policing | Transparency International; World Justice Project |
| Welfare: healthcare, pensions, unemployment support | OECD, WHO UHC index |
| Education system (already in round 2) | OECD, UNESCO |
| Economy: informal work, child labour, remittances | ILO, World Bank |
| Violence: homicide rate, conflict, domestic violence | UNODC; WHO |
| Urban/rural split, migration routes | UN DESA |

### 2.2 Region-specific life events (examples)

- **South Asia:**
  - arranged marriage negotiations, dowry pressure
  - caste in school, work and marriage
  - joint family, coaching-centre years and entrance exams
  - son preference, migration to the Gulf
- **Sub-Saharan Africa:**
  - extended-family obligations ("black tax")
  - informal work, school fees, malaria, HIV care
  - bride price, ethnic politics
- **East Asia:**
  - exam hell (gaokao, suneung), hagwon cram schools
  - filial piety, long working hours, hikikomori
  - very low fertility, elder care
- **Middle East and North Africa:**
  - guardianship rules, honour norms
  - youth unemployment, conflict and displacement
  - kafala labour systems for migrants
- **Latin America:**
  - gang violence and informal economies
  - strong family networks, machismo and marianismo norms
  - migration north
- **North America:**
  - medical debt, gun violence
  - student loans, car dependence
  - opioid crisis, polarisation
- **Western Europe and the Nordics:**
  - welfare safety nets, late home-leaving in the south, early in the north
  - secular life, migrant integration
- **Eastern Europe:**
  - post-Soviet institutions, emigration of the young
  - low trust, alcohol mortality in men
- **Southeast Asia and Oceania:**
  - overseas work (the Philippines)
  - Indigenous communities (Aboriginal Australians, Māori)
  - disaster exposure

**Build:** a new `society.py`, which turns an archetype into factor settings and a table of region-only moments. Every round 1–3 module reads the society instead of the coarse region. The population report gets per-region targets: life expectancy, marriage age, fertility, education and income from World Bank and UN data.

---

## 3. Sexual orientation and gender identity

These are modelled as **who he is, discovered over time**, and **how his society and family respond**. That response is where most of the harm, and most of the protection, lies.

### 3.1 Sexual orientation

**Prevalence:**
- Gallup 2025: about **9%** of US adults identify as LGBTQ+. That is **23%** of under-30s, against 3% or less of over-50s. The difference reflects mostly openness, not biology.
- Among LGBTQ+ adults, about 58% are bisexual.

**What sets it:**
- No single cause.
- Twin studies give moderate heritability, about 30% in men (Bailey et al. 2016 review).
- The largest genetic study, Ganna et al. 2019 (*Science*, about 470,000 people), found many small effects and **no "gay gene"**.
- The **fraternal birth order effect:** each older brother raises a boy's odds of being gay by about 33% (Blanchard; Bogaert).
- Parenting does **not** set orientation.

**In his life:**
- An orientation is drawn at birth from `genome.py` plus the birth-order effect. It is a spectrum (a Kinsey-like scale), not a switch.
- **Awareness** comes first, at a median of about 10–13.
- **Self-labelling** comes in the teens.
- **Coming out** happens to different people at different times, or never. It depends on family acceptance, religiosity, society and local law. In 62–64 UN member states same-sex relations are criminalised, some with the death penalty (ILGA World 2024–2025).
- In those societies:
  - hiding, sham marriage, blackmail, arrest
  - emigration as an escape route, using round 2's emigration code
- Relationships, marriage and children follow his orientation and local law: same-sex marriage, adoption, surrogacy, co-parenting.

### 3.2 Gender identity

**Prevalence:** Williams Institute (2025): **0.8%** of US adults and **3.3%** of 13–17-year-olds identify as transgender. Comparisons over time are unreliable because the methods changed.

**What sets it:** not well understood. Twin studies suggest some heritability; brain and hormone theories exist but are contested. The simulation treats it as an innate disposition that may or may not surface, with honest uncertainty.

**In his life:**
- **Gender identity** is drawn at birth: congruent, transgender, or non-binary. **Gender dysphoria** has a strength and an age of onset: childhood, puberty or adulthood.
- Some young people's dysphoria eases over time, and the evidence on how many is contested. The simulation includes desistance as a real path and doesn't hide it.
- **Wanting to transition** grows with dysphoria, and is held back or enabled by:
  - family response
  - religion
  - law (legal gender recognition, bans on care)
  - money and healthcare access
- **Steps, each a choice with consequences:**
  - telling someone
  - social transition (name, pronouns, clothes)
  - legal change
  - hormones
  - surgery
  - Each is available or blocked by region and age.
- **Evidence on outcomes, stated honestly:**
  - Family acceptance is strongly protective. Family rejection goes with about **8.4 times** the rate of suicide attempts in LGB young adults (Ryan et al. 2009).
  - For adults, gender-affirming care is associated with better mental health in many studies.
  - For **minors**, the **Cass Review (UK, 2024)** found the evidence base for puberty blockers and hormones weak.
  - The simulation encodes these as uncertain effects with wide ranges. It does not take a side.
- **Detransition** is a modelled path with its own experience: regret, or changed identity.
- **The simulation's own text** uses the pronouns he or she chooses from the point they change, building on round 3's `voice.py`.

### 3.3 What happens to LGBTQ+ people in each society

This draws on Meyer's **minority stress** model (2003):
- distal stressors: rejection, violence, discrimination
- proximal stressors: concealment, expecting rejection, internalised stigma
- higher depression, anxiety and suicidality, buffered by support and community

The Trevor Project's 2024 survey of LGBTQ+ youth is the calibration target. It is self-selected, so it is used as an upper bound.

---

## 4. Society's sections and their struggles

Every life belongs to several groups at once (**intersectionality**). Each group brings its own struggles, which enter as events, factor penalties or barriers. Some brief examples (each is calibrated in the build):

| Group | Struggles to model | Some sources |
|---|---|---|
| Poor and working class | food insecurity, debt traps, unsafe housing, eviction, informal work, child labour, untreated illness, the scarcity mindset (Mullainathan & Shafir) | World Bank, Fed SHED |
| Rich and elite | achievement pressure, isolation, substance use in affluent teens (Luthar 2003), inheritance conflict | Luthar |
| Rural | distance to care and school, fewer jobs, isolation, farm accidents, climate shocks | WHO, FAO |
| Urban poor and slums | crowding, sanitation, crime, eviction, pollution | UN-Habitat |
| Ethnic and racial minorities | hiring bias (round 1), policing, segregation, health gaps, weathering (Geronimus 2006) | Quillian, Pager |
| Caste | segregation, violence, job and marriage barriers, reservation policy | NFHS, Thorat |
| Religious minorities | persecution, blasphemy laws, school bullying | Pew GRI, SHI |
| Migrants and refugees | deskilling (round 2), status insecurity, detention, family separation, camps | UNHCR, IOM |
| Women and girls | domestic violence (**about 27%** of ever-partnered women, WHO 2021), child marriage, unpaid care, pay gaps, maternal risk, harassment, female genital cutting where it occurs | WHO, UNICEF, World Bank |
| Men and boys | suicide about 3–4 times women's rate, workplace deaths, emotional restriction, falling behind at school, loneliness, forced conscription | WHO, OECD |
| LGBTQ+ people | section 3 | ILGA, Meyer, Trevor |
| Disabled people | access, employment gaps, abuse risk, carer dependence | WHO World Report on Disability |
| Neurodivergent people | masking, burnout, unemployment | NAS, CDC |
| Older people | ageism, isolation, scams (round 2), elder abuse, pensions | WHO |
| Children | abuse, neglect, child labour, child soldiers in conflict zones, online exploitation risk | UNICEF |
| People in prison or with a record | jail, lost work (Pager), lost voting rights, re-offending | BJS, World Prison Brief |
| Homeless people | health, violence, the job–address trap | HUD, FEANTSA |
| Carers | burnout, lost income | Pew 2025 (round 2) |
| Veterans and soldiers | PTSD, injury, reintegration | VA, RAND |
| People with addictions | stigma, overdose, treatment access | UNODC |
| Sex workers, trafficking survivors | violence, criminalisation, exploitation (modelled factually, without detail) | UNODC |
| Body size, appearance, accent, age | weight stigma, the beauty premium, accent bias | Puhl & Heuer, Hamermesh |

**Prejudice (extending `prejudice.py`):**
- Every group above can be the **target**, and he can **hold** the prejudice himself, absorbing it from family, region and media and unlearning it through contact (round 1).
- New: **intersectional stacking.** Penalties combine rather than simply add, and are calibrated where data exists.
- New: **structural vs. interpersonal prejudice.** Laws and institutions act on him; so do individual acts.

---

## 5. How to build it

| Step | Module | What it does |
|---|---|---|
| 1 | `genome.py` | polygenic scores, inheritance from parents to children, twin and sibling checks |
| 2 | `traits.py` | sections 1.1–1.4: every trait as genes + environment + chance, with how it develops |
| 3 | `society.py` | about 25 archetypes, region-only events, laws |
| 4 | `identity.py` | orientation, gender identity, discovery, coming out, transition paths, law and family response |
| 5 | `groups.py` | intersecting memberships and their struggles; extended `prejudice.py` |
| 6 | Population report v2 | per-region and per-group targets, twin correlations, LGBTQ+ prevalence by generation, intersectional checks |
| 7 | UI | the life page shows his society, identity timeline and groups; a "compare two societies" view |
| 8 | Bibliography | every new source added |

**Order:** 1 → 2 → 3, then 4 and 5 together, then 6–8.
**Size:** the biggest round so far, roughly as large as rounds 1–3 combined.
**Rule:** every new module must pass the population report before the next one starts.

---

## 6. After round 4: the psychological phase

With the life finished, the focus moves inside him:
- How does each trait, society and struggle become **beliefs, schemas and defences**?
- Self-concept, identity formation (Erikson, Marcia), meaning-making and narrative identity (McAdams).
- Coping styles, cognitive distortions, resilience.
- How his own network represents all of this, using round 3's feature dictionary and probes.

---

## Sources checked for this plan

- Gallup (2025), *LGBTQ+ Identification Holds at 9% in U.S.* <https://news.gallup.com/poll/702206/lgbtq-identification-holds.aspx>
- Williams Institute (2025), *How Many Adults and Youth Identify as Transgender in the United States?* <https://williamsinstitute.law.ucla.edu/publications/trans-adults-united-states/>
- ILGA World (2024), *Laws on Us*, and the 2025 data update. <https://ilga.org/news/laws-on-us-2024-lgbti-human-rights/>
- Polderman, T. J. C., et al. (2015). Meta-analysis of the heritability of human traits based on fifty years of twin studies. *Nature Genetics*. <https://www.nature.com/articles/ng.3285.pdf>

The other citations above (Turkheimer, Bouchard, Hatemi, Ganna, Blanchard and Bogaert, Ryan, Cass Review, Meyer, Gelfand, Inglehart–Welzel, Hofstede, WHO, Luthar, Geronimus, Hamermesh and others) are well established, but I haven't re-checked their figures for this plan. Each number will be checked against the original before it goes into code and `bibliography.md`.
