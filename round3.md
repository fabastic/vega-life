# Round 3: what could be added next

Status at the start of round 3 (2026-11-15):
- Rounds 1 and 2 are finished and pushed.
- All 16 population rates are inside their real-world ranges.
- The `/life` story page, the what-if launcher and the population check all work.
- What is still missing is a big mind. Every life so far has been tiny: at 2.4M parameters he babbles.

Round 3 ideas fall into five groups, roughly in the order they matter for the goal of a "second brain":

| # | Group | What it gives you | Size |
|---|---|---|---|
| A | Make him actually talk | A mind worth chatting with | Large, mostly GPU time |
| B | Look inside his mind | See *what* he has learned, not just the loss | Medium |
| C | Deeper life | More true-to-life lives | Medium, many small pieces |
| D | Prove it works | Evidence that being raised changes him | Medium |
| E | Interface | Easier to watch, compare and share | Small to medium |

Each item below says what it is in plain words, why it matters, and roughly how it would be built. **★** marks the items I would do first.

---

## A. Make him actually talk (the model)

### A1. ★ One real `laptop_xl` life on all the new code
- **What:** Run a full life on the biggest profile the 8 GB GPU allows, not the tiny test profile.
- **Why:** Nothing since round 1 has been tested at a size where he can form sentences. Chat, inner voice, dreams and the self-knowledge probe all need this before we can judge them.
- **How:**
  - Start a life from the UI.
  - Leave it running for days.
  - Check chat at ages 5, 10, 18 and 30.
  - Record what works and what doesn't in a short report.

### A2. ★ Hybrid learning objective (what won BabyLM 2024)
- **What:** Today he only learns by predicting the next byte. The winning small-data model also learned to fill in hidden gaps in the middle of text, inside the same network.
- **Why:** It was the clearest win for learning from little data, which is exactly his situation.
- **How:**
  - Add a masked-byte loss on some batches in `trainer.py`.
  - Compare against the current setup with the fork lab.

### A3. Talking practice that grows with him
- **What:** Practice conversations that get harder with age: small talk, then explaining, then arguing, then comforting someone.
- **Why:** He mostly copies the prompt now. Graded practice gives verifiable targets beyond "how old are you".
- **How:**
  - Templates in `selftalk.py` with checkable answers: did he name the right person, the right feeling, the right reason?
  - BabyLM found ordering by difficulty alone rarely helps, so treat this as an experiment.

### A4. ★ Memory in chat that is really his
- **What:** When you ask "do you remember your first day at school?", he retrieves the actual episode from his memory and talks from it.
- **Why:** This is the core "second brain" behaviour.
- **How:**
  - Match words and topics in your message against his episodic memories (`memory.py`).
  - Put the best one in the prompt.
  - Reward answers that mention its details.

### A5. Measuring forgetting
- **What:** Track whether he still knows things from childhood as he ages, with sleep replay on and off.
- **Why:** It tests whether replay protects old knowledge, as Tadros 2022 found it did in other networks.
- **How:** Freeze a set of early-life questions and score them every year, in two fork-lab arms.

### A6. Theory-of-mind questions about his own people
- **What:** Questions like "Mum hid the keys while Dad was out. Where will Dad look?", each with a slightly altered version.
- **Why:** These check whether he understands other people's beliefs. The altered versions catch fake understanding (Ullman 2023).
- **How:** Generate them from real events in his life, and score them the same way as the self-questions.

---

## B. Look inside his mind

### B1. ★ A feature dictionary (sparse autoencoder)
- **What:** Train a small sparse autoencoder on his hidden states every decade. It splits them into "features" you can name: *Mum*, *school*, *fear*, *money*.
- **Why:** It turns the network map from "this region is busy" into "this region is thinking about his father".
- **How:**
  - Build it from scratch in PyTorch, following Anthropic's *Towards Monosemanticity* (2023).
  - Show the top features on `/cortex`.

### B2. Probes for age and place
- **What:** Like the self-knowledge probe, but asking "how old is he?" and "where is he?".
- **Why:** Language models carry time and place internally (Gurnee & Tegmark 2023). This checks whether his do.
- **How:** Two more ridge probes in `cortex.py`.

### B3. Compare two minds
- **What:** After a what-if experiment, show where the two networks differ: which features exist in one but not the other.
- **Why:** It answers "what did growing up poor or lonely change *inside* him?"
- **How:** Run the feature dictionary on both arms and list the features that differ.

---

## C. Deeper life (the simulation)

### C1. ★ Pronouns everywhere
- **What:** Many event lines still say "he" or "his" in a woman's life.
- **Why:** It is a visible error in every female life's story and chat.
- **How:** A small helper that fills in he/she and his/her, applied across the modules.

### C2. ★ Poverty that passes down generations
- **What:** A lasting "trap" state, not just inheritance. Low childhood wealth affects school, health and starting pay, which in turn shapes his own children.
- **Why:** Round 2 only partly did this.
- **How:** Calibrate so parents' and children's income ranks line up with a slope of about 0.34 (Chetty 2014), checked in the population report.

### C3. A world timeline
- **What:** Dated recessions, booms, pandemics and new technology, hitting everyone born in the same year at once.
- **Why:** Graduating in a recession costs about 9% of pay at first, fading over 8–10 years, and longer for the poor (Oreopoulos 2012). Generations differ.
- **How:**
  - A dated event list keyed to birth year.
  - `economy.py` reads it.
  - The timeline's World lane shows it.

### C4. Parenting styles
- **What:** His parents have a style: authoritative, authoritarian, permissive or neglectful. Later he has one too.
- **Why:** Authoritative parenting goes with the best outcomes across cultures (Pinquart & Kauser 2018, 428 studies).
- **How:** One factor that sets warmth and strictness, flowing into bonds, mood and school.

### C5. An ACE score
- **What:** Count adverse childhood experiences (abuse, neglect, divorce, a parent in prison, and so on).
- **Why:** Four or more go with roughly 4–12 times the risk of addiction and depression (Felitti 1998). It is a strong check on whether childhood carries forward correctly.
- **How:** Computed from existing events, plus a population-report line comparing adult risk by ACE score.

### C6. AI companions
- **What:** Chatbot friends in his online life.
- **Why:** Heavy daily use went with more loneliness (OpenAI and MIT 2025). It is a very current part of growing up.
- **How:** A new online activity in `digital.py`, with that dose-response.

### C7. Values and life goals
- **What:** He picks goals (family, money, craft, faith, adventure) and pursues them, reaching or abandoning them.
- **Why:** Regret and pride follow goals. Today they follow events only.
- **How:** Schwartz-style values set by temperament and upbringing, plus a goal tracker in `seasons.py`.

### C8. Smaller pieces
- **Housing ladder:** renting, a mortgage, negative equity, eviction.
- **Moves within a country:** dots on the map that actually move.
- **Grandparenting:** as a weekly role, not just one moment.
- **Workplace people:** a boss, colleagues and office politics.
- **Language and culture at home:** bilingualism, festivals.
- **Climate over his lifetime:** heat and disasters that rise with the year.

---

## D. Prove it works

### D1. ★ A standing experiment set
- **What:** The same five what-ifs run on every big life: poor vs. rich, loved vs. neglected, memory off, conscience off, replay off.
- **Why:** It turns "it seems to matter" into numbers you can show.
- **How:** One button that runs all five and writes a single report.

### D2. Many small lives in parallel
- **What:** 20–50 tiny lives on the CPU with different upbringings, compared by what they say.
- **Why:** One life is an anecdote; fifty is evidence.
- **How:** Reuse the population tool with the network on, at the tiny size.

### D3. Baseline against a prompted agent
- **What:** Give an ordinary off-the-shelf chatbot the same life as a written prompt (like Park et al.'s generative agents, 2023) and compare its answers with his.
- **Why:** It shows what being *raised* adds over being *told*.
- **How:** Needs an outside model, so check with you before using an API.

### D4. Full test run, automated
- **What:** A script that runs the whole suite plus the population check and saves a report.
- **Why:** The full suite now takes hours when the CPU is shared, so it gets skipped.
- **How:** `tools/check_all.py`, run overnight.

---

## E. Interface

- **E1. ★ Compare two lives side by side:** timelines, family trees and mood curves stacked, for what-if arms or two separate lives.
- **E2. Chat with memory shown:** next to each reply, which memory he drew on and his Feel vector at that moment.
- **E3. A "how well he talks" chart:** self-answer score, probe R² and forgetting over his life, on one chart.
- **E4. A better phone view:** a scrollable feed of what he sees, with his likes and how long he lingers.
- **E5. An export pack:** life story, timeline, family tree and the experiment report as one shareable file.

---

## Suggested order

1. **C1** pronouns and **D4** test automation: quick fixes that stop recurring errors.
2. **A1** a real life, run in the background for days. Meanwhile, **B1** the feature dictionary and **A4** memory in chat.
3. **A2** the hybrid objective, tested with **D1** the standing experiments.
4. **C2** to **C5**: deeper life, each checked against the population report.
5. **E1** to **E3**: interface for comparing and watching.

Rule of thumb: anything that needs the GPU (A1, A2, D1) runs in the background while the CPU-side work (B, C, E) happens.
