# Bibliography

This file lists every study, survey and dataset that Vega's life simulation and model are built on or checked against. Each entry says:
- what the source found, in one line;
- how the project uses it;
- where in the code or docs it is used.

The figures are as cited in the code comments. Where a number was reported second-hand (from a summary rather than the original paper), the entry says so. Before quoting a figure anywhere else, check it against the original.

Entries are grouped by area. Within each area they are alphabetical.

---

## 1. Life and death

- **CDC / NCHS, *Mortality in the United States* (2019–2023 data briefs).**
  - Findings: US period life expectancy was about 78.4 years in 2023 (75.8 for men). Leading causes of death were heart disease (about 21–23%, heart attacks included), cancer (about 18–21%), unintentional injury (about 7%), stroke (about 5%), and Alzheimer's plus other dementias (about 6% as the underlying cause).
  - Use: target for life expectancy and the cause-of-death mix.
  - Where: `tools/population.py`, `tools/calibrate.py`, `illness.py` (`cause`, `_wear`).
- **Chetty, R., et al. (2016). The association between income and life expectancy in the United States, 2001–2014. *JAMA*.**
  - Findings: the gap in life expectancy between the richest and poorest 1% is about 10–15 years.
  - Use: calibration check on how much income changes lifespan.
  - Where: `tools/calibrate.py`.
- **Collard, R. M., Boter, H., Schoevers, R. A., & Oude Voshaar, R. C. (2012). Prevalence of frailty in community-dwelling older persons: a systematic review. *JAGS*.**
  - Findings: 10.7% of over-65s are frail (21 studies).
  - Use: target for the frailty condition.
  - Where: `illness.py`, `tools/population.py`.
- **GBD 2016 Lifetime Risk of Stroke Collaborators (2018). *NEJM*.**
  - Findings: about 1 in 4 adults will have a stroke after the age of 25.
  - Use: stroke base rate.
  - Where: `illness.py`.
- **Holt-Lunstad, J., Smith, T. B., & Layton, J. B. (2010). Social relationships and mortality risk: a meta-analytic review. *PLoS Medicine*.**
  - Findings: strong social ties go with about 50% better survival (OR 1.50).
  - Use: check on how much loneliness raises mortality.
  - Where: `tools/calibrate.py`, `world.py`.
- **Moon, J. R., Kondo, N., Glymour, M. M., & Subramanian, S. V. (2011). Widowhood and mortality: a meta-analysis. *PLoS ONE*.**
  - Findings: widowed people's risk of dying is about 1.41 times higher in the first six months and about 1.14 times higher after that.
  - Use: the "widowhood effect".
  - Where: `family.py`.
- **Mostofsky, E., et al. (2012). Risk of acute myocardial infarction after the death of a significant person. *Circulation*.**
  - Findings: the risk of a heart attack rises sharply in the days after a loved one dies.
  - Use: acute risk after a loss.
  - Where: `family.py`.
- **Roelfs, D. J., Shor, E., Davidson, K. W., & Schwartz, J. E. (2011). Losing life and livelihood: a meta-analysis of unemployment and all-cause mortality. *Social Science & Medicine*.**
  - Findings: unemployment goes with a mortality hazard ratio of about 1.63 (adjusted).
  - Use: mortality while unemployed.
  - Where: `world.py`, `tools/calibrate.py`.
- **WHO (2023). *Infertility prevalence estimates*.**
  - Findings: about 1 in 6 adults experience infertility.
  - Use: share of people who are subfertile.
  - Where: `family.py`.

## 2. Body, illness and hormones

- **Gettler, L. T., McDade, T. W., Feranil, A. B., & Kuzawa, C. W. (2011). Longitudinal evidence that fatherhood decreases testosterone in human males. *PNAS*.**
  - Findings: men's testosterone falls when they become fathers, especially for fathers who do hands-on care.
  - Where: `hormones.py`.
- **Holden, B. A., et al. (2016). Global prevalence of myopia and high myopia and temporal trends from 2000 through 2050. *Ophthalmology*.**
  - Findings: about 34% of people worldwide were short-sighted in 2020, projected to reach about 50% by 2050.
  - Use: target for short-sightedness.
  - Where: `illness.py`, `tools/population.py`.
- **Lambert, G. W., Reid, C., Kaye, D. M., Jennings, G. L., & Esler, M. D. (2002). Effect of sunlight and season on serotonin turnover in the brain. *The Lancet*.**
  - Findings: brain serotonin turnover is lowest in winter.
  - Use: winter mood and seasonal depression.
  - Where: `chemistry.py`, `hormones.py`.
- **Lanphear, B. P., et al. (2005). Low-level environmental lead exposure and children's intellectual function: an international pooled analysis. *Environmental Health Perspectives*.**
  - Findings: blood lead rising from 2.4 to 10 µg/dL costs about 3.9 IQ points, and from 2.4 to 30 µg/dL about 6.9. The loss is log-linear: steepest at low doses.
  - Use: IQ lost to lead, set at age 6.
  - Where: `surroundings.py`.
- **Paulson, J. F., & Bazemore, S. D. (2010). Prenatal and postpartum depression in fathers. *JAMA*.**
  - Findings: about 10.4% of fathers are depressed around a birth, rising to 25.6% at 3–6 months after it.
  - Where: `seasons.py`.
- **Peppard, P. E., et al. (2013). Increased prevalence of sleep-disordered breathing in adults. *American Journal of Epidemiology*.**
  - Findings: sleep apnoea is common, more so in men, and mostly undiagnosed.
  - Where: `illness.py`.
- **Pontzer, H., et al. (2021). Daily energy expenditure through the human life course. *Science*.**
  - Findings: metabolism holds steady from about 20 to 60.
  - Where: `LIFE_SEASONS.md`, `hormones.py`.
- **Rose, K. A., et al. (2008). Outdoor activity reduces the prevalence of myopia in children. *Ophthalmology*.**
  - Findings: more time outdoors goes with about half the odds of myopia.
  - Use: the weekday budget's outdoor hours lower the risk of short-sightedness.
  - Where: `illness.py`.
- **SWAN (Study of Women's Health Across the Nation)** and **Carskadon's adolescent sleep research.**
  - Use: the course of menopause, and the shift to later sleep in teenagers.
  - Where: `hormones.py`, `LIFE_SEASONS.md`.

## 3. Mind and mental health

- **CDC ADDM Network (2025).**
  - Findings: about 1 in 31 US 8-year-olds are identified as autistic, boys about 3.4 times as often as girls.
  - Where: `mental.py`.
- **Hughes, K., et al. (2017). The effect of multiple adverse childhood experiences on health: a systematic review and meta-analysis. *The Lancet Public Health*.**
  - Findings: four or more ACEs go with about 3–6 times the odds of mental ill health.
  - Where: `tools/calibrate.py`.
- **Felitti, V. J., et al. (1998). Relationship of childhood abuse and household dysfunction to many of the leading causes of death in adults (the ACE Study). *American Journal of Preventive Medicine*.**
  - Findings: four or more ACEs go with roughly 4–12 times the risk of alcoholism, drug abuse, depression and suicide attempts.
  - Use: proposed calibration.
  - Where: `round2.md`.
- **NSCH (National Survey of Children's Health), 2022.**
  - Findings: about 11% of US children have ever been diagnosed with ADHD.
  - Where: `mental.py`.
- **Snowling, M. J. (2013). Early identification and interventions for dyslexia. *Journal of Research in Special Educational Needs*.**
  - Findings: dyslexia affects 5–10% of people, depending on the cut-off used.
  - Where: `mental.py`, `tools/population.py`.
- **Solmi, M., et al. (2021). Age at onset of mental disorders worldwide: large-scale meta-analysis of 192 epidemiological studies. *Molecular Psychiatry*.**
  - Use: the age-of-onset curves for each condition.
  - Where: `mental.py`.
- **Vassos, E., Pedersen, C. B., Murray, R. M., Collier, D. A., & Lewis, C. M. (2012). Meta-analysis of the association of urbanicity with schizophrenia. *Schizophrenia Bulletin*.**
  - Findings: psychosis risk is about 2.4 times higher in the most urban areas than in the most rural.
  - Where: `surroundings.py`, `factors.py`.
- **Engemann, K., et al. (2019). Residential green space in childhood is associated with lower risk of psychiatric disorders from adolescence into adulthood. *PNAS*.**
  - Findings: children with the least green space had 15–55% higher risk of adult psychiatric disorders (about 1 million Danes).
  - Where: `surroundings.py`.

## 4. Grief, emotion and wellbeing

- **Blanchflower, D. G. (2021). Is happiness U-shaped everywhere? *Journal of Population Economics*.**
  - Findings: wellbeing dips through midlife, with a low around 47–48 (132 countries).
- **Blanchflower, D. G., et al. (2024).**
  - Findings: the young are now the least happy of all age groups.
  - Use, for both: the midlife dip and the young adults of today.
  - Where: `seasons.py`.
- **Bonanno, G. A., et al. (2002). Resilience to loss and chronic grief: a prospective study from preloss to 18 months postloss. *Journal of Personality and Social Psychology*.**
  - Findings: grief follows distinct paths (resilient, recovering, chronic), and chronic grief tracks how dependent the person was before the loss.
  - Where: `family.py`.
- **Brown, M., et al. (2024)** and **Walasek, L., Mullett, T. L., & Stewart, N. (2018)**, on loss aversion.
  - Findings: the meta-analytic loss-aversion coefficient is about 1.96 (Brown), with a wide spread; Walasek et al. estimate 1.31.
  - Where: `character.py`.
- **Diekelmann, S., & Born, J. (2010). The memory function of sleep. *Nature Reviews Neuroscience*.**
  - Use: sleep consolidating memories.
  - Where: `trainer.py` (`sleep`), `memory.py`.
- **Diener, E., & Diener, C. (1996). Most people are happy. *Psychological Science*.**
- **Diener, E., Lucas, R. E., & Scollon, C. N. (2006). Beyond the hedonic treadmill. *American Psychologist*.**
  - Findings, for both: most people are mildly happy, and they adapt to circumstances, but only partly.
  - Where: `character.py`, `chemistry.py`.
- **Ditzen, B., et al. (2007)** and **Dreisoerner, A., et al. (2021).**
  - Findings: supportive touch and self-soothing touch lower cortisol under stress.
  - Where: `chemistry.py`.
- **Gallup Global Emotions.**
  - Findings: about 74% of people report mostly positive days ("yesterday" items, about 140–160 countries).
  - Use: target for good-mood months.
  - Where: `tools/population.py`, `chemistry.py`.
- **Hall, J. A. (2018). How many hours does it take to make a friend? *Journal of Social and Personal Relationships*.**
  - Findings: about 200 hours together to become a close friend.
  - Where: `LIFE_SEASONS.md`, `people.py`.
- **Hickman, C., et al. (2021). Climate anxiety in children and young people. *The Lancet Planetary Health*.**
  - Findings: more than half of young people are very worried about climate change.
  - Where: `LIFE_SEASONS.md`.
- **Lucas, R. E. (2004)** and **Lucas, R. E., et al. (2004). Unemployment alters the set point for life satisfaction. *Psychological Science*.**
  - Findings: long unemployment leaves a lasting dent in life satisfaction.
  - Where: `career.py`, `chemistry.py` (`scar`).
- **Lundorff, M., et al. (2017). Prevalence of prolonged grief disorder in adult bereavement: a systematic review and meta-analysis. *Journal of Affective Disorders*.**
  - Findings: about 9.8% of bereaved people develop prolonged grief disorder.
  - Where: `family.py`.
- **Simbi, C. M. M., et al. (2020).** Danish register study of bereavement.
  - Findings: adult depression risk is about 1.2 times higher after a natural death and about 3 times higher after a violent one.
  - Where: `family.py`.
- **Starcke, K., & Brand, M. (2012). Decision making under stress. *Neuroscience & Biobehavioral Reviews*.**
  - Where: `character.py`.
- **Wilson, M. A., & McNaughton, B. L. (1994). Reactivation of hippocampal ensemble memories during sleep. *Science*.**
  - Use: the idea behind the model's sleep replay.
  - Where: `trainer.py`.
- **World Happiness Report 2024.**
  - Findings: the US ranks 62nd for under-30s.
  - Use: proposed calibration.
  - Where: `round2.md`.

## 5. Personality and development

- **Bleidorn, W., et al. (2022). Personality stability and change: a meta-analysis of longitudinal studies. *Psychological Bulletin*.**
  - Findings: traits change across the lifespan, and emotional stability rises the most.
  - Where: `character.py`.
- **Buhler, J. L., et al. (2024). Life events and personality change: a systematic review and meta-analysis. *European Journal of Personality*.**
  - Findings: life events change personality only a little, and work events more than love events.
  - Where: `character.py` (`nudge`).
- **Hartshorne, J. K., Tenenbaum, J. B., & Pinker, S. (2018). A critical period for second language acquisition. *Cognition*.**
  - Findings: grammar learning ability stays high until about 17–18, then declines.
  - Where: `character.py`, `growth.py`.
- **Laursen, B., Coy, K. C., & Collins, W. A. (1998). Reconsidering changes in parent–child conflict across adolescence. *Child Development*.**
  - Findings: parent–child conflict peaks in early adolescence and eases after.
  - Where: `bonds.py`.
- **Pinquart, M., & Kauser, R. (2018). Do the associations of parenting styles with behavior problems and academic achievement vary by culture? *Cultural Diversity and Ethnic Minority Psychology*.**
  - Findings: authoritative parenting goes with the best outcomes across cultures, from 428 studies.
  - Use: proposed parenting styles.
  - Where: `round2.md`.
- **Roberts, B. W., & DelVecchio, W. F. (2000). The rank-order consistency of personality traits from childhood to old age. *Psychological Bulletin*.**
- **Roberts, B. W., Walton, K. E., & Viechtbauer, W. (2006). Patterns of mean-level change in personality traits across the life course. *Psychological Bulletin*.**
  - Use, for both: traits settle with age, and their average level drifts toward maturity.
  - Where: `character.py` (`plasticity`).
- **Steinberg, L., et al. (2009). Age differences in future orientation and delay discounting. *Child Development*.**
  - Findings: impulsive choice falls through adolescence.
  - Where: `character.py` (`present_bias`).
- **Carstensen's socioemotional selectivity theory.**
  - Findings: older people choose fewer, closer ties, and attend more to the good.
  - Where: `seasons.py`.
- **Gilovich, T., & Medvec, V. H. (1995). The experience of regret. *Psychological Review*.**
- **Pink, D. (2022). *The Power of Regret* / World Regret Survey.**
  - Findings, for both: people regret what they didn't do more than what they did. Pink sorts regrets into four kinds: foundation, boldness, moral and connection.
  - Where: `seasons.py`.

## 6. Family and relationships

- **CDC NSFG (National Survey of Family Growth).**
  - Findings: 40–45% of first marriages end. Cohabiting unions end more often.
  - Where: `tools/population.py`, `family.py`.
- **General Social Survey (GSS).**
  - Findings: about 20% of married men and 13% of married women report an affair.
  - Where: `bonds.py` (`_affair`), `tools/population.py`.
- **Lundberg, S., & Pollak, R. A. (2016)** on cohabitation and marriage.
  - Findings: cohabitation now usually comes before marriage in rich countries, and marriage raises the cost of leaving.
  - Where: `family.py` (`_household`).
- **Pew Research Center (2014)**, analysis of Census data.
  - Findings: by 45, 19% of men and 14% of women had never married.
- **US Census reporting (2025).**
  - Findings: it now takes until about 45 for 80% of adults to marry.
  - Note: this figure comes from a news summary, not the Census release itself.
  - Use, for both: target for "ever married".
  - Where: `tools/population.py`.
- **Pew Research Center (2025).**
  - Findings: a quarter of US adults, and 54% of those in their 40s, care for both an ageing parent and a child (the sandwich generation).
  - Where: `seasons.py`.
- **Pillemer, K. (2020). *Fault Lines*, Cornell Family Reconciliation Project.**
  - Findings: about 27% of US adults are estranged from a relative.
  - Where: `bonds.py`.
- **US Census Bureau, Current Population Survey (2023).**
  - Findings: about a third of US 18–34-year-olds live with their parents.
  - Use: the age at which he leaves home.
  - Where: `economy.py`.
- **OECD equivalence scale (square-root scale).**
  - Findings: a couple needs about √2 ≈ 1.41 times a single person's income for the same living standard.
  - Use: costs in a pooled household.
  - Where: `world.py`, `economy.py`.

## 7. Money, work and place

- **Chetty, R., & Hendren, N. (2018). The impacts of neighborhoods on intergenerational mobility I. *Quarterly Journal of Economics*.**
- **Chetty, R., Hendren, N., & Katz, L. F. (2016). The effects of exposure to better neighborhoods on children (Moving to Opportunity). *American Economic Review*.**
  - Findings, for both: each year of childhood spent in a better area moves adult outcomes about 4% of the way toward that area's level.
  - Where: `surroundings.py`.
- **Chetty, R., Hendren, N., Kline, P., & Saez, E. (2014). Where is the land of opportunity? *Quarterly Journal of Economics*.**
  - Findings: in the US, the rank-rank slope between parents' and children's income is about 0.34.
  - Use: proposed calibration of poverty passing down generations.
  - Where: `round2.md`.
- **Clark, C., et al. (2006). Exposure–effect relations between aircraft and road traffic noise exposure at school and reading comprehension: the RANCH project. *American Journal of Epidemiology*.**
  - Where: `surroundings.py`.
- **Federal Reserve, *Economic Well-Being of U.S. Households in 2023* (SHED, 2024).**
  - Findings: 72% of adults are "at least okay" financially. The share is 48–67% for those without a degree, and 64% for parents of young children.
  - Use: targets for money stress.
  - Where: `tools/population.py`.
- **Noble, K. G., et al. (2015). Family income, parental education and brain structure in children and adolescents. *Nature Neuroscience*.**
  - Findings: income's link to development is logarithmic, so the poorest gain the most from a little more.
  - Where: `surroundings.py`.
- **OECD, *Education at a Glance 2025*.**
  - Use: share of people with a tertiary degree, by region.
  - Where: `schooling.py`.
- **Oreopoulos, P., von Wachter, T., & Heisz, A. (2012). The short- and long-term career effects of graduating in a recession. *AEJ: Applied Economics*.**
  - Findings: graduating in a recession costs about 9% of earnings at first, fading over 8–10 years.
  - Use: proposed.
  - Where: `round2.md`.
- **Park, R. J., Goodman, J., Hurwitz, M., & Smith, J. (2020). Heat and learning. *AEJ: Economic Policy*.**
  - Findings: each 1°F hotter school year costs about 1% of a year's learning. Air conditioning largely offsets it.
  - Where: `surroundings.py`.
- **Stutzer, A., & Frey, B. S. (2008). Stress that doesn't pay: the commuting paradox. *Scandinavian Journal of Economics*.**
  - Findings: a one-hour commute each way needs about 40% more pay to leave people equally satisfied.
  - Where: `surroundings.py`, `factors.py`.
- **UN DESA, *International Migrant Stock 2024*.**
  - Findings: about 3.6% of people live outside the country they were born in.
  - Where: `economy.py`, `tools/population.py`.
- **US FTC, Consumer Sentinel data.**
  - Findings: median losses to fraud rise with age.
  - Where: `seasons.py` (`_scam`).

## 8. Prejudice and the justice system

- **Pager, D. (2003). The mark of a criminal record. *American Journal of Sociology*.**
  - Findings: a criminal record roughly halves callbacks from employers.
  - Where: `hardships.py`, `economy.py`.
- **Pascoe, E. A., & Smart Richman, L. (2009). Perceived discrimination and health: a meta-analytic review. *Psychological Bulletin*.**
  - Findings: discrimination harms mental and physical health (134 studies).
  - Where: `prejudice.py`.
- **Pettigrew, T. F., & Tropp, L. R. (2006). A meta-analytic test of intergroup contact theory. *Journal of Personality and Social Psychology*.**
  - Findings: contact between groups reduces prejudice (r ≈ −0.21, 515 studies).
  - Where: `prejudice.py`.
- **Quillian, L., Pager, D., Hexel, O., & Midtbøen, A. H. (2017). Meta-analysis of field experiments shows no change in racial discrimination in hiring over time. *PNAS*.**
- **Quillian, L., et al. (2019). Do some countries discriminate more than others? *Sociological Science*.**
  - Findings, for both: callback gaps for equal CVs have not changed since 1989, and appear in all nine countries studied.
  - Where: `prejudice.py`, `career.py`.

## 9. Screens, phones and AI

- **Common Sense Media, *Census: Media Use by Tweens and Teens* (latest edition).**
  - Use: hours of screen time by age.
  - Where: `digital.py`.
- **Goodyear, V. A., et al. (2025). School phone policies and their association with mental wellbeing… (SMART Schools study). *The Lancet Regional Health – Europe*.**
  - Findings: school phone bans made no difference to wellbeing; total phone time did matter.
  - Where: `round2.md`, `digital.py`.
- **OpenAI & MIT Media Lab (2025).** Studies of affective chatbot use.
  - Findings: heavy daily use went with more loneliness.
  - Use: proposed.
  - Where: `round2.md`.
- **Orben, A., & Przybylski, A. K. (2019). The association between adolescent well-being and digital technology use. *Nature Human Behaviour*.**
  - Findings: digital technology use explains at most 0.4% of the variance in teen wellbeing.
  - Where: `SURROUNDINGS.md`, `digital.py`.
- **Pew Research Center (2022).**
  - Findings: 46% of US teens have been cyberbullied, rising to 54% of older girls.
  - Where: `digital.py`.

## 10. Machine learning and the model

- **Alain, G., & Bengio, Y. (2016). Understanding intermediate layers using linear classifier probes.** arXiv:1610.01644.
  - Use: the self-knowledge probe.
  - Where: `cortex.py`.
- **Bricken, T., et al. (2023). *Towards Monosemanticity: Decomposing Language Models With Dictionary Learning*.** Anthropic.
  - Use: proposed sparse autoencoders on his hidden states.
  - Where: `round2.md`.
- **BabyLM Challenge findings (2024).** arXiv:2504.08165.
  - Findings: GPT-BERT, a hybrid of causal and masked language modelling, won both tracks. Curriculum learning was largely unsuccessful.
  - Where: `round2.md`.
- **Gurnee, W., & Tegmark, M. (2023). Language models represent space and time.** arXiv:2310.02207.
  - Use: proposed probes for his age and where he is.
  - Where: `round2.md`.
- **Kosinski, M. (2023). Theory of mind may have spontaneously emerged in large language models**, and **Ullman, T. (2023). Large language models fail on trivial alterations to theory-of-mind tasks.** arXiv.
  - Use: proposed theory-of-mind tests, each with a perturbed variant.
  - Where: `round2.md`.
- **Park, J. S., et al. (2023). Generative agents: interactive simulacra of human behavior. *UIST*.**
  - Use: a proposed baseline to compare him against.
  - Where: `round2.md`.
- **Shao, Z., et al. (2024). DeepSeekMath (GRPO).**
  - Use: the method he learns from verifiable rewards with: group relative policy optimisation.
  - Where: `trainer.py` (`grpo`).
- **Tadros, T., Krishnan, G. P., Ramyaa, R., & Bazhenov, M. (2022). Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks. *Nature Communications*.**
  - Use: why the model has sleep replay.
  - Where: `trainer.py` (`sleep`), `round2.md`.

---

### Other references and tools

- **Python 3.12 and PyTorch.** The only third-party code in the model. Everything else, including the brain map, the network map, the timeline and the world map, was written for this project.
- **Map outlines and city coordinates (`ui/life.html`, `story.py`).** Coarse continent outlines drawn by hand for this project. The city latitudes and longitudes are approximate public values.
