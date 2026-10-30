"""Talking with him, in his own words.

He answers with his own network, not another model. Each reply is sampled from a prompt in the same shape as
everything he has learned from: the moment he is in, one memory that the conversation brings back (as he remembers
it now: faded, sometimes wrong), the conversation so far, then his name. So what he says comes from the life he lived,
and he can only speak as well as he has learned to.

Talking does not change his life: it uses its own random generators and never trains him.

Two ways to reach him:
  * a running life answers between its own learning steps (trainer.Life.serve_chat), with the live network
  * a life that is not running is woken by a small worker that loads its last checkpoint:
        python -m vegalife.chat runs/<name>
    (resume.pt when there is one; otherwise the older mind.pt with memory.json). It exits after 10 idle minutes.

Messages go through two files in the run folder: chat_in.jsonl (from the UI) and chat_out.jsonl (his replies).
"""
from __future__ import annotations

import json
import os
import pickle
import random
import re
import sys
import time
from dataclasses import fields
from pathlib import Path
from typing import Callable, List, Optional

import torch

from .model import BOS, Mind, Shape, decode, encode

WORD = re.compile(r"[a-z']+")
QUIET = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "is", "are", "was", "were", "you", "your", "i",
         "me", "my", "do", "did", "does", "it", "that", "this", "what", "how", "why", "when", "who", "with", "for",
         "be", "have", "has", "had", "about", "tell", "so", "can", "could", "would", "there", "they", "he", "she"}
MAX_NEW = 160
CANDIDATES = 6                    # he says it a few ways in his head and goes with the one that comes most easily
FRESH_S = 180                     # a message older than this, unanswered when a life (re)starts, is left alone


def words(text: str) -> set:
    return set(WORD.findall(text.lower())) - QUIET


def pick_memory(mem, talk: str):
    """The memory this conversation brings back: the one sharing most words with it, the stronger the likelier.
    No randomness, and recalling it here does not strengthen or rewrite it."""
    if mem is None or not mem.episodes:
        return None
    want = words(talk)
    if not want:
        return None
    best, score = None, 0.0
    for ep in mem.episodes:
        have = words(" ".join([ep.what, ep.did_text, ep.key.replace("_", " "), ep.feeling] + list(ep.who)))
        s = len(want & have) * (0.5 + ep.strength)
        if s > score:
            best, score = ep, s
    return best


def build_prompt(now: str, name: str, history: List[dict], message: str, memory: Optional[str],
                 ctx: int = 512, max_new: int = MAX_NEW, thought: str = "") -> str:
    head = now + "\n" + (thought + "\n" if thought else "") + (f"Memory: {memory}\n" if memory else "")
    tail = f"You: {message}\n{name}:"
    turns = [f"{'You' if h['who'] == 'you' else name}: {h['text']}" for h in history[-8:]]
    while True:
        prompt = head + "".join(t + "\n" for t in turns) + tail
        if len(encode(prompt)) + 1 <= ctx - max_new or not turns:
            return prompt
        turns.pop(0)                                       # the oldest part of the conversation drops out first


class Talker:
    def __init__(self, model: Mind, device, amp, name: str, mem, now: Callable[[], str], age_months: int, seed: int = 0,
                 thought: Optional[Callable[[], str]] = None):
        self.model, self.device, self.amp, self.name, self.mem, self.now = model, device, amp, name, mem, now
        self.thought = thought or (lambda: "")
        self.age = age_months
        self.gen = torch.Generator(device=device).manual_seed(seed * 31 + 7)

    @torch.no_grad()
    def reply(self, message: str, history: List[dict]) -> dict:
        talk = " ".join([h["text"] for h in history[-2:]] + [message])
        ep = pick_memory(self.mem, talk)
        memory = self.mem.render(ep)[:110] if ep is not None else None
        thought = self.thought()
        prompt = build_prompt(self.now(), self.name, history, message, memory, self.model.shape.ctx, thought=thought)
        was = self.model.training
        self.model.eval()
        toks = torch.tensor([[BOS] + encode(prompt)] * CANDIDATES, device=self.device)
        with self.amp():
            out, n = self.model.generate(toks, MAX_NEW, 0.7, generator=self.gen)
            best = self._most_fluent(toks, out, n)
        if was:
            self.model.train()
        text = decode(out[best, : int(n[best])].tolist()).strip()
        return {"reply": text or "...", "memory": memory, "thought": thought[9:] if thought else None, "memory_id": f"mem:{ep.id}" if ep is not None else None,
                "age_years": round(self.age / 12, 2), "prompt": prompt}


    @torch.no_grad()
    def _most_fluent(self, idx, gen, lengths) -> int:
        """Which candidate his own network finds most natural: highest mean log-probability per byte, less for
        bytes that are not words or punctuation, and for answers that are empty. Still entirely his own words."""
        full = torch.cat([idx, gen], 1)[:, -self.model.shape.ctx:]
        n_new = gen.shape[1]
        logits = self.model(full[:, :-1])[:, -n_new:].float()
        logp = torch.log_softmax(logits, -1).gather(-1, gen[..., None]).squeeze(-1)
        steps = torch.arange(n_new, device=gen.device)[None, :]
        mask = (steps < lengths[:, None]).float()
        mean = (logp * mask).sum(1) / mask.sum(1).clamp(min=1)
        scores = []
        for i in range(gen.shape[0]):
            t = decode(gen[i, : int(lengths[i])].tolist()).strip()
            odd = sum(1 for c in t if not (c.isalnum() or c in " .,!?'-:;")) / max(1, len(t))
            scores.append(float(mean[i]) - 3.0 * odd - (1.0 if len(t) < 2 else 0.0))
        return max(range(len(scores)), key=scores.__getitem__)


class Inbox:
    """Reads chat_in.jsonl and answers each new message once, appending to chat_out.jsonl."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir
        self.inp, self.out = run_dir / "chat_in.jsonl", run_dir / "chat_out.jsonl"
        self.pos = 0
        self.answered = set()
        if self.out.exists():
            for line in self.out.read_text(encoding="utf-8").splitlines():
                try:
                    self.answered.add(json.loads(line)["id"])
                except (ValueError, KeyError):
                    pass

    def waiting(self) -> bool:
        try:
            return self.inp.stat().st_size > self.pos
        except OSError:
            return False

    def serve(self, talker: Callable[[], Talker], source: str) -> int:
        if not self.waiting():
            return 0
        with open(self.inp, "rb") as f:
            f.seek(self.pos)
            data = f.read()
        cut = data.rfind(b"\n") + 1                      # only whole lines; a half-written one waits
        self.pos += cut
        n = 0
        for line in data[:cut].decode("utf-8", errors="replace").splitlines():
            try:
                req = json.loads(line)
            except ValueError:
                continue
            if req.get("id") in self.answered or time.time() - req.get("t", 0) > FRESH_S:
                continue
            res = talker().reply(str(req.get("message", ""))[:400], list(req.get("history", []))[-8:])
            res.update(id=req["id"], source=source, t=time.time())
            with open(self.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(res) + "\n")
            self.answered.add(req["id"])
            n += 1
        return n


# ---------------------------------------------------------------------------- the worker for a life at rest
def _load(run_dir: Path, device):
    """(model, name, memory, now(), age_months, source) from the last checkpoint, or the older saved mind."""
    from . import factors as fx
    from .memory import Episode, Memory
    from .trainer import merged
    cfg = merged(json.loads((run_dir / "config.json").read_text(encoding="utf-8-sig")))
    lean = cfg["profile"] in {"laptop_xl", "tiny_lean"}
    ck_path = run_dir / "resume.pt"
    if ck_path.exists():
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        py = pickle.loads(ck["py"])
        sh, state, age = ck["shape"], ck["model"], ck["age"]
        p, F, present, mem, speech = py["p"], py["F"], py["present"], py["mem"], py["speech"]
        p.upgrade(F, int(cfg["seed"]))
        rng = random.Random(age * 13 + 1)
        now = lambda: present.moment(p, F, rng, "talk", keep=False).line()
        name, source = speech.name, f"checkpoint at {age / 12:.1f} years"
        thought = lambda: p.conscious.line()
    else:
        ck = torch.load(run_dir / "mind.pt", map_location="cpu", weights_only=False)
        sh, state, age = ck["shape"], ck["model"], ck["age"]
        F = fx.sample(int(cfg["seed"]), cfg["factors"], cfg["timeline"])
        mem = Memory(F, int(cfg["seed"]))
        keep = {f.name for f in fields(Episode)}
        rows = json.loads((run_dir / "memory.json").read_text(encoding="utf-8")) if (run_dir / "memory.json").exists() else []
        mem.episodes = [Episode(**{k: v for k, v in r.items() if k in keep}) for r in rows]
        mem.names = {n for e in mem.episodes for n in e.who}
        y, m = divmod(age, 12)
        now = lambda: f"Now ({y}y{m}m): talking with someone."
        name, source = "Vega", f"saved mind at {age / 12:.1f} years (memories from memory.json)"
        thought = lambda: ""
    model = Mind(Shape(sh["d"], sh["layers"], sh["ctx"]))
    if lean:
        model = model.to(torch.bfloat16)
    model.load_state_dict(state)
    model = model.to(device).eval()
    model.thought = thought                # carried alongside, for the Talker
    return model, name, mem, now, age, source


def gpu_free(runs: Path) -> bool:
    """True when no life is training (on the GPU or anywhere): the 8 GB GPU is left to a training life."""
    from . import proc
    if not torch.cuda.is_available():
        return False
    for d in runs.iterdir() if runs.exists() else []:
        if (d / "pid").exists() and proc.alive(d):
            return False
    return True


def main() -> None:
    from . import proc
    import contextlib
    run_dir = Path(sys.argv[1])
    me = {"pid": os.getpid(), "created": proc.create_time(os.getpid())}
    (run_dir / "chat.pid").write_text(json.dumps(me), encoding="utf-8")
    device = torch.device("cuda" if gpu_free(run_dir.parent) else "cpu")
    model, name, mem, now, age, source = _load(run_dir, device)
    amp = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if device.type == "cuda" and \
        next(model.parameters()).dtype == torch.float32 else contextlib.nullcontext
    cfg_seed = int(json.loads((run_dir / "config.json").read_text(encoding="utf-8-sig")).get("seed", 1))
    talker = Talker(model, device, amp, name, mem, now, age, cfg_seed, thought=getattr(model, "thought", None))
    inbox = Inbox(run_dir)
    last = time.time()
    while time.time() - last < 600:
        if (run_dir / "pid").exists() and proc.alive(run_dir):   # his life has started again: it answers now
            break
        if inbox.serve(lambda: talker, f"{source}, on {device.type}"):
            last = time.time()
        time.sleep(0.3)
    (run_dir / "chat.pid").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
