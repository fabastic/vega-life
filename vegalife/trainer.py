"""A life, month by month: the world acts on him, he hears language, he faces situations, and he learns from all of it.

Each month:
  1. scheduled and live factor changes are applied, and the world advances (world.Person.step_month)
  2. if he has reached a growth milestone, the network grows (function-preserving)
  3. he trains on the language he heard that month, plus some replay of earlier months
  4. every scenario and problem that month is a GRPO update with rewards from the simulator (rlvr.py);
     the first sampled answer is the one he lives, and its effect is applied to his real state
  5. his language, problem solving and cognition are measured on the model and written back into his state
  6. in late life, neurodegeneration damages the weights and plasticity falls

Usage:  python -m vegalife.trainer runs/<name>            (the folder must contain config.json; see configs/)
        python -m vegalife.trainer runs/<name> --resume   (carry on from the last checkpoint, resume.pt)

Every few months (sim.checkpoint_months) the whole life is checkpointed: the network and its optimiser, his world,
character, friends, memories, the random generators, and how far the event and brain-map files had got. A resume
cuts those files back to that point, so a crash, a driver reset or a restart costs at most a few months.
"""
from __future__ import annotations

import collections
import contextlib
import json
import math
import os
import pickle
import random
import sys
import threading
import time
from pathlib import Path

import torch

from . import factors as fx
from . import growth
from .model import BOS, Mind, Shape, answer_weights, decode, encode, lm_loss
from .rlvr import grpo, parse_choice, score_problem, score_scenario
from . import brainmap as bmod
from .brainmap import BrainMap
from .character import Character, learning_plasticity
from .lifecore import live_choice, world_month
from .memory import Memory, fade_lines, retention
from .present import Present, problem_scene
from .scenarios import TIERS, Problem, draw, max_tier, problem_rate, render_problem, render_scenario_ex, shuffled_order
from . import proc
from .chat import Inbox, Talker
from .selftalk import SelfQuestion, score_self, self_question
from .optim import Lean, backward_step
from .people import Circle
from .speech import Speech
from .world import Person

DEFAULTS = {
    "seed": 1,
    "profile": "laptop",           # laptop | full | tiny (see growth.PROFILES)
    "max_age_years": 90,
    "factors": {},                 # key -> value in [0, 1]; anything left out is seeded
    "timeline": [],                # [{"age_years": 30, "key": "...", "value": 0.8}]
    "friends": [],                 # [{"name","joined_years","left_years","closeness","kindness","risk","studiousness","online"}]
    "friend_seed": True,           # seed friends from the friend factors when none are listed
    "family": [],                  # [{"relation","name","age_at_his_birth","closeness","dies_at_years",...}]; empty: seeded
    "seed_phrase": "",             # the words the seed was made from, if any (shown in the UI)
    "corpus_dir": "",              # optional folder of .txt he can read from school age
    "sim": {
        "speech_bytes_per_month": 40000,
        "max_items_per_month": 6,
        "group_size": 6,
        "temperature": 1.0,
        "lm_batch": 16,
        "lm_seq": 256,
        "max_lm_steps_per_month": 24,
        "replay_months": 120,
        "base_lr": 1.5e-3,
        "rl_lr_scale": 0.1,
        "answer_weight": 8.0,
        "eval_every_months": 3,
        "memory_in_prompts": True,
        "brain_map": True,
        "checkpoint_months": 6,        # how often the whole life is saved for resuming             # record what led to what (brainmap.py)     # False: he still forms memories, but they are not shown to him when he decides
    },
}


def merged(cfg: dict) -> dict:
    out = json.loads(json.dumps(DEFAULTS))
    for k, v in cfg.items():
        if k == "sim":
            out["sim"].update(v)
        else:
            out[k] = v
    return out


class _ProblemRate:
    """Lets the problem rate be analysed like a situation's rate, to see which factors set how much he practises."""
    key = "problems"

    @staticmethod
    def rate(p, F):
        return problem_rate(p, F)


class StopLife(Exception):
    """Raised inside a month when a stop has been asked for, so the life ends within seconds, not at month's end."""


class Control(threading.Thread):
    """Watches the run folder so Stop and Kill work in seconds even in the middle of a long training step.

    A `STOP` file asks the life to stop at the next safe point (it checks between learning steps and between
    situations, then saves). A `KILL` file ends the process at once from this thread, without waiting for the main
    thread, which may be deep inside a long GPU step."""

    def __init__(self, run_dir: Path, stop: threading.Event):
        super().__init__(daemon=True, name="control")
        self.dir, self.stop = run_dir, stop

    def run(self) -> None:
        while True:
            if (self.dir / "KILL").exists():
                try:
                    live = self.dir / "live.json"
                    data = json.loads(live.read_text(encoding="utf-8"))
                    data["status"] = "killed"
                    tmp = live.with_suffix(".tmp")
                    tmp.write_text(json.dumps(data), encoding="utf-8")
                    tmp.replace(live)
                except (OSError, ValueError):
                    pass
                os._exit(137)
            if (self.dir / "STOP").exists():
                self.stop.set()
            time.sleep(0.3)


def write_json(path: Path, data) -> bool:
    """Writes a status file atomically. On Windows the replace fails while another process (the UI server) has the
    file open for a moment, so it retries; and it never raises, because a status file must not end a life."""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        return False
    for attempt in range(40):
        try:
            tmp.replace(path)
            return True
        except PermissionError:
            time.sleep(0.025 * (1 + attempt % 4))
        except OSError:
            break
    return False


class Life:
    def __init__(self, run_dir: Path, resume: bool = False):
        self.dir = run_dir
        self.cfg = merged(json.loads((run_dir / "config.json").read_text(encoding="utf-8-sig")))
        ck = self._load_checkpoint() if resume else None          # also cuts the log files back to that point
        sim = self.cfg["sim"]
        self.sim = sim
        seed = int(self.cfg["seed"])
        self.F = fx.sample(seed, self.cfg["factors"], self.cfg["timeline"])
        self.circle = Circle(self.F, seed, self.cfg["friends"], bool(self.cfg["friend_seed"]))
        self.p = Person(self.F, seed, self.circle, self.cfg["family"] or None)
        self.character = Character(self.p, self.F)      # personality, sleep, mood, and how outcomes are felt
        self.chosen = collections.Counter()              # (situation, choice) -> times lived, for the novelty pull
        corpus = Path(self.cfg["corpus_dir"]) if self.cfg["corpus_dir"] else None
        self.speech = Speech(self.F, seed, corpus)
        self.r = random.Random(seed * 999 + 1)
        self.cap = growth.PROFILES[self.cfg["profile"]]
        self.lean = self.cfg["profile"] in growth.LEAN
        want = os.environ.get("VEGA_DEVICE", "")                  # e.g. VEGA_DEVICE=cpu to leave the GPU to another life
        self.device = torch.device(want or ("cuda" if torch.cuda.is_available() else "cpu"))
        torch.manual_seed(seed)
        self.gen = torch.Generator().manual_seed(seed)
        self.model = Mind(growth.target_shape(0.0, 0.0, self.cap, 512))
        if self.lean:                          # bf16 weights, lean optimiser, recomputed blocks
            self.model = self.model.to(torch.bfloat16)
        self.model = self.model.to(self.device)
        self.model.checkpointing = self.lean
        self._optimizer()
        self.amp = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if self.device.type == "cuda" and not self.lean \
            else contextlib.nullcontext
        self.mem = Memory(self.F, seed)
        self.speech.mem = self.mem
        self.mem.state = self.p.s                           # neuroticism tempers how vivid and intrusive memories are
        self.present = Present(self.F, seed, self.speech.kin)
        self.speech.present = self.present
        self.lessons = collections.deque(maxlen=int(sim["replay_months"]))     # skills: replayed as they were
        self.life_months = []                                                  # (age, bytes): ordinary life; it fades
        eval_speech = Speech(self.F, seed + 10_000)
        self.eval_text = encode("\n".join(eval_speech._caregiver(self.p, self.F) for _ in range(150))
                                + "\n" + "\n".join(eval_speech._school(self.p, self.F) for _ in range(80)))
        self.best_eval = float("inf")
        self.ps_ema = 0.0
        self.tier_ema = [0.0] * len(TIERS)         # pass rate per problem tier, over his sampled groups
        self.tier_n = [0] * len(TIERS)
        self.curves = {"lm_loss": [], "eval_loss": [], "reward": [], "wellbeing": [], "params": [],
                       "informative": [], "distinct": [], "problem_solving": [], "language": []}
        self.items = collections.deque(maxlen=40)
        self.log = collections.deque(maxlen=80)
        self.babble = ""
        self.heard = ""
        self.interventions_seen = 0
        self.started = time.time()
        self.events_f = open(run_dir / "events.jsonl", "a", encoding="utf-8")
        self.brain = BrainMap(run_dir) if sim["brain_map"] else None
        if self.brain is not None and ck is None:
            bmod.backbone(self.brain)
        self.stop = threading.Event()
        Control(run_dir, self.stop).start()
        self.inbox = Inbox(run_dir)                         # people talking to him from the UI (chat.py)
        self._talker = None
        if ck is None:
            self.say(f"born. network: {self._shape_text()}")
        else:
            self._restore(ck)
            self.say(f"resumed from the checkpoint at {self.p.years:.2f} years. network: {self._shape_text()}")

    # ------------------------------------------------------------------ helpers
    def _shape_text(self) -> str:
        c = self.model.config()
        return f"{c['params'] / 1e6:.2f}M params, {c['layers']} layers, width {c['d']}, {c['heads']} heads"

    def _groups(self) -> list:
        """One optimiser group per layer, so each can have its own critical period (growth.plasticity)."""
        groups = [{"params": [p for p in b.parameters() if p.requires_grad], "block": i, "scale": 1.0}
                  for i, b in enumerate(self.model.blocks)]
        groups.append({"params": [self.model.emb.weight], "block": "emb", "scale": 1.0})
        groups.append({"params": list(self.model.norm.parameters()), "block": "norm", "scale": 1.0})
        return [g for g in groups if g["params"]]

    def _optimizer(self):
        if self.lean:
            opt = Lean(self._groups(), self.sim["base_lr"])
        else:
            opt = torch.optim.AdamW(self._groups(), lr=self.sim["base_lr"], betas=(0.9, 0.95), weight_decay=0.05)
        self.opt = opt
        self.consolidate(freeze=False)        # scales only: freezing (and recording it) is the monthly step
        return opt

    def lr(self) -> float:
        y, s = self.p.years, self.p.s
        size = math.sqrt(128 / self.model.shape.d)               # smaller steps for a bigger network
        plastic = learning_plasticity(y)                          # strong to ~17, then slowing (character.py)
        sleep = 0.6 + 0.4 * s["sleep"]                            # poor sleep impairs taking in new things
        return self.sim["base_lr"] * size * plastic * sleep * (1 - 0.7 * s["neurodegeneration"])

    def check_stop(self) -> None:
        if self.inbox.waiting():
            self.serve_chat()
        if self.stop.is_set():
            raise StopLife()

    def serve_chat(self) -> None:
        """Answer anyone talking to him, with his live network, between learning steps. It uses its own random
        generators and never trains him, so talking to him does not change his life."""
        if self._talker is None:
            chat_r = random.Random(int(self.cfg["seed"]) * 17 + 5)
            now = lambda: self.present.moment(self.p, self.F, chat_r, "talk", keep=False).line()
            self._talker = Talker(self.model, self.device, self.amp, self.speech.name, self.mem, now, self.p.age,
                                  int(self.cfg["seed"]), thought=lambda: self.p.conscious.line())
        self._talker.model, self._talker.mem, self._talker.age = self.model, self.mem, self.p.age
        try:
            self.inbox.serve(lambda: self._talker, "live")
        except Exception as e:                       # a failed reply must never end a life
            with open(self.dir / "chat_out.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": "error", "error": repr(e)[:300], "t": time.time()}) + "\n")

    def say(self, text: str) -> None:
        self.log.append({"age": round(self.p.years, 2), "text": text})
        self.events_f.write(json.dumps({"age": round(self.p.years, 3), "event": text}) + "\n")

    def set_lr(self, lr: float) -> None:
        for g in self.opt.param_groups:
            g["lr"] = lr * g.get("scale", 1.0)

    def consolidate(self, record: bool = True, freeze: bool = True) -> None:
        """Critical periods: each layer's learning rate follows its own window (open when it forms, then down to a
        tenth), and in adulthood a closed layer is frozen and its weakest connections pruned. The top layer is never
        frozen, so a network capped before it grows executive layers can still learn."""
        blocks = list(self.model.blocks)
        y = self.p.years
        kinds = {k: [b for b in blocks if b.kind == k] for k in ("core", "assoc", "exec")}
        for g in self.opt.param_groups:
            i = g.get("block")
            if i == "emb":
                g["scale"] = growth.embedding_plasticity(y)
                continue
            if not isinstance(i, int) or i >= len(blocks):
                continue
            b = blocks[i]
            same = kinds[b.kind]
            rel = same.index(b) / max(1, len(same) - 1)
            scale, frozen = growth.plasticity(y, b.kind, b.born, rel)
            g["scale"] = scale
            if freeze and frozen and not b.frozen and i < len(blocks) - 1:
                self.freeze(i, b, record)

    def freeze(self, i: int, b, record: bool = True) -> None:
        b.frozen = True
        params = list(b.parameters())
        pruned = self.model.prune(b, 0.05)
        for p in params:
            p.requires_grad_(False)
            p.grad = None
        if self.lean:
            self.opt.forget(params)
        else:
            for p in params:
                self.opt.state.pop(p, None)
        if not record:
            return
        self.say(f"critical period closes: layer {i + 1} ({b.kind}, formed at {b.born:.1f}) is frozen, "
                 f"{pruned:,} weak connections pruned")
        if self.brain is not None:
            age = self.p.age
            nid = self.brain.node(f"milestone:freeze:{i}:{age}", "milestone", f"layer {i + 1} hardens ({b.kind})", age,
                                  layer=i + 1, layer_kind=b.kind, formed_years=round(b.born, 2), pruned=pruned)
            self.brain.edge(bmod.SELF, nid, "his network hardened", 1.0, age)
            bmod.during(self.brain, nid, age)

    # ------------------------------------------------------------------ steps
    def grow_if_due(self) -> None:
        d = growth.delay(self.p.s["allostatic_load"], self.p.s["attachment"])
        target = growth.target_shape(self.p.years, d, self.cap, 512)
        if target.d > self.model.shape.d or target.layers > self.model.shape.layers:
            if self.lean:
                self.opt.close()                 # frees its state and hooks before the parameters are replaced
            y = self.p.years
            sched = y - d                          # a delayed milestone keeps the kind of layer it was due to make
            done = self.model.grow(target, at_top=growth.grows_on_top(sched), born=y, kind=growth.block_kind(sched))
            self._optimizer()
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
            self.say(f"brain grows ({', '.join(done)}): {self._shape_text()}")
            if self.brain is not None:
                mid = self.brain.node(f"milestone:grow:{self.p.age}", "milestone", f"brain grows to {self.model.n_params() / 1e6:.0f}M",
                                      self.p.age, params=self.model.n_params(), delay_years=round(d, 2))
                if d > 0.05:
                    self.brain.edge(self.brain.state("allostatic_load"), mid, "delayed", -d, self.p.age)
                self.brain.edge(bmod.SELF, mid, "his network grew", 1.0, self.p.age)
                bmod.during(self.brain, mid, self.p.age)

    def learn_language(self, lessons: list, life: list) -> float:
        data = encode("\n".join(lessons + life))
        # Lessons are skills: they are replayed whole. Ordinary life is replayed the way memory keeps it: older
        # months less often, with lines missing and the rest cut short (memory.fade_lines).
        self.lessons.append(encode("\n".join(lessons)))
        self.life_months.append((self.p.age, "\n".join(life).encode("utf-8", errors="replace")))
        pool = list(data)
        chunk = len(data) // 5
        if len(self.lessons) > 1:
            for old in self.r.sample(list(self.lessons)[:-1], min(2, len(self.lessons) - 1)):
                pool += old[:chunk]
        if len(self.life_months) > 1:
            past = self.life_months[:-1]
            keeps = [retention(self.p.age - a, self.p.s, self.F) for a, _ in past]
            for i in self.r.choices(range(len(past)), keeps, k=min(2, len(past))):
                lines = past[i][1].decode("utf-8", errors="replace").split("\n")
                faded = fade_lines(lines, keeps[i], self.r)
                pool += encode("\n".join(faded))[:chunk]
        B, T = self.sim["lm_batch"], self.sim["lm_seq"]
        if len(pool) < T + 2:
            return float("nan")
        # Adults take in less new material than children: fewer learning steps after 30, which also keeps late
        # life affordable with a large network.
        y = self.p.years
        adult = 1.0 if y < 30 else max(0.25, 1.0 - (y - 30) / 80)
        steps = max(1, min(int(int(self.sim["max_lm_steps_per_month"]) * adult), len(pool) // (B * T)))
        buf = torch.tensor(pool, dtype=torch.long)
        wbuf = torch.tensor(answer_weights(pool, float(self.sim["answer_weight"])))
        losses = []
        self.model.train()
        self.set_lr(self.lr())
        for _ in range(steps):
            self.check_stop()
            ix = torch.randint(0, len(buf) - T - 1, (B,), generator=self.gen)
            x = torch.stack([buf[i: i + T] for i in ix]).to(self.device)
            y = torch.stack([buf[i + 1: i + T + 1] for i in ix]).to(self.device)
            w = torch.stack([wbuf[i + 1: i + T + 1] for i in ix]).to(self.device)
            with self.amp():
                loss = lm_loss(self.model, x, y, w)
            backward_step(self.opt, self.model, loss)
            losses.append(float(loss))
        return sum(losses) / len(losses)

    def mastered(self, i: int) -> bool:
        return self.tier_n[i] >= 8 and self.tier_ema[i] >= 0.6

    def pick_tier(self) -> int:
        """Teach at the edge of what he can do: mostly the first tier he has not mastered, sometimes one easier
        (to keep it) or one harder (to stretch). He still meets harder material in school, in worked examples."""
        top = max_tier(self.p)
        frontier = next((i for i in range(len(TIERS)) if not self.mastered(i)), len(TIERS) - 1)
        frontier = min(frontier, top)
        u = self.r.random()
        if u < 0.5:
            tier = frontier
        elif u < 0.65:
            tier = frontier - 1
        elif u < 0.75:
            tier = frontier + 1
        else:                                  # review of anything already learned: skills are lost if not used
            tier = self.r.randint(0, frontier)
        return max(0, min(tier, top))

    def face(self, item) -> dict:
        self.check_stop()
        k, temp = int(self.sim["group_size"]), float(self.sim["temperature"])
        self.set_lr(self.lr() * self.sim["rl_lr_scale"])
        before = self.p.wellbeing()
        # The learning group keeps a fixed spread; the answer he lives is drawn at a temperature his state sets.
        lived_temp = self.character.decision_temperature(self.p, temp)
        if isinstance(item, SelfQuestion):           # knowing his own life: rewarded only if the number is right
            texts, rewards, _, lived, lived_r = grpo(self.model, self.opt, item.prompt, lambda t: score_self(item, t), k,
                                                     12, temp, self.device, self.amp, lived_temperature=lived_temp)
            rec = {"kind": "self", "key": item.key, "prompt": item.prompt, "answer": item.answer, "responses": texts,
                   "rewards": rewards, "lived": lived, "lived_reward": lived_r,
                   "outcome": "right" if lived_r == 1.0 else "wrong"}
        elif isinstance(item, Problem):
            now = self.present.moment(self.p, self.F, self.r, problem_scene(self.p)).line()
            prompt = render_problem(item, self.p, now)
            texts, rewards, _, lived, lived_r = grpo(self.model, self.opt, prompt, lambda t: score_problem(item, t), k, 8,
                                                     temp, self.device, self.amp, lived_temperature=lived_temp)
            correct = lived_r == 1.0
            self.ps_ema += 0.05 * (float(correct) - self.ps_ema)
            rate = sum(1 for x in rewards if x == 1.0) / len(rewards)
            was = self.mastered(item.tier)
            self.tier_n[item.tier] += 1
            self.tier_ema[item.tier] += max(0.1, 1 / self.tier_n[item.tier]) * (rate - self.tier_ema[item.tier])
            if self.brain is not None and self.mastered(item.tier) != was:
                self.record_skill(item.tier, self.mastered(item.tier))
            rec = {"kind": "problem", "key": item.key, "tier": item.tier, "prompt": prompt, "answer": item.answer, "responses": texts,
                   "rewards": rewards, "lived": lived, "lived_reward": lived_r,
                   "outcome": "right" if correct else "wrong"}
        else:
            use_mem = self.mem if self.sim["memory_in_prompts"] else None
            now = self.present.moment(self.p, self.F, self.r, item.key).line()
            order = shuffled_order(item, self.r)                 # letters mean nothing; he has to read the options
            prompt, sit, recs = render_scenario_ex(item, self.p, self.F, self.r, use_mem, rehearse=True, now=now,
                                                   order=order)
            pick = lambda t: (lambda i: order[i] if 0 <= i < len(order) else -1)(parse_choice(t))
            sc_r = random.Random(self.r.random())
            # He learns from outcomes as he feels them (loss aversion, present bias, a pull toward the untried)...
            def felt(t):                             # as he feels it, and as his conscience weighs it
                c_ = pick(t)
                f = score_scenario(item, self.p, self.F, c_, sc_r, character=self.character,
                                   novelty=lambda c: self.novelty(item.key, c))
                return f if c_ < 0 else max(-1.0, min(1.0, f + self.p.conscious.weigh(self.p, self.F, item.choices[c_].text)))
            texts, rewards, _, lived, lived_r = grpo(self.model, self.opt, prompt, felt, k, 4, temp, self.device, self.amp,
                                                     lived_temperature=lived_temp)
            choice = pick(lived)
            c = item.choices[choice] if choice >= 0 else None
            # ...while what actually happens, now and later, is the real outcome.
            real = score_scenario(item, self.p, self.F, choice, random.Random(self.r.random())) if c else None
            if c is not None:
                self.chosen[(item.key, choice)] += 1
                lived_out = live_choice(self, item, sit, choice, lived_r, real, recs, lived)
                deltas, brain_id = lived_out["deltas"], lived_out["choice_id"]
            else:
                deltas = {"anxiety": 0.01}                    # no valid answer: he froze
                self.p.apply(deltas, fades=True)
                brain_id = self.record_froze(item, sit) if self.brain is not None else None
            rec = {"kind": "scenario", "key": item.key, "domain": item.domain, "prompt": prompt, "responses": texts,
                   "rewards": rewards, "lived": lived, "lived_reward": lived_r,
                   "real_outcome": None if real is None else round(real, 3),
                   "later": {"deltas": c.later, "months": c.delay} if c is not None and c.later else None,
                   "choice": c.text if c is not None else "(no valid answer: froze)",
                   "outcome": {k: round(v, 3) for k, v in deltas.items()}, "memory": [x.text for x in recs],
                   "brain_id": brain_id}
        rec["distinct"] = len(set(rec["responses"])) / len(rec["responses"])
        rec["informative"] = float(max(rec["rewards"]) - min(rec["rewards"]) > 1e-6)
        rec["age"] = round(self.p.years, 2)
        rec["wellbeing_change"] = round(self.p.wellbeing() - before, 4)
        self.items.append(rec)
        self.events_f.write(json.dumps(rec) + "\n")
        return rec

    def record_froze(self, item, sit: str) -> str:
        """He gave no usable answer (mostly an infant who cannot yet say A-D). It still frightened him a little, and
        the map should say where that came from."""
        bm, age = self.brain, self.p.age
        bmod.situation_drivers(bm, item, self.p, self.F, age)
        cid = bm.next_id("choice", age)
        bm.node(cid, "choice", f"{item.key.replace('_', ' ')}: froze, no answer", age, situation=sit[:200], froze=True)
        bm.edge(bm.situation(item.key, sit), cid, "faced", 1.0, age)
        bm.edge(cid, bm.state("anxiety"), "changed", 0.01, age)
        bmod.during(bm, cid, age)
        return cid

    def record_skill(self, tier: int, gained: bool) -> None:
        """A skill tier mastered or lost: practice (and what set how much of it he got) led there."""
        bm, age = self.brain, self.p.age
        practice = bm.situation("problems", "problems put to him at school, at home and at work")
        if not bm.counter[("drivers", "problems", bmod.STAGE_OF(age))]:
            bmod.situation_drivers(bm, _ProblemRate(), self.p, self.F, age)
        name = TIERS[tier][1].replace("_", " ")
        sid = bm.node(f"skill:{tier}:{'gained' if gained else 'lost'}:{age}", "skill",
                      f"{'masters' if gained else 'loses'} {name}", age, tier=tier, pass_rate=round(self.tier_ema[tier], 3))
        bm.edge(practice, sid, "practised into" if gained else "too little practice", 1.0 if gained else -1.0, age)
        bm.edge(sid, bm.state("problem_solving"), "raises" if gained else "lowers", 1.0 / len(TIERS), age)
        bmod.during(bm, sid, age)

    def novelty(self, key: str, choice: int) -> float:
        """A pull toward choices he has rarely made in this kind of situation, scaled by openness and age."""
        return 0.15 * self.character.curiosity(self.p) / math.sqrt(1 + self.chosen[(key, choice)])

    @torch.no_grad()
    def measure(self) -> None:
        self.model.eval()
        T = self.model.shape.ctx
        data = torch.tensor(self.eval_text, dtype=torch.long)
        n = (len(data) - 1) // T
        x = data[: n * T].view(n, T).to(self.device)
        y = data[1: n * T + 1].view(n, T).to(self.device)
        with self.amp():
            loss = float(lm_loss(self.model, x, y))
        self.best_eval = min(self.best_eval, loss)
        s = self.p.s
        s["language"] = max(0.0, min(1.0, 1 - loss / math.log(259)))
        s["problem_solving"] = sum(self.mastered(i) for i in range(len(TIERS))) / len(TIERS)
        s["cognition"] = max(0.0, min(1.0, self.best_eval / loss))
        self.curves["eval_loss"].append([round(self.p.years, 2), round(loss, 4)])
        self.curves["problem_solving"].append([round(self.p.years, 2), round(s["problem_solving"], 4)])
        self.curves["language"].append([round(self.p.years, 2), round(s["language"], 4)])
        # What he says is sampled from the moment he is in, so his words can be about now.
        head = f"{self.present.moment(self.p, self.F, self.r, keep=False).line()}\n{self.speech.name}:"
        toks = torch.tensor([[BOS] + encode(head)], device=self.device)
        with self.amp():
            gen, n_ = self.model.generate(toks, 80, 0.8, stop=(258,))
        self.babble = decode(gen[0, : int(n_[0])].tolist())

    def check_interventions(self) -> bool:
        path = self.dir / "interventions.jsonl"
        if self.stop.is_set():
            return False
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines[self.interventions_seen:]:
                try:
                    it = json.loads(line)
                    if "friend" in it:
                        d = dict(it["friend"])
                        d["joined_years"] = self.p.years
                        f = self.circle.add(d, seeded=False)
                        self.say(f"intervention: {f.name} becomes his friend")
                        continue
                    self.F.set(it["key"], float(it["value"]), "live")
                    self.say(f"intervention: {fx.ALL[it['key']].label} = {float(it['value']):.2f}")
                except (ValueError, KeyError) as e:
                    self.say(f"ignored intervention {line!r}: {e}")
            self.interventions_seen = len(lines)
        return True

    # ------------------------------------------------------------------ the month and the life
    def month(self) -> None:
        for change in self.F.apply_timeline(self.p.age):
            self.say(f"scheduled: {change}")
        events = world_month(self)                            # the world acts; memory, present and brain map follow
        if not self.p.alive:
            return
        self.grow_if_due()
        self.consolidate()
        budget = self.speech.budget(self.p, self.F, int(self.sim["speech_bytes_per_month"]))
        lessons, life = self.speech.month_parts(self.p, self.F, events, budget, self.pick_tier)
        self.heard = "\n".join(life)[:400]
        loss = self.learn_language(lessons, life)
        rewards, distinct, informative = [], [], []
        items = draw(self.p, self.F, self.r, int(self.sim["max_items_per_month"]), self.pick_tier)
        if self.p.years >= 3 and self.r.random() < 0.5:   # a question about himself with a checkable answer
            items.append(self_question(self.p, self.F, self.present, self.speech.name, self.r))
        for item in items:
            rec = self.face(item)
            rewards.append(rec["lived_reward"])
            distinct.append(rec["distinct"])
            informative.append(rec["informative"])
        if self.p.s["neurodegeneration"] > 0.02 and self.p.age % 3 == 0:
            self.model.degrade(self.p.s["neurodegeneration"], self.gen)
        if self.p.age % int(self.sim["eval_every_months"]) == 0:
            self.measure()
        y = round(self.p.years, 2)
        if loss == loss:
            self.curves["lm_loss"].append([y, round(loss, 4)])
        if rewards:
            self.curves["reward"].append([y, round(sum(rewards) / len(rewards), 4)])
            self.curves["informative"].append([y, round(sum(informative) / len(informative), 3)])
            self.curves["distinct"].append([y, round(sum(distinct) / len(distinct), 3)])
        self.curves["wellbeing"].append([y, round(self.p.wellbeing(), 4)])
        self.curves["params"].append([y, self.model.n_params()])

    def live(self, status: str) -> None:
        write_json(self.dir / "live.json", {
            "status": status, "age_months": self.p.age, "age_years": round(self.p.years, 2), "stage": self.p.stage,
            "stage_label": fx.STAGE_LABEL[self.p.stage], "alive": self.p.alive, "cause_of_death": self.p.cause_of_death,
            "wellbeing": round(self.p.wellbeing(), 4), "state": self.p.snapshot(), "factors": self.F.to_json(),
            "model": self.model.config(), "profile": self.cfg["profile"], "cap": self.cap,
            "schedule": growth.describe(self.cap), "curves": {k: v[-600:] for k, v in self.curves.items()},
            "items": list(self.items)[-25:], "log": list(self.log)[-60:], "babble": self.babble, "heard": self.heard,
            "kin": self.speech.kin, "seed": self.cfg["seed"], "elapsed_s": round(time.time() - self.started),
            "device": str(self.device),
            "optimizer": "lean bf16 (checkpointed)" if self.lean else "AdamW fp32",
            "gpu_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if self.device.type == "cuda" else 0,
            "pid": os.getpid(),
            "friends": self.circle.to_json(self.p.age),
            "family": self.p.family.to_json(self.p.age),
            "work": self.p.work.to_json(),
            "mind": self.p.conscious.to_json(),
            "schooling": self.p.school.to_json(),
            "mental": self.p.mind.to_json(self.p.age),
            "online": self.p.online.to_json(),
            "bonds": self.p.bonds.to_json(),
            "prejudice": self.p.prejudice.to_json(),
            "seasons": self.p.seasons.to_json(self.p, self.F),
            "illness": self.p.illness.to_json(self.p),
            "hormones": self.p.hormones.to_json(),
            "hardships": self.p.hardships.to_json(),
            "memory": self.mem.summary(self.p.age),
            "brain": self.brain.stats() if self.brain is not None else None,
            "now": self.present.last.to_json() if self.present.last else None,
            "school": {"studying": self.p.s["schooling"] > 0.5, "belonging": round(self.p.s["school_belonging"], 3),
                       "academic": round(self.p.s["academic"], 3), "credential": self.p.s["credential"],
                       "effectiveness": round(fx.school_effectiveness(self.F), 3)},
            "tiers": [{"name": k, "min_age": a, "pass_rate": round(self.tier_ema[i], 3), "tried": self.tier_n[i],
                       "mastered": self.mastered(i)} for i, (a, k) in enumerate(TIERS)],
        })

    # ------------------------------------------------------------------ checkpoint and resume
    PY_STATE = ("F", "circle", "p", "character", "chosen", "speech", "r", "mem", "present", "lessons", "life_months",
                "best_eval", "ps_ema", "tier_ema", "tier_n", "curves", "items", "log", "babble", "heard",
                "interventions_seen")
    BRAIN_STATE = ("nodes", "out", "inn", "counter", "pending_estimates", "pending_counts", "pending_scale")
    LOGS = ("events.jsonl", "brain_nodes.jsonl", "brain_edges.jsonl")

    def checkpoint(self) -> None:
        """Everything needed to carry on from this month, written atomically to resume.pt."""
        self.events_f.flush()
        if self.brain is not None:
            self.brain.flush()
        names = {p: n for n, p in self.model.named_parameters()}
        py = {k: getattr(self, k) for k in self.PY_STATE}
        if self.brain is not None:
            py["brain"] = {k: getattr(self.brain, k) for k in self.BRAIN_STATE}
        blob = {
            "version": 1, "age": self.p.age, "elapsed": time.time() - self.started,
            "shape": self.model.config(), "model": self.model.state_dict(),
            "blocks": [{"born": b.born, "kind": b.kind, "frozen": b.frozen} for b in self.model.blocks],
            "eps": [m.eps for m in self.model.modules() if hasattr(m, "eps")],
            "opt": {"t": getattr(self.opt, "t", 0),
                    "state": {names[p]: dict(st) for p, st in self.opt.state.items() if p in names}},
            "py": pickle.dumps(py, protocol=pickle.HIGHEST_PROTOCOL),
            "rng": {"torch": torch.get_rng_state(), "gen": self.gen.get_state(),
                    "cuda": torch.cuda.get_rng_state_all() if self.device.type == "cuda" else None},
            "offsets": {n: (self.dir / n).stat().st_size for n in self.LOGS if (self.dir / n).exists()},
        }
        tmp = self.dir / "resume.tmp"
        torch.save(blob, tmp)
        for attempt in range(40):
            try:
                tmp.replace(self.dir / "resume.pt")
                return
            except PermissionError:
                time.sleep(0.05)

    def _load_checkpoint(self) -> dict:
        path = self.dir / "resume.pt"
        if not path.exists():
            raise FileNotFoundError(f"{self.dir.name} has no checkpoint to resume from (resume.pt)")
        ck = torch.load(path, map_location="cpu", weights_only=False)
        for name, size in ck["offsets"].items():                  # forget what was written after the checkpoint
            f = self.dir / name
            if f.exists() and f.stat().st_size > size:
                with open(f, "r+b") as fh:
                    fh.truncate(size)
        return ck

    def _restore(self, ck: dict) -> None:
        py = pickle.loads(ck["py"])
        brain = py.pop("brain", None)
        for k, v in py.items():
            setattr(self, k, v)
        self.p.upgrade(self.F, int(self.cfg["seed"]))          # a checkpoint from older code gains what is new
        if self.brain is not None and brain is not None:
            for k, v in brain.items():
                setattr(self.brain, k, v)
        sh = ck["shape"]
        model = Mind(Shape(sh["d"], sh["layers"], sh["ctx"]))
        for b, meta in zip(model.blocks, ck["blocks"]):
            b.born, b.kind, b.frozen = meta["born"], meta["kind"], meta["frozen"]
        for m, eps in zip([m for m in model.modules() if hasattr(m, "eps")], ck["eps"]):
            m.eps = eps
        if self.lean:
            model = model.to(torch.bfloat16)
        model.load_state_dict(ck["model"])
        for b in model.blocks:
            for p in b.parameters():
                p.requires_grad_(not b.frozen)
        self.model = model.to(self.device)
        self.model.checkpointing = self.lean
        if self.lean and hasattr(self.opt, "close"):
            self.opt.close()
        self._optimizer()
        params = dict(self.model.named_parameters())
        for name, st in ck["opt"]["state"].items():
            p = params.get(name)
            if p is not None and p.requires_grad:
                self.opt.state[p] = {k: (v.to(p.device) if torch.is_tensor(v) and v.dim() > 0 else v) for k, v in st.items()}
        if hasattr(self.opt, "t"):
            self.opt.t = ck["opt"]["t"]
        torch.set_rng_state(ck["rng"]["torch"])
        self.gen.set_state(ck["rng"]["gen"])
        if ck["rng"]["cuda"] is not None and self.device.type == "cuda":
            torch.cuda.set_rng_state_all(ck["rng"]["cuda"])
        self.started = time.time() - ck["elapsed"]

    def save(self) -> None:
        torch.save({"shape": self.model.config(), "model": self.model.state_dict(), "state": self.p.s,
                    "age": self.p.age}, self.dir / "mind.pt")

    def run(self) -> None:
        self.live("running")
        max_m = int(self.cfg["max_age_years"] * 12)
        try:
            while self.p.alive and self.p.age < max_m:
                if not self.check_interventions():
                    break
                if self.inbox.waiting():
                    self.serve_chat()
                self.month()
                if self.brain is not None:
                    self.brain.flush()
                self.live("running")
                if self.p.age % 120 == 0 or not self.p.alive:
                    write_json(self.dir / "memory.json", self.mem.dump())
                    self.save()
                if self.p.alive and self.p.age % int(self.sim["checkpoint_months"]) == 0:
                    self.checkpoint()
        except StopLife:
            pass
        if self.stop.is_set():
            self.say("stopped by user")
            self.live("stopping")                     # shown at once; the save below can take a few seconds
        self.save()
        write_json(self.dir / "memory.json", self.mem.dump())
        if self.stop.is_set() and self.p.alive:
            self.checkpoint()                         # a stopped life can be resumed from exactly here
        if self.brain is not None:
            bmod.flush_estimates(self.brain, self.p.age)
            self.brain.close()
        self.live("finished" if not self.p.alive or self.p.age >= max_m else "stopped")
        self.events_f.close()


def main() -> None:
    run_dir = Path(sys.argv[1])
    for stale in ("STOP", "KILL"):                                    # left over from an earlier run in this folder
        (run_dir / stale).unlink(missing_ok=True)
    proc.write_pidfile(run_dir)                                          # so the UI can tell it is alive, and end it
    proc.keep_awake()                                                    # vega-7 died when the laptop went to sleep
    Life(run_dir, resume="--resume" in sys.argv[2:]).run()


if __name__ == "__main__":
    main()
