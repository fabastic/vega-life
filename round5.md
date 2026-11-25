# Round 5: more to build (expansion list)

Status on 2026-11-25:
- **Round 3 done:**
  - C1 pronouns, D4 overnight check, A4 memory questions, A6 theory of mind (tom.py).
  - C3 world timeline (`timeline.py`): NBER recessions, a pay scar for starting work in a recession (Oreopoulos 2012), and dated world events.
  - C4 parenting styles (`world.py` `parenting_style`): warmth × the new `parent_strictness` factor gives Baumrind's four styles.
  - C5 ACE score (`ace.py`): eight BRFSS categories, calibrated to 64% with one or more and 17% with four or more (Swedo 2023). It raises adult depression and drinking risk. The population report checks all three.
- **Round 5 done (2026-11-25, later the same day):**
  - A1 job-loss pay scar (`timeline.py` `lost_job`): about 25% lower pay, about 15% six years on (Jacobson et al. 1993).
  - A3 Vietnam-era draft for men born 1944-52, about a quarter of them, with a veterans' pay gap (Angrist 1990).
  - C1 hiring bias now also applies when work turns up without a scenario (`world.py`); it was already in `career.py` and `economy.py`.
  - C4 pandemic 2020-21: learning loss of about a third of a school year, more for poorer children (Betthäuser et al. 2023), and more loneliness.
  - B5 a PHQ-9-style depression screen (`mental.py` `phq9`); the population report checks that about 8% of adult years score 10 or more (NHANES 2013-2016).
  - B1 replaced by a check that the young are the least happy age group, since the classic midlife low has faded (Blanchflower, Bryson & Xu 2024; citation unverified).
  - ACE, recession and war events now move his beliefs and land in the story lanes; the life page shows his childhood and his times.
- **Round 3 still open:** A1 a real laptop_xl life (GPU), A2 hybrid objective, A3 graded talk practice, A5 forgetting, B1–B3 looking inside, C2 poverty trap slope, C6–C8, D1–D3, E1–E5.
- **Round 4** (a whole human in a whole society) has not started; its plan is in `round 4(FINAL ROUND).md`.

The items below are new: none of rounds 1–4 or `expansionplan.md` covers them. They come from a scan of the docs plus ideas researched from memory. **Every figure is unverified until its source is checked.** Check each one before calibrating to it.

★ = do first.

---

## A. Life events

| # | Item | What | Source to check | Plugs into | Size |
|---|---|---|---|---|---|
| A1 ★ | Job-loss scar | A layoff cuts earnings for years, not months | Jacobson, LaLonde & Sullivan 1993: about 25% loss for high-tenure workers | `career.py`, `economy.py` | M |
| A2 | Job loss and death | Displacement raises mortality for years | Sullivan & von Wachter 2009 | `world.py` hazard | M |
| A3 | Military service | Conscription by birth year; veterans' later pay | Angrist 1990: about 15% lower earnings for draftees | `timeline.py`, `career.py` | S |
| A4 | Windfalls | Lottery wins and inheritances change work and spending | Imbens, Rubin & Sacerdote 2001 | `economy.py` | S |
| A5 | Housing ladder | Renting, mortgage, negative equity, eviction | round 3 C8; Desmond 2016 for evictions | `economy.py` | M |

## B. Mind and psychology

| # | Item | What | Source to check | Plugs into | Size |
|---|---|---|---|---|---|
| B1 ★ | Wellbeing U-curve check | Mood dips in midlife and recovers | Blanchflower & Oswald 2008: low around mid-40s | population report | S |
| B2 | Delay of gratification | Self-control in childhood predicts later outcomes, less after controls | Moffitt 2011 (Dunedin); Watts, Duncan & Quan 2018 | `drives.py`, `character.py` | S |
| B3 | Procrastination | Intended tasks put off, worse under stress | Steel 2007 | `drives.py` | S |
| B4 | Mind-wandering | Share of waking time off-task, and its mood cost | Killingsworth & Gilbert 2010: about 47% | `conscious.py`, `present.py` | S |
| B5 | Depression screen | A PHQ-9-style score each year, cutoff 10 | Kroenke, Spitzer & Williams 2001 | `mental.py` | S |
| B6 | Empathy across cohorts | Dispositional empathy shifting by birth year | Konrath, O'Brien & Hsing 2011 | `tom.py`, `timeline.py` | S |

## C. Society and world

| # | Item | What | Source to check | Plugs into | Size |
|---|---|---|---|---|---|
| C1 ★ | Hiring discrimination | Callbacks by name and group | Bertrand & Mullainathan 2004: about 50% more callbacks | `prejudice.py`, `career.py` | S |
| C2 | Basic income | An unconditional income arm for what-ifs | Kangas et al. 2019 (Finland trial) | `economy.py`, `experiment.py` | M |
| C3 | Rent control | Rental supply and moves | Diamond, McQuade & Qian 2019 | `surroundings.py` | M |
| C4 | Pandemic years | Schools shut, isolation, learning loss for the 2020 cohort | e.g. Betthäuser 2023 meta-analysis on learning loss | `timeline.py`, `schooling.py` | M |

## D. Model and learning

| # | Item | What | Source to check | Plugs into | Size |
|---|---|---|---|---|---|
| D1 ★ | Data budget check | How much text each profile sees vs. its size | Hoffmann et al. 2022 (Chinchilla): about 20 tokens per parameter | `growth.py`, report | S |
| D2 ★ | Repeated data | How many passes over his own life text still help | Muennighoff et al. 2023: about 4 epochs nearly as good as fresh data | `trainer.py` replay | S |
| D3 | Deduplication | Drop repeated lines from his corpus | Lee et al. 2022 | `trainer.py` | S |
| D4 | Word order by age of acquisition | Words he hears follow when children learn them | Kuperman et al. 2012 norms | `speech.py` | S |
| D5 | Vocabulary norms | Compare his word count with child norms by age | Fenson et al. 1994 (MacArthur-Bates CDI) | `speech.py`, report | S |

## E. Instruments and UI

| # | Item | What | Plugs into | Size |
|---|---|---|---|---|
| E1 ★ | Self-control gradient check | Childhood self-control vs adult health, wealth and crime, as in Moffitt 2011 | `experiment.py`, population report | M |
| E2 | Timeline lane | Recessions and world events on the life page | `life.html` | S |
| E3 | ACE and parenting card | Score, categories and style on the Mind tab | `index.html` | S |

---

## Suggested order

1. Quick checks that need no new mechanics: **B1**, **D1**, **E3**.
2. **A1** job-loss scar, then **C1** hiring discrimination: both reuse `career.py` and `prejudice.py`.
3. **D2** repeated data, on a small profile in the fork lab, while the GPU is free.
4. Round 3's GPU items (A1, A2) whenever the laptop can run for days.
