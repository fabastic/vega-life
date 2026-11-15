"""The overnight check: the whole test suite on the CPU, then the population check, written to one report.

    python tools/check_all.py            # writes runs/_checks/YYYY-MM-DD_HHMM.md (and latest.md)
    python tools/check_all.py --lives 400

The full suite takes hours when the CPU is shared with a life, so it is meant to be left running; it never touches
the GPU."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "_checks"


def run(args: list, env: dict) -> tuple:
    t = time.time()
    r = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, r.stdout + r.stderr, time.time() - t


def main() -> None:
    lives = int(sys.argv[sys.argv.index("--lives") + 1]) if "--lives" in sys.argv else 400
    env = dict(os.environ, VEGA_DEVICE="cpu", PYTHONIOENCODING="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    code, out, secs = run([sys.executable, "-m", "pytest", "-q", "-rf", "--no-header", "-p", "no:cacheprovider"], env)
    summary = next((l for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed)", l)), "no summary")
    failed = [l for l in out.splitlines() if l.startswith("FAILED")]
    pcode, pout, psecs = run([sys.executable, str(ROOT / "tools" / "population.py"), str(lives)], env)
    pop = (ROOT / "runs" / "_population" / "report.md")
    md = [f"# Overnight check {stamp}", "",
          f"## Tests ({secs / 60:.0f} min)", "", f"**{summary.strip('= ')}**", ""]
    md += [f"- {l}" for l in failed] or ["All passed."]
    md += ["", f"## Population ({psecs / 60:.0f} min)", ""]
    md.append(pop.read_text(encoding="utf-8").split("\n", 2)[-1] if pcode == 0 and pop.exists()
              else "The population check failed:\n\n```\n" + pout[-2000:] + "\n```")
    if failed:
        md += ["", "## Test output (tail)", "", "```", out[-6000:], "```"]
    text = "\n".join(md) + "\n"
    (OUT / f"{stamp}.md").write_text(text, encoding="utf-8")
    (OUT / "latest.md").write_text(text, encoding="utf-8")
    print(text)
    sys.exit(1 if code or pcode else 0)


if __name__ == "__main__":
    main()
