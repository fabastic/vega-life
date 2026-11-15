"""Pronouns for the person whose life it is. The modules write their lines about "him"; for a woman's life `in_voice`
turns he/his/him/himself into she/her/her/herself. A line can also mention a man in his family ("Dad loses his job"),
so once such a man appears (not "his father", which is still hers), only "him" is swapped after it."""
from __future__ import annotations

import re

SWAP = {"he": "she", "his": "her", "him": "her", "himself": "herself"}
MALE_OTHERS = {"dad", "father", "brother", "son", "grandad", "grandpa", "grandfather", "uncle", "husband",
               "boyfriend", "stepfather", "nephew", "grandson", "man", "boy", "mr", "he's"}
WORD = re.compile(r"[A-Za-z']+|[^A-Za-z']+")


def in_voice(text: str, female: bool) -> str:
    if not female or not text:
        return text
    out, other, prev, kin = [], False, "", False
    for tok in WORD.findall(text):
        low = tok.lower()
        if tok.strip() and not tok[0].isalpha():
            prev = ""
        if low in MALE_OTHERS and (prev in ("his", "her") or (kin and prev in MALE_OTHERS)):
            kin = True                         # "his father", or "his father Dad": still her own relative
        elif low in MALE_OTHERS:
            other = True                       # a man is in the line: his "he", "his" and "himself" may be that man
        if low in SWAP and (not other or low == "him"):
            new = SWAP[low]
            tok = new.capitalize() if tok[0].isupper() else new
        out.append(tok)
        if tok[0].isalpha():
            prev = low
    return "".join(out)
