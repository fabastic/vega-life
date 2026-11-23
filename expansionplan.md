# Vega Life — Expansion Plan

Goal: move Vega from a detailed life simulator to an experimental platform where every new system comes with a
test it can fail. Each item lists what it builds on in the current code, what to add, and how to tell it works.

Rule for every phase: a feature is done only when an experiment in `vegalife/experiment.py` can switch it off and
show a measurable difference across seeds. No feature ships on "it looks lifelike".

Vega models parts of human development. Parameter count and a human-like life history do not show consciousness or
subjective experience. The plan treats every "mind" feature as a mechanism to measure, not a claim.

---

## Phase 1 — Cognitive core (beliefs and other minds)

### 1.1 Belief system
- Builds on: `memory.py`, `mental.py`, `character.py`, `rlvr.py`.
- Add `vegalife/beliefs.py`: propositions ("people can be trusted", "failure is recoverable") with confidence,
  supporting and contradicting memory ids, origin (parent, peer, feed, own experience), last update, and links to
  other beliefs.
- Update rule: Bayesian-style confidence shift weighted by the emotional salience of the event and the
  plasticity of the layer period it happens in.
- Test: give the same contradicting events at age 8 and at 40. Childhood beliefs should move more and resist
  later reversal. Ablation: freeze beliefs and check that decisions in `scenarios.py` change.

### 1.2 Theory of Mind
- Builds on: `people.py`, `bonds.py`, `family.py`.
- Give each simulated person their own belief store (reuse 1.1), goals, and a model of Vega.
- New scenario class: false-belief tasks (Sally-Anne style), deception detection, predicting another person's
  choice. Each has one checkable answer, so it plugs into RLVR as a reward.
- Test: accuracy curve by age. Expect a jump around ages 4-6 if the critical-period setup matters. Ablation: run
  with a caregiver who never models Vega's mind and compare the curve.

### 1.3 Digital unconscious
- Builds on: `memory.py`, `conscious.py`, `cortex.py`.
- Split memory into explicit (retrievable, can be put into words through `selftalk.py`) and implicit (weight
  traces and association strengths that bias choices but can't be retrieved).
- Add unresolved conflicts: events with high salience and no resolution that keep biasing related choices.
- Test: explicit-memory ablation versus implicit ablation. If Vega can't recall an event but its choices still
  shift, the split is real.

### 1.4 Autobiographical memory store
- A persistent, queryable life record (event, age, people, emotion, which beliefs it touched). It is the backbone
  for 2.x and 4.x. (The earlier proposal called this EIDOLON. No module of that name exists in this repo yet.)

---

## Phase 2 — Identity and development

### 2.1 Identity continuity experiment
- Manipulate memory availability, memory accuracy (inject false memories), and access to childhood records.
- Measure: consistency of self-descriptions, preference stability, decision similarity against an untouched fork.
- Flagship question: does Vega stay "the same individual" when its past changes?

### 2.2 Counterfactual memory
- At big decisions (school, career in `career.py`, partner in `bonds.py`) store the road not taken: a short
  forecast of the other path plus how uncertain it is.
- Test: does regret (in `mental.py`) track the gap between the real and the imagined outcome? Do later choices get
  more risk-averse after high regret?

### 2.3 Dreams as an experiment arm
- Builds on: sleep replay in `seasons.py` / `trainer.py`.
- Arms: normal replay, no replay (sleep deprivation), salience-weighted replay, random recombination.
- Measure: retention on problem sets, error reinforcement, new associations.

### 2.4 Longitudinal cognitive tests
- A fixed battery run every simulated year: working memory, reasoning, vocabulary, ToM, moral reasoning.
- The same battery across all runs, so lives can be compared.

### 2.5 Moral development lab
- Scenarios with conflicting duties, personal cost, social pressure, missing information, and delayed
  consequences.
- Measure: gap between what Vega says it believes (speech) and what it does (choices), and whether the gap grows
  when it has more to lose.

---

## Phase 3 — Social scale

### 3.1 Population of Vegas
- Builds on: `tools/population.py`.
- Step 1: many small lives (frozen at ~0.5M–20M parameters) instead of full 1B lives. Full size for a few chosen
  individuals only.
- Shared world: lives meet, befriend, compete for jobs and housing in `economy.py`.
- Same starting conditions across many seeds to separate chance from cause.

### 3.2 Cultural evolution across generations
- Parents pass beliefs (1.1) to children. Children can reject them.
- Norms drift. Technology shifts (`digital.py`) change work and relationships per generation.
- Measure: how fast a belief spreads, and when communities split into different cultures.

### 3.3 Information ecology
- Builds on: feeds, misinformation and AI companions in `digital.py`.
- Recommendation algorithms (engagement-max versus diverse), echo chambers, rumour spread, correction, reputation.
- Measure: belief polarisation, trust in others, decision quality.

### 3.4 Institutions
- Schools (`schooling.py`), employers, courts, governments as agents with rules that can change.
- Test the effects of policy: what happens to the population when a minimum income or school funding changes.

### 3.5 Inequality and mobility
- Track wealth, health and education across generations. Measure mobility and how prejudice
  (`prejudice.py`) compounds.

---

## Phase 4 — Instruments

### 4.1 Life replay debugger
- Checkpoint the full state (weights, beliefs, memory, world) each simulated year.
- Rewind to any age, inspect which memories and beliefs drove a decision, change one factor, branch, and compare
  the two lives side by side.

### 4.2 Brain explorer
- Builds on: `brainmap.py`, `cortex.py`.
- Activations per layer, retrieval paths, gradient flow, plasticity by period, damage, connectivity over decades.
- Kept minimal, in line with the current UI.

### 4.3 Automated experiment runner
- Declarative experiment files in `configs/`: arms, seeds, metrics, stopping rule.
- Runs in batches, resumes after a crash, writes results to `runs/`.

### 4.4 Statistical reports
- Effect sizes, confidence intervals, correction for multiple comparisons, and pre-registered hypotheses saved
  before a run.
- Report generator that outputs a fixed-format summary per experiment.

### 4.5 Reproducibility
- Pin every seed, factor, config and code version per run. Any result can be re-run bit for bit.

---

## Phase 5 — Compute scale

The full 1B-per-life profile does not scale to populations on one machine. Options, in order:

1. **Tiered fidelity.** Most lives run as small models or rule-driven agents. Only "focal" lives get the full
   growing network. Promote a life to full size when it becomes interesting.
2. **Shared base, per-life adapters.** One shared frozen trunk with small per-life LoRA-style adapters on the
   plastic layers. Cuts memory per life by orders of magnitude. Trade-off: lives share inductive bias, which
   weakens the "born from scratch" claim. Report this honestly.
3. **Event-driven time.** Skip months where nothing happens. Simulate dense periods (childhood, crises) at full
   resolution.
4. **Distributed runs.** Spread independent lives across machines or GPUs. Only sync at social interaction points.
5. **Mixed precision and activation checkpointing** for the focal 1B lives.

Measure the scaling: lives per GPU-hour at each tier, and how much each shortcut changes outcomes against a
full-fidelity baseline.

---

## Phase 6 — Longer horizons and new questions

- **Ageing and dementia.** Builds on the epigenetic wear in `world.py`. Structured network damage, then test which
  memories and beliefs survive.
- **Language change.** Each generation's speech in `speech.py` feeds the next. Track drift in vocabulary and
  grammar.
- **Multiple lives, one body (twins).** Same genes, different families. A natural nature-versus-nurture design.
- **Transfer.** Put an adult Vega in a culture it never saw. Measure adaptation against a native-born life.
- **Surprise detection.** Automatically flag behaviour no rule predicts (outliers across seeds), then queue a
  controlled experiment to explain it.

---

## Order and risk

| Order | Item | Why this order | Main risk |
|---|---|---|---|
| 1 | 1.1 Beliefs | Base layer for ToM, unconscious, culture | Update rule too hand-tuned |
| 2 | 1.4 Life record | Needed by identity, replay, counterfactuals | Storage size over 80 years |
| 3 | 1.2 ToM | Clear right answers, plugs into RLVR | Small model may never pass |
| 4 | 4.3 Runner + 4.5 repro | Every later claim depends on it | Takes time without visible features |
| 5 | 1.3 Unconscious | Clean ablation experiment | Hard to tell implicit from noise |
| 6 | 2.x Identity, dreams, battery | Uses 1.1–1.4 | Metrics for "same identity" are contested |
| 7 | 5.1–5.2 Compute tiers | Needed before populations | Adapters weaken "from scratch" |
| 8 | 3.x Population, culture, info | The big scale step | Compute and run time |
| 9 | 4.1–4.2 Replay, brain explorer | Most useful once there is a lot inside | UI scope creep |
| 10 | 6.x Long horizons | Research extensions | Open-ended |

Riskiest early step: 1.1, because nearly everything later reads beliefs. Build it first and test it with an
ablation before starting the rest.
